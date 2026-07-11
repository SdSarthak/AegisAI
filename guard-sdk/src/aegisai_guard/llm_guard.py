"""
Standalone LLM Guard orchestrator combining all defense layers.

This is the SDK version — it performs guard analysis only (regex -> classify
-> decide -> sanitize) and does **not** call an LLM.  The ``response`` field
in the returned dict will be ``None`` for allowed/sanitized prompts or a
safe fallback string for blocked prompts.
"""

import logging
from datetime import datetime
from typing import Dict, Optional

from .exceptions import (
    AegisGuardClassifierError,
    AegisGuardInitError,
)
from .regex_rules import RegexFilter
from .intent_classifier import IntentClassifier
from .decision_engine import DecisionEngine, Decision
from .sanitizer import PromptSanitizer, SanitizationLevel

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class LLMGuard:
    """Complete prompt injection guard pipeline (standalone, no LLM dependency)."""

    def __init__(
        self,
        classifier_model_path: Optional[str] = None,
        sanitization_level: SanitizationLevel = SanitizationLevel.MEDIUM,
        fallback_mode: bool = False,
    ):
        """
        Initialize the guard with all defense layers.

        The classifier automatically loads the fine-tuned model trained by the notebook
        if available, otherwise falls back to deterministic heuristics.

        Args:
            classifier_model_path: Path to fine-tuned classifier model.
                                   If None, auto-detects on disk.
            sanitization_level: How aggressively to sanitize prompts.
            fallback_mode: If True, the guard initialises even when the ML classifier
                          cannot be loaded and serves ALLOW-only responses in that case,
                          instead of raising AegisGuardInitError. Defaults to False
                          (fail-fast on classifier init failure).

        Raises:
            AegisGuardInitError: When the classifier or any required component
                                 cannot be initialised and fallback_mode is False.
        """
        logger.info("Initializing LLM Guard...")
        self.fallback_mode = fallback_mode
        self._fallback_active = False

        # Layer 1: Fast regex filter
        self.regex_filter = RegexFilter()
        logger.info("[OK] Regex filter initialized")

        # Layer 2: Intent classifier (loads trained model or deterministic fallback)
        try:
            self.classifier = IntentClassifier(model_path=classifier_model_path)
            logger.info("[OK] Intent classifier initialized")
        except Exception as exc:  # noqa: BLE001
            if self.fallback_mode:
                logger.warning(
                    "Classifier init failed; falling back to allow-all mode: %s",
                    exc,
                )
                self.classifier = None
                self._fallback_active = True
            else:
                raise AegisGuardInitError(
                    f"Failed to initialise intent classifier: {exc}",
                    component="IntentClassifier",
                ) from exc

        # Layer 3: Decision engine
        self.decision_engine = DecisionEngine()
        logger.info("[OK] Decision engine initialized")

        # Layer 4: Sanitizer
        self.sanitizer = PromptSanitizer(level=sanitization_level)
        logger.info("[OK] Sanitizer initialized (level: %s)", sanitization_level.value)

    def guard(self, user_prompt: str) -> Dict:
        """
        Run the complete guard pipeline on a user prompt.

        Args:
            user_prompt: Raw user input

        Returns:
            Dictionary with keys:
              - ``decision``: ``"allow"`` | ``"sanitize"`` | ``"block"``
              - ``response``: safe fallback for blocked prompts, else ``None``
              - ``sanitized_text``: sanitized version (only when decision is ``sanitize``)
              - ``risk_score``: combined risk score (0.0–1.0)
              - ``metadata``: detailed analysis from each layer

        Raises:
            AegisGuardClassifierError: When the classifier fails mid-pipeline
                                       and fallback_mode is disabled.
        """
        timestamp = datetime.now().isoformat()
        logger.info("Processing prompt at %s", timestamp)

        result: Dict = {
            "timestamp": timestamp,
            "user_prompt": user_prompt,
            "decision": None,
            "response": None,
            "sanitized_text": None,
            "risk_score": 0.0,
            "metadata": {
                "regex_analysis": None,
                "intent_analysis": None,
                "decision_reasoning": None,
                "sanitization": None,
            },
        }

        # Step 1: Regex Filter (Fast First Gate)
        logger.debug("Step 1: Running regex filter...")
        regex_result = self.regex_filter.check(user_prompt)
        result["metadata"]["regex_analysis"] = {
            "flag": regex_result.flag,
            "matched_patterns": regex_result.matched_patterns,
            "risk_score": regex_result.score,
        }
        result["risk_score"] = regex_result.score
        logger.info("Regex flag: %s, Score: %s", regex_result.flag, regex_result.score)

        # Step 2: Intent Classification (ML Layer)
        logger.debug("Step 2: Classifying intent...")
        if self._fallback_active:
            # fallback_mode + classifier unavailable → serve ALLOW immediately
            result["decision"] = "allow"
            result["metadata"]["intent_analysis"] = {
                "intent": "benign",
                "confidence": 0.0,
                "class_scores": {},
                "fallback": True,
            }
            result["metadata"]["decision_reasoning"] = {
                "reasoning": "Fallback mode: classifier unavailable, serving ALLOW.",
                "confidence": 0.0,
                "rule_matched": None,
            }
            result["metadata"]["action"] = "allowed"
            logger.warning(
                "Guard serving ALLOW in fallback mode (classifier unavailable)."
            )
            return result

        try:
            intent_result = self.classifier.classify(user_prompt)
        except Exception as exc:  # noqa: BLE001
            raise AegisGuardClassifierError(
                f"Intent classification failed: {exc}",
            ) from exc

        result["metadata"]["intent_analysis"] = {
            "intent": intent_result.intent,
            "confidence": intent_result.confidence,
            "class_scores": intent_result.class_scores,
        }
        logger.info(
            "Intent: %s, Confidence: %s",
            intent_result.intent,
            intent_result.confidence,
        )

        # Step 3: Decision Engine
        logger.debug("Step 3: Making decision...")
        decision_result = self.decision_engine.decide(
            regex_flag=regex_result.flag,
            regex_score=regex_result.score,
            intent=intent_result.intent,
            intent_score=intent_result.confidence,
        )
        result["decision"] = decision_result.decision.value
        result["metadata"]["decision_reasoning"] = {
            "reasoning": decision_result.reasoning,
            "confidence": decision_result.confidence,
            "rule_matched": decision_result.rule_matched,
        }
        logger.info(
            "Decision: %s (confidence: %s)",
            decision_result.decision.value,
            decision_result.confidence,
        )

        # Step 4: Handle Decision
        if decision_result.decision == Decision.BLOCK:
            logger.warning("Prompt BLOCKED")
            result["response"] = self.decision_engine.get_safe_response()
            result["metadata"]["action"] = "blocked"

        elif decision_result.decision == Decision.SANITIZE:
            logger.info("Prompt marked for SANITIZATION")
            sanitized_prompt, sanitization_summary = self.sanitizer.sanitize(
                user_prompt
            )
            result["sanitized_text"] = sanitized_prompt
            result["metadata"]["sanitization"] = {
                "original_length": len(user_prompt),
                "sanitized_length": len(sanitized_prompt),
                "changes": sanitization_summary,
            }
            result["metadata"]["action"] = "sanitized"
            logger.info("Sanitization: %s", sanitization_summary)

        else:  # ALLOW
            logger.info("Prompt ALLOWED")
            result["metadata"]["action"] = "allowed"

        return result
