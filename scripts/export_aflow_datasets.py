"""Export sports_understanding + finqa splits to AFlow JSONL format.

Reproduces the paper cells' exact subsetting by calling
secretagent.dataset.Dataset.configure — the same code path cli.expt uses —
so the AFlow search/validation sets are bit-identical to the NSGA-II cells:

  - sports validate: valid.json, shuffle_seed=137, n=50   (NSGA-II sweep subset)
  - sports test:     test.json,  shuffle_seed=137, all 100
  - finqa validate:  valid.json, unshuffled head-50        (NSGA-II sweep subset)
  - finqa test:      test.json,  unshuffled head-300       (REPORT.md test set)

Sports rows use BBHBenchmark keys (input/target, yes|no) with the original
BBH plausibility phrasing reconstructed around the stored sentence. FinQA
rows use question/answer keys with the case input exported verbatim (it is
already the fully formatted problem string).

Usage (from repo root; needs the project env for secretagent.dataset):
    uv run python scripts/export_aflow_datasets.py [--aflow-dir DIR]
"""

import argparse
import json
from pathlib import Path

from secretagent.dataset import Dataset

ROOT = Path(__file__).resolve().parents[1]


def load(p: Path) -> Dataset:
    return Dataset.model_validate_json(p.read_text(encoding="utf-8"))


def write_jsonl(rows, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows):4d} rows -> {path}")


def sports_rows(ds: Dataset):
    return [{
        "input": f'Is the following sentence plausible? "{c.input_args[0]}"',
        "target": "yes" if c.expected_output else "no",
        "case_name": c.name,
    } for c in ds.cases]


def finqa_rows(ds: Dataset):
    none_gold = sum(1 for c in ds.cases if c.expected_output is None)
    if none_gold:
        print(f"WARNING: {none_gold} cases with None gold in this slice "
              "(scored as wrong by AFlow, excluded by our harness — resolve before comparing)")
    return [{
        "question": c.input_args[0],
        "answer": c.expected_output,
        "case_name": c.name,
        "finqa_id": (c.metadata or {}).get("finqa_id"),
    } for c in ds.cases]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aflow-dir", default="C:/Users/STUDENT/aflow")
    args = ap.parse_args()
    out = Path(args.aflow_dir) / "data" / "datasets"

    sp = ROOT / "benchmarks" / "bbh" / "sports_understanding" / "data"
    write_jsonl(sports_rows(load(sp / "valid.json").configure(shuffle_seed=137, n=50)),
                out / "sportsunderstanding_validate.jsonl")
    write_jsonl(sports_rows(load(sp / "test.json").configure(shuffle_seed=137)),
                out / "sportsunderstanding_test.jsonl")

    fq = ROOT / "benchmarks" / "finqa" / "data"
    write_jsonl(finqa_rows(load(fq / "valid.json").configure(n=50)),
                out / "finqa_validate.jsonl")
    write_jsonl(finqa_rows(load(fq / "test.json").configure(n=300)),
                out / "finqa_test.jsonl")


if __name__ == "__main__":
    main()
