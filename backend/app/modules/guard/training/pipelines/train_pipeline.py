"""Run the end-to-end training pipeline for the guard safety classifier.

The pipeline handles config loading, dataset acquisition, train/validation
splitting, model training, optional MLflow logging, and artifact export in
one place so the CLI and any automation can reuse the same path.
"""

import argparse
from copy import deepcopy
from pathlib import Path
from typing import Any

from app.modules.guard import guard_config as guard_config
from app.modules.guard.training.data.dataset_loader import (
    load_or_download_dataset,
    resolve_backend_path,
)
from app.modules.guard.training.data.split import train_validation_split
from app.modules.guard.training.utils.checkpoint import save_json_artifact, utc_run_id
from app.modules.guard.training.utils.logger import get_training_logger
from app.modules.guard.training.utils.mlflow_logger import log_metrics, mlflow_run
from app.modules.guard.training.utils.seed import set_seed


LOGGER = get_training_logger(__name__)


DEFAULT_CONFIG: dict[str, Any] = {
    "dataset": {
        "source": "huggingface",
        "huggingface_name": "xTRam1/safe-guard-prompt-injection",
        "local_csv_path": str(guard_config.TRAINING_DATA_PATH),
        "text_column": "prompt",
        "label_column": "label",
        "valid_labels": guard_config.INTENT_CLASSES,
    },
    "split": {"test_size": 0.2, "random_state": 42, "stratify": True},
    "model": {"output_dir": guard_config.CLASSIFIER_MODEL_PATH, "device": "auto"},
    "training": {"epochs": 3, "batch_size": 16, "learning_rate": 2e-5, "force_download": False},
    "artifacts": {
        "metrics_dir": "app/modules/guard/training/artifacts/metrics",
        "reports_dir": "app/modules/guard/training/artifacts/reports",
    },
    "mlflow": {"enabled": False, "experiment_name": "aegisai-guard-safety-classifier"},
}


def load_training_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load pipeline config, falling back to defaults if YAML support is unavailable."""
    if config_path is None:
        config_path = Path(__file__).parents[1] / "configs" / "training.yaml"
    path = Path(config_path)
    if not path.exists():
        return deepcopy(DEFAULT_CONFIG)

    try:
        import yaml
    except ImportError:
        LOGGER.warning("PyYAML is not installed; using built-in training defaults.")
        return deepcopy(DEFAULT_CONFIG)

    with path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file) or {}

    merged = deepcopy(DEFAULT_CONFIG)
    for section, values in loaded.items():
        if isinstance(values, dict) and isinstance(merged.get(section), dict):
            merged[section] = {**merged[section], **values}
        else:
            merged[section] = values
    return merged


def run_training_pipeline(
    config_path: str | Path | None = None,
    epochs: int | None = None,
    force_download: bool | None = None,
) -> dict:
    """Run download/load, split, train, and artifact persistence."""
    cfg = load_training_config(config_path)
    run_id = utc_run_id("train")
    split_cfg = cfg["split"]
    training_cfg = cfg["training"]
    dataset_cfg = cfg["dataset"]

    if epochs is not None:
        training_cfg["epochs"] = epochs
    if force_download is not None:
        training_cfg["force_download"] = force_download

    set_seed(int(split_cfg.get("random_state", 42)))
    LOGGER.info("Loading guard training dataset")
    df = load_or_download_dataset(
        local_csv_path=dataset_cfg["local_csv_path"],
        dataset_name=dataset_cfg["huggingface_name"],
        force_download=training_cfg.get("force_download", False),
        text_column=dataset_cfg.get("text_column", "prompt"),
        label_column=dataset_cfg.get("label_column", "label"),
        valid_labels=dataset_cfg.get("valid_labels", guard_config.INTENT_CLASSES),
    )
    train_df, val_df = train_validation_split(
        df,
        test_size=float(split_cfg.get("test_size", 0.2)),
        random_state=int(split_cfg.get("random_state", 42)),
        stratify=bool(split_cfg.get("stratify", True)),
    )

    LOGGER.info(
        "Training classifier with %s train and %s validation rows",
        len(train_df),
        len(val_df),
    )
    from app.modules.guard.training.trainer.trainer import SafetyClassifierTrainer

    trainer = SafetyClassifierTrainer(
        model_output_dir=cfg["model"]["output_dir"],
        device=cfg["model"].get("device", "auto"),
    )

    with mlflow_run(
        enabled=bool(cfg["mlflow"].get("enabled", False)),
        experiment_name=cfg["mlflow"].get("experiment_name", "aegisai-guard-safety-classifier"),
        run_name=run_id,
    ):
        result = trainer.train(
            train_df=train_df,
            val_df=val_df,
            epochs=int(training_cfg.get("epochs", 3)),
            batch_size=int(training_cfg.get("batch_size", 16)),
            learning_rate=float(training_cfg.get("learning_rate", 2e-5)),
        )
        final_metrics = {
            "train_loss": result.metrics.get("train_loss", [])[-1],
            "val_accuracy": result.metrics.get("val_accuracy", [])[-1],
            "val_f1": result.metrics.get("val_f1", [])[-1],
        }
        if cfg["mlflow"].get("enabled", False):
            log_metrics(final_metrics, prefix="final_")

    artifact = {
        "run_id": run_id,
        "dataset_rows": len(df),
        "train_rows": len(train_df),
        "validation_rows": len(val_df),
        "model_output_dir": str(result.model_output_dir),
        "metrics": result.metrics,
    }
    metrics_path = resolve_backend_path(cfg["artifacts"]["metrics_dir"]) / f"{run_id}.json"
    save_json_artifact(artifact, metrics_path)
    LOGGER.info("Training metrics saved to %s", metrics_path)
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser(description="Run guard safety classifier training pipeline")
    parser.add_argument("--config", help="Path to training YAML config")
    parser.add_argument("--epochs", type=int, help="Override number of training epochs")
    parser.add_argument("--force-download", action="store_true", help="Refresh the source dataset")
    args = parser.parse_args()
    run_training_pipeline(args.config, epochs=args.epochs, force_download=args.force_download)


if __name__ == "__main__":
    main()
