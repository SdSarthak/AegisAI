"""
Guard API — LLM Prompt Injection Detection & Threat Scanning
=============================================================

This module exposes the Guard API, which provides a single endpoint for
scanning LLM prompts for prompt injection attempts, jailbreaks, and other
adversarial inputs before they reach the underlying model.

Endpoint
--------
POST /guard/scan
    Accepts a ScanRequest payload and returns a ScanResponse with a threat
    decision, confidence score, and human-readable reasoning.

Rate Limiting
-------------
The API enforces a sliding-window rate limit of 60 requests per minute per
user. The rate limit counters are stored in-memory; they reset whenever the
server restarts. For persistent rate limiting across restarts, an external
store (e.g. Redis) would be required.

Request Shape (ScanRequest)
---------------------------
    prompt   : str            — The user prompt to be scanned.
    user_id  : str | None     — Optional identifier for per-user rate limiting.

Response Shape (ScanResponse)
------------------------------
    decision   : str   — One of "allow", "block", or "sanitize".
    confidence : float — Model confidence in the decision (0.0 – 1.0).
    reasoning  : str   — Human-readable explanation of the decision.

Notes
-----
- This module contains no functional logic changes; it is documentation only.
- The in-memory rate limit store does NOT persist across server restarts.
"""