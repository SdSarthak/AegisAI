"""
Re-exports making the Guard pipeline importable as a standalone package.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from aegisai_guard.llm_guard import LLMGuard
from aegisai_guard.sanitizer import SanitizationLevel
from aegisai_guard.decision_engine import Decision as GuardDecision

# Convenience type re-exports
from typing import TypedDict, Literal


class GuardResult(TypedDict):
    decision: Literal["allow", "sanitize", "block"]
    sanitized_text: str | None
    risk_score: float


__all__ = ["LLMGuard", "SanitizationLevel", "GuardDecision", "GuardResult"]
