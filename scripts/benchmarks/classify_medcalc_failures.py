#!/usr/bin/env python3
"""Classify MedCalc result rows that should be retried for fairness.

This does not label model-wrong answers as retryable. It only extracts rows
whose prediction/rollout looks like infrastructure, API, timeout, validation, or
request-limit failure. It writes JSON/CSV summaries into the result directory.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any


RETRY_PATTERNS = [
    ("api_unavailable", r"\b(500|503|502|504|InternalServer|ServiceUnavailable|UNAVAILABLE|server disconnected|Bad Gateway|Gateway Timeout)\b"),
    ("rate_limit", r"\b(429|RateLimit|rate limit|quota|Too Many Requests)\b"),
    ("timeout", r"\b(timeout|timed out|exceeded llm\.timeout|TimeoutError)\b"),
    ("request_limit", r"\b(request_limit|maximum number of retries|exceeded.*retries)\b"),
    ("validation", r"\b(ValidationError|validation error|tool-call.*args|failed to parse|output validation)\b"),
    ("transport", r"\b(APIConnectionError|APIError|ConnectionError|Connection error|RemoteProtocolError|ReadError|WriteError|connection reset)\b"),
    ("local_cache", r"\b(invalid load key|pickle|UnpicklingError|EOFError)\b"),
    ("nan_usage", r"\bnan\b"),
]


def flatten_text(value: Any, limit: int = 20000) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except TypeError:
        text = str(value)
    return text[:limit]


def is_nan(value: Any) -> bool:
    try:
        return math.isnan(float(value))
    except (TypeError, ValueError):
        return False


def classify(row: dict[str, Any]) -> tuple[str | None, str]:
    predicted = str(row.get("predicted_output", ""))
    rollout_text = flatten_text(row.get("rollout", ""))
    text = f"{predicted}\n{rollout_text}"

    if predicted.startswith("**exception"):
        for label, pattern in RETRY_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return label, predicted[:1000]
        return "exception", predicted[:1000]

    if any(is_nan(row.get(key)) for key in ("input_tokens", "output_tokens", "latency", "cost")):
        for label, pattern in RETRY_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return label, predicted[:1000]
        return "nan_usage", predicted[:1000]

    return None, ""


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("result_dir", type=Path)
    args = parser.parse_args()

    result_dir = args.result_dir
    rows = read_jsonl(result_dir / "results.jsonl")
    retry_rows = []
    counts: dict[str, int] = {}

    for index, row in enumerate(rows):
        label, reason = classify(row)
        if not label:
            continue
        case_name = row.get("name") or row.get("case_name") or row.get("example_name") or ""
        item = {
            "index": index,
            "case_name": case_name,
            "label": label,
            "calculator_name": row.get("calculator_name", ""),
            "category": row.get("category", ""),
            "output_type": row.get("output_type", ""),
            "expected_output": row.get("expected_output", ""),
            "predicted_output": row.get("predicted_output", ""),
            "reason": reason,
        }
        retry_rows.append(item)
        counts[label] = counts.get(label, 0) + 1

    summary = {
        "result_dir": str(result_dir),
        "rows_seen": len(rows),
        "retryable_count": len(retry_rows),
        "counts": counts,
    }

    (result_dir / "retryable_failures.summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )
    (result_dir / "retryable_failures.json").write_text(
        json.dumps(retry_rows, indent=2, default=str)
    )
    case_names = sorted({str(row["case_name"]) for row in retry_rows if row["case_name"]})
    (result_dir / "retryable_case_names.txt").write_text(
        "".join(f"{case_name}\n" for case_name in case_names)
    )
    with (result_dir / "retryable_failures.csv").open("w", newline="") as f:
        fieldnames = [
            "index", "case_name", "label", "calculator_name", "category",
            "output_type", "expected_output", "predicted_output", "reason",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(retry_rows)

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
