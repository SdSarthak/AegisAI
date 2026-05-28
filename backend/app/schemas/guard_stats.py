"""
Pydantic schemas for Guard scan statistics.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from pydantic import BaseModel
from typing import List, Dict


class StatsBreakdown(BaseModel):
    count: int
    pct: float


class PatternCount(BaseModel):
    pattern: str
    count: int


class DailyBucket(BaseModel):
    date: str
    allow: int
    sanitize: int
    block: int


class GuardStatsResponse(BaseModel):
    window: str
    total_scans: int
    by_decision: Dict[str, StatsBreakdown]
    by_detection_type: Dict[str, StatsBreakdown]
    top_matched_patterns: List[PatternCount]
    scans_per_day: List[DailyBucket]
