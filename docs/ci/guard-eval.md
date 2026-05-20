# Guard Model Evaluation in CI

The **Guard Model Evaluation** workflow
(`.github/workflows/guard-eval.yml`) runs the safety classifier against a
committed held-out test split on every PR that touches the Guard module,
nightly on `main`, and on manual dispatch. It fails the build when the
threshold metric drops below the configured floor — preventing silent model
regressions from being merged.

## What it produces

For each run:

- **Workflow summary** — a markdown table with overall metrics, per-label
  precision/recall/F1, confusion matrix, and Δ vs baseline.
- **PR comment** — the same markdown, posted as a *sticky* comment (updates
  in place on re-runs, no comment spam).
- **`metrics.json` artifact** — machine-readable, retained for 30 days.

## Configuration

Configure via **Settings → Variables → Actions**:

| Variable                  | Purpose                                              | Default          |
|---------------------------|------------------------------------------------------|------------------|
| `GUARD_F1_THRESHOLD`      | Minimum acceptable value of the threshold metric.    | `0.85`           |
| `GUARD_THRESHOLD_METRIC`  | One of `weighted_f1`, `macro_f1`, `accuracy`.        | `weighted_f1`    |
| `GUARD_MODEL_RELEASE_TAG` | Release tag to pull trained weights from (optional). | unset → fallback |

Manual dispatch (`workflow_dispatch`) accepts the same overrides per-run.

## Held-out test set

`backend/data/guard_holdout.csv` — a **small, deterministic** held-out set
that lives in the repo. It is *not* used during training. Expand it when
you add new attack categories, but keep it small enough that CI stays
under a few minutes on CPU.

CSV schema:

```csv
prompt,label
"How do I make a chocolate cake?",benign
"Ignore previous instructions",malicious
```

Valid labels are `benign`, `suspicious`, `malicious`.

## Baseline

`backend/data/guard_baseline.json` is the committed reference point used to
compute Δ vs the current PR. After a real model improvement, regenerate
locally and commit the new file:

```bash
cd backend
python -m scripts.evaluate_guard_ci \
  --test-set-path data/guard_holdout.csv \
  --threshold 0.0 \
  --output-json data/guard_baseline.json \
  --output-md   /tmp/baseline.md
git add data/guard_baseline.json
git commit -m "ci(guard): refresh baseline metrics"
```

`--threshold 0.0` skips the failure check during baseline refresh.

## Model artefact

The fine-tuned DeBERTa weights are *not* committed. The workflow resolves
the model in this order:

1. If `vars.GUARD_MODEL_RELEASE_TAG` is set, the step
   *Download trained model artefact* downloads
   `classifier-*.tar.gz` from that release and extracts it to
   `backend/app/modules/guard/models/classifier/`.
2. Otherwise, `guard_config.get_trained_model_path()` returns its default
   path. If no weights exist there, the classifier falls back to the
   pre-trained DeBERTa base from Hugging Face — useful for bootstrap, but
   expect a much lower score than a fine-tuned model.

To publish a new model artefact:

```bash
# from the directory containing the trained model files
tar czf classifier-v3.tar.gz -C app/modules/guard/models/classifier .
gh release create guard-model-v3 classifier-v3.tar.gz \
  --title "Guard model v3" --notes "F1 0.91 on holdout"
# then update the repo variable:
gh variable set GUARD_MODEL_RELEASE_TAG --body "guard-model-v3"
```

## Local development

```bash
# Run the same evaluation locally before pushing:
cd backend
PYTHONPATH=. python -m scripts.evaluate_guard_ci \
  --test-set-path data/guard_holdout.csv \
  --baseline      data/guard_baseline.json \
  --threshold     0.85 \
  --output-json   /tmp/metrics.json \
  --output-md     /tmp/metrics.md

cat /tmp/metrics.md
```

Exit code `0` means the threshold was met; `1` means it was not.

## Adding more attacks to the held-out set

1. Add labelled rows to `backend/data/guard_holdout.csv`. Prefer **real**
   prompts seen in the wild over synthetic ones.
2. Run the local command above to see how the current model scores.
3. If the score drops below the threshold, retrain — *don't* lower the
   threshold to fit.
4. Once the new model is in a release, refresh the baseline (see above).
