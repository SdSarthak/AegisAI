"""
Pydantic schemas for Guard explanation (issue #77).

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ExplainMethod = Literal["shap", "lime"]


class TokenAttribution(BaseModel):
    """One row per token in the explained prompt."""

    token: str = Field(..., description="The token as the tokenizer rendered it.")
    attribution: float = Field(
        ...,
        description=(
            "Signed contribution to the predicted class. Positive values push "
            "the model toward the predicted label; negative values push away. "
            "Magnitude reflects how influential the token was."
        ),
    )
    char_span: tuple[int, int] = Field(
        ...,
        description=(
            "[start, end) byte offsets in the *original* text. Lets the frontend "
            "highlight the token in the input verbatim, including whitespace."
        ),
    )


class ExplainRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="The prompt to explain. Capped at 4000 chars for latency.",
    )
    method: ExplainMethod = Field(
        default="shap",
        description=(
            "`shap` is the primary path (Shapley values via PartitionExplainer); "
            "`lime` is a faster fallback for very long inputs."
        ),
    )
    max_evals: int = Field(
        default=200,
        ge=10,
        le=1000,
        description="SHAP perturbation budget. Higher = more accurate, slower.",
    )


class ExplainResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    predicted_label: str
    predicted_proba: float = Field(..., ge=0.0, le=1.0)
    base_value: float = Field(
        ...,
        description=(
            "Expected model output averaged over the masker — the 'starting "
            "point' before any token contributes. predicted_proba - base_value "
            "approximately equals the sum of token attributions (Shapley "
            "efficiency)."
        ),
    )
    tokens: list[TokenAttribution]
    method: ExplainMethod
    model_version: str
    latency_ms: float
