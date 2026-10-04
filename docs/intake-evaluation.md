# Intake evaluation

`sample-data/intake-evaluation.json` contains 25 fictional customer messages and
their expected extracted quantity, catalog SKU, and review/availability status.
The regression cases cover exact catalog references, missing quantities,
unknown items, and requests that exceed available stock.

Run the evaluation from `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_intake_evaluation.py
```

Each case passes only when the local extractor and matcher return the expected
number of items, quantities, suggested SKUs, and statuses. A passing run
therefore measures exact agreement on all four fields across the 25-case set.
The normal pytest summary reports the number of passing and failing cases.

This dataset evaluates the deterministic local demo extractor and matcher. It
does not measure OpenAI extraction quality, and the expected cases should be
expanded with reviewed examples before using them to compare live providers.
