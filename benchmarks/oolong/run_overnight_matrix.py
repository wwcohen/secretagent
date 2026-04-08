"""Run Oolong experiments for large context lengths.

This script runs expt.py end-to-end (phase 1 + phase 2) for:
  context_len in [8192, 16384, 32768]

Phase setup used here:
  - phase 1 infer:   simulate_pydantic
  - phase 1 classify: simulate_pydantic
  - phase 2 answer:  program_of_thought with inject_args=true
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


CONTEXT_LENS = [8192, 16384, 32768]
SPLIT = "test"
PHASE1_WORKERS = 4
PHASE2_WORKERS = 1
ANSWER_RETRIES = 3
MAX_TOKENS = 8000

# Cache behavior:
# - window cache is the per-context-window payload cache (phase 1 artifacts)
# - cachier cache is framework LLM cache
# - phase2_enable_llm_cache controls only phase-2 cachier behavior in expt.py
ENABLE_WINDOW_CACHE = True
ENABLE_CACHIER = False
ENABLE_PHASE2_LLM_CACHE = False


def _phase2_args(context_len: int) -> list[str]:
    return [
        f"dataset.split={SPLIT}",
        "dataset.n=null",
        f"dataset.context_len={context_len}",
        "ptools.answer_from_cached_records.method=program_of_thought",
        "ptools.answer_from_cached_records.inject_args=true",
        "evaluate.record_details=true",
        "echo.model=false",
        "echo.llm_input=false",
        "echo.llm_output=false",
        "echo.code_eval_input=true",
        "echo.code_eval_output=false",
        f"oolong.answer_retries={ANSWER_RETRIES}",
        f"oolong.enable_window_cache={'true' if ENABLE_WINDOW_CACHE else 'false'}",
        f"llm.max_tokens={MAX_TOKENS}",
        f"cachier.enable_caching={'true' if ENABLE_CACHIER else 'false'}",
        f"oolong.phase2_enable_llm_cache={'true' if ENABLE_PHASE2_LLM_CACHE else 'false'}",
    ]


def run_one(context_len: int, cwd: Path) -> int:
    expt_name = f"test_pot_trace_inject_cached_par{PHASE2_WORKERS}_{context_len}"
    # Step 1: build phase-1 artifacts with higher parallelism.
    phase1_cmd = [
        "uv",
        "run",
        "python",
        "expt.py",
        "phase1-only",
        f"dataset.split={SPLIT}",
        f"dataset.context_len={context_len}",
        "dataset.n=null",
        f"oolong.enable_window_cache={'true' if ENABLE_WINDOW_CACHE else 'false'}",
        f"cachier.enable_caching={'true' if ENABLE_CACHIER else 'false'}",
        f"oolong.max_workers={PHASE1_WORKERS}",
    ]
    print(f"\n=== Phase 1 only ({context_len}) ===", flush=True)
    print(" ".join(phase1_cmd), flush=True)
    rc = subprocess.run(phase1_cmd, cwd=cwd).returncode
    if rc != 0:
        return rc

    # Step 2: full run with phase-2 worker setting. Phase 1 should be cache hits.
    cmd = [
        "uv",
        "run",
        "python",
        "expt.py",
        "run",
        f"oolong.max_workers={PHASE2_WORKERS}",
        *_phase2_args(context_len),
        f"evaluate.expt_name={expt_name}",
    ]
    print(f"\n=== Running: {expt_name} ===", flush=True)
    print(" ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd).returncode


def main() -> int:
    cwd = Path(__file__).resolve().parent
    failures: list[str] = []

    for context_len in CONTEXT_LENS:
        rc = run_one(context_len, cwd)
        if rc != 0:
            failures.append(f"context_len={context_len}, rc={rc}")

    print("\n=== Overnight matrix complete ===", flush=True)
    if failures:
        print("Failures:", flush=True)
        for f in failures:
            print(f"  - {f}", flush=True)
        return 1
    print("All runs succeeded.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
