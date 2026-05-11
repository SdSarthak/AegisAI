"""
aegisai-guard — standalone LLM prompt injection guard.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

Usage:
    from aegisai_guard import LLMGuard, SanitizationLevel

    guard = LLMGuard(sanitization_level=SanitizationLevel.MEDIUM)
    result = guard.guard("Your prompt here")
    print(result["decision"])   # "allow" | "sanitize" | "block"

TODO (good first issue — package scaffold):
  - The imports below will fail until the Guard module source is copied
    (or symlinked) into this package. See guard.py in this directory
    for the re-export strategy.
  - Acceptance criteria: `python -c "from aegisai_guard import LLMGuard"`
    succeeds after `pip install -e guard-sdk/`.

TODO (help wanted — re-export):
  - Copy (do NOT duplicate logic) the Guard pipeline files from
    backend/app/modules/guard/ into guard-sdk/src/aegisai_guard/.
  - Adjust imports so they are self-contained (no app.core.config dependency).
  - Expose a clean public API: LLMGuard, SanitizationLevel, GuardDecision.
  - Acceptance criteria: the package works without a running FastAPI server.
"""

from aegisai_guard.guard import LLMGuard, SanitizationLevel, GuardDecision
 
__version__ = "0.1.0"
__all__: list[str] = ["LLMGuard", "SanitizationLevel", "GuardDecision"]
