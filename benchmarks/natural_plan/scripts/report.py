#!/usr/bin/env python3
"""Quick view of all runs: table by task, accuracy, cost, time.

Usage:
  uv run python scripts/report.py              # write to report.md
  uv run python scripts/report.py -o report.md
"""
import argparse
import csv
import json
from pathlib import Path

try:
    from omegaconf import OmegaConf
except ImportError:
    OmegaConf = None

BENCHMARK_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BENCHMARK_DIR / "results"

# Level order: zeroshot_unstructured (level 1), zeroshot_structured (level 2), workflow, pot, react
LEVEL_ORDER = ["zeroshot_unstructured", "zeroshot_structured", "workflow", "pot", "react"]
LEVEL_ALIAS = {"zs_struct": "zeroshot_structured", "zs_unstruct": "zeroshot_unstructured"}

# Exclude test runs
EXCLUDE_EXPTS = {"cal_test", "cal_trace_test", "meet_trace_test"}


def load_run_summary(run_dir: Path) -> dict | None:
    """Load run_summary.json or compute from results.csv."""
    summary_path = run_dir / "run_summary.json"
    csv_path = run_dir / "results.csv"
    if summary_path.exists():
        with open(summary_path) as f:
            s = json.load(f)
        # Add expt_name from folder (format: YYYYMMDD.HHMMSS.expt_name)
        parts = run_dir.name.split(".", 2)
        s["expt_name"] = s.get("expt_name") or (parts[-1] if len(parts) > 2 else run_dir.name)
        s["folder"] = run_dir.name
        return s
    if csv_path.exists():
        with open(csv_path) as f:
            rows = list(csv.DictReader(f))
        if not rows:
            return None
        correct = sum(1 for r in rows if str(r.get("correct", "")).lower() == "true")
        total_cost = sum(float(r.get("cost", 0) or 0) for r in rows)
        total_time = sum(float(r.get("latency", 0) or 0) for r in rows)
        expt = rows[0].get("expt_name", "")
        config_path = run_dir / "config.yaml"
        reproduce = ""
        if config_path.exists() and OmegaConf:
            cfg = OmegaConf.load(config_path)
            parts = ["uv run python expt.py run --config-file"]
            task = (cfg.get("dataset") or {}).get("split", "calendar")
            parts.append(f"conf/{task}.yaml")
            parts.append(f"evaluate.expt_name={expt}")
            ds = cfg.get("dataset") or {}
            if ds.get("n") is not None:
                parts.append(f"dataset.n={ds['n']}")
            ptools = cfg.get("ptools") or {}
            ep = (cfg.get("evaluate") or {}).get("entry_point", "")
            if ep and ep in ptools:
                m = ptools[ep].get("method")
                if m == "direct":
                    parts.append(f"ptools.{ep}.method=direct")
                    fn = ptools[ep].get("fn") or f"ptools_{task}.{ep}"
                    parts.append(f"ptools.{ep}.fn={fn}")
                elif m == "simulate":
                    parts.append(f"ptools.{ep}.method=simulate")
                elif m == "prompt_llm":
                    parts.append(f"ptools.{ep}.method=prompt_llm")
                    parts.append(f"ptools.{ep}.prompt_template_file=prompt_templates/zeroshot.txt")
                elif m == "program_of_thought":
                    parts.append(f"ptools.{ep}.method=program_of_thought")
                    tools = ptools[ep].get("tools", [])
                    tools_str = "[" + ",".join(str(t) for t in tools) + "]"
                    parts.append(f"ptools.{ep}.tools={tools_str}")
                elif m == "simulate_pydantic":
                    parts.append(f"ptools.{ep}.method=simulate_pydantic")
                    tools = ptools[ep].get("tools", [])
                    tools_str = "[" + ",".join(str(t) for t in tools) + "]"
                    parts.append(f"ptools.{ep}.tools={tools_str}")
            reproduce = " ".join(str(p) for p in parts)
        return {
            "reproduce_cmd": reproduce,
            "accuracy": correct / len(rows) if rows else 0,
            "total_cost_usd": round(total_cost, 6),
            "total_time_sec": round(total_time, 2),
            "n_samples": len(rows),
            "expt_name": expt,
            "folder": run_dir.name,
        }
    return None


def _task_from_expt(expt: str) -> str:
    """cal_workflow -> calendar, meet_zs_struct -> meeting, trip_pot -> trip."""
    if expt.startswith("cal"):
        return "calendar"
    if expt.startswith("meet"):
        return "meeting"
    if expt.startswith("trip"):
        return "trip"
    return "other"


def main():
    ap = argparse.ArgumentParser(description="Report table of all runs")
    ap.add_argument("--output", "-o", default="report.md", help="Output file (default: report.md)")
    ap.add_argument("--latest", type=int, default=0, help="Per expt_name, keep only latest N (0=all)")
    ap.add_argument("--run-dir", type=str, default="", help="Only scan this run dir (e.g. results/run_YYYYMMDD_HHMMSS)")
    args = ap.parse_args()

    def iter_run_dirs():
        """Scan results/, results/run_*/, and results/{task}/ for run dirs."""
        if args.run_dir:
            run_dir = Path(args.run_dir)
            if not run_dir.is_absolute():
                run_dir = BENCHMARK_DIR / run_dir
            if run_dir.exists():
                for sub in run_dir.iterdir():
                    if sub.is_dir() and (sub / "results.csv").exists():
                        yield sub
            return
        for p in RESULTS_DIR.iterdir():
            if not p.is_dir():
                continue
            if p.name.startswith("run_"):
                for sub in p.iterdir():
                    if sub.is_dir() and (sub / "results.csv").exists():
                        yield sub
            elif p.name in ("calendar", "meeting", "trip"):
                for sub in p.iterdir():
                    if sub.is_dir() and (sub / "results.csv").exists():
                        yield sub
            elif (p / "results.csv").exists():
                yield p

    runs = []
    seen = {}
    for d in sorted(iter_run_dirs(), key=lambda x: x.stat().st_mtime, reverse=True):
        s = load_run_summary(d)
        if not s:
            continue
        expt = s.get("expt_name", d.name.split(".", 2)[-1] if "." in d.name else "")
        if expt in EXCLUDE_EXPTS:
            continue
        if args.latest > 0:
            seen[expt] = seen.get(expt, 0) + 1
            if seen[expt] > args.latest:
                continue
        s["folder"] = d.name
        s["task"] = _task_from_expt(expt)
        runs.append(s)

    # Group by task, sort levels by LEVEL_ORDER
    by_task: dict[str, list] = {}
    for r in runs:
        t = r["task"]
        by_task.setdefault(t, []).append(r)

    def level_sort_key(expt: str) -> int:
        level = expt.replace("cal_", "").replace("meet_", "").replace("trip_", "")
        level = LEVEL_ALIAS.get(level, level)
        try:
            return LEVEL_ORDER.index(level)
        except ValueError:
            return 99

    task_order = ["calendar", "meeting", "trip", "other"]
    for t in by_task:
        by_task[t] = sorted(by_task[t], key=lambda r: level_sort_key(r.get("expt_name", "")))

    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = BENCHMARK_DIR / out_path
    with open(out_path, "w") as f:
        f.write("# NaturalPlan Run Report\n\n")
        for task in task_order:
            if task not in by_task:
                continue
            task_runs = by_task[task]
            f.write(f"## {task.capitalize()}\n\n")
            f.write("| level | accuracy | cost ($) | time (s) | n | reproduce |\n")
            f.write("|-------|----------|----------|----------|---|----------|\n")
            for r in task_runs:
                expt = r.get("expt_name", r.get("folder", ""))
                level = expt.replace("cal_", "").replace("meet_", "").replace("trip_", "") if "_" in expt else expt
                acc = r.get("accuracy", 0)
                cost = r.get("total_cost_usd", 0)
                time_s = r.get("total_time_sec", 0)
                n = r.get("n_samples", 0)
                cmd = r.get("reproduce_cmd", "")
                cmd_short = (cmd[:60] + "…") if len(cmd) > 60 else cmd
                f.write(f"| {level} | {acc:.1%} | ${cost:.4f} | {time_s:.1f}s | {n} | `{cmd_short}` |\n")
            f.write("\n")
        f.write("---\n\n## Reproduce commands\n\n")
        for task in task_order:
            if task not in by_task:
                continue
            task_runs = by_task[task]
            f.write(f"### {task.capitalize()}\n\n")
            for r in task_runs:
                f.write(f"**{r.get('expt_name', '')}**\n\n```bash\n{r.get('reproduce_cmd', '')}\n```\n\n")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
