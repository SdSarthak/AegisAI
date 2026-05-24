<!-- guard-eval-comment -->
## Guard model evaluation

**Status:** ✅ **PASS** — `weighted_f1` = `0.1667` (threshold `0.0000`)

### Overall metrics

| Metric | Value | Δ vs baseline |
| --- | --- | --- |
| `weighted_f1` | 0.1667 | -0.0784 |
| `macro_f1` | 0.1667 | -0.0294 |
| `accuracy` | 0.3333 | -0.0833 |

### Per-label

| Label | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| `benign` | 0.0000 | 0.0000 | 0.0000 | 5 |
| `malicious` | 0.3333 | 1.0000 | 0.5000 | 4 |
| `suspicious` | 0.0000 | 0.0000 | 0.0000 | 3 |

### Confusion matrix

| true ╲ pred | `benign` | `suspicious` | `malicious` |
| --- | --- | --- | --- |
| `benign` | 0 | 0 | 5 |
| `suspicious` | 0 | 0 | 3 |
| `malicious` | 0 | 0 | 4 |

**Model:** `/app/app/modules/guard/models/classifier` &nbsp;&nbsp; **Samples:** `12` &nbsp;&nbsp; **Evaluated:** `2026-05-24T11:37:55Z`
