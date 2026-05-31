"""
Guard model explainability (issue #77).

Wraps the fine-tuned DeBERTa intent classifier with SHAP and LIME to
produce per-token attribution scores. Auditors querying ``/guard/explain``
get back exactly which tokens drove the verdict, with character spans
into the original text so the frontend can highlight in place.

Why SHAP (primary) over LIME (fallback):

* SHAP's ``PartitionExplainer`` uses Shapley values over coalitions of
  tokens. The values respect Shapley efficiency — they approximately
  sum to ``predicted_proba - base_value`` — which means consumers can
  trust the magnitudes for ranking.
* LIME perturbs a bag-of-words representation and fits a local linear
  surrogate. Faster on long inputs, less faithful for transformers
  because the surrogate doesn't see attention. Kept as the
  ``method="lime"`` opt-in for inputs that exceed SHAP's reasonable
  latency budget.

The class loads model + tokenizer once via a module-level singleton.
Subsequent calls are nearly 0.5s to 5s of compute (CPU, 64-token prompts) — no
re-load cost.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

import numpy as np

from app.modules.guard import guard_config
from app.schemas.guard_explain import (
    ExplainMethod,
    ExplainResponse,
    TokenAttribution,
)

logger = logging.getLogger("aegisai.guard.explainer")

# Bump when the model artefact or label map changes. Surfaces in the
# explanation response so consumers can pin to a known classifier
# version for reproducibility.
MODEL_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Singleton with lazy init
# ---------------------------------------------------------------------------

_explainer_lock = threading.Lock()
_explainer_instance: Optional["GuardExplainer"] = None


def get_explainer() -> "GuardExplainer":
    """Return the process-wide explainer. Thread-safe lazy init."""
    global _explainer_instance
    if _explainer_instance is not None:
        return _explainer_instance
    with _explainer_lock:
        if _explainer_instance is None:
            _explainer_instance = GuardExplainer()
        return _explainer_instance


def reset_explainer() -> None:
    """Clear the singleton — used by tests that want a fresh instance."""
    global _explainer_instance
    _explainer_instance = None


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ExplainerUnavailable(RuntimeError):
    """Raised when no fine-tuned model is on disk and we won't synth-explain."""


class ExplainerTimeout(RuntimeError):
    """Raised when explanation exceeds the configured timeout budget."""


# ---------------------------------------------------------------------------
# GuardExplainer
# ---------------------------------------------------------------------------


class GuardExplainer:
    """SHAP/LIME wrapper around the Guard classifier."""

    def __init__(self) -> None:
        # Lazy import — heavy ML stack only loads when an explainer is
        # actually instantiated (not on module import).
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            from transformers import pipeline as hf_pipeline
        except ImportError as exc:
            raise ExplainerUnavailable(
                "Guard explainability requires the optional transformers "
                "dependency and a fine-tuned classifier model."
            ) from exc

        model_path = guard_config.CLASSIFIER_MODEL_PATH

        if not self._has_trained_weights(model_path):
            raise ExplainerUnavailable(
                "No fine-tuned Guard classifier found at "
                f"{model_path}. Explainability requires a real model — "
                "the heuristic fallback used by /guard/scan can't produce "
                "meaningful Shapley values."
            )

        logger.info("guard.explainer.loading", extra={"model_path": model_path})
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.model.eval()

        # transformers pipeline gives us .predict() returning per-class
        # probabilities in the shape SHAP/LIME expect.
        self._pipeline = hf_pipeline(
            "text-classification",
            model=self.model,
            tokenizer=self.tokenizer,
            top_k=None,  # all scores, sorted desc
            function_to_apply="softmax",
        )

        # Resolve label ids (the model may not know human-readable names).
        # Try id2label first; fall back to the order guard_config defines.
        id2label = getattr(self.model.config, "id2label", None) or {}
        if id2label and all(isinstance(v, str) for v in id2label.values()):
            # Some checkpoints store id2label as {0: "LABEL_0", ...}; replace
            # those with the canonical labels.
            if all(v.startswith("LABEL_") for v in id2label.values()):
                self.labels = ["benign", "suspicious", "malicious"]
            else:
                self.labels = [id2label[i] for i in sorted(id2label.keys())]
        else:
            self.labels = ["benign", "suspicious", "malicious"]

        logger.info(
            "guard.explainer.ready",
            extra={"labels": self.labels, "version": MODEL_VERSION},
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def explain(
        self,
        text: str,
        method: ExplainMethod = "shap",
        max_evals: int = 200,
    ) -> ExplainResponse:
        if not text.strip():
            raise ValueError("text must not be empty or whitespace-only")

        started = time.perf_counter()
        if method == "shap":
            payload = self._explain_shap(text, max_evals=max_evals)
        elif method == "lime":
            payload = self._explain_lime(text, num_samples=max_evals)
        else:  # pragma: no cover - pydantic validation catches this
            raise ValueError(f"unknown method: {method}")

        return ExplainResponse(
            method=method,
            model_version=MODEL_VERSION,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            **payload,
        )

    # ------------------------------------------------------------------
    # SHAP path
    # ------------------------------------------------------------------

    def _explain_shap(self, text: str, max_evals: int) -> dict[str, Any]:
        import shap

        # Predict first so we know which class we're explaining.
        predicted_label, predicted_proba, predicted_idx = self._predict(text)

        # Partition explainer with a Text masker keyed on our tokenizer.
        masker = shap.maskers.Text(self.tokenizer)
        explainer = shap.Explainer(self._pipeline, masker, output_names=self.labels)
        shap_values = explainer([text], max_evals=max_evals, silent=True)

        # shap_values.values has shape (n_samples=1, n_tokens, n_classes).
        # Pick the predicted class's column.
        per_token = np.asarray(shap_values.values[0])[:, predicted_idx]
        base_value = float(shap_values.base_values[0][predicted_idx])
        raw_tokens = list(shap_values.data[0])

        tokens = self._build_token_rows(text, raw_tokens, per_token)
        return {
            "predicted_label": predicted_label,
            "predicted_proba": predicted_proba,
            "base_value": base_value,
            "tokens": tokens,
        }

    # ------------------------------------------------------------------
    # LIME path
    # ------------------------------------------------------------------

    def _explain_lime(self, text: str, num_samples: int) -> dict[str, Any]:
        from lime.lime_text import LimeTextExplainer

        predicted_label, predicted_proba, predicted_idx = self._predict(text)

        def predict_proba(texts: list[str]) -> np.ndarray:
            outputs = self._pipeline(texts)
            # outputs is List[List[{"label":..., "score":...}]]
            rows = []
            for output in outputs:
                row = [0.0] * len(self.labels)
                for entry in output:
                    label = entry["label"]
                    if label in self.labels:
                        row[self.labels.index(label)] = float(entry["score"])
                rows.append(row)
            return np.asarray(rows)

        explainer = LimeTextExplainer(class_names=self.labels)
        explanation = explainer.explain_instance(
            text,
            predict_proba,
            num_features=64,
            num_samples=max(num_samples, 50),
            labels=[predicted_idx],
        )

        # LIME yields a list of (word, weight) for the explained class.
        word_to_weight = {
            word: float(weight)
            for word, weight in explanation.as_list(label=predicted_idx)
        }

        # Use the tokenizer's offset mapping to anchor to char spans.
        rows = self._tokenize_with_offsets(text)
        tokens: list[TokenAttribution] = []
        for token, span in rows:
            # LIME's "word" is the raw word; match on the substring at span.
            substring = text[span[0] : span[1]]
            attribution = word_to_weight.get(substring, word_to_weight.get(token, 0.0))
            tokens.append(
                TokenAttribution(
                    token=token, attribution=attribution, char_span=span
                )
            )

        return {
            "predicted_label": predicted_label,
            "predicted_proba": predicted_proba,
            # LIME doesn't produce a base value; use predicted_proba minus
            # the sum of attributions as a best-effort approximation.
            "base_value": float(
                predicted_proba - sum(t.attribution for t in tokens)
            ),
            "tokens": tokens,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _predict(self, text: str) -> tuple[str, float, int]:
        """Return (predicted_label, predicted_proba, predicted_idx)."""
        outputs = self._pipeline([text])
        scores = {entry["label"]: entry["score"] for entry in outputs[0]}
        predicted_label = max(scores, key=scores.get)
        predicted_proba = float(scores[predicted_label])
        if predicted_label not in self.labels:
            # The pipeline returned a label string we didn't expect — fall
            # back to argmax over our canonical order so callers see a
            # known class.
            predicted_label = self.labels[0]
        predicted_idx = self.labels.index(predicted_label)
        return predicted_label, predicted_proba, predicted_idx

    def _tokenize_with_offsets(self, text: str) -> list[tuple[str, tuple[int, int]]]:
        """Tokenize with character offsets, stripping special tokens."""
        enc = self.tokenizer(
            text,
            return_offsets_mapping=True,
            truncation=True,
            max_length=256,
            add_special_tokens=False,
        )
        offsets = enc["offset_mapping"]
        ids = enc["input_ids"]
        out: list[tuple[str, tuple[int, int]]] = []
        for tok_id, (start, end) in zip(ids, offsets):
            if start == end:  # special tokens like [CLS]/[SEP] have (0,0)
                continue
            token = self.tokenizer.decode([tok_id]).strip()
            if not token:
                continue
            out.append((token, (int(start), int(end))))
        return out

    def _build_token_rows(
        self,
        text: str,
        raw_tokens: list[str],
        attributions: np.ndarray,
    ) -> list[TokenAttribution]:
        """Align SHAP's tokens with character spans into the original text.

        SHAP's ``maskers.Text`` returns tokens by walking through ``text``
        sequentially, so we can locate each token by greedy substring
        search starting from the last cursor.
        """
        rows: list[TokenAttribution] = []
        cursor = 0
        for raw_token, weight in zip(raw_tokens, attributions):
            token = str(raw_token)
            # SHAP sometimes includes empty / whitespace-only tokens at
            # the boundaries — they have zero attribution and contribute
            # nothing useful to the UI.
            if not token.strip():
                continue

            # Anchor: find token in text from cursor onwards. SHAP tokens
            # often include leading whitespace (BPE-style); strip for
            # match purposes then expand the span to cover what we found.
            search = token.lstrip()
            idx = text.find(search, cursor)
            if idx == -1:
                # Couldn't anchor; skip — better than reporting bogus span.
                continue

            span_start = idx
            span_end = idx + len(search)
            cursor = span_end

            rows.append(
                TokenAttribution(
                    token=token,
                    attribution=float(weight),
                    char_span=(span_start, span_end),
                )
            )
        return rows

    # ------------------------------------------------------------------
    @staticmethod
    def _has_trained_weights(model_path: str) -> bool:
        import os
        return any(
            os.path.exists(os.path.join(model_path, name))
            for name in ("pytorch_model.bin", "model.safetensors")
        )
