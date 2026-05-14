"""Training and data preparation script for the intent classifier."""

import os
import argparse
import logging
from typing import Dict, List, Optional

import pandas as pd
import numpy as np
from datasets import load_dataset
from sklearn.model_selection import train_test_split

from app.modules.guard import guard_config as config
from app.modules.guard import IntentClassifier

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
HF_DATASET_NAME = "xTRam1/safe-guard-prompt-injection"
LOCAL_CSV_PATH = config.DATA_DIR / "prompts.csv"


def download_and_process_dataset(
    output_path: str = str(LOCAL_CSV_PATH), force_download: bool = False
):
    """
    Download the production-grade dataset from Hugging Face and process it for training.

    Dataset: xTRam1/safe-guard-prompt-injection
    - Contains ~10,000 prompts
    - Balanced between 'safe' and 'injection'
    """
    if os.path.exists(output_path) and not force_download:
        logger.info(f"Dataset already exists at {output_path}. Skipping download.")
        return pd.read_csv(output_path)

    logger.info(f"Downloading dataset '{HF_DATASET_NAME}' from Hugging Face...")

    try:
        # Load dataset from Hugging Face
        dataset = load_dataset(HF_DATASET_NAME)

        # Convert to pandas DataFrame
        # The dataset typically has 'prompt' and 'label' or similar columns
        # We need to standardize them
        df = dataset["train"].to_pandas()

        # Inspect and standardized columns
        logger.info(f"Raw dataset columns: {df.columns.tolist()}")

        # The xTRam1 dataset usually has 'prompt' and 'label' (1 for injection, 0 for safe)
        # We need to map numerical labels to our string labels: "benign", "malicious"
        # Note: This specific dataset binaries 1=injection, 0=safe.

        # Rename columns if necessary (adjust based on actual dataset structure)
        if "text" in df.columns:
            df = df.rename(columns={"text": "prompt"})

        if "label" in df.columns:
            # Map 0 -> benign, 1 -> malicious
            # We treat all injections as "malicious" for the base training
            label_map = {0: "benign", 1: "malicious"}
            df["label"] = df["label"].map(label_map)

        # Ensure we have the right columns
        if "prompt" not in df.columns or "label" not in df.columns:
            raise ValueError(
                f"Dataset does not contain required columns after processing. Got: {df.columns.tolist()}"
            )

        # Drop any NA values
        df = df.dropna(subset=["prompt", "label"])

        # Remove duplicates
        df = df.drop_duplicates(subset=["prompt"])

        # Save to local CSV
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False)

        logger.info(f"✓ Dataset saved to {output_path}")
        logger.info(f"  - Total samples: {len(df)}")
        logger.info(f"  - Benign samples: {len(df[df['label'] == 'benign'])}")
        logger.info(f"  - Malicious samples: {len(df[df['label'] == 'malicious'])}")

        return df

    except Exception as e:
        logger.error(f"Failed to download/process dataset: {e}")
        raise


def train_classifier(
    dataset_path: str,
    model_output_dir: str,
    epochs: int = 3,
    force_retrain: bool = False,
):
    """
    Train the intent classifier on the processed dataset.
    """
    if not os.path.exists(dataset_path):
        logger.error(f"Dataset not found at {dataset_path}. Please download it first.")
        return

    logger.info(f"Loading training data from {dataset_path}...")
    df = pd.read_csv(dataset_path)

    # Filter for valid labels only
    valid_labels = ["benign", "malicious", "suspicious"]
    df = df[df["label"].isin(valid_labels)]

    # Stratified split
    train_df, val_df = train_test_split(
        df, test_size=0.2, stratify=df["label"], random_state=42
    )

    train_texts = train_df["prompt"].tolist()
    train_labels = train_df["label"].tolist()
    val_texts = val_df["prompt"].tolist()
    val_labels = val_df["label"].tolist()

    logger.info(f"Training set: {len(train_texts)} samples")
    logger.info(f"Validation set: {len(val_texts)} samples")

    # Initialize Classifier
    logger.info("Initializing IntentClassifier (DeBERTa-v3-small)...")
    classifier = IntentClassifier(device="cuda" if os.environ.get("USE_GPU") else None)

    # Train
    logger.info(f"Starting training for {epochs} epochs...")
    metrics = classifier.train(
        train_texts=train_texts,
        train_labels=train_labels,
        val_texts=val_texts,
        val_labels=val_labels,
        epochs=epochs,
        batch_size=16,  # Adjust based on VRAM
        learning_rate=2e-5,
        output_dir=model_output_dir,
    )

    logger.info("✓ Training complete!")
    logger.info(f"Final Validation Accuracy: {metrics['val_accuracy'][-1]:.4f}")


def main():
    parser = argparse.ArgumentParser(description="Train LLM Guard Intent Classifier")
    parser.add_argument(
        "--download-only", action="store_true", help="Only download and process data"
    )
    parser.add_argument(
        "--train-only", action="store_true", help="Only train (assumes data exists)"
    )
    parser.add_argument("--all", action="store_true", help="Download data and train")
    parser.add_argument(
        "--force-download", action="store_true", help="Force re-download of dataset"
    )
    parser.add_argument(
        "--epochs", type=int, default=3, help="Number of training epochs"
    )

    args = parser.parse_args()

    # Default to --all if no specific action given
    if not any([args.download_only, args.train_only, args.all]):
        args.all = True

    dataset_path = str(LOCAL_CSV_PATH)
    model_dir = config.CLASSIFIER_MODEL_PATH

    if args.download_only or args.all:
        download_and_process_dataset(dataset_path, force_download=args.force_download)

    if args.train_only or args.all:
        train_classifier(dataset_path, model_dir, epochs=args.epochs)


if __name__ == "__main__":
    main()
