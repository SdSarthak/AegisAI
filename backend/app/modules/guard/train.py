"""Compatibility CLI for the standardized guard training pipeline.

The legacy entrypoint stays available for older commands, but the actual
work is delegated to the standardized pipeline implementation under
``app.modules.guard.training``.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from app.modules.guard import guard_config as config
from app.modules.guard.training.data.dataset_loader import load_or_download_dataset
from app.modules.guard.training.data.split import train_validation_split
from app.modules.guard.training.pipelines.train_pipeline import run_training_pipeline


logger = logging.getLogger(__name__)

HF_DATASET_NAME = "xTRam1/safe-guard-prompt-injection"
LOCAL_CSV_PATH = config.DATA_DIR / "prompts.csv"


def download_and_process_dataset(
    output_path: str = str(LOCAL_CSV_PATH),
    force_download: bool = False,
):
    """Download or reuse the standardized prompt-injection dataset."""
    df = load_or_download_dataset(
        local_csv_path=output_path,
        dataset_name=HF_DATASET_NAME,
        force_download=force_download,
        valid_labels=config.INTENT_CLASSES,
    )
    logger.info("Dataset ready at %s with %s samples", output_path, len(df))
    return df


def train_classifier(
    dataset_path: str,
    model_output_dir: str,
    epochs: int = 3,
    force_retrain: bool = False,
):
    """Train the intent classifier through the standardized trainer facade."""
    dataset = download_and_process_dataset(dataset_path, force_download=force_retrain)
    train_df, val_df = train_validation_split(
        dataset,
        test_size=config.TEST_SPLIT,
        random_state=42,
        stratify=True,
    )
    from app.modules.guard.training.trainer.trainer import SafetyClassifierTrainer

    result = SafetyClassifierTrainer(model_output_dir=Path(model_output_dir)).train(
        train_df=train_df,
        val_df=val_df,
        epochs=epochs,
        batch_size=16,
        learning_rate=2e-5,
    )
    logger.info("Training complete. Model saved to %s", result.model_output_dir)
    if result.metrics.get("val_accuracy"):
        logger.info("Final validation accuracy: %.4f", result.metrics["val_accuracy"][-1])
    return result.metrics


def main():
    """Parse CLI arguments and route them into the training pipeline."""
    parser = argparse.ArgumentParser(description="Train LLM Guard Intent Classifier")
    parser.add_argument(
        "--download-only", action="store_true", help="Only download and process data"
    )
    parser.add_argument(
        "--train-only", action="store_true", help="Only train using existing data"
    )
    parser.add_argument("--all", action="store_true", help="Download data and train")
    parser.add_argument("--force-download", action="store_true", help="Force re-download of dataset")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--config", help="Optional standardized training YAML config")

    args = parser.parse_args()

    if not any([args.download_only, args.train_only, args.all]):
        args.all = True

    if args.download_only:
        download_and_process_dataset(
            str(LOCAL_CSV_PATH), force_download=args.force_download
        )
        return

    if args.train_only:
        train_classifier(str(LOCAL_CSV_PATH), config.CLASSIFIER_MODEL_PATH, epochs=args.epochs)
        return

    run_training_pipeline(
        config_path=args.config,
        epochs=args.epochs,
        force_download=args.force_download,
    )


if __name__ == "__main__":
    from app.core.logging import configure_logging
    
    configure_logging()
    main()
