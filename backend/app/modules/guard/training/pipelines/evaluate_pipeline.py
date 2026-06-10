"""Run evaluation for a trained guard safety classifier.

This pipeline loads the cached dataset, evaluates the current model, and
writes both aggregate metrics and per-example predictions to artifact files.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.modules.guard.intent_classifier import IntentClassifier
from app.modules.guard.training.data.dataset_loader import (
    load_local_dataset,
    resolve_backend_path,
)
from app.modules.guard.training.evaluation.evaluator import SafetyClassifierEvaluator
from app.modules.guard.training.pipelines.train_pipeline import load_training_config
from app.modules.guard.training.utils.checkpoint import (
    save_json_artifact,
    save_predictions,
    utc_run_id,
)
from app.modules.guard.training.utils.logger import get_training_logger


LOGGER = get_training_logger(__name__)


def run_evaluation_pipeline(
    config_path: str | Path | None = None,
    dataset_path: str | Path | None = None,
    model_path: str | Path | None = None,
) -> dict:
    cfg = load_training_config(config_path)
    run_id = utc_run_id("eval")
    dataset_cfg = cfg["dataset"]
    artifacts_cfg = cfg["artifacts"]

    df = load_local_dataset(
        dataset_path or dataset_cfg["local_csv_path"],
        text_column=dataset_cfg.get("text_column", "prompt"),
        label_column=dataset_cfg.get("label_column", "label"),
        valid_labels=dataset_cfg.get("valid_labels"),
    )
    classifier = IntentClassifier(
        model_path=str(resolve_backend_path(model_path)) if model_path else None
    )
    result = SafetyClassifierEvaluator(classifier).evaluate(df)

    metrics_path = resolve_backend_path(artifacts_cfg["metrics_dir"]) / f"{run_id}.json"
    report_path = resolve_backend_path(artifacts_cfg["reports_dir"]) / f"{run_id}-predictions.json"
    artifact = {
        "run_id": run_id,
        "dataset_rows": len(df),
        "model_path": str(model_path) if model_path else "auto",
        "metrics": result.metrics,
    }
    save_json_artifact(artifact, metrics_path)
    save_predictions(result.predictions, report_path)
    LOGGER.info("Evaluation metrics saved to %s", metrics_path)
    LOGGER.info("Evaluation predictions saved to %s", report_path)
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser(description="Run guard safety classifier evaluation pipeline")
    parser.add_argument("--config", help="Path to training YAML config")
    parser.add_argument("--dataset", help="CSV dataset to evaluate")
    parser.add_argument("--model-path", help="Model directory to evaluate")
    args = parser.parse_args()
    run_evaluation_pipeline(args.config, dataset_path=args.dataset, model_path=args.model_path)


if __name__ == "__main__":
    main()
