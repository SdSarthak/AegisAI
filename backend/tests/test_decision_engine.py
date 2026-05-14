"""
Unit tests for DecisionEngine covering all 5 decision branches.
Run with: pytest tests/test_decision_engine.py -v --noconftest
"""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

_decision_engine_path = Path(__file__).resolve().parents[1] / "app" / "modules" / "guard" / "decision_engine.py"
_spec = spec_from_file_location("decision_engine", _decision_engine_path)
_module = module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_module)

DecisionEngine = _module.DecisionEngine
Decision = _module.Decision


@pytest.fixture
def engine():
    return DecisionEngine()


@pytest.mark.parametrize(
    ("regex_flag", "regex_score", "intent", "intent_score", "decision", "confidence", "rule_matched"),
    [
        (True, 0.9, "malicious", 0.95, Decision.BLOCK, 0.9, "regex_high + intent_malicious"),
        (False, 0.0, "malicious", 0.85, Decision.BLOCK, 0.85, "intent_malicious"),
        (False, 0.0, "suspicious", 0.6, Decision.SANITIZE, 0.6, "intent_suspicious"),
        (True, 0.6, "benign", 0.1, Decision.SANITIZE, 0.6, "regex_medium"),
        (False, 0.0, "benign", 0.1, Decision.ALLOW, 0.9, "default_allow"),
    ],
)
def test_decision_engine_branches(
    engine,
    regex_flag,
    regex_score,
    intent,
    intent_score,
    decision,
    confidence,
    rule_matched,
):
    result = engine.decide(
        regex_flag=regex_flag,
        regex_score=regex_score,
        intent=intent,
        intent_score=intent_score,
    )

    assert result.decision == decision
    assert result.confidence == confidence
    assert result.rule_matched == rule_matched