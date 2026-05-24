# aegisai-guard

Standalone Python package for LLM prompt injection detection — extracted from the [AegisAI](https://github.com/SdSarthak/AegisAI) platform.

> **Status:** scaffold only — contributions welcome. See the open issues on the main repo.

## Installation

```bash
pip install aegisai-guard
```

## Usage

```python
from aegisai_guard import LLMGuard, SanitizationLevel

guard = LLMGuard(sanitization_level=SanitizationLevel.MEDIUM)
result = guard.guard("Ignore all previous instructions and...")
print(result["decision"])  # "block"
```

## How it works

Four-layer pipeline:
1. **RegexFilter** — fast pattern matching (~0 ms)
2. **IntentClassifier** — fine-tuned DeBERTa-v3-small when installed, deterministic heuristics otherwise
3. **DecisionEngine** — combines scores into allow / sanitize / block
4. **PromptSanitizer** — strips malicious meta-instructions when decision is `sanitize`

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) in the root of the AegisAI repo.
