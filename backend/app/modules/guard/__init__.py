"""LLM Guard package for prompt injection detection and mitigation."""

from importlib import import_module
from types import ModuleType
import sys

__all__ = [
    "RegexFilter",
    "IntentClassifier",
    "DecisionEngine",
    "PromptSanitizer",
    "llm_guard",
]


def __getattr__(name):
    """Lazily load guard components for lightweight imports.

    Args:
        name: Attribute name being requested from the package namespace.

    Returns:
        The requested guard component or fallback module.

    Raises:
        AttributeError: If the attribute does not exist on the package.
    """
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
    if name == "llm_guard":
        try:
            return import_module(".llm_guard", __name__)
        except ModuleNotFoundError as exc:
            if exc.name != "torch":
                raise

            module_name = f"{__name__}.llm_guard"
            fallback = ModuleType(module_name)

            class LLMGuard:
                def __init__(self, *args, **kwargs):
                    raise ModuleNotFoundError(
                        "No module named 'torch'"
                    )

            fallback.LLMGuard = LLMGuard
            sys.modules[module_name] = fallback
            return fallback
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
