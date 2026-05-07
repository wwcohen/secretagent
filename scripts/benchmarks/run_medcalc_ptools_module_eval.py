#!/usr/bin/env python3
"""Evaluate MedCalc with an explicitly selected ptools module.

The benchmark's native expt.py imports benchmarks/medcalc/ptools.py as the
top-level module. This runner keeps the same dataset/evaluator logic but lets a
run use a different ptools module as the entry-point owner.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MEDCALC_DIR = REPO_ROOT / "benchmarks" / "medcalc"
DEFAULT_MODEL = "together_ai/deepseek-ai/DeepSeek-V3.1"


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ptools-module", required=True)
    parser.add_argument("--config-file", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--split", default="test")
    parser.add_argument("--n", default="null")
    parser.add_argument("--result-dir", required=True)
    parser.add_argument("--expt-name", required=True)
    parser.add_argument("--max-workers", type=int, default=None)
    parser.add_argument("--llm-timeout", type=int, default=None)
    parser.add_argument(
        "--case-names-file",
        default=None,
        help="Optional newline-delimited case names to evaluate, e.g. test.0001.",
    )
    parser.add_argument(
        "extra_overrides",
        nargs="*",
        help="Additional OmegaConf dotlist overrides.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env_file(REPO_ROOT / ".env")
    normalize_together_env()

    sys.path.insert(0, str(MEDCALC_DIR))
    os.chdir(MEDCALC_DIR)

    import importlib

    from secretagent import config
    from secretagent.core import implement_via_config

    import expt

    ptools_module = importlib.import_module(args.ptools_module)
    config_file = Path(args.config_file)
    if not config_file.is_absolute():
        config_file = MEDCALC_DIR / config_file

    dotlist = [
        f"llm.model={args.model}",
        f"dataset.split={args.split}",
        "dataset.stratified=false",
        f"dataset.n={args.n}",
        f"evaluate.result_dir={args.result_dir}",
        f"evaluate.expt_name={args.expt_name}",
        "cachier.enable_caching=true",
        "cachier.cache_dir=llm_cache",
    ]
    if args.max_workers is not None:
        dotlist.append(f"evaluate.max_workers={args.max_workers}")
    if args.llm_timeout is not None:
        dotlist.append(f"llm.timeout={args.llm_timeout}")
    dotlist.extend(args.extra_overrides)

    config.configure(yaml_file=config_file, dotlist=dotlist)
    config.set_root(MEDCALC_DIR)

    dataset = expt.load_dataset(config.require("dataset.split"))
    n = config.get("dataset.n")
    shuffle_seed = config.get("dataset.shuffle_seed", 42)
    if config.get("dataset.stratified", False) and n:
        dataset.cases = expt.stratified_sample(dataset.cases, int(n), seed=shuffle_seed)
    else:
        dataset = dataset.configure(shuffle_seed=shuffle_seed, n=n or None)
    if args.case_names_file:
        case_names_path = Path(args.case_names_file)
        wanted = {
            line.strip()
            for line in case_names_path.read_text().splitlines()
            if line.strip()
        }
        before = len(dataset.cases)
        dataset.cases = [case for case in dataset.cases if case.name in wanted]
        missing = sorted(wanted - {case.name for case in dataset.cases})
        if missing:
            raise SystemExit(
                f"{len(missing)} case names were not found in the dataset; "
                f"first missing: {missing[0]}"
            )
        print(
            f"Filtered to {len(dataset.cases)} / {before} cases from "
            f"{case_names_path}",
            flush=True,
        )
    print("dataset is", dataset.summary(), flush=True)

    implement_via_config(ptools_module, config.require("ptools"))
    entry_point_name = config.get("evaluate.entry_point", "calculate_medical_value")
    interface = getattr(ptools_module, entry_point_name)

    evaluator = expt.MedCalcEvaluator()
    csv_path = evaluator.evaluate(dataset, interface)

    import pandas as pd

    df = pd.read_csv(csv_path)
    print()
    print(f"Results: {csv_path}", flush=True)
    print(f"Rows: {len(df)}", flush=True)
    print(f"Accuracy (within tolerance): {df['correct'].mean():.3f}", flush=True)
    print(f"Exact match: {df['exact_match'].mean():.3f}", flush=True)
    if "cost" in df.columns:
        print(f"Total cost: ${df['cost'].sum():.4f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
