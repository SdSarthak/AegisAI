"""
Re-exports and thin wrappers making the Guard pipeline importable
as a standalone package without the FastAPI server.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

TODO (help wanted):
  - Copy the following files from backend/app/modules/guard/ into
    guard-sdk/src/aegisai_guard/ (preserve directory structure):
      * regex_rules.py
      * intent_classifier.py
      * decision_engine.py
      * sanitizer.py
      * llm_guard.py
  - Remove any imports of `app.core.config` or `app.core.security` —
    replace config values with constructor arguments or env vars.
  - Expose LLMGuard, SanitizationLevel, and a typed GuardResult TypedDict.
  - Write at least 3 unit tests in guard-sdk/tests/test_guard.py covering
    allow / sanitize / block decisions.
  - Acceptance criteria: `pip install -e guard-sdk/` then
    `from aegisai_guard import LLMGuard; LLMGuard().guard("hello")` works.
"""

from enum import Enum
from typing import TypedDict, Literal

class SanitizationLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class GuardDecision(str, Enum):
    ALLOW = "allow"
    SANITIZE = "sanitize"
    BLOCK = "block"

class GuardResult(TypedDict):
    decision: Literal["allow", "sanitize", "block"]
    sanitized_text: str | None
    risk_score: float

class LLMGuard:
    def __init__(self, sanitization_level: SanitizationLevel = SanitizationLevel.MEDIUM):
        self.sanitization_level = sanitization_level

    def guard(self, text: str) -> GuardResult:
        # Dummy implementation
        return {
            "decision": "allow",
            "sanitized_text": text,
            "risk_score": 0.0
        }
