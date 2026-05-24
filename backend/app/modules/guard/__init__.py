"""LLM Guard package for prompt injection detection and mitigation."""

__all__ = ["RegexFilter", "IntentClassifier", "DecisionEngine", "PromptSanitizer"]


def __getattr__(name):
    """Lazily load guard components so lightweight modules do not require torch."""
    if name == "RegexFilter":
        from .regex_rules import RegexFilter

        return RegexFilter
    if name == "IntentClassifier":
        from .intent_classifier import IntentClassifier

        return IntentClassifier
    if name == "DecisionEngine":
        from .decision_engine import DecisionEngine

        return DecisionEngine
    if name == "PromptSanitizer":
        from .sanitizer import PromptSanitizer

        return PromptSanitizer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
