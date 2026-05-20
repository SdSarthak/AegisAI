"""
aegisai-guard — standalone LLM prompt injection guard.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

Usage:
    from aegisai_guard import LLMGuard, SanitizationLevel

    guard = LLMGuard(sanitization_level=SanitizationLevel.MEDIUM)
    result = guard.guard("Your prompt here")
    print(result["decision"])   # "allow" | "sanitize" | "block"
"""

from aegisai_guard.llm_guard import LLMGuard
from aegisai_guard.sanitizer import SanitizationLevel

__version__ = "0.1.0"
__all__ = ["LLMGuard", "SanitizationLevel"]
