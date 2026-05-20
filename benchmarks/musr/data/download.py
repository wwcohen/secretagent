# /// script
# dependencies = ["datasets"]
# ///
"""Download the MUSR dataset from HuggingFace and save as Dataset JSON files.

For each MUSR task, writes a standard secretagent Dataset JSON file into
the task's data/ subdirectory:

    benchmarks/musr/murder/data/murder_mysteries.json
    benchmarks/musr/object/data/object_placements.json
    benchmarks/musr/team/data/team_allocation.json

Each Case stores (narrative, question, choices) as input_args and the
0-based answer_index as expected_output.

Usage (from repo root):
    uv run benchmarks/musr/data/download.py
"""

import ast
import json
from pathlib import Path

from datasets import load_dataset

# (huggingface split name, task subdir name)
SPLITS = [
    ("murder_mysteries",  "murder"),
    ("object_placements", "object"),
    ("team_allocation",   "team"),
]


def _to_case(i: int, ex: dict) -> dict:
    choices = ex["choices"]
    if isinstance(choices, str):
        choices = ast.literal_eval(choices)
    return {
        "name": f"ex{i:03d}",
        "input_args": [ex["narrative"], ex["question"], choices],
        "expected_output": ex["answer_index"],
    }


def main():
    benchmark_dir = Path(__file__).resolve().parent.parent
    ds = load_dataset("TAUR-Lab/MuSR")
    for split, task in SPLITS:
        out_dir = benchmark_dir / task / "data"
        out_dir.mkdir(parents=True, exist_ok=True)
        cases = [_to_case(i, dict(row)) for i, row in enumerate(ds[split])]
        dataset = {"name": "musr", "split": split, "cases": cases}
        out_path = out_dir / f"{split}.json"
        with open(out_path, "w") as f:
            json.dump(dataset, f, indent=2)
        print(f"{split}: {len(cases)} cases -> {out_path}")


if __name__ == "__main__":
    main()
