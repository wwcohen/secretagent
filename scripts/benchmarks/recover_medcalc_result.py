#!/usr/bin/env python3
"""Recover an interrupted MedCalc result directory.

This fills missing cases and retries infrastructure failures while preserving
legacy parse failures for apples-to-apples comparisons.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime
import json
import os
from pathlib import Path
import random
import re
import shutil
import sys
import time
from string import Template
from textwrap import dedent
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
MEDCALC_DIR = REPO_ROOT / "benchmarks" / "medcalc"
HF_MEDCALC_TEST_ARROW = (
    Path.home()
    / ".cache/huggingface/datasets/ncbi___med_calc-bench-v1.2/default/0.0.0"
    / "915b1aad1fd2aa67790f369658cc365dfd440e90"
    / "med_calc-bench-v1.2-test.arrow"
)

PARSE_MARKERS = (
    "cannot find answer matching pattern",
    "could not convert string to float",
)

RETRY_MARKERS = (
    "credit limit exceeded",
    "resource temporarily unavailable",
    "timeout",
    "timed out",
    "litellm",
    "apierror",
    "rate limit",
    "ratelimit",
    "connection",
    "connecterror",
    "serverdisconnected",
    "serviceunavailable",
    "internalservererror",
)


def _parse_env_value(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {"'", '"'}:
        return raw[1:-1]
    return raw


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].strip()
        if "=" not in stripped:
            continue
        key, raw_value = stripped.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = _parse_env_value(raw_value)


def normalize_together_env() -> None:
    key = (
        os.environ.get("TOGETHER_API_KEY")
        or os.environ.get("TOGETHER_AI_API_KEY")
        or os.environ.get("TOGETHERAI_API_KEY")
    )
    if not key:
        raise SystemExit(
            "No Together API key found. Add TOGETHER_API_KEY to .env or export it."
        )
    os.environ.setdefault("TOGETHER_API_KEY", key)
    os.environ.setdefault("TOGETHER_AI_API_KEY", key)
    os.environ.setdefault("TOGETHERAI_API_KEY", key)


def read_rows(result_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    jsonl_path = result_dir / "results.jsonl"
    if not jsonl_path.exists():
        return rows
    with jsonl_path.open() as fp:
        for line in fp:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_rows(result_dir: Path, rows: list[dict[str, Any]]) -> None:
    jsonl_path = result_dir / "results.jsonl"
    csv_path = result_dir / "results.csv"

    tmp_jsonl = result_dir / "results.jsonl.tmp"
    with tmp_jsonl.open("w") as fp:
        for row in rows:
            fp.write(json.dumps(row, default=str) + "\n")
    tmp_jsonl.replace(jsonl_path)

    csv_rows = [{k: v for k, v in row.items() if k != "rollout"} for row in rows]
    tmp_csv = result_dir / "results.csv.tmp"
    fieldnames: list[str] = []
    seen: set[str] = set()
    for preferred in ("case_name",):
        seen.add(preferred)
        fieldnames.append(preferred)
    for row in csv_rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with tmp_csv.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(csv_rows)
    tmp_csv.replace(csv_path)


def is_exception_row(row: dict[str, Any]) -> bool:
    return bool(
        row.get("_timeout")
        or row.get("_error")
        or str(row.get("predicted_output", "")).startswith("**exception")
    )


def row_text(row: dict[str, Any]) -> str:
    return " ".join(str(row.get(key, "")) for key in ("predicted_output", "_error", "_timeout"))


def is_parse_exception(row: dict[str, Any]) -> bool:
    if not is_exception_row(row):
        return False
    low = row_text(row).lower()
    return any(marker in low for marker in PARSE_MARKERS)


def is_retriable_exception(row: dict[str, Any]) -> bool:
    if not is_exception_row(row) or is_parse_exception(row):
        return False
    low = row_text(row).lower()
    return bool(row.get("_timeout")) or any(marker in low for marker in RETRY_MARKERS)


def summarize(rows: list[dict[str, Any]], total_cases: int) -> dict[str, Any]:
    counts = {
        "rows": len(rows),
        "total_cases": total_cases,
        "missing": max(total_cases - len({row.get("case_name") for row in rows}), 0),
        "retriable": sum(1 for row in rows if is_retriable_exception(row)),
        "parse_retained": sum(1 for row in rows if is_parse_exception(row)),
        "exceptions": sum(1 for row in rows if is_exception_row(row)),
        "correct": sum(float(row.get("correct") or 0) for row in rows),
        "exact": sum(float(row.get("exact_match") or 0) for row in rows),
        "cost": sum(float(row.get("cost") or 0) for row in rows),
    }
    counts["accuracy"] = counts["correct"] / counts["rows"] if counts["rows"] else 0.0
    counts["exact_rate"] = counts["exact"] / counts["rows"] if counts["rows"] else 0.0
    return counts


def _extract_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value)
    if s.startswith("**exception"):
        return None
    try:
        return float(s)
    except ValueError:
        pass
    match = re.search(r"<answer>\s*([\d.eE+-]+)\s*</answer>", s)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    match = re.search(r"ANSWER:\s*([\d.eE+-]+)", s)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    numbers = re.findall(r"-?\d+\.?\d*", s)
    if numbers:
        try:
            return float(numbers[-1])
        except ValueError:
            pass
    return None


def _coerce_float_answer(text: str) -> float:
    return float(text.strip().replace(",", "").replace("$", ""))


def _extract_prompt_llm_float(text: str, answer_pattern: str | None) -> float:
    if answer_pattern is None:
        return _coerce_float_answer(text)
    match_result = re.search(answer_pattern, text, re.DOTALL | re.MULTILINE)
    if match_result is None:
        raise ValueError(f"cannot find answer matching pattern {answer_pattern!r}")
    return _coerce_float_answer(match_result.group(1))


def aggregate_usage_stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, float] = {}
    for rec in records:
        for key, value in rec["stats"].items():
            if isinstance(value, (int, float)):
                result[key] = result.get(key, 0.0) + value
    return result


def measure_case(case: Any, interface: Any) -> dict[str, Any]:
    from accuracy import calculate_accuracy
    from secretagent import config, record

    meta = case.metadata or {}
    with record.recorder() as records:
        try:
            predicted_output = interface(*case.input_args)
        except Exception as ex:
            predicted_output = f"**exception raised**: {ex}"

    llm_usage_stats = aggregate_usage_stats(records)
    predicted = _extract_number(predicted_output)
    output_type = meta.get("output_type", "numeric")
    output_type_lower = str(output_type).lower()
    predicted_for_accuracy = (
        predicted_output
        if output_type_lower == "date"
        or "week" in output_type_lower
        or "day" in output_type_lower
        else predicted
    )

    acc = calculate_accuracy(
        predicted=predicted_for_accuracy,
        ground_truth=case.expected_output,
        lower_limit=meta.get("lower_limit"),
        upper_limit=meta.get("upper_limit"),
        output_type=output_type,
        category=meta.get("category", "formula-based"),
    )

    result = dict(
        predicted_output=predicted_output,
        predicted_numeric=predicted,
        expected_output=case.expected_output,
        correct=float(acc.is_within_tolerance),
        exact_match=float(acc.is_exact_match),
        within_limits=float(acc.is_within_limits),
        absolute_error=acc.absolute_error,
        calculator_name=meta.get("calculator_name", ""),
        category=meta.get("category", ""),
        output_type=meta.get("output_type", ""),
        **llm_usage_stats,
    )
    if config.get("evaluate.record_details"):
        result["rollout"] = records
    return result


def parse_medcalc_row(row: dict[str, Any], idx: int, split: str):
    from secretagent.dataset import Case

    output_type = str(row.get("Output Type", "decimal")).lower()
    gt_raw = str(row.get("Ground Truth Answer", ""))
    if output_type == "date" or "week" in output_type or "day" in output_type:
        gt_answer: Any = gt_raw.strip()
    else:
        gt_val = row.get("Ground Truth Answer", 0)
        if isinstance(gt_val, str):
            match = re.search(r"-?\d+\.?\d*", gt_val)
            gt_answer = float(match.group()) if match else 0.0
        else:
            gt_answer = float(gt_val)

    def parse_limit(key: str) -> float | None:
        value = row.get(key)
        if value == "" or value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    row_number = row.get("Row Number", idx)
    try:
        row_number = int(row_number)
    except (ValueError, TypeError):
        row_number = idx

    return Case(
        name=f"{split}.{row_number:04d}",
        input_args=(row.get("Patient Note", ""), row.get("Question", "")),
        expected_output=gt_answer,
        metadata={
            "calculator_name": row.get("Calculator Name", "unknown"),
            "category": row.get("Category", "unknown"),
            "output_type": row.get("Output Type", "decimal"),
            "lower_limit": parse_limit("Lower Limit"),
            "upper_limit": parse_limit("Upper Limit"),
            "row_number": row_number,
        },
    )


def load_cached_test_cases(split: str, shuffle_seed: int | None, n: int | None):
    if split != "test":
        raise SystemExit(f"This recovery script currently supports split=test, got {split!r}")
    if not HF_MEDCALC_TEST_ARROW.exists():
        raise SystemExit(f"Missing cached MedCalc Arrow file: {HF_MEDCALC_TEST_ARROW}")

    print("Loading cached Arrow test set", flush=True)
    import pyarrow.ipc as ipc

    with HF_MEDCALC_TEST_ARROW.open("rb") as fp:
        table = ipc.open_stream(fp).read_all()
    cases = [parse_medcalc_row(row, idx, split) for idx, row in enumerate(table.to_pylist())]
    if shuffle_seed is not None:
        random.Random(int(shuffle_seed)).shuffle(cases)
    if n is not None:
        cases = cases[: int(n)]
    return cases


def setup_for_result(result_dir: Path):
    print("Configuring MedCalc recovery", flush=True)
    from secretagent import config

    sys.path.insert(0, str(MEDCALC_DIR))
    os.chdir(MEDCALC_DIR)

    config.reset()
    config.configure(
        yaml_file=result_dir / "config.yaml",
        dotlist=[
            "cachier.enable_caching=true",
            "cachier.cache_dir=llm_cache",
        ],
    )
    config.set_root(MEDCALC_DIR)

    split = config.require("dataset.split")
    n = config.get("dataset.n")
    shuffle_seed = config.get("dataset.shuffle_seed", 42)
    cases = load_cached_test_cases(split=split, shuffle_seed=shuffle_seed, n=n)
    print(f"Loaded {len(cases)} cached test cases", flush=True)
    entry_point_name = config.get("evaluate.entry_point", "calculate_medical_value")
    tool_cfg = dict(config.require("ptools")[entry_point_name])
    if tool_cfg.get("method") != "prompt_llm":
        raise SystemExit(
            f"This recovery path only supports prompt_llm; got {tool_cfg.get('method')!r}"
        )

    prompt_template_file = Path(tool_cfg["prompt_template_file"])
    if not prompt_template_file.is_absolute():
        prompt_template_file = MEDCALC_DIR / prompt_template_file
    template = Template(dedent(prompt_template_file.read_text()))
    answer_pattern = tool_cfg.get("answer_pattern")

    def interface(patient_note: str, question: str) -> float:
        from secretagent import config, llm_util, record

        args = (patient_note, question)
        prompt = template.substitute(
            {"patient_note": patient_note, "question": question}
        )
        llm_output, stats = llm_util.llm(prompt, config.require("llm.model"))
        try:
            answer = _extract_prompt_llm_float(llm_output, answer_pattern)
        except Exception as ex:
            record.record(
                func=entry_point_name,
                args=args,
                kw={},
                output=f"**exception**: {ex}",
                stats=stats,
            )
            raise
        record.record(
            func=entry_point_name,
            args=args,
            kw={},
            output=answer,
            stats=stats,
        )
        return answer

    return cases, interface


def measure_with_retries(
    interface: Any,
    case: Any,
    expt_name: str,
    reason: str,
    old_row: dict[str, Any] | None,
    max_attempts: int,
    retry_delay: float,
) -> dict[str, Any]:
    last_row: dict[str, Any] | None = None
    for attempt in range(1, max_attempts + 1):
        row = measure_case(case, interface)
        row["case_name"] = case.name
        row["expt_name"] = expt_name
        row["retried"] = True
        row["retry_attempt"] = attempt
        row["recovery_reason"] = reason
        if old_row is not None:
            row["original_predicted_output"] = old_row.get("predicted_output")
        last_row = row
        if not is_retriable_exception(row):
            return row
        if attempt < max_attempts and retry_delay > 0:
            time.sleep(retry_delay)
    assert last_row is not None
    return last_row


def backup_once(result_dir: Path) -> None:
    timestamp = datetime.now().strftime("%Y%m%d.%H%M%S")
    for name in ("results.jsonl", "results.csv"):
        path = result_dir / name
        if path.exists():
            stem, suffix = name.rsplit(".", 1)
            shutil.copy2(path, result_dir / f"{stem}.pre_recovery_{timestamp}.{suffix}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_dir", type=Path)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--retry-delay", type=float, default=10.0)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument(
        "--single-case",
        help="Recover exactly one case and rewrite results in place.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result_dir = args.result_dir.resolve()
    if not result_dir.exists():
        raise SystemExit(f"Missing result dir: {result_dir}")

    load_env_file(REPO_ROOT / ".env")
    normalize_together_env()
    cases, interface = setup_for_result(result_dir)

    rows = read_rows(result_dir)
    rows_by_case = {row.get("case_name"): row for row in rows}
    index_by_case = {row.get("case_name"): idx for idx, row in enumerate(rows)}
    expt_name = str(rows[0].get("expt_name") if rows else result_dir.name.split(".", 2)[-1])

    cases_by_name = {case.name: case for case in cases}
    if args.single_case:
        case = cases_by_name.get(args.single_case)
        if case is None:
            raise SystemExit(f"Unknown case {args.single_case!r}")
        old_row = rows_by_case.get(args.single_case)
        reason = "retry" if old_row is not None else "missing"
        backup_once(result_dir)
        new_row = measure_with_retries(
            interface=interface,
            case=case,
            expt_name=expt_name,
            reason=reason,
            old_row=old_row,
            max_attempts=args.max_attempts,
            retry_delay=args.retry_delay,
        )
        if args.single_case in index_by_case:
            rows[index_by_case[args.single_case]] = new_row
        else:
            rows.append(new_row)
        write_rows(result_dir, rows)
        final = summarize(rows, len(cases))
        print(
            f"Single-case recovery {args.single_case}: "
            f"retriable={is_retriable_exception(new_row)} "
            f"parse={is_parse_exception(new_row)} "
            f"correct={new_row.get('correct')} exact={new_row.get('exact_match')}",
            flush=True,
        )
        print("Summary", final, flush=True)
        return 1 if is_retriable_exception(new_row) else 0

    missing_cases = [case for case in cases if case.name not in rows_by_case]
    retry_cases = [
        (cases_by_name[row["case_name"]], row)
        for row in rows
        if row.get("case_name") in cases_by_name and is_retriable_exception(row)
    ]
    tasks = (
        [("missing", case, None) for case in missing_cases]
        + [("retry", case, row) for case, row in retry_cases]
    )

    print("Recovery target")
    print(f"  result_dir={result_dir}")
    print(f"  existing_rows={len(rows)} total_cases={len(cases)}")
    print(f"  missing={len(missing_cases)} retriable={len(retry_cases)}")
    print(f"  parse_retained={sum(1 for row in rows if is_parse_exception(row))}")
    print(f"  max_workers={args.max_workers} cache_enabled=true")
    if args.dry_run or not tasks:
        print("Summary", summarize(rows, len(cases)))
        return 0

    backup_once(result_dir)
    completed = 0
    remaining_retriable = 0

    def run_task(task):
        reason, case, old_row = task
        return reason, case.name, measure_with_retries(
            interface=interface,
            case=case,
            expt_name=expt_name,
            reason=reason,
            old_row=old_row,
            max_attempts=args.max_attempts,
            retry_delay=args.retry_delay,
        )

    max_workers = max(1, int(args.max_workers))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(run_task, task) for task in tasks]
        for fut in as_completed(futures):
            reason, case_name, new_row = fut.result()
            completed += 1
            if case_name in index_by_case:
                rows[index_by_case[case_name]] = new_row
            else:
                index_by_case[case_name] = len(rows)
                rows.append(new_row)
            write_rows(result_dir, rows)
            if is_retriable_exception(new_row):
                remaining_retriable += 1
            if completed == 1 or completed % 10 == 0 or completed == len(tasks):
                status = summarize(rows, len(cases))
                print(
                    f"  [{completed}/{len(tasks)}] rows={status['rows']} "
                    f"missing={status['missing']} retriable={status['retriable']} "
                    f"parse_retained={status['parse_retained']} "
                    f"acc={status['accuracy']:.3f} exact={status['exact_rate']:.3f}",
                    flush=True,
                )

    final = summarize(rows, len(cases))
    print("Final summary", final)
    return 0 if final["missing"] == 0 and final["retriable"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
