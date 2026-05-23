"""
Guard API — LLM Prompt Injection Detection & Threat Scanning
=============================================================

This module exposes the Guard API, which provides a single endpoint for
scanning LLM prompts for prompt injection attempts, jailbreaks, and other
adversarial inputs before they reach the underlying model.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

Endpoint
--------
POST /guard/scan
    Accepts a ScanRequest payload and returns a ScanResponse with a threat
    decision, confidence score, and human-readable reasoning.

Rate Limiting
-------------
The API enforces a sliding-window rate limit of 60 requests per minute per
user. Rate limit counters are stored in-memory and reset on server restart.
For persistence across restarts, an external store (e.g. Redis) is required.

Request Shape (ScanRequest)
---------------------------
    prompt : str — The user prompt to be scanned.

Response Shape (ScanResponse)
------------------------------
    decision         : str        — One of "allow", "block", or "sanitize".
    confidence       : float      — Confidence score (0.0 – 1.0).
    reasoning        : str        — Explanation of the decision.
    sanitized_prompt : str | None — Cleaned prompt if decision is "sanitize".
    matched_patterns : list[str]  — Regex patterns that triggered detection.

TODO for contributors (medium difficulty):
  - Add per-user rate limiting on POST /guard/scan
  - Persist scan results to the database for audit logs
  - Add a GET /guard/stats endpoint returning block/allow/sanitize counts
"""

from collections import defaultdict, deque
...