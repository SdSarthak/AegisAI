"""Logging helpers for guard training and evaluation jobs.

The training pipeline uses a dedicated logger so its progress messages stay
separate from the main API logger and remain easy to scan in local runs.
"""

from __future__ import annotations

import logging


def get_training_logger(name: str = "aegisai.guard.training") -> logging.Logger:
    """Return a configured training logger for guard pipeline runs."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        )
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
