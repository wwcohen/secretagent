#!/usr/bin/env python3
"""Run all 15 combinations (3 tasks x 5 levels).

Default: n=50 with stratified sampling (align AgentProject: 50 cal, 50 meet, 48 trip).
All 15 go into one run folder: results/run_YYYYMMDD_HHMMSS/
At end writes report_run_YYYYMMDD_HHMMSS.md (no overwrite).

Usage:
  uv run python scripts/run_all_15.py           # full 15x50
  uv run python scripts/run_all_15.py -n 5       # quick n=5
  uv run python scripts/run_all_15.py --trace    # save prompt_trace.jsonl per run
"""
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parent.parent
DEFAULT_N = 50

RUNS = [
    # Calendar (level 1=unstruct, level 2=struct)
    ("cal", "zeroshot_unstructured", "conf/calendar.yaml", "cal_zs_unstruct",
     "ptools.calendar_scheduling.method=prompt_llm", "ptools.calendar_scheduling.prompt_template_file=prompt_templates/zeroshot.txt",
     "dataset.prompt_mode=0shot"),
    ("cal", "zeroshot_structured", "conf/calendar.yaml", "cal_zs_struct",
     "ptools.calendar_scheduling.method=simulate", "dataset.prompt_mode=0shot"),
    ("cal", "workflow", "conf/calendar.yaml", "cal_workflow",
     "ptools.calendar_scheduling.method=direct", "ptools.calendar_scheduling.fn=ptools_calendar.calendar_workflow"),
    ("cal", "pot", "conf/calendar.yaml", "cal_pot",
     "ptools.calendar_scheduling.method=program_of_thought",
     "ptools.calendar_scheduling.tools=[ptools_calendar.parse_schedules,ptools_calendar.find_available_slots,ptools_calendar.select_and_format]"),
    ("cal", "react", "conf/calendar.yaml", "cal_react",
     "ptools.calendar_scheduling.method=simulate_pydantic",
     "ptools.calendar_scheduling.tools=[ptools_calendar.parse_schedules,ptools_calendar.find_available_slots,ptools_calendar.select_and_format]"),
    # Meeting (level 1=unstruct, level 2=struct)
    ("meet", "zeroshot_unstructured", "conf/meeting.yaml", "meet_zs_unstruct",
     "ptools.meeting_planning.method=prompt_llm", "ptools.meeting_planning.prompt_template_file=prompt_templates/zeroshot.txt",
     "dataset.prompt_mode=0shot"),
    ("meet", "zeroshot_structured", "conf/meeting.yaml", "meet_zs_struct",
     "ptools.meeting_planning.method=simulate", "dataset.prompt_mode=0shot"),
    ("meet", "workflow", "conf/meeting.yaml", "meet_workflow",
     "ptools.meeting_planning.method=direct", "ptools.meeting_planning.fn=ptools_meeting.meeting_workflow"),
    ("meet", "pot", "conf/meeting.yaml", "meet_pot",
     "ptools.meeting_planning.method=program_of_thought",
     "ptools.meeting_planning.tools=[ptools_meeting.parse_meeting_info,ptools_meeting.plan_visit_order,ptools_meeting.build_meeting_plan]"),
    ("meet", "react", "conf/meeting.yaml", "meet_react",
     "ptools.meeting_planning.method=simulate_pydantic",
     "ptools.meeting_planning.tools=[ptools_meeting.parse_meeting_info,ptools_meeting.plan_visit_order,ptools_meeting.build_meeting_plan]"),
    # Trip (level 1=unstruct, level 2=struct)
    ("trip", "zeroshot_unstructured", "conf/trip.yaml", "trip_zs_unstruct",
     "ptools.trip_planning.method=prompt_llm", "ptools.trip_planning.prompt_template_file=prompt_templates/zeroshot.txt",
     "dataset.prompt_mode=0shot"),
    ("trip", "zeroshot_structured", "conf/trip.yaml", "trip_zs_struct",
     "ptools.trip_planning.method=simulate", "dataset.prompt_mode=0shot"),
    ("trip", "workflow", "conf/trip.yaml", "trip_workflow",
     "ptools.trip_planning.method=direct", "ptools.trip_planning.fn=ptools_trip.trip_workflow"),
    ("trip", "pot", "conf/trip.yaml", "trip_pot",
     "ptools.trip_planning.method=program_of_thought",
     "ptools.trip_planning.tools=[ptools_trip.parse_trip_constraints,ptools_trip.find_valid_route,ptools_trip.build_trip_plan]"),
    ("trip", "react", "conf/trip.yaml", "trip_react",
     "ptools.trip_planning.method=simulate_pydantic",
     "ptools.trip_planning.tools=[ptools_trip.parse_trip_constraints,ptools_trip.find_valid_route,ptools_trip.build_trip_plan]"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--n", type=int, default=DEFAULT_N, help=f"Samples per run (default {DEFAULT_N})")
    ap.add_argument("--trace", action="store_true", default=True, help="Save prompt_trace.jsonl per run (default on)")
    ap.add_argument("--no-trace", action="store_true", help="Disable prompt_trace")
    ap.add_argument("--quick", action="store_true", help="Run only first run with n=1 (for testing)")
    ap.add_argument("--prompt-mode", type=str, default="", help="Override dataset.prompt_mode for all runs (e.g. 0shot)")
    args = ap.parse_args()
    trace_arg = [] if args.no_trace else ["evaluate.prompt_trace=true"]
    prompt_mode_arg = [f"dataset.prompt_mode={args.prompt_mode}"] if args.prompt_mode else []
    n = 1 if args.quick else args.n
    runs = RUNS[:1] if args.quick else RUNS

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = BENCHMARK_DIR / "results" / f"run_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    result_dir_arg = [f"evaluate.result_dir={run_dir}"]
    # Stratified sampling for n>=50 (align AgentProject: 50 cal, 50 meet, 48 trip)
    stratified_arg = (
        ["dataset.stratified=true", "dataset.sample_n=50", "dataset.sample_seed=42"]
        if n >= 50 else []
    )

    results = []
    for i, run in enumerate(runs):
        task_short, level, config, expt_name = run[:4]
        overrides = (
            list(run[4:]) + [f"evaluate.expt_name={expt_name}", f"dataset.n={n}"]
            + result_dir_arg + stratified_arg + prompt_mode_arg + trace_arg
        )
        cmd = [
            "uv", "run", "python", "expt.py", "run",
            "--config-file", config,
            *overrides,
        ]
        tag = f"{task_short}_{level}"
        total = len(runs)
        print(f"\n[{i+1}/{total}] {tag} ...", flush=True)
        try:
            timeout = 7200 if n >= 50 else 900  # 2h for n=50 (cal_zs_struct slow, Pot/React slow)
            r = subprocess.run(
                cmd,
                cwd=BENCHMARK_DIR,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if r.returncode != 0:
                print(f"  FAILED (exit {r.returncode})")
                if r.stderr:
                    print(r.stderr[-500:])
                results.append((tag, "FAIL", None, r.stderr))
            else:
                # Parse accuracy from output
                acc = None
                for line in r.stdout.splitlines():
                    if "Accuracy:" in line:
                        acc = line.strip().split(":")[-1].strip()
                        break
                results.append((tag, "OK", acc, None))
                print(f"  OK  acc={acc}")
        except subprocess.TimeoutExpired:
            print(f"  TIMEOUT")
            results.append((tag, "TIMEOUT", None, None))
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append((tag, "ERROR", None, str(e)))

    print(f"\nResults in {run_dir}")
    print("=" * 60)
    print(f"SUMMARY ({len(runs)} runs, n={n} each)")
    print("=" * 60)
    for tag, status, acc, err in results:
        print(f"  {tag:30} {status:10} {acc or ''}")
    ok = sum(1 for r in results if r[1] == "OK")
    print(f"\nPassed: {ok}/{len(runs)}")

    # Write timestamped report (no overwrite)
    report_path = BENCHMARK_DIR / f"report_run_{ts}.md"
    if ok == len(runs):
        subprocess.run(
            [
                "uv", "run", "python", "scripts/report.py",
                "-o", str(report_path),
                "--run-dir", str(run_dir),
                "--latest", "1",
            ],
            cwd=BENCHMARK_DIR,
            check=True,
        )
        print(f"Report: {report_path}")
    return 0 if ok == len(runs) else 1


if __name__ == "__main__":
    sys.exit(main())
