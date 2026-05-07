#!/usr/bin/env python3
"""Convert raw FinQA JSON into secretagent ``Dataset`` JSON files.

Expects ``raw/*.json`` from ``download.py``. Writes:

- ``train.json`` — official train
- ``valid.json`` — official dev (development set)
- ``test.json`` — official public test (has labels)

Usage::

    uv run python benchmarks/finqa/data/build_datasets.py
    uv run python benchmarks/finqa/data/build_datasets.py --max-per-split 50   # smoke test

"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Run as script: add project src for secretagent
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from secretagent.dataset import Case, Dataset


def _table_to_markdown(table: list[list[str]]) -> str:
    if not table:
        return ""
    lines = []
    for row in table:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def format_problem(
    pre_text: list[str],
    table: list[list[str]],
    post_text: list[str],
    question: str,
) -> str:
    parts = [
        "You are answering a numerical reasoning question over a financial report excerpt.",
        "",
        "## Context (text before table)",
        "\n".join(pre_text) if pre_text else "(none)",
        "",
        "## Table",
        _table_to_markdown(table) if table else "(none)",
        "",
        "## Context (text after table)",
        "\n".join(post_text) if post_text else "(none)",
        "",
        "## Question",
        question,
        "",
        "Reply with only the final answer (a number, percentage, or short phrase as appropriate). "
        "For rates or proportions you may answer as a decimal (e.g. 0.935) or as a percent (e.g. 93.5%). "
        "Do not use XML tags or labels—only the value.",
    ]
    return "\n".join(parts)


def _gold_answer(qa: dict) -> tuple[object | None, bool]:
    """Returns (expected_output, has_label)."""
    if "exe_ans" in qa and qa["exe_ans"] is not None:
        return qa["exe_ans"], True
    if qa.get("answer") not in (None, ""):
        return str(qa["answer"]), True
    return None, False


def raw_to_cases(rows: list[dict], split: str, max_n: int | None) -> list[Case]:
    cases: list[Case] = []
    for i, row in enumerate(rows):
        if max_n is not None and len(cases) >= max_n:
            break
        qa = row.get("qa") or {}
        question = qa.get("question")
        if not question:
            continue

        fid = row.get("id")
        if not fid:
            fname = row.get("filename", "unknown")
            fid = f"{fname}::{split}::{i}"

        problem = format_problem(
            row.get("pre_text") or [],
            row.get("table") or [],
            row.get("post_text") or [],
            question,
        )
        gold, has_label = _gold_answer(qa)
        cases.append(
            Case(
                name=f"{split}.{len(cases):05d}",
                metadata={
                    "finqa_id": fid,
                    "filename": row.get("filename"),
                    "split": split,
                },
                input_args=[problem],
                expected_output=gold if has_label else None,
            )
        )
    return cases


def write_dataset(name: str, split: str, cases: list[Case], out_path: Path) -> None:
    ds = Dataset(name=name, split=split, metadata={"source": "FinQA/czyssrs"}, cases=cases)
    out_path.write_text(ds.model_dump_json(indent=2), encoding="utf-8")
    print(f"Wrote {out_path} ({len(cases)} cases)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-per-split",
        type=int,
        default=None,
        help="Limit examples per split (for quick tests)",
    )
    args = parser.parse_args()

    data_dir = Path(__file__).resolve().parent
    raw_dir = data_dir / "raw"
    if not raw_dir.is_dir():
        print(f"Missing {raw_dir}. Run download.py first.", file=sys.stderr)
        sys.exit(1)

    mapping = [
        ("train.json", "train", "train"),
        ("dev.json", "valid", "valid"),
        ("test.json", "test", "test"),
    ]

    for raw_name, split_key, out_split in mapping:
        path = raw_dir / raw_name
        if not path.exists():
            print(f"Skip missing {path}")
            continue
        rows = json.loads(path.read_text(encoding="utf-8"))
        cases = raw_to_cases(rows, split_key, args.max_per_split)
        write_dataset("finqa", out_split, cases, data_dir / f"{out_split}.json")


if __name__ == "__main__":
    main()
