#!/usr/bin/env python3
"""Run the MedCalc-Bench v1.2 test split for all standard strategies.

Default behavior runs the full Hugging Face ``test`` split for:

  - unstructured_baseline
  - structured_baseline
  - workflow
  - react
  - pot

Use ``--smoke`` to run one example per strategy. Smoke results are written
under a temporary result directory and deleted at the end; the LLM cache is
left untouched.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MEDCALC_DIR = REPO_ROOT / "benchmarks" / "medcalc"
DEFAULT_MODEL = "together_ai/deepseek-ai/DeepSeek-V3.1"


@dataclass(frozen=True)
class Strategy:
    name: str
    config_file: str


STRATEGIES = (
    Strategy("unstructured_baseline", "conf/baseline.yaml"),
    Strategy("structured_baseline", "conf/simulate.yaml"),
    Strategy("workflow", "conf/workflow.yaml"),
    Strategy("react", "conf/react.yaml"),
    Strategy("pot", "conf/pot.yaml"),
)


def _parse_env_value(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {"'", '"'}:
        return raw[1:-1]
    return raw


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE lines without requiring python-dotenv."""
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
    """Expose the Together API key under all names used in this repo."""
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


def result_dir_to_path(result_dir: str) -> Path:
    path = Path(result_dir)
    if path.is_absolute():
        return path
    return MEDCALC_DIR / path


def display_command(cmd: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in cmd)


def build_command(
    strategy: Strategy,
    args: argparse.Namespace,
    result_dir: str,
    n_value: str,
) -> list[str]:
    expt_name = f"smoke_{strategy.name}" if args.smoke else strategy.name
    overrides = [
        f"llm.model={args.model}",
        f"dataset.split={args.split}",
        "dataset.stratified=false",
        f"dataset.n={n_value}",
        f"evaluate.expt_name={expt_name}",
        f"evaluate.result_dir={result_dir}",
    ]

    if args.max_workers is not None:
        overrides.append(f"evaluate.max_workers={args.max_workers}")
    if args.llm_timeout is not None:
        overrides.append(f"llm.timeout={args.llm_timeout}")
    overrides.extend(args.extra_overrides)
    overrides.extend([
        "cachier.enable_caching=true",
        "cachier.cache_dir=llm_cache",
    ])

    return [
        "uv",
        "run",
        "python",
        "expt.py",
        "run",
        "--config-file",
        strategy.config_file,
        *overrides,
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run MedCalc-Bench v1.2 test split for all standard strategies."
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"LiteLLM model string to use. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--split",
        default="test",
        help="Hugging Face split to run. Default: test",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=None,
        help="Limit examples per strategy. Default: full split. Ignored by --smoke.",
    )
    parser.add_argument(
        "--result-dir",
        default="results",
        help="Medcalc result directory. Relative paths are under benchmarks/medcalc.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Optional evaluate.max_workers override.",
    )
    parser.add_argument(
        "--llm-timeout",
        type=int,
        default=None,
        help="Optional llm.timeout override in seconds.",
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="Continue running later strategies after a subprocess exits nonzero.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run one example per strategy and delete smoke result files afterward.",
    )
    parser.add_argument(
        "--keep-smoke-results",
        action="store_true",
        help="Keep smoke result files instead of deleting them.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them.",
    )
    parser.add_argument(
        "extra_overrides",
        nargs="*",
        help="Additional OmegaConf dotlist overrides passed after built-in overrides.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env_file(REPO_ROOT / ".env")
    normalize_together_env()

    if not MEDCALC_DIR.exists():
        raise SystemExit(f"Expected medcalc benchmark directory at {MEDCALC_DIR}")

    n_value = "1" if args.smoke else ("null" if args.n is None else str(args.n))
    cleanup_dir: Path | None = None
    result_dir = args.result_dir
    if args.smoke:
        run_id = datetime.now().strftime("%Y%m%d.%H%M%S")
        result_dir = str(Path(args.result_dir) / f"_smoke_medcalc_{run_id}")
        cleanup_dir = result_dir_to_path(result_dir)

    print(f"MedCalc directory: {MEDCALC_DIR}", flush=True)
    print(f"Split: {args.split}", flush=True)
    print(
        f"Examples per strategy: {'full split' if n_value == 'null' else n_value}",
        flush=True,
    )
    print(f"Model: {args.model}", flush=True)
    print(f"Result dir: {result_dir_to_path(result_dir)}", flush=True)

    failures: list[tuple[str, int]] = []
    run_env = os.environ.copy()
    run_env.setdefault("PYTHONUNBUFFERED", "1")
    try:
        for strategy in STRATEGIES:
            cmd = build_command(strategy, args, result_dir, n_value)
            print(flush=True)
            print(f"== {strategy.name} ==", flush=True)
            print(display_command(cmd), flush=True)
            if args.dry_run:
                continue

            completed = subprocess.run(cmd, cwd=MEDCALC_DIR, env=run_env)
            if completed.returncode != 0:
                failures.append((strategy.name, completed.returncode))
                if not args.keep_going:
                    return completed.returncode
    finally:
        if args.smoke and cleanup_dir and not args.keep_smoke_results and not args.dry_run:
            if cleanup_dir.exists():
                shutil.rmtree(cleanup_dir)
                print(f"\nDeleted smoke result files: {cleanup_dir}", flush=True)

    if failures:
        print("\nFailures:")
        for name, returncode in failures:
            print(f"  {name}: exit {returncode}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
