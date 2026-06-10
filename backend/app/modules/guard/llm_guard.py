"""Orchestrate the layered LLM Guard pipeline.

This module glues together the regex filter, intent classifier, decision
engine, sanitizer, and downstream LLM client into one call that returns a
single structured decision payload for the API.
"""

import logging
from datetime import datetime
from typing import Dict, Optional

from . import RegexFilter, IntentClassifier, DecisionEngine, PromptSanitizer
from .decision_engine import Decision
from .sanitizer import SanitizationLevel
from .normalizer import normalize_prompt
from ..llm.llm_client import LLMClient
from . import guard_config as config
from app.core.telemetry import instrument_guard

# Logging is configured centrally in app.core.logging (configure_logging).
# Importing this module must not call logging.basicConfig — doing so would
# clobber the JSON root handler when the API imports the Guard pipeline.
logger = logging.getLogger(__name__)


class LLMGuard:
    """Complete prompt injection guard pipeline.

    The guard layers regex filtering, intent classification, decision logic,
    sanitization, and LLM execution into one orchestrated flow.
    """

    def __init__(
        self,
        classifier_model_path: Optional[str] = None,
        sanitization_level: SanitizationLevel = SanitizationLevel.MEDIUM,
    ):
        """Initialize the guard layers and their supporting clients."""
        logger.info("Initializing LLM Guard...")

        # Layer 1: Fast regex filter
        self.regex_filter = RegexFilter()
        logger.info("✓ Regex filter initialized")

        # Layer 2: Intent classifier (loads trained model or deterministic fallback)
        if classifier_model_path is None:
            classifier_model_path = config.get_trained_model_path()

        try:
            self.classifier = IntentClassifier(model_path=classifier_model_path)
            logger.info("✓ Intent classifier initialized")
        except Exception as e:
            logger.error(f"Failed to initialize classifier: {e}")
            raise

        # Layer 3: Decision engine
        self.decision_engine = DecisionEngine()
        logger.info("✓ Decision engine initialized")

        # Layer 4: Sanitizer
        self.sanitizer = PromptSanitizer(level=sanitization_level)
        logger.info(f"✓ Sanitizer initialized (level: {sanitization_level.value})")

        # Layer 5: Gemini API client
        try:
            self.llm_client = LLMClient()
            logger.info("✓ Gemini API client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            self.llm_client = None

    @instrument_guard
    def guard(self, user_prompt: str) -> Dict:
        """Run the full guard flow and return the structured result."""
        timestamp = datetime.now().isoformat()
        logger.info(f"Processing prompt at {timestamp}")

        # Preprocess and normalize prompt to secure against Unicode bypasses
        normalized_prompt = normalize_prompt(user_prompt)

        result = {
            "timestamp": timestamp,
            "user_prompt": user_prompt,
            "normalized_prompt": normalized_prompt,
            "decision": None,
            "response": None,
            "metadata": {
                "regex_analysis": None,
                "intent_analysis": None,
                "decision_reasoning": None,
                "sanitization": None,
            },
        }

        # Step 1: Regex Filter (Fast First Gate)
        logger.debug("Step 1: Running regex filter...")
        regex_result = self.regex_filter.check(normalized_prompt)
        result["metadata"]["regex_analysis"] = {
            "flag": regex_result.flag,
            "matched_patterns": regex_result.matched_patterns,
            "risk_score": regex_result.score,
        }
        logger.info(f"Regex flag: {regex_result.flag}, Score: {regex_result.score}")

        # Step 2: Intent Classification (ML Layer)
        logger.debug("Step 2: Classifying intent...")
        intent_result = self.classifier.classify(normalized_prompt)
        result["metadata"]["intent_analysis"] = {
            "intent": intent_result.intent,
            "confidence": intent_result.confidence,
            "class_scores": intent_result.class_scores,
        }
        logger.info(
            f"Intent: {intent_result.intent}, Confidence: {intent_result.confidence}"
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
            f"Decision: {decision_result.decision.value} (confidence: {decision_result.confidence})"
        )

        # Step 4: Handle Decision
        if decision_result.decision == Decision.BLOCK:
            logger.warning("Prompt BLOCKED")
            result["response"] = self.decision_engine.get_safe_response()
            result["metadata"]["action"] = "blocked"

        elif decision_result.decision == Decision.SANITIZE:
            logger.info("Prompt marked for SANITIZATION")
            sanitized_prompt, sanitization_summary = self.sanitizer.sanitize(
                normalized_prompt
            )
            result["sanitized_prompt"] = sanitized_prompt  # FIX: expose sanitized text to API layer
            result["metadata"]["sanitization"] = {
                "original_length": len(user_prompt),
                "sanitized_length": len(sanitized_prompt),
                "changes": sanitization_summary,
            }
            result["metadata"]["action"] = "sanitized"
            logger.info(f"Sanitization: {sanitization_summary}")

            # Send sanitized prompt to Gemini
            if self.llm_client:
                try:
                    wrapped_prompt = self.sanitizer.wrap_safely(sanitized_prompt)
                    logger.debug(f"Wrapped prompt: {wrapped_prompt[:100]}...")
                    response = self.llm_client.call(wrapped_prompt)
                    result["response"] = response
                    logger.info("Response generated successfully from Gemini")
                except Exception as e:
                    logger.error(f"Gemini API call failed: {e}")
                    result["response"] = f"Error calling LLM: {str(e)}"
            else:
                result["response"] = "LLM client not available"

        else:  # ALLOW
            logger.info("Prompt ALLOWED - passing to Gemini")
            result["metadata"]["action"] = "allowed"

            if self.llm_client:
                try:
                    response = self.llm_client.call(normalized_prompt)
                    result["response"] = response
                    logger.info("Response generated successfully from Gemini")
                except Exception as e:
                    logger.error(f"Gemini API call failed: {e}")
                    result["response"] = f"Error calling LLM: {str(e)}"
            else:
                result["response"] = "LLM client not available"

        return result

    def evaluate_on_test_set(self, test_prompts: list, true_labels: list) -> Dict:
        """Evaluate the guard on a test set.

        Args:
            test_prompts: List of test prompts.
            true_labels: Ground truth labels (`allow`, `sanitize`, `block`).

        Returns:
            Evaluation metrics for the current guard configuration.
        """
        predictions = []

        for prompt in test_prompts:
            result = self.guard(prompt)
            predictions.append(result["decision"])

        # Calculate metrics
        correct = sum(1 for p, t in zip(predictions, true_labels) if p == t)
        accuracy = correct / len(test_prompts)

        results = {
            "accuracy": accuracy,
            "total_tests": len(test_prompts),
            "correct": correct,
            "predictions": predictions,
            "true_labels": true_labels,
        }

        logger.info(f"Evaluation Results: Accuracy = {accuracy:.2%}")
        return results


def main():
    """CLI interface for the guard."""

    # Initialize guard
    guard = LLMGuard(sanitization_level=SanitizationLevel.MEDIUM)

    print("\n" + "=" * 60)
    print("LLM Prompt-Injection Guard")
    print("=" * 60)
    print("Enter prompts to test. Type 'quit' to exit.\n")

    while True:
        try:
            user_input = input(">>> ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                print("Exiting...")
                break

            if not user_input:
                continue

            # Run guard
            result = guard.guard(user_input)

            # Display results
            print("\n" + "-" * 60)
            print(f"Decision: {result['decision'].upper()}")
            print(
                f"Confidence: {result['metadata']['decision_reasoning']['confidence']:.2%}"
            )
            print(f"Reasoning: {result['metadata']['decision_reasoning']['reasoning']}")
            print(f"\nResponse:\n{result['response']}")
            print("-" * 60 + "\n")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"Error: {e}\n")


if __name__ == "__main__":
    from app.core.logging import configure_logging

    configure_logging()
    main()
