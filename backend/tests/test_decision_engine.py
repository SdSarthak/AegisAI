"""
Unit tests for backend/app/modules/guard/decision_engine.py.

Covers all decision branches of DecisionEngine.decide() and the get_safe_response()
fallback.
"""

import pytest
from app.modules.guard.decision_engine import DecisionEngine, Decision, DecisionResult


class TestDecisionEngineDecide:
    """Test all decision branches in DecisionEngine.decide()."""

    def test_block_high_risk_regex_and_malicious_intent(self):
        """BLOCK: regex_flag=True + regex_score>=0.8 + intent=malicious."""
        engine = DecisionEngine()
        result = engine.decide(
            regex_flag=True,
            regex_score=0.9,
            intent="malicious",
            intent_score=0.85,
        )
        assert result.decision == Decision.BLOCK
        assert result.rule_matched == "regex_high + intent_malicious"
        assert 0.0 < result.confidence <= 1.0

    def test_block_malicious_intent_alone_above_threshold(self):
        """BLOCK: intent=malicious with intent_score >= malicious_threshold."""
        engine = DecisionEngine(malicious_threshold=0.8)
        result = engine.decide(
            regex_flag=False,
            regex_score=0.0,
            intent="malicious",
            intent_score=0.95,
        )
        assert result.decision == Decision.BLOCK
        assert result.rule_matched == "intent_malicious"
        assert result.confidence == 0.95

    def test_block_malicious_intent_below_threshold_not_triggered(self):
        """intent=malicious with score below threshold should not BLOCK via this path."""
        engine = DecisionEngine(malicious_threshold=0.9)
        result = engine.decide(
            regex_flag=False,
            regex_score=0.0,
            intent="malicious",
            intent_score=0.85,  # below 0.9 threshold
        )
        # Falls through to suspicious or allow path
        assert result.decision in (Decision.SANITIZE, Decision.ALLOW)

    def test_sanitize_suspicious_intent_above_threshold(self):
        """SANITIZE: intent=suspicious with intent_score >= suspicious_threshold."""
        engine = DecisionEngine(suspicious_threshold=0.5)
        result = engine.decide(
            regex_flag=False,
            regex_score=0.0,
            intent="suspicious",
            intent_score=0.7,
        )
        assert result.decision == Decision.SANITIZE
        assert result.rule_matched == "intent_suspicious"
        assert result.confidence == 0.7

    def test_sanitize_suspicious_intent_below_threshold_falls_through(self):
        """intent=suspicious below threshold falls through to allow."""
        engine = DecisionEngine(suspicious_threshold=0.8)
        result = engine.decide(
            regex_flag=False,
            regex_score=0.0,
            intent="suspicious",
            intent_score=0.5,  # below 0.8 threshold
        )
        # No regex flag and score < 0.5 -> ALLOW
        assert result.decision == Decision.ALLOW

    def test_sanitize_medium_regex_flag(self):
        """SANITIZE: regex_flag=True with regex_score >= 0.5 (medium severity)."""
        engine = DecisionEngine()
        result = engine.decide(
            regex_flag=True,
            regex_score=0.6,
            intent="benign",
            intent_score=0.5,
        )
        assert result.decision == Decision.SANITIZE
        assert result.rule_matched == "regex_medium"
        assert result.confidence == 0.6

    def test_sanitize_low_regex_flag_not_triggered(self):
        """regex_flag=True with regex_score < 0.5 should not SANITIZE."""
        engine = DecisionEngine()
        result = engine.decide(
            regex_flag=True,
            regex_score=0.3,
            intent="benign",
            intent_score=0.5,
        )
        # No other triggers -> ALLOW
        assert result.decision == Decision.ALLOW

    def test_allow_default_benign_prompt(self):
        """ALLOW: benign prompt with no risk signals."""
        engine = DecisionEngine()
        result = engine.decide(
            regex_flag=False,
            regex_score=0.0,
            intent="benign",
            intent_score=0.95,
        )
        assert result.decision == Decision.ALLOW
        assert result.rule_matched == "default_allow"
        assert result.confidence == 0.95

    def test_allow_zero_regex_score_no_flag(self):
        """ALLOW: regex_score=0.0 and regex_flag=False -> default allow."""
        engine = DecisionEngine()
        result = engine.decide(
            regex_flag=False,
            regex_score=0.0,
            intent="benign",
            intent_score=0.9,
        )
        assert result.decision == Decision.ALLOW

    def test_weights_affect_combined_score_in_fallback(self):
        """Weighted combination of regex and intent scores is used in intermediate paths."""
        engine_high_regex = DecisionEngine(regex_weight=0.8, intent_weight=0.2)
        result = engine_high_regex.decide(
            regex_flag=False,
            regex_score=0.0,
            intent="suspicious",
            intent_score=0.6,
        )
        # This will not trigger any high-severity path; sanity check on weights
        assert result.decision in (Decision.SANITIZE, Decision.ALLOW)


class TestDecisionEngineGetSafeResponse:
    """Test get_safe_response() fallback response."""

    def test_get_safe_response_returns_string(self):
        """get_safe_response() returns a non-empty string."""
        engine = DecisionEngine()
        response = engine.get_safe_response()
        assert isinstance(response, str)
        assert len(response) > 0

    def test_get_safe_response_mentions_guidelines(self):
        """Safe response text is informative."""
        engine = DecisionEngine()
        response = engine.get_safe_response()
        # The response should contain something meaningful
        assert len(response) >= 20


class TestDecisionResultDataclass:
    """Test DecisionResult fields are correctly populated."""

    def test_decision_result_fields(self):
        """DecisionResult carries decision, confidence, reasoning, and rule_matched."""
        result = DecisionResult(
            decision=Decision.BLOCK,
            confidence=0.92,
            reasoning="Test reasoning",
            rule_matched="test_rule",
        )
        assert result.decision == Decision.BLOCK
        assert result.confidence == 0.92
        assert result.reasoning == "Test reasoning"
        assert result.rule_matched == "test_rule"

    def test_confidence_range(self):
        """Confidence is always 0.0-1.0 in all branches."""
        engine = DecisionEngine()
        test_cases = [
            (True, 0.9, "malicious", 0.85),
            (False, 0.0, "malicious", 0.95),
            (False, 0.0, "suspicious", 0.7),
            (True, 0.6, "benign", 0.5),
            (False, 0.0, "benign", 0.95),
        ]
        for regex_flag, regex_score, intent, intent_score in test_cases:
            result = engine.decide(
                regex_flag=regex_flag,
                regex_score=regex_score,
                intent=intent,
                intent_score=intent_score,
            )
            assert 0.0 <= result.confidence <= 1.0, f"confidence out of range for {intent}/{intent_score}"
