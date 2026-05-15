import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent  # backend/app/modules/guard/
BACKEND_ROOT = PROJECT_ROOT.parent.parent.parent  # backend/
DATA_DIR = BACKEND_ROOT / "data"  # backend/data/
MODELS_DIR = PROJECT_ROOT / "models"  # backend/app/modules/guard/models/

# Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"  # or gemini-1.5-pro

# Model paths - supports both Colab (Google Drive) and local training
# Colab notebook saves to: /content/drive/My Drive/llm-guard/intent_classifier
# Local training saves to: guard/models/intent_classifier
CLASSIFIER_MODEL_PATH = os.getenv(
    "CLASSIFIER_MODEL_PATH", str(MODELS_DIR / "intent_classifier")
)
TOKENIZER_PATH = CLASSIFIER_MODEL_PATH  # Tokenizer stored in same directory as model

# Security settings
MAX_PROMPT_LENGTH = int(os.getenv("MAX_PROMPT_LENGTH", 2000))
SANITIZATION_LEVEL = os.getenv("SANITIZATION_LEVEL", "medium")  # low, medium, high

# Classification thresholds
INTENT_CLASSIFIER_THRESHOLD = 0.6  # Confidence threshold for classification
SUSPICIOUS_THRESHOLD = 0.4
MALICIOUS_THRESHOLD = 0.7

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Training data
TRAINING_DATA_PATH = DATA_DIR / "prompts.csv"
TEST_SPLIT = 0.2
VALIDATION_SPLIT = 0.1

# Intent classes
INTENT_CLASSES = ["benign", "suspicious", "malicious"]
INTENT_TO_ID = {"benign": 0, "suspicious": 1, "malicious": 2}
ID_TO_INTENT = {v: k for k, v in INTENT_TO_ID.items()}

# Model training metadata (from notebook)
MODEL_METADATA_PATH = MODELS_DIR / "config.json"
TRAINING_METRICS_PATH = MODELS_DIR / "training_metrics.json"


def get_trained_model_path() -> str:
    """
    Detect trained model location. Checks multiple paths:
    1. Environment variable CLASSIFIER_MODEL_PATH
    2. Local models directory (guard/models/intent_classifier)
    3. Current directory (intent_classifier)
    Returns default path if not found (will use pre-trained model as fallback).
    """
    if os.path.exists(CLASSIFIER_MODEL_PATH):
        return CLASSIFIER_MODEL_PATH

    # Check alternative locations
    alt_paths = [
        str(MODELS_DIR / "intent_classifier"),
        "./intent_classifier",
    ]

    for path in alt_paths:
        if os.path.exists(path) and os.path.exists(
            os.path.join(path, "pytorch_model.bin")
        ):
            return path

    # Return default path (will use pre-trained if fine-tuned not found)
    return CLASSIFIER_MODEL_PATH
