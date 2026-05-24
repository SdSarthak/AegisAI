"""
CI evaluation harness for the Guard safety classifier.

Wraps the existing ``SafetyClassifierEvaluator`` with CI-specific concerns:

  * Loads a held-out CSV fixture (not the training set), runs the classifier,
    computes the metrics the evaluator already exposes plus a confusion matrix.
  * Compares to a committed baseline JSON if one is provided, surfacing Δs so
    silent regressions are obvious in the PR diff.
  * Checks a configurable threshold metric against a configurable threshold.
    Exit code 1 when the threshold is missed — the GitHub Actions step fails,
    the PR cannot be merged.
  * Writes two artefacts:
      - ``metrics.json``  -- machine-readable, uploaded as an actions artifact
      - ``metrics.md``    -- markdown summary, appended to $GITHUB_STEP_SUMMARY
                              and posted as a sticky PR comment.

Run locally to regenerate the baseline:

    python -m scripts.evaluate_guard_ci \\
        --test-set-path backend/data/guard_holdout.csv \\
        --output-json    backend/data/guard_baseline.json \\
        --threshold      0.0   # don't fail when regenerating

Usage in CI is in ``.github/workflows/guard-eval.yml``.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Protocol

from sklearn.metrics import confusion_matrix

from app.modules.guard import guard_config
from app.modules.guard.training.data.dataset_loader import load_local_dataset
from app.modules.guard.training.evaluation.metrics import (
    compute_classification_metrics,
)

logger = logging.getLogger("aegisai.ci.guard_eval")

ALLOWED_THRESHOLD_METRICS = ("weighted_f1", "macro_f1", "accuracy")
DEFAULT_LABELS = ("benign", "suspicious", "malicious")


class _Classifier(Protocol):
    """Structural type the script needs from any classifier."""

    def classify(self, prompt: str) -> Any: ...  # returns obj with .intent


ClassifierFactory = Callable[[Optional[str]], _Classifier]


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------


def _default_classifier_factory(model_path: Optional[str]) -> _Classifier:
    """Default factory: import lazily so unit tests don't pull torch."""
    from app.modules.guard.intent_classifier import IntentClassifier

    return IntentClassifier(model_path=model_path)


def _build_confusion_matrix(
    predictions: list[dict[str, Any]],
    labels: Iterable[str],
) -> dict[str, Any]:
    label_list = list(labels)
    y_true = [p["label"] for p in predictions]
    y_pred = [p["prediction"] for p in predictions]
    matrix = confusion_matrix(y_true, y_pred, labels=label_list).tolist()
    return {"labels": label_list, "matrix": matrix}


def _baseline_delta(
    current: dict[str, Any],
    baseline_path: Optional[Path],
) -> Optional[dict[str, float]]:
    if not baseline_path:
        return None
    if not baseline_path.exists():
        logger.warning("Baseline file %s not found — skipping delta", baseline_path)
        return None
    baseline = json.loads(baseline_path.read_text())
    base_metrics = baseline.get("metrics", {})
    deltas = {}
    for key in ("weighted_f1", "macro_f1", "accuracy"):
        if key in current and key in base_metrics:
            deltas[key] = round(float(current[key]) - float(base_metrics[key]), 6)
    return deltas


def evaluate(
    *,
    test_set_path: Path,
    threshold: float,
    threshold_metric: str,
    model_path: Optional[str],
    baseline_path: Optional[Path],
    labels: Iterable[str] = DEFAULT_LABELS,
    classifier_factory: Optional[ClassifierFactory] = None,
) -> dict[str, Any]:
    """Run the evaluation and return a CI-shaped result dict."""
    if threshold_metric not in ALLOWED_THRESHOLD_METRICS:
        raise ValueError(
            f"--threshold-metric must be one of {ALLOWED_THRESHOLD_METRICS}"
        )

    # Resolve the factory at call time (not as a function default) so tests
    # that monkeypatch ``_default_classifier_factory`` see their stub even
    # when calling through ``main()``.
    factory = classifier_factory or _default_classifier_factory

    df = load_local_dataset(test_set_path)
    if df.empty:
        raise ValueError(f"Held-out dataset is empty: {test_set_path}")

    classifier = factory(model_path)

    # Inline loop instead of SafetyClassifierEvaluator: keeps this script
    # importable in environments without torch (e.g. unit tests with stubs).
    predictions: list[dict[str, Any]] = []
    for row in df.itertuples(index=False):
        outcome = classifier.classify(row.prompt)
        predictions.append(
            {
                "prompt": row.prompt,
                "label": row.label,
                "prediction": outcome.intent,
                "confidence": getattr(outcome, "confidence", None),
            }
        )

    metrics = compute_classification_metrics(
        df["label"].tolist(),
        [p["prediction"] for p in predictions],
    )
    actual = float(metrics[threshold_metric])
    passed = actual >= threshold

    return {
        "metrics": metrics,
        "confusion_matrix": _build_confusion_matrix(predictions, labels),
        "threshold": {
            "metric": threshold_metric,
            "value": threshold,
            "actual": actual,
            "passed": passed,
        },
        "baseline_delta": _baseline_delta(metrics, baseline_path),
        "n_samples": int(len(df)),
        "model_path": model_path or "auto",
        "evaluated_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
    }


# ---------------------------------------------------------------------------
# Output rendering
# ---------------------------------------------------------------------------


def _fmt(value: float) -> str:
    return f"{value:.4f}"


def _fmt_delta(value: Optional[float]) -> str:
    if value is None:
        return "—"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.4f}"


def render_markdown(result: dict[str, Any]) -> str:
    threshold = result["threshold"]
    status_emoji = "✅" if threshold["passed"] else "❌"
    status_word = "PASS" if threshold["passed"] else "FAIL"

    lines: list[str] = [
        "<!-- guard-eval-comment -->",
        "## Guard model evaluation",
        "",
        f"**Status:** {status_emoji} **{status_word}** — "
        f"`{threshold['metric']}` = `{_fmt(threshold['actual'])}` "
        f"(threshold `{_fmt(threshold['value'])}`)",
        "",
        "### Overall metrics",
        "",
        "| Metric | Value | Δ vs baseline |",
        "| --- | --- | --- |",
    ]

    deltas = result.get("baseline_delta") or {}
    for key in ("weighted_f1", "macro_f1", "accuracy"):
        if key in result["metrics"]:
            lines.append(
                f"| `{key}` | {_fmt(result['metrics'][key])} | {_fmt_delta(deltas.get(key))} |"
            )

    # Per-label table from sklearn classification_report
    report = result["metrics"].get("classification_report", {})
    label_rows = [
        (label, vals)
        for label, vals in report.items()
        if isinstance(vals, dict) and label not in {"accuracy", "macro avg", "weighted avg"}
    ]
    if label_rows:
        lines += [
            "",
            "### Per-label",
            "",
            "| Label | Precision | Recall | F1 | Support |",
            "| --- | --- | --- | --- | --- |",
        ]
        for label, vals in label_rows:
            lines.append(
                f"| `{label}` | {_fmt(vals.get('precision', 0))} "
                f"| {_fmt(vals.get('recall', 0))} "
                f"| {_fmt(vals.get('f1-score', 0))} "
                f"| {int(vals.get('support', 0))} |"
            )

    cm = result["confusion_matrix"]
    if cm["labels"]:
        header = "| true ╲ pred | " + " | ".join(f"`{c}`" for c in cm["labels"]) + " |"
        sep = "| --- |" + " --- |" * len(cm["labels"])
        lines += ["", "### Confusion matrix", "", header, sep]
        for label, row in zip(cm["labels"], cm["matrix"]):
            lines.append(
                f"| `{label}` | " + " | ".join(str(v) for v in row) + " |"
            )

    lines += [
        "",
        f"**Model:** `{result['model_path']}` &nbsp;&nbsp; "
        f"**Samples:** `{result['n_samples']}` &nbsp;&nbsp; "
        f"**Evaluated:** `{result['evaluated_at']}`",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Guard classifier against a held-out test set and "
        "enforce a metric threshold in CI."
    )
    parser.add_argument(
        "--test-set-path",
        type=Path,
        default=Path("backend/data/guard_holdout.csv"),
        help="Path to the held-out CSV (default: backend/data/guard_holdout.csv).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Minimum acceptable value for the threshold metric (default: 0.85).",
    )
    parser.add_argument(
        "--threshold-metric",
        choices=ALLOWED_THRESHOLD_METRICS,
        default="weighted_f1",
        help="Metric to check against the threshold (default: weighted_f1).",
    )
    parser.add_argument(
        "--model-path",
        help="Override the model directory. Default: auto-detected via "
        "guard_config.get_trained_model_path().",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Path to a baseline metrics JSON to compute deltas against.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("metrics.json"),
        help="Where to write the machine-readable metrics JSON.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("metrics.md"),
        help="Where to write the markdown summary.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)

    # Configure JSON logging if available (issue #66). Fall back silently
    # so this script is also runnable in a stripped-down CI environment.
    try:
        from app.core.logging import configure_logging

        configure_logging("INFO")
    except Exception:  # pragma: no cover - logging is best-effort
        logging.basicConfig(level=logging.INFO)

    model_path = args.model_path or guard_config.get_trained_model_path()
    logger.info(
        "guard_eval.start",
        extra={
            "test_set_path": str(args.test_set_path),
            "model_path": str(model_path),
            "threshold": args.threshold,
            "threshold_metric": args.threshold_metric,
        },
    )

    result = evaluate(
        test_set_path=args.test_set_path,
        threshold=args.threshold,
        threshold_metric=args.threshold_metric,
        model_path=model_path,
        baseline_path=args.baseline,
    )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True))

    markdown = render_markdown(result)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(markdown)

    threshold = result["threshold"]
    logger.info(
        "guard_eval.complete",
        extra={
            "passed": threshold["passed"],
            "metric": threshold["metric"],
            "actual": threshold["actual"],
            "threshold": threshold["value"],
            "n_samples": result["n_samples"],
        },
    )

    # Human-readable line for plain-text CI logs in addition to JSON.
    summary = (
        f"{'PASS' if threshold['passed'] else 'FAIL'}: "
        f"{threshold['metric']}={threshold['actual']:.4f} "
        f"threshold={threshold['value']:.4f} "
        f"n={result['n_samples']}"
    )
    print(summary, file=sys.stderr)

    return 0 if threshold["passed"] else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())