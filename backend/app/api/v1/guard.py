"""
LLM Guard API — exposes prompt injection scanning as a REST endpoint.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

TODO for contributors (medium difficulty):
  - Add per-user rate limiting on POST /guard/scan
  - Persist scan results to the database for audit logs
  - Add a GET /guard/stats endpoint returning block/allow/sanitize counts
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock

import json

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.core.security import get_current_user
from app.core.database import get_db
from app.models.user import User
from sqlalchemy.orm import Session
from jose import JWTError
from app.core.config import settings

router = APIRouter()


_RATE_LIMIT_REQUESTS = 60
_RATE_LIMIT_WINDOW_SECONDS = 60
_scan_attempts_by_user: dict[int, deque[datetime]] = defaultdict(deque)
_rate_limit_lock = Lock()


class ScanRequest(BaseModel):
    prompt: str


class ScanResponse(BaseModel):
    decision: str  # "allow" | "sanitize" | "block"
    confidence: float
    reasoning: str
    sanitized_prompt: str | None = None
    matched_patterns: list[str] = []


def _check_rate_limit(user_id: int) -> tuple[bool, int]:
    """Return whether the user is limited and the seconds to retry after."""
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=_RATE_LIMIT_WINDOW_SECONDS)

    with _rate_limit_lock:
        attempts = _scan_attempts_by_user[user_id]
        while attempts and attempts[0] <= window_start:
            attempts.popleft()

        if len(attempts) >= _RATE_LIMIT_REQUESTS:
            retry_after = max(
                1,
                int(
                    (_RATE_LIMIT_WINDOW_SECONDS - (now - attempts[0]).total_seconds())
                    + 0.999
                ),
            )
            return True, retry_after

        attempts.append(now)
        return False, 0


@router.post("/scan", response_model=ScanResponse)
def scan_prompt(
    request: ScanRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Scan a prompt for injection risks.
    Returns a decision: allow, sanitize, or block.
    """
    limited, retry_after = _check_rate_limit(current_user.id)
    if limited:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Rate limit exceeded: 60 requests per minute per user. Please try again later.",
            },
            headers={"Retry-After": str(retry_after)},
        )

    try:
        from app.modules.guard.llm_guard import LLMGuard
        from app.modules.guard.sanitizer import SanitizationLevel
        from app.core.config import settings

        level_map = {
            "low": SanitizationLevel.LOW,
            "medium": SanitizationLevel.MEDIUM,
            "high": SanitizationLevel.HIGH,
        }
        san_level = level_map.get(
            settings.GUARD_SANITIZATION_LEVEL, SanitizationLevel.MEDIUM
        )
        guard = LLMGuard(sanitization_level=san_level)
        result = guard.guard(request.prompt)

        return ScanResponse(
            decision=result["decision"],
            confidence=result["metadata"]["decision_reasoning"]["confidence"],
            reasoning=result["metadata"]["decision_reasoning"]["reasoning"],
            sanitized_prompt=None,
            matched_patterns=result["metadata"]["regex_analysis"].get(
                "matched_patterns", []
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.websocket("/stream")
async def stream_guard_pipeline(websocket: WebSocket, db: Session = Depends(get_db)):
    """
    Stream pipeline progress as each layer completes.
    Client must send: {"prompt": "...", "token": "<jwt>"}
    Server emits one JSON message per layer, then closes.
    """
    await websocket.accept()
    try:
        data = await websocket.receive_json()
    except Exception:
        await websocket.close(code=1003)
        return

    # Authenticate via token sent in the first message
    token = data.get("token", "")
    prompt = data.get("prompt", "").strip()

    if not prompt:
        await websocket.send_json({"error": "prompt is required"})
        await websocket.close(code=1003)
        return

    try:
        from jose import jwt
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("no sub")
        from app.models.user import User
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise ValueError("user not found")
    except Exception:
        await websocket.send_json({"error": "unauthorized"})
        await websocket.close(code=1008)
        return

    try:
        from app.modules.guard.regex_rules import RegexFilter
        from app.modules.guard.intent_classifier import IntentClassifier
        from app.modules.guard.decision_engine import DecisionEngine
        from app.modules.guard.sanitizer import SanitizationLevel
        from app.core.config import settings as cfg

        # Layer 1: Regex
        regex_result = RegexFilter().check(prompt)
        await websocket.send_json({
            "layer": "regex",
            "flag": regex_result.flag,
            "score": round(regex_result.score, 4),
            "matched_patterns": regex_result.matched_patterns,
        })

        # Layer 2: Classifier
        classifier = IntentClassifier()
        intent_result = classifier.classify(prompt)
        await websocket.send_json({
            "layer": "classifier",
            "intent": intent_result.intent,
            "confidence": round(intent_result.confidence, 4),
            "class_scores": {k: round(v, 4) for k, v in intent_result.class_scores.items()},
        })

        # Layer 3: Decision
        decision_result = DecisionEngine().decide(
            regex_flag=regex_result.flag,
            regex_score=regex_result.score,
            intent=intent_result.intent,
            intent_score=intent_result.confidence,
        )
        await websocket.send_json({
            "layer": "decision",
            "decision": decision_result.decision.value,
            "confidence": round(decision_result.confidence, 4),
            "reasoning": decision_result.reasoning,
        })

    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()


@router.get("/health", tags=["LLM Guard"])
def guard_health():
    """Check if the Guard module is available."""
    return {"module": "llm_guard", "status": "available"}
class BulkScanRequest(BaseModel):
    prompts: list[str]

    def validate_prompts(self):
        if len(self.prompts) > 50:
            raise ValueError("Maximum 50 prompts allowed per batch request.")
        return self

class BulkScanResponse(BaseModel):
    results: list[ScanResponse]
    total: int
    processed: int

@router.post("/scan/batch", response_model=BulkScanResponse)
def bulk_scan_prompts(
    request: BulkScanRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Scan a batch of prompts (max 50) for injection risks.
    Processes sequentially to respect memory constraints.
    Returns a decision for each prompt.
    """
    if len(request.prompts) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 prompts allowed per batch request."
        )

    limited, retry_after = _check_rate_limit(current_user.id)
    if limited:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Please try again later."},
            headers={"Retry-After": str(retry_after)},
        )

    try:
        from app.modules.guard.llm_guard import LLMGuard
        from app.modules.guard.sanitizer import SanitizationLevel
        from app.core.config import settings

        level_map = {
            "low": SanitizationLevel.LOW,
            "medium": SanitizationLevel.MEDIUM,
            "high": SanitizationLevel.HIGH,
        }
        san_level = level_map.get(settings.GUARD_SANITIZATION_LEVEL, SanitizationLevel.MEDIUM)
        guard = LLMGuard(sanitization_level=san_level)

        results = []
        for prompt in request.prompts:
            result = guard.guard(prompt)
            results.append(ScanResponse(
                decision=result["decision"],
                confidence=result["metadata"]["decision_reasoning"]["confidence"],
                reasoning=result["metadata"]["decision_reasoning"]["reasoning"],
                sanitized_prompt=None,
                matched_patterns=result["metadata"]["regex_analysis"].get("matched_patterns", []),
            ))

        return BulkScanResponse(
            results=results,
            total=len(request.prompts),
            processed=len(results),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
