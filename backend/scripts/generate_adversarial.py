"""
Adversarial dataset generator for Guard classifier training.
Issue #78 — Add adversarial dataset generator for Guard classifier training

Usage:
    python backend/scripts/generate_adversarial.py [--limit N] [--output PATH]

    --limit N      Number of seed malicious prompts to process (default: all)
    --output PATH  CSV to append results to (default: backend/data/prompts.csv)

What it does:
    1. Reads existing malicious prompts from the seed CSV.
    2. For each seed, generates 5 adversarial variants via the LLM:
         - paraphrase        : rephrase while keeping the malicious intent
         - translate         : translate to another language then back to English
         - base64            : wrap the core instruction in Base64 encoding
         - split_lines       : split the prompt across multiple lines / newlines
         - unicode_obfuscate : replace key characters with Unicode look-alikes
    3. Appends all new rows (label=malicious) to the output CSV.

Goal: double the training set with hard negatives that bypass naive filters.

Requirements:
    - LLM_API_KEY and optionally LLM_BASE_URL / LLM_MODEL set in backend/.env
    - pip install openai python-dotenv (already in requirements.txt)
"""

import argparse
import csv
import sys
import textwrap
from pathlib import Path

# ── Bootstrap: make sure backend/ is on sys.path so app.core.config loads ──
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from app.modules.llm.llm_client import LLMClient  # noqa: E402

# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_CSV = BACKEND_DIR / "data" / "prompts.csv"

MUTATION_SYSTEM_PROMPT = textwrap.dedent("""
    You are a red-team security researcher generating adversarial prompt variants
    for training an AI safety classifier. Your output will be used ONLY to improve
    detection of prompt injection attacks — never to cause real harm.

    Follow the instruction exactly. Output ONLY the mutated prompt text, nothing else.
    Do not add explanations, disclaimers, or labels.
""").strip()

MUTATION_PROMPTS = {
    "paraphrase": (
        "Rewrite the following malicious prompt using different wording while "
        "preserving its harmful intent. Output only the rewritten prompt.\n\n"
        "Original:\n{seed}"
    ),
    "translate": (
        "Translate the following malicious prompt to French, then immediately "
        "translate it back to English using different phrasing. "
        "Output only the final English version.\n\n"
        "Original:\n{seed}"
    ),
    "base64": (
        "Rewrite the following malicious prompt so that the core harmful instruction "
        "is Base64-encoded and embedded inside an innocent-looking wrapper sentence "
        "that asks the model to decode and follow it. "
        "Output only the final prompt.\n\n"
        "Original:\n{seed}"
    ),
    "split_lines": (
        "Rewrite the following malicious prompt by splitting it across multiple lines "
        "and inserting benign filler text between the lines so the harmful intent is "
        "obscured but still present when read together. "
        "Output only the rewritten prompt.\n\n"
        "Original:\n{seed}"
    ),
    "unicode_obfuscate": (
        "Rewrite the following malicious prompt by replacing several key Latin letters "
        "with visually identical Unicode characters (e.g. Cyrillic a instead of a, "
        "Greek o instead of o). Keep the prompt readable but subtly obfuscated. "
        "Output only the rewritten prompt.\n\n"
        "Original:\n{seed}"
    ),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_seeds(csv_path: Path) -> list[str]:
    """Return all prompts labelled 'malicious' from the CSV."""
    seeds = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("label", "").strip().lower() == "malicious":
                seeds.append(row["prompt"].strip())
    return seeds


def existing_prompts(csv_path: Path) -> set[str]:
    """Return the set of all existing prompt texts to avoid duplicates."""
    prompts = set()
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            prompts.add(row["prompt"].strip())
    return prompts


def generate_variants(llm: LLMClient, seed: str) -> dict[str, str]:
    """Generate one variant per mutation type for a single seed prompt."""
    variants: dict[str, str] = {}
    for mutation_name, template in MUTATION_PROMPTS.items():
        user_prompt = template.format(seed=seed)
        try:
            variant = llm.call(
                prompt=user_prompt,
                system_prompt=MUTATION_SYSTEM_PROMPT,
                temperature=0.9,
                max_tokens=512,
            ).strip()
            if variant:
                variants[mutation_name] = variant
        except Exception as exc:
            print(f"  [WARN] {mutation_name} failed: {exc}", file=sys.stderr)
    return variants


def append_rows(csv_path: Path, new_rows: list[dict]) -> int:
    """Append new_rows to the CSV. Returns number of rows written."""
    if not new_rows:
        return 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["prompt", "label"])
        for row in new_rows:
            writer.writerow(row)
    return len(new_rows)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate adversarial prompt variants and append to prompts.csv"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of seed prompts to process (default: all)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_CSV,
        help=f"CSV file to append results to (default: {DEFAULT_CSV})",
    )
    args = parser.parse_args()

    csv_path: Path = args.output
    if not csv_path.exists():
        print(f"[ERROR] CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    seeds = load_seeds(csv_path)
    if not seeds:
        print("[ERROR] No malicious prompts found in CSV.", file=sys.stderr)
        sys.exit(1)

    if args.limit:
        seeds = seeds[: args.limit]

    print(f"Loaded {len(seeds)} seed malicious prompt(s) from {csv_path}")

    try:
        llm = LLMClient()
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    seen = existing_prompts(csv_path)
    new_rows: list[dict] = []

    for i, seed in enumerate(seeds, 1):
        print(f"[{i}/{len(seeds)}] Generating variants ...")
        variants = generate_variants(llm, seed)
        for mutation_name, variant_text in variants.items():
            if variant_text not in seen:
                new_rows.append({"prompt": variant_text, "label": "malicious"})
                seen.add(variant_text)
                print(f"  + {mutation_name}")
            else:
                print(f"  ~ {mutation_name} (duplicate, skipped)")

    written = append_rows(csv_path, new_rows)
    print(f"\nDone. {written} new adversarial row(s) appended to {csv_path}.")


if __name__ == "__main__":
    main()
