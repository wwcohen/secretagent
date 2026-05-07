# FinQA data provenance

**Benchmark:** [FinQA: A Dataset of Numerical Reasoning over Financial Data](https://aclanthology.org/2021.emnlp-main.300) (Chen et al., EMNLP 2021).

**Official repository:** [github.com/czyssrs/FinQA](https://github.com/czyssrs/FinQA) (MIT license). Raw JSON is downloaded from the `dataset/` path on the default branch into `data/raw/` by `download.py`.

**Splits used here**

| Our file      | FinQA file   | Labels |
|---------------|--------------|--------|
| `train.json`  | `train.json` | yes (`exe_ans` / `answer`) |
| `valid.json`  | `dev.json`   | yes |
| `test.json`   | `test.json`  | yes |

**Case format:** Each `Case` passes a single string `input_args[0]`: structured prompt with pre-table text, a markdown table, post-table text, and the question. `metadata["finqa_id"]` stores the official example id for traceability.

**Regeneration**

```bash
uv run python benchmarks/finqa/data/download.py
uv run python benchmarks/finqa/data/build_datasets.py
```

Large raw files are gitignored; generated JSON splits are gitignored. Quick slice:

```bash
uv run python benchmarks/finqa/data/build_datasets.py --max-per-split 20
```

**If `dataset.n=100` only runs a handful of examples:** rebuild without `--max-per-split`.
