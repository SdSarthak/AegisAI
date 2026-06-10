"""Seed the training stack for reproducible guard experiments.

The guard training pipeline relies on deterministic splits and model
initialisation when comparing runs, so this helper centralizes the seeding.
"""

import os
import random

import numpy as np


def set_seed(seed: int = 42) -> None:
    """Seed Python, NumPy, and PyTorch for reproducible training runs."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    import torch

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
