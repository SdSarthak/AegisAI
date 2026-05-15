"""
Export queued GuardFeedback rows as training examples in prompts.csv format.
Issue #80 — Add continual learning pipeline: queue false positives for Guard retraining

Usage:
    python backend/scripts/export_guard_feedback.py [--output PATH] [--dry-run]

    --output PATH  CSV to append results to (default: backend/data/prompts.csv)
    --dry-run      Print rows that would be exported without writing or marking them

What it does:
    1. Queries all GuardFeedback rows where exported="false".
    2. Maps each row to a prompts.csv row:
         - false_positive  → prompt, label=benign   (Guard over-blocked)
         - false_negative  → prompt, label=malicious (Guard missed it)
         - correct         → skipped (no new information for retraining)
    3. Appends the new rows to prompts.csv.
    4. Marks exported rows as exported="true" so they are not re-exported.

How to trigger a retraining run after export:
    1. Export feedback:
         python backend/scripts/export_guard_feedback.py

    2. Retrain the Guard classifier on the updated dataset:
         python backend/app/modules/guard/train.py

       Or use the Jupyter notebook (GPU-accelerated, Colab-ready):
         notebooks/train_guard_classifier.ipynb

    3. The retrained model weights are saved to:
         backend/app/modules/guard/models/

    4. Restart the backend to load the new weights:
         uvicorn app.main:app --reload

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import argparse
import csv
import sys
from pathlib import Path

# ── Bootstrap ─────────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from app.core.database import SessionLocal          # noqa: E402
from app.models.guard_feedback import GuardFeedback  # noqa: E402

# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_CSV = BACKEND_DIR / "data" / "prompts.csv"

# Map feedback_type → CSV label
LABEL_MAP = {
    "false_positive": "benign",
    "false_negative": "malicious",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def existing_prompts(csv_path: Path) -> set[str]:
    """Return set of all existing prompt texts to avoid duplicates."""
    prompts: set[str] = set()
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            prompts.add(row["prompt"].strip())
    return prompts


def append_rows(csv_path: Path, rows: list[dict]) -> int:
    """Append rows to CSV. Returns number written."""
    if not rows:
        return 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["prompt", "label"])
        for row in rows:
            writer.writerow(row)
    return len(rows)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export queued GuardFeedback rows to prompts.csv for retraining"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_CSV,
        help=f"CSV file to append results to (default: {DEFAULT_CSV})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print rows without writing or marking them as exported",
    )
    args = parser.parse_args()

    csv_path: Path = args.output
    if not csv_path.exists():
        print(f"[ERROR] CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        # Fetch all un-exported feedback rows
        pending = (
            db.query(GuardFeedback)
            .filter(GuardFeedback.exported == "false")
            .order_by(GuardFeedback.created_at.asc())
            .all()
        )

        if not pending:
            print("No pending feedback rows to export.")
            return

        print(f"Found {len(pending)} pending feedback row(s).")

        seen = existing_prompts(csv_path)
        new_rows: list[dict] = []
        exported_ids: list[int] = []

        for fb in pending:
            label = LABEL_MAP.get(fb.feedback_type)
            if label is None:
                # feedback_type="correct" — skip, no new training signal
                print(f"  SKIP  id={fb.id} feedback_type=correct")
                exported_ids.append(fb.id)
                continue

            prompt_text = fb.prompt.strip()
            if prompt_text in seen:
                print(f"  SKIP  id={fb.id} (duplicate prompt)")
                exported_ids.append(fb.id)
                continue

            print(f"  QUEUE id={fb.id} feedback_type={fb.feedback_type} → label={label}")
            new_rows.append({"prompt": prompt_text, "label": label})
            seen.add(prompt_text)
            exported_ids.append(fb.id)

        if args.dry_run:
            print(f"\n[DRY RUN] Would append {len(new_rows)} row(s) to {csv_path}.")
            print("[DRY RUN] No changes written.")
            return

        # Write to CSV
        written = append_rows(csv_path, new_rows)

        # Mark all processed rows as exported
        if exported_ids:
            db.query(GuardFeedback).filter(
                GuardFeedback.id.in_(exported_ids)
            ).update({"exported": "true"}, synchronize_session=False)
            db.commit()

        print(f"\nDone. {written} new row(s) appended to {csv_path}.")
        print(f"{len(exported_ids)} feedback row(s) marked as exported.")
        print("\nNext step — retrain the Guard classifier:")
        print("  python backend/app/modules/guard/train.py")

    finally:
        db.close()


if __name__ == "__main__":
    main()
