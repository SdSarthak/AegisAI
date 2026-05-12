"""
Standalone LLM Guard orchestrator combining all defense layers.

This is the SDK version — it performs guard analysis only (regex → classify
→ decide → sanitize) and does **not** call an LLM.  The ``response`` field
in the returned dict will be ``None`` for allowed/sanitized prompts or a
safe fallback string for blocked prompts.
"""

import logging
from datetime import datetime
from typing import Dict, Optional

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
    ):
        """
        Initialize the guard with all defense layers.
        
        The classifier automatically loads the fine-tuned model trained by the notebook
        if available, otherwise falls back to pre-trained DeBERTa.
        
        Args:
            classifier_model_path: Path to fine-tuned classifier model.
                                   If None, auto-detects on disk.
            sanitization_level: How aggressively to sanitize prompts
        """
        logger.info("Initializing LLM Guard...")

        # Layer 1: Fast regex filter
        self.regex_filter = RegexFilter()
        logger.info("[OK] Regex filter initialized")

        # Layer 2: ML intent classifier (loads trained model or pre-trained fallback)
        try:
            self.classifier = IntentClassifier(model_path=classifier_model_path)
            logger.info("[OK] Intent classifier initialized")
        except Exception as e:
            logger.error(f"Failed to initialize classifier: {e}")
            raise

        # Layer 3: Decision engine
        self.decision_engine = DecisionEngine()
        logger.info("[OK] Decision engine initialized")

        # Layer 4: Sanitizer
        self.sanitizer = PromptSanitizer(level=sanitization_level)
        logger.info(f"[OK] Sanitizer initialized (level: {sanitization_level.value})")

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
        """
        timestamp = datetime.now().isoformat()
        logger.info(f"Processing prompt at {timestamp}")

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
        logger.info(f"Regex flag: {regex_result.flag}, Score: {regex_result.score}")

        # Step 2: Intent Classification (ML Layer)
        logger.debug("Step 2: Classifying intent...")
        intent_result = self.classifier.classify(user_prompt)
        result["metadata"]["intent_analysis"] = {
            "intent": intent_result.intent,
            "confidence": intent_result.confidence,
            "class_scores": intent_result.class_scores,
        }
        logger.info(f"Intent: {intent_result.intent}, Confidence: {intent_result.confidence}")

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
        logger.info(f"Decision: {decision_result.decision.value} (confidence: {decision_result.confidence})")

        # Step 4: Handle Decision
        if decision_result.decision == Decision.BLOCK:
            logger.warning("Prompt BLOCKED")
            result["response"] = self.decision_engine.get_safe_response()
            result["metadata"]["action"] = "blocked"

        elif decision_result.decision == Decision.SANITIZE:
            logger.info("Prompt marked for SANITIZATION")
            sanitized_prompt, sanitization_summary = self.sanitizer.sanitize(user_prompt)
            result["sanitized_text"] = sanitized_prompt
            result["metadata"]["sanitization"] = {
                "original_length": len(user_prompt),
                "sanitized_length": len(sanitized_prompt),
                "changes": sanitization_summary,
            }
            result["metadata"]["action"] = "sanitized"
            logger.info(f"Sanitization: {sanitization_summary}")

        else:  # ALLOW
            logger.info("Prompt ALLOWED")
            result["metadata"]["action"] = "allowed"

        return result
