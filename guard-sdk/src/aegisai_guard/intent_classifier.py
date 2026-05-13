"""Transformer-based intent classifier for detecting prompt injection attempts."""

import os
import json
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from pathlib import Path
import numpy as np

import torch
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    AdamW,
    get_linear_schedule_with_warmup,
)

# ---------------------------------------------------------------------------
# Constants (inlined from backend guard_config to keep SDK self-contained)
# ---------------------------------------------------------------------------
INTENT_CLASSES = ["benign", "suspicious", "malicious"]
INTENT_TO_ID = {"benign": 0, "suspicious": 1, "malicious": 2}
ID_TO_INTENT = {v: k for k, v in INTENT_TO_ID.items()}


def _detect_model_path() -> str:
    """
    Auto-detect a trained model on disk.

    Checks (in order):
      1. ``CLASSIFIER_MODEL_PATH`` environment variable
      2. ``./models/intent_classifier`` relative to this file
      3. ``./intent_classifier`` in the current working directory

    Returns the first path that contains ``pytorch_model.bin``, or the
    env-var path (which will trigger a pre-trained fallback later).
    """
    env_path = os.getenv("CLASSIFIER_MODEL_PATH", "")
    if env_path and os.path.exists(env_path):
        return env_path

    candidates = [
        str(Path(__file__).parent / "models" / "intent_classifier"),
        "./intent_classifier",
    ]
    for path in candidates:
        if os.path.exists(path) and os.path.exists(os.path.join(path, "pytorch_model.bin")):
            return path

    return env_path or str(Path(__file__).parent / "models" / "intent_classifier")


@dataclass
class ClassificationResult:
    """Result of intent classification."""
    intent: str  # "benign", "suspicious", "malicious"
    confidence: float  # 0.0 to 1.0
    class_scores: Dict[str, float]  # Scores for each class


class PromptDataset(Dataset):
    """PyTorch Dataset for prompt classification."""

    def __init__(self, texts: List[str], labels: List[int], tokenizer, max_length: int = 128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = self.texts[idx]
        label = self.labels[idx]

        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "labels": torch.tensor(label, dtype=torch.long),
        }


class IntentClassifier:
    """Fine-tuned DeBERTa classifier for prompt injection intent detection."""

    def __init__(self, model_path: Optional[str] = None, device: Optional[str] = None):
        """
        Initialize classifier with fine-tuned or pre-trained model.
        
        Tries to load fine-tuned model first, falls back to pre-trained DeBERTa-v3-small.
        
        Args:
            model_path: Path to trained model directory. If None, auto-detects.
            device: Device to use ('cpu' or 'cuda'). Auto-detects GPU if None.
        """
        # Auto-detect device
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        
        # Use intent classes
        self.intent_to_id = INTENT_TO_ID
        self.id_to_intent = ID_TO_INTENT
        
        # Determine model path
        if model_path is None:
            model_path = _detect_model_path()
        
        # Load tokenizer from model directory
        tokenizer_path = model_path
        
        # Load model
        model_exists = model_path and os.path.exists(model_path)
        has_weights = model_exists and os.path.exists(os.path.join(model_path, "pytorch_model.bin"))
        
        if model_exists and has_weights:
            print(f"[OK] Loading fine-tuned model from {model_path}")
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
                self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
                print(f"[OK] Model and tokenizer loaded successfully")
            except Exception as e:
                print(f"[WARNING] Failed to load model: {e}. Falling back to pre-trained.")
                self._load_pretrained()
        else:
            print(f"[WARNING] Fine-tuned model not found at {model_path}")
            print(f"  Using pre-trained DeBERTa (train with notebook for better results)")
            self._load_pretrained()
        
        self.model.to(self.device)
        self.model.eval()
    
    def _load_pretrained(self):
        """Load pre-trained DeBERTa model."""
        print("Loading pre-trained DeBERTa v3 small...")
        model_name = "microsoft/deberta-v3-small"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name, num_labels=3
        )

    def classify(self, prompt: str) -> ClassificationResult:
        """
        Classify a prompt's intent.
        
        Args:
            prompt: Prompt to classify
            
        Returns:
            ClassificationResult with intent, confidence, and class scores
        """
        inputs = self.tokenizer(
            prompt,
            max_length=128,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=1)[0].cpu().numpy()

        # Get top prediction
        predicted_id = np.argmax(probabilities)
        predicted_intent = self.id_to_intent[predicted_id]
        confidence = float(probabilities[predicted_id])

        # Create class scores dict
        class_scores = {
            self.id_to_intent[i]: float(probabilities[i]) for i in range(len(probabilities))
        }

        return ClassificationResult(
            intent=predicted_intent, confidence=confidence, class_scores=class_scores
        )

    def batch_classify(self, prompts: List[str]) -> List[ClassificationResult]:
        """
        Classify multiple prompts at once.
        
        Args:
            prompts: List of prompts to classify
            
        Returns:
            List of ClassificationResult objects
        """
        results = []
        for prompt in prompts:
            results.append(self.classify(prompt))
        return results

    def train(
        self,
        train_texts: List[str],
        train_labels: List[str],
        val_texts: List[str],
        val_labels: List[str],
        epochs: int = 3,
        batch_size: int = 16,
        learning_rate: float = 2e-5,
        output_dir: str = None,
    ) -> Dict:
        """
        Fine-tune the model on labeled prompt data.
        
        Args:
            train_texts: Training prompt texts
            train_labels: Training labels ("benign", "suspicious", "malicious")
            val_texts: Validation prompt texts
            val_labels: Validation labels
            epochs: Number of training epochs
            batch_size: Batch size for training
            learning_rate: Learning rate for optimizer
            output_dir: Directory to save fine-tuned model
            
        Returns:
            Dictionary with training metrics
        """
        from sklearn.metrics import f1_score  # optional dep, only needed for training

        # Convert labels to ids
        train_label_ids = [self.intent_to_id[label] for label in train_labels]
        val_label_ids = [self.intent_to_id[label] for label in val_labels]

        # Create datasets and dataloaders
        train_dataset = PromptDataset(train_texts, train_label_ids, self.tokenizer)
        val_dataset = PromptDataset(val_texts, val_label_ids, self.tokenizer)

        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size)

        # Setup optimizer and scheduler
        optimizer = AdamW(self.model.parameters(), lr=learning_rate)
        total_steps = len(train_loader) * epochs
        scheduler = get_linear_schedule_with_warmup(
            optimizer, num_warmup_steps=0, num_training_steps=total_steps
        )

        # Training loop
        self.model.train()
        metrics = {"train_loss": [], "val_accuracy": [], "val_f1": []}

        for epoch in range(epochs):
            print(f"\nEpoch {epoch + 1}/{epochs}")

            # Training
            total_loss = 0
            for batch in train_loader:
                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)
                labels = batch["labels"].to(self.device)

                optimizer.zero_grad()
                outputs = self.model(
                    input_ids=input_ids, attention_mask=attention_mask, labels=labels
                )
                loss = outputs.loss
                loss.backward()
                optimizer.step()
                scheduler.step()

                total_loss += loss.item()

            avg_loss = total_loss / len(train_loader)
            metrics["train_loss"].append(avg_loss)
            print(f"Training loss: {avg_loss:.4f}")

            # Validation
            self.model.eval()
            val_preds = []
            val_true = []

            with torch.no_grad():
                for batch in val_loader:
                    input_ids = batch["input_ids"].to(self.device)
                    attention_mask = batch["attention_mask"].to(self.device)
                    labels = batch["labels"].to(self.device)

                    outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
                    logits = outputs.logits
                    preds = torch.argmax(logits, dim=1)

                    val_preds.extend(preds.cpu().numpy())
                    val_true.extend(labels.cpu().numpy())

            accuracy = (np.array(val_preds) == np.array(val_true)).mean()
            f1 = f1_score(val_true, val_preds, average="weighted", zero_division=0)

            metrics["val_accuracy"].append(accuracy)
            metrics["val_f1"].append(f1)

            print(f"Validation accuracy: {accuracy:.4f}, F1: {f1:.4f}")

            self.model.train()

        # Save model if output dir specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            self.model.save_pretrained(output_dir)
            self.tokenizer.save_pretrained(output_dir)
            print(f"\nModel saved to {output_dir}")

        return metrics
