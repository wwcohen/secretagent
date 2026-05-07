#!/usr/bin/env python3
"""Retry failed MedCalc result rows and rewrite result files in place.

This is intended to run after ``run_medcalc_test_set.py`` finishes. It finds
the latest full-test result directory for each standard MedCalc strategy,
retries rows whose prediction is an exception or timeout, and updates
``results.jsonl`` and ``results.csv`` so aggregate accuracy/cost/latency reflect
the retried measurements.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
from omegaconf import OmegaConf


REPO_ROOT = Path(__file__).resolve().parents[2]
MEDCALC_DIR = REPO_ROOT / "benchmarks" / "medcalc"
DEFAULT_MODEL = "together_ai/deepseek-ai/DeepSeek-V3.1"
STRATEGIES = (
    "unstructured_baseline",
    "structured_baseline",
    "workflow",
    "react",
    "pot",
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


def select_cfg(cfg: Any, key: str) -> Any:
    return OmegaConf.select(cfg, key)


def is_full_test_result_dir(path: Path, strategy: str, model: str) -> bool:
    cfg_path = path / "config.yaml"
    if not cfg_path.exists() or not path.name.endswith(f".{strategy}"):
        return False
    cfg = OmegaConf.load(cfg_path)
    return (
        select_cfg(cfg, "evaluate.expt_name") == strategy
        and select_cfg(cfg, "dataset.split") == "test"
        and select_cfg(cfg, "dataset.stratified") is False
        and select_cfg(cfg, "llm.model") == model
    )


def latest_result_dir(strategy: str, model: str) -> Path | None:
    candidates = [
        path
        for path in (MEDCALC_DIR / "results").iterdir()
        if path.is_dir() and is_full_test_result_dir(path, strategy, model)
    ]
    return sorted(candidates, key=lambda p: p.name)[-1] if candidates else None


def is_failed_row(row: dict[str, Any]) -> bool:
    if row.get("_timeout"):
        return True
    return str(row.get("predicted_output", "")).startswith("**exception")


def read_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as fp:
        for line in fp:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_rows(result_dir: Path, rows: list[dict[str, Any]]) -> None:
    jsonl_path = result_dir / "results.jsonl"
    csv_path = result_dir / "results.csv"
    timestamp = datetime.now().strftime("%Y%m%d.%H%M%S")
    if jsonl_path.exists():
        shutil.copy2(jsonl_path, result_dir / f"results.pre_retry_{timestamp}.jsonl")
    if csv_path.exists():
        shutil.copy2(csv_path, result_dir / f"results.pre_retry_{timestamp}.csv")

    tmp_jsonl = result_dir / "results.jsonl.tmp"
    with tmp_jsonl.open("w") as fp:
        for row in rows:
            fp.write(json.dumps(row, default=str) + "\n")
    tmp_jsonl.replace(jsonl_path)

    csv_rows = [{k: v for k, v in row.items() if k != "rollout"} for row in rows]
    df = pd.DataFrame(csv_rows)
    if "case_name" in df.columns:
        df = df.set_index("case_name")
    tmp_csv = result_dir / "results.csv.tmp"
    df.to_csv(tmp_csv)
    tmp_csv.replace(csv_path)


def import_medcalc_expt():
    sys.path.insert(0, str(MEDCALC_DIR))
    os.chdir(MEDCALC_DIR)
    return importlib.import_module("expt")


def setup_for_result(expt_module: Any, result_dir: Path):
    from secretagent import config

    config.reset()
    ctx = SimpleNamespace(args=[
        "cachier.enable_caching=true",
        "cachier.cache_dir=llm_cache",
    ])
    dataset, interface = expt_module.setup(ctx, result_dir / "config.yaml")
    return {case.name: case for case in dataset.cases}, interface


def retry_one_case(
    evaluator: Any,
    interface: Any,
    case: Any,
    expt_name: str,
    max_attempts: int,
    retry_delay: float,
) -> dict[str, Any]:
    last_row: dict[str, Any] | None = None
    for attempt in range(1, max_attempts + 1):
        row = evaluator.measure(case, interface)
        row["case_name"] = case.name
        row["expt_name"] = expt_name
        row["retry_attempt"] = attempt
        row["retried"] = True
        last_row = row
        if not is_failed_row(row):
            return row
        if attempt < max_attempts and retry_delay > 0:
            time.sleep(retry_delay)
    assert last_row is not None
    return last_row


def retry_result_dir(
    expt_module: Any | None,
    result_dir: Path,
    max_attempts: int,
    retry_delay: float,
    dry_run: bool,
) -> tuple[int, int]:
    rows = read_rows(result_dir / "results.jsonl")
    failed_indices = [idx for idx, row in enumerate(rows) if is_failed_row(row)]
    print(f"\n{result_dir}", flush=True)
    print(f"  rows={len(rows)} failed_rows={len(failed_indices)}", flush=True)
    if not failed_indices:
        return 0, 0
    if dry_run:
        return len(failed_indices), len(failed_indices)

    cases_by_name, interface = setup_for_result(expt_module, result_dir)
    evaluator = expt_module.MedCalcEvaluator()
    remaining = 0
    for position, idx in enumerate(failed_indices, start=1):
        old_row = rows[idx]
        case_name = old_row["case_name"]
        case = cases_by_name.get(case_name)
        if case is None:
            print(
                f"  [{position}/{len(failed_indices)}] missing case {case_name}; keeping old row",
                flush=True,
            )
            remaining += 1
            continue

        print(f"  [{position}/{len(failed_indices)}] retry {case_name}", flush=True)
        new_row = retry_one_case(
            evaluator=evaluator,
            interface=interface,
            case=case,
            expt_name=old_row.get("expt_name", result_dir.name.split(".", 2)[-1]),
            max_attempts=max_attempts,
            retry_delay=retry_delay,
        )
        new_row["original_predicted_output"] = old_row.get("predicted_output")
        rows[idx] = new_row
        if is_failed_row(new_row):
            remaining += 1

    write_rows(result_dir, rows)
    print(f"  updated; remaining_failed_rows={remaining}", flush=True)
    return len(failed_indices), remaining


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retry failed rows in MedCalc result files.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--retry-delay", type=float, default=10.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strategy", action="append", choices=STRATEGIES)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env_file(REPO_ROOT / ".env")
    normalize_together_env()
    expt_module = None if args.dry_run else import_medcalc_expt()

    strategies = tuple(args.strategy) if args.strategy else STRATEGIES
    total_failed = 0
    total_remaining = 0
    missing: list[str] = []

    for strategy in strategies:
        result_dir = latest_result_dir(strategy, args.model)
        if result_dir is None:
            print(f"\n{strategy}: no matching full-test result directory found", flush=True)
            missing.append(strategy)
            continue
        failed, remaining = retry_result_dir(
            expt_module=expt_module,
            result_dir=result_dir,
            max_attempts=args.max_attempts,
            retry_delay=args.retry_delay,
            dry_run=args.dry_run,
        )
        total_failed += failed
        total_remaining += remaining

    print("\nRetry summary", flush=True)
    print(f"  failed_rows_seen={total_failed}", flush=True)
    print(f"  failed_rows_remaining={total_remaining}", flush=True)
    if missing:
        print(f"  missing_strategies={','.join(missing)}", flush=True)
        return 2
    return 0 if total_remaining == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
