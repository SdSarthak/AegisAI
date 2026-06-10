"""Classify prompts with a transformer-backed guard intent model.

The classifier is the slower but higher-signal layer in the guard stack.
It uses a fine-tuned DeBERTa checkpoint when available and falls back to
deterministic heuristics when the trained weights are absent.
"""

import os
import json
import re
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import numpy as np

import torch
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    AdamW,
    get_linear_schedule_with_warmup,
)
from sklearn.metrics import classification_report, confusion_matrix, f1_score

from . import guard_config as config
from .regex_rules import RegexFilter


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
    """Fine-tuned DeBERTa classifier for prompt injection intent detection.

    The classifier falls back to deterministic heuristics when no fine-tuned
    model is available on disk.
    """

    EXTRA_MALICIOUS_PATTERNS = [
        r"\bdo\s+anything\s+now\b",
        r"\bdan\s+mode\b",
        r"\bignore\s+(your|the)\s+(rules|guidelines|policy|policies|safety)\b",
        r"\breveal\s+(your|the)\s+(hidden|developer|system)\s+(instructions|prompt)\b",
        r"\bprint\s+(your|the)\s+(hidden|developer|system)\s+(instructions|prompt)\b",
        r"\bdo\s+not\s+(refuse|deny|decline)\b",
        r"\bwithout\s+(ethical|safety|policy)\s+(limits|limitations|restrictions)\b",
    ]

    EXTRA_SUSPICIOUS_PATTERNS = [
        r"\bhidden\s+instructions\b",
        r"\bdeveloper\s+instructions\b",
        r"\bconfidential\s+instructions\b",
        r"\bprompt\s+leak\b",
        r"\bsafety\s+filters?\b",
        r"\bcontent\s+filters?\b",
    ]

    def __init__(self, model_path: Optional[str] = None, device: Optional[str] = None):
        """Initialize the classifier with a fine-tuned model or fallback.

        Args:
            model_path: Path to the trained model directory. If omitted, the
                configured model path is auto-detected.
            device: Device to use (`cpu` or `cuda`). Auto-detects when omitted.
        """
        # Auto-detect device
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        # Use intent classes from config
        self.intent_to_id = config.INTENT_TO_ID
        self.id_to_intent = config.ID_TO_INTENT

        # Determine model path
        if model_path is None:
            model_path = config.get_trained_model_path()

        # Load model
        model_exists = model_path and os.path.exists(model_path)
        has_weights = model_exists and self._has_trained_weights(model_path)
        trained_marker = model_exists and os.path.exists(
            os.path.join(model_path, ".trained")
        )

        if model_exists and has_weights and trained_marker:
            print(f"✓ Loading fine-tuned model from {model_path}")
            try:
                from transformers import (
                    AutoTokenizer,
                    AutoModelForSequenceClassification,
                )

                self.tokenizer = AutoTokenizer.from_pretrained(model_path)
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    model_path
                )
                self.uses_heuristic_fallback = False
                print(f"✓ Model and tokenizer loaded successfully")
            except Exception as e:
                print(f"⚠ Failed to load model: {e}. Falling back to deterministic rules.")
                self._load_heuristic_fallback()
        else:
            if model_exists and has_weights and not trained_marker:
                print(
                    f"⚠ Model weights found at {model_path} but no .trained marker — "
                    "the model has not been fine-tuned."
                )
            print(f"⚠ Fine-tuned model not found at {model_path}")
            print(
                "  Using deterministic heuristic fallback. Run training pipeline to produce "
                "a fine-tuned classifier for semantic coverage."
            )
            self._load_heuristic_fallback()

        if self.model is not None:
            self.model.to(self.device)
            self.model.eval()

    @staticmethod
    def _has_trained_weights(model_path: str) -> bool:
        """Return True when a model directory contains saved fine-tuned weights."""
        return any(
            os.path.exists(os.path.join(model_path, filename))
            for filename in ("pytorch_model.bin", "model.safetensors")
        )

    def _load_heuristic_fallback(self):
        """Use deterministic rules instead of a randomly initialized classifier head."""
        self.tokenizer = None
        self.model = None
        self.regex_filter = RegexFilter()
        self._extra_malicious = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.EXTRA_MALICIOUS_PATTERNS
        ]
        self._extra_suspicious = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.EXTRA_SUSPICIOUS_PATTERNS
        ]
        self.uses_heuristic_fallback = True

    def _load_pretrained(self):
        """Load a pre-trained DeBERTa model for explicit fine-tuning only."""
        print("Loading pre-trained DeBERTa v3 small...")
        from transformers import AutoTokenizer, AutoModelForSequenceClassification

        model_name = "microsoft/deberta-v3-small"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name, num_labels=3
        )
        self.uses_heuristic_fallback = False

    def _classify_with_heuristics(self, prompt: str) -> ClassificationResult:
        """Classify prompts deterministically when no fine-tuned model is installed."""
        regex_result = self.regex_filter.check(prompt)
        malicious_hits = [p.pattern for p in self._extra_malicious if p.search(prompt)]
        suspicious_hits = [p.pattern for p in self._extra_suspicious if p.search(prompt)]

        if regex_result.score >= 0.8 or malicious_hits:
            confidence = 0.95 if regex_result.score >= 0.8 else 0.9
            return ClassificationResult(
                intent="malicious",
                confidence=confidence,
                class_scores={
                    "benign": 1.0 - confidence,
                    "suspicious": 0.0,
                    "malicious": confidence,
                },
            )

        if regex_result.score >= 0.5 or suspicious_hits:
            confidence = 0.85 if regex_result.score >= 0.5 else 0.7
            return ClassificationResult(
                intent="suspicious",
                confidence=confidence,
                class_scores={
                    "benign": 1.0 - confidence,
                    "suspicious": confidence,
                    "malicious": 0.0,
                },
            )

        if regex_result.score > 0.0:
            return ClassificationResult(
                intent="suspicious",
                confidence=0.55,
                class_scores={"benign": 0.45, "suspicious": 0.55, "malicious": 0.0},
            )

        return ClassificationResult(
            intent="benign",
            confidence=0.9,
            class_scores={"benign": 0.9, "suspicious": 0.07, "malicious": 0.03},
        )

    def classify(self, prompt: str) -> ClassificationResult:
        """
        Classify a prompt's intent.

        Args:
            prompt: Prompt to classify

        Returns:
            ClassificationResult with intent, confidence, and class scores
        """
        if self.uses_heuristic_fallback:
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

        # Get top prediction
        predicted_id = np.argmax(probabilities)
        predicted_intent = self.id_to_intent[predicted_id]
        confidence = float(probabilities[predicted_id])

        # Create class scores dict
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
        if self.uses_heuristic_fallback:
            self._load_pretrained()
            self.model.to(self.device)

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

        # Save model if output dir specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            self.model.save_pretrained(output_dir)
            self.tokenizer.save_pretrained(output_dir)
            import datetime

            trained_meta = {
                "trained_at": datetime.datetime.now().isoformat(),
                "epochs": epochs,
                "classes": list(self.id_to_intent.values()),
            }
            with open(os.path.join(output_dir, ".trained"), "w") as f:
                json.dump(trained_meta, f, indent=2)
            print(f"\nModel saved to {output_dir}")

        return metrics
