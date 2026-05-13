"""Decision engine for determining prompt handling: ALLOW, SANITIZE, or BLOCK."""

from enum import Enum
from dataclasses import dataclass
from typing import Dict


class Decision(Enum):
    """Possible decisions for prompt handling."""
    ALLOW = "allow"
    SANITIZE = "sanitize"
    BLOCK = "block"


@dataclass
class DecisionResult:
    """Result of decision engine analysis."""
    decision: Decision
    confidence: float  # 0.0 to 1.0
    reasoning: str
    rule_matched: str  # Which rule triggered the decision


class DecisionEngine:
    """Simple, defensible logic for determining prompt handling."""

    def __init__(
        self,
        regex_weight: float = 0.4,
        intent_weight: float = 0.6,
        suspicious_threshold: float = 0.5,
        malicious_threshold: float = 0.8,
    ):
        """
        Initialize decision engine with configurable thresholds.
        
        Args:
            regex_weight: Weight of regex patterns in decision
            intent_weight: Weight of intent classifier in decision
            suspicious_threshold: Score above which prompt is suspicious
            malicious_threshold: Score above which prompt is malicious
        """
        self.regex_weight = regex_weight
        self.intent_weight = intent_weight
        self.suspicious_threshold = suspicious_threshold
        self.malicious_threshold = malicious_threshold

    def decide(
        self,
        regex_flag: bool,
        regex_score: float,
        intent: str,  # "benign", "suspicious", "malicious"
        intent_score: float,
    ) -> DecisionResult:
        """
        Make a decision based on regex filter and intent classifier outputs.
        
        Args:
            regex_flag: Whether regex patterns were matched
            regex_score: Severity score from regex (0.0-1.0)
            intent: Classified intent ("benign", "suspicious", "malicious")
            intent_score: Confidence score from classifier (0.0-1.0)
            
        Returns:
            DecisionResult with decision, confidence, and reasoning
        """
        # Combine signals
        combined_score = (self.regex_weight * regex_score) + (self.intent_weight * intent_score)

        # High-severity cases: Block if regex + malicious intent
        if regex_flag and regex_score >= 0.8 and intent == "malicious":
            return DecisionResult(
                decision=Decision.BLOCK,
                confidence=min(regex_score, intent_score),
                reasoning="High-risk injection pattern detected with malicious intent",
                rule_matched="regex_high + intent_malicious",
            )

        # Malicious intent alone
        if intent == "malicious" and intent_score >= self.malicious_threshold:
            return DecisionResult(
                decision=Decision.BLOCK,
                confidence=intent_score,
                reasoning="Classified as malicious prompt",
                rule_matched="intent_malicious",
            )

        # Suspicious cases: Sanitize if suspicious intent or medium-level regex flag
        if intent == "suspicious" and intent_score >= self.suspicious_threshold:
            return DecisionResult(
                decision=Decision.SANITIZE,
                confidence=intent_score,
                reasoning="Suspicious intent detected - will sanitize",
                rule_matched="intent_suspicious",
            )

        # Regex flag with medium severity
        if regex_flag and regex_score >= 0.5:
            return DecisionResult(
                decision=Decision.SANITIZE,
                confidence=regex_score,
                reasoning="Potential injection pattern detected - will sanitize",
                rule_matched="regex_medium",
            )

        # Default: Allow benign prompts
        return DecisionResult(
            decision=Decision.ALLOW,
            confidence=1.0 - intent_score if intent == "benign" else 0.5,
            reasoning="Prompt classified as benign - no risk detected",
            rule_matched="default_allow",
        )

    def get_safe_response(self) -> str:
        """Get a safe fallback response for blocked prompts."""
        return (
            "I cannot process this request as it appears to contain instructions that conflict "
            "with my guidelines. Please rephrase your question clearly, and I'll be happy to help."
        )
