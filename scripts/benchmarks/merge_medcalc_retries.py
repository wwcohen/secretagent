#!/usr/bin/env python3
"""Merge MedCalc retry result dirs into one clean result dir.

The base result dir must contain the full 1100-row first pass. Retry dirs may
contain only failed case names. A retry row replaces the base row only when the
base row is retryable and the retry row is no longer retryable.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path
from typing import Any

from classify_medcalc_failures import classify


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def case_name(row: dict[str, Any]) -> str:
    return str(row.get("case_name") or row.get("name") or row.get("example_name") or "")


def write_outputs(rows: list[dict[str, Any]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "results.jsonl").open("w") as f:
        for row in rows:
            f.write(json.dumps(row, default=str) + "\n")

    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key == "rollout" or key in seen:
                continue
            seen.add(key)
            fieldnames.append(key)
    with (out_dir / "results.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: v for k, v in row.items() if k != "rollout"})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--retry-dir", action="append", default=[], type=Path)
    args = parser.parse_args()

    base_rows = read_jsonl(args.base_dir / "results.jsonl")
    if not base_rows:
        raise SystemExit(f"No base rows found in {args.base_dir / 'results.jsonl'}")

    retryable_base: dict[str, str] = {}
    for row in base_rows:
        label, _ = classify(row)
        if label:
            retryable_base[case_name(row)] = label

    replacements: dict[str, dict[str, Any]] = {}
    still_retryable: dict[str, str] = {}
    retry_rows_seen = 0
    for retry_dir in args.retry_dir:
        for row in read_jsonl(retry_dir / "results.jsonl"):
            retry_rows_seen += 1
            name = case_name(row)
            if name not in retryable_base:
                continue
            label, _ = classify(row)
            if label:
                still_retryable[name] = label
                continue
            replacements[name] = row
            still_retryable.pop(name, None)

    merged_rows: list[dict[str, Any]] = []
    for row in base_rows:
        name = case_name(row)
        merged_rows.append(replacements.get(name, row))

    remaining = []
    for row in merged_rows:
        label, reason = classify(row)
        if label:
            remaining.append({
                "case_name": case_name(row),
                "label": label,
                "predicted_output": row.get("predicted_output", ""),
                "reason": reason,
            })

    write_outputs(merged_rows, args.out_dir)
    if (args.base_dir / "config.yaml").exists():
        shutil.copy2(args.base_dir / "config.yaml", args.out_dir / "config.yaml")

    summary = {
        "base_dir": str(args.base_dir),
        "out_dir": str(args.out_dir),
        "retry_dirs": [str(path) for path in args.retry_dir],
        "base_rows": len(base_rows),
        "base_retryable": len(retryable_base),
        "retry_rows_seen": retry_rows_seen,
        "successful_replacements": len(replacements),
        "remaining_retryable": len(remaining),
    }
    (args.out_dir / "merge_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )
    (args.out_dir / "remaining_retryable_failures.json").write_text(
        json.dumps(remaining, indent=2, default=str)
    )
    (args.out_dir / "remaining_retryable_case_names.txt").write_text(
        "".join(f"{item['case_name']}\n" for item in remaining)
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
