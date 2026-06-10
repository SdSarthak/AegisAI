"""Logging setup for guard training pipelines."""

from __future__ import annotations

import logging


def get_training_logger(name: str = "aegisai.guard.training") -> logging.Logger:
    """Return a configured training logger for guard pipeline runs.

    Args:
        name: Logger name to create or reuse.

    Returns:
        A logger configured with a stream handler and INFO level.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        )
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
