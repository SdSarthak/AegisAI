"""Hallucination Validator checking grounding score for generated outputs.

Copyright (C) 2026 AegisAI Contributors
"""

from typing import List
from app.modules.rag.grounding import GroundingChecker


class HallucinationValidator:
    """Verifies that generated answer matches context chunks to prevent hallucination."""

    def __init__(self) -> None:
        self.checker = GroundingChecker()

    def check(self, answer: str, chunks: List[str]) -> float:
        """Calculate grounding score for answer against context chunks.

        Returns:
            A score between 0.0 and 1.0 (higher is better).
        """
        if not answer or not chunks:
            return 0.0

        try:
            result = self.checker.check(answer=answer, chunks=chunks)
            return result.score
        except Exception:
            # Fallback to zero if anything goes wrong during embedding check
            return 0.0
