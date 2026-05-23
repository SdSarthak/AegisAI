"""Transformer-based intent classifier for detecting prompt injection attempts."""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import torch
from sklearn.metrics import f1_score
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AdamW,
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

from . import guard_config as config
from .regex_rules import RegexFilter


MODEL_WEIGHT_FILENAMES = ("pytorch_model.bin", "model.safetensors")


@dataclass
class ClassificationResult:
    """Result of intent classification."""

    intent: str  # "benign", "suspicious", "malicious"
    confidence: float  # 0.0 to 1.0
    class_scores: Dict[str, float]  # Scores for each class


class PromptDataset(Dataset):
    """PyTorch Dataset for prompt classification."""

    def __init__(
        self, texts: List[str], labels: List[int], tokenizer, max_length: int = 128
    ):
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

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: Optional[str] = None,
        allow_untrained_fallback: bool = False,
    ):
        """
        Initialize classifier with a fine-tuned model for inference.

        In inference mode this never falls back to a fresh DeBERTa classification
        head, because that head is randomly initialized and produces unreliable
        decisions. Training code can set ``allow_untrained_fallback=True`` to
        intentionally bootstrap from the base model before fine-tuning.

        Args:
            model_path: Path to trained model directory. If None, auto-detects using config.
            device: Device to use ('cpu' or 'cuda'). Auto-detects GPU if None.
            allow_untrained_fallback: Permit loading the base model with a new
                classification head. Use only for training, never inference.
        """
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.intent_to_id = config.INTENT_TO_ID
        self.id_to_intent = config.ID_TO_INTENT

        if model_path is None:
            model_path = config.get_trained_model_path()

        self.model_path = model_path
        self.allow_untrained_fallback = allow_untrained_fallback
        self.model_source = "unknown"
        self._heuristic_filter = RegexFilter()

        if self._has_model_weights(model_path):
            print(f"[OK] Loading fine-tuned model from {model_path}")
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(model_path)
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    model_path
                )
                self.model_source = "fine_tuned"
                print("[OK] Model and tokenizer loaded successfully")
            except Exception as exc:
                print(f"[WARNING] Failed to load fine-tuned model: {exc}")
                if allow_untrained_fallback:
                    self._load_pretrained()
                else:
                    self._load_heuristic_fallback()
        else:
            print(f"[WARNING] Fine-tuned model weights not found at {model_path}")
            if allow_untrained_fallback:
                self._load_pretrained()
            else:
                self._load_heuristic_fallback()

        if self.model is not None:
            self.model.to(self.device)
            self.model.eval()

    @staticmethod
    def _has_model_weights(model_path: Optional[str]) -> bool:
        """Return True when a local model directory contains trained weights."""
        if not model_path or not os.path.isdir(model_path):
            return False
        return any(
            os.path.exists(os.path.join(model_path, filename))
            for filename in MODEL_WEIGHT_FILENAMES
        )

    def _load_pretrained(self):
        """Load base DeBERTa with a fresh head for training only."""
        print("[WARNING] Loading base DeBERTa v3 small with an untrained classifier head")
        model_name = "microsoft/deberta-v3-small"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name, num_labels=3
        )
        self.model_source = "untrained_base"

    def _load_heuristic_fallback(self):
        """Use deterministic rules when trained weights are unavailable."""
        self.tokenizer = None
        self.model = None
        self.model_source = "heuristic_fallback"
        print("[WARNING] Using deterministic heuristic classifier fallback")

    def _classify_with_heuristics(self, prompt: str) -> ClassificationResult:
        """Classify using the regex risk signal instead of random ML weights."""
        regex_result = self._heuristic_filter.check(prompt)

        if regex_result.score >= 0.8:
            class_scores = {"benign": 0.05, "suspicious": 0.10, "malicious": 0.85}
            intent = "malicious"
        elif regex_result.score >= 0.5:
            class_scores = {"benign": 0.10, "suspicious": 0.75, "malicious": 0.15}
            intent = "suspicious"
        elif regex_result.flag:
            class_scores = {"benign": 0.35, "suspicious": 0.55, "malicious": 0.10}
            intent = "suspicious"
        else:
            class_scores = {"benign": 0.90, "suspicious": 0.08, "malicious": 0.02}
            intent = "benign"

        return ClassificationResult(
            intent=intent,
            confidence=class_scores[intent],
            class_scores=class_scores,
        )

    def classify(self, prompt: str) -> ClassificationResult:
        """
        Classify a prompt's intent.

        Args:
            prompt: Prompt to classify

        Returns:
            ClassificationResult with intent, confidence, and class scores
        """
        if self.model is None:
            return self._classify_with_heuristics(prompt)

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

        predicted_id = np.argmax(probabilities)
        predicted_intent = self.id_to_intent[predicted_id]
        confidence = float(probabilities[predicted_id])

        class_scores = {
            self.id_to_intent[i]: float(probabilities[i])
            for i in range(len(probabilities))
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
        if self.model is None or self.tokenizer is None:
            raise RuntimeError(
                "Training requires a transformer model. Initialize with "
                "allow_untrained_fallback=True to bootstrap from DeBERTa."
            )

        train_label_ids = [self.intent_to_id[label] for label in train_labels]
        val_label_ids = [self.intent_to_id[label] for label in val_labels]

        train_dataset = PromptDataset(train_texts, train_label_ids, self.tokenizer)
        val_dataset = PromptDataset(val_texts, val_label_ids, self.tokenizer)

        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size)

        optimizer = AdamW(self.model.parameters(), lr=learning_rate)
        total_steps = len(train_loader) * epochs
        scheduler = get_linear_schedule_with_warmup(
            optimizer, num_warmup_steps=0, num_training_steps=total_steps
        )

        self.model.train()
        metrics = {"train_loss": [], "val_accuracy": [], "val_f1": []}

        for epoch in range(epochs):
            print(f"\nEpoch {epoch + 1}/{epochs}")

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

            self.model.eval()
            val_preds = []
            val_true = []

            with torch.no_grad():
                for batch in val_loader:
                    input_ids = batch["input_ids"].to(self.device)
                    attention_mask = batch["attention_mask"].to(self.device)
                    labels = batch["labels"].to(self.device)

                    outputs = self.model(
                        input_ids=input_ids, attention_mask=attention_mask
                    )
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

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            self.model.save_pretrained(output_dir)
            self.tokenizer.save_pretrained(output_dir)
            print(f"\nModel saved to {output_dir}")

        return metrics
