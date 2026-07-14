"""Cheap predictor f(X) for PPI-inside-the-search-loop.

Generalizes ppi_demo/cheap_predictor.py. For each benchmark we build a FIXED,
cheap, per-case prediction table that PPI later uses as the "unlabeled" signal
inside the NSGA-II inner loop:

  f_correct(X) in {0,1}  -- a cheap binary predictor of the expensive pipeline's
                            correctness Y. For musr this is a full rollout of the
                            BASELINE workflow under a cheap model (flash-lite),
                            i.e. the PEMC "cheap parallelizable simulation as
                            features" (arxiv 2412.11257).
  f_cost(X)              -- a cheap predictor of the expensive pipeline's per-case
                            cost C (the cheap rollout's measured cost; near-free).

Plus per-case features for the smarter rectifiers (R1 stratified, R2 regression,
R3 matrix factorization): input_tokens, output_tokens, latency, narrative_chars.

The cheap predictor is anchored to the baseline workflow. As NSGA-II mutates a
candidate away from baseline, corr(f, Y_candidate) decays -- the decorrelation
the rectifiers must handle honestly.

Output: ppi_eval/cache/cheap_preds_<benchmark>.json
  {
    "meta":  {benchmark, model, split, n, base_f_accuracy, base_f_cost_mean, ...},
    "cases": { case_name: {f_correct, f_cost, input_tokens, output_tokens,
                           latency, narrative_chars, expected} }
  }

Run:
  uv run python -m ppi_eval.cheap_predictor --benchmark musr_team
  uv run python -m ppi_eval.cheap_predictor --benchmark musr_team --n 4   # smoke
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
CACHE_DIR = Path(__file__).resolve().parent / "cache"
ROLLOUT_DIR = CACHE_DIR / "rollouts"


# --- benchmark configuration -------------------------------------------------
#
# A "rollout" benchmark generates f by subprocess-running the project's expt.py
# with the BASELINE method override under a cheap model. This reuses the
# benchmark's deterministic case sampling (shuffle_seed) so the cheap table and
# the candidate's real runs align on case_name for free.

BENCHMARKS = {
    "musr_team": dict(
        mode="rollout",
        cwd=REPO / "benchmarks/musr",
        # base_command is split into argv; expt.py resolves config_file vs cwd.
        base_command=[
            "uv", "run", "python", "expt.py", "run",
            "--config-file", "conf/team.yaml",
        ],
        # The baseline workflow: structured_baseline from nsga2_team.yaml.
        baseline_overrides=["ptools.answer_question.method=simulate"],
        # Cheap-and-robust knobs: no <thought> scaffolding (short outputs),
        # capped output, and a short per-call timeout so a stalled flash-lite
        # request fails fast rather than hanging the watchdog-less serial loop.
        robust_overrides=[
            "llm.thinking=false",
            "llm.max_tokens=2048",
            "llm.timeout=60",
        ],
        cheap_model="gemini/gemini-2.5-flash-lite",
        split="team_allocation_trainval",
        # Source data file (same dir) used to attach narrative-length features.
        data_file=REPO / "benchmarks/musr/data/team_allocation_trainval.json",
        default_n=150,
    ),
}


def _data_features(data_file: Path) -> dict[str, dict]:
    """Map case_name -> input-length features from the raw split file.

    Case names are ex{i:03d} assigned by the loader in pre-shuffle file order,
    so examples[i] corresponds to case ex{i:03d}.
    """
    feats: dict[str, dict] = {}
    if not data_file or not Path(data_file).exists():
        return feats
    data = json.loads(Path(data_file).read_text(encoding="utf-8"))
    for i, ex in enumerate(data["examples"]):
        narrative = str(ex.get("narrative", ""))
        question = str(ex.get("question", ""))
        feats[f"ex{i:03d}"] = dict(
            narrative_chars=len(narrative),
            question_chars=len(question),
        )
    return feats


def _run_rollout(cfg: dict, n: int, timeout: int, workers: int) -> Path:
    """Subprocess-run the baseline cheap rollout; return the results.csv path."""
    ROLLOUT_DIR.mkdir(parents=True, exist_ok=True)
    result_dir = ROLLOUT_DIR / cfg["split"]
    cmd = (
        list(cfg["base_command"])
        + list(cfg["baseline_overrides"])
        + list(cfg.get("robust_overrides", []))
        + [
            f"dataset.split={cfg['split']}",
            f"dataset.n={n}",
            f"llm.model={cfg['cheap_model']}",
            "evaluate.expt_name=cheap_f",
            f"evaluate.result_dir={result_dir}",
            f"evaluate.max_workers={workers}",
        ]
    )
    print(f"  rollout: {' '.join(str(c) for c in cmd)}")
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cfg["cwd"]),
        timeout=timeout,
        env=os.environ.copy(),
    )
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().split("\n")[-8:])
        sys.exit(f"cheap rollout FAILED (exit {proc.returncode}):\n{tail}")

    csv_path = None
    for line in proc.stdout.split("\n"):
        if "saved in" in line and ".csv" in line:
            csv_path = line.split("saved in ")[-1].strip()
    if not csv_path or not Path(csv_path).exists():
        sys.exit(f"could not locate results.csv in rollout stdout:\n{proc.stdout[-500:]}")
    return Path(csv_path)


def reshape_csv_to_cache(benchmark: str, csv_path: Path, n: int | None = None) -> Path:
    """Reshape a baseline rollout results.csv into the cheap-prediction cache."""
    cfg = BENCHMARKS[benchmark]
    df = pd.read_csv(csv_path)
    feats = _data_features(cfg.get("data_file"))

    cases: dict[str, dict] = {}
    for _, row in df.iterrows():
        name = str(row["case_name"])
        correct = row.get("correct")
        # correct is read as bool/str depending on pandas; coerce to 0/1.
        f_correct = int(bool(correct)) if not pd.isna(correct) else None
        cost = row.get("cost")
        f_cost = float(cost) if not pd.isna(cost) else None
        rec = dict(
            f_correct=f_correct,
            f_cost=f_cost,
            input_tokens=(None if pd.isna(row.get("input_tokens")) else float(row["input_tokens"])),
            output_tokens=(None if pd.isna(row.get("output_tokens")) else float(row["output_tokens"])),
            latency=(None if pd.isna(row.get("latency")) else float(row["latency"])),
            expected=(None if pd.isna(row.get("expected_output")) else str(row["expected_output"])),
        )
        rec.update(feats.get(name, {}))
        cases[name] = rec

    valid_correct = [v["f_correct"] for v in cases.values() if v["f_correct"] is not None]
    valid_cost = [v["f_cost"] for v in cases.values() if v["f_cost"] is not None]
    meta = dict(
        benchmark=benchmark,
        model=cfg["cheap_model"],
        split=cfg["split"],
        n=(n if n is not None else len(cases)),
        n_cases=len(cases),
        base_f_accuracy=(sum(valid_correct) / len(valid_correct) if valid_correct else None),
        base_f_cost_mean=(sum(valid_cost) / len(valid_cost) if valid_cost else None),
        source_csv=str(csv_path),
    )

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CACHE_DIR / f"cheap_preds_{benchmark}.json"
    out_path.write_text(
        json.dumps(dict(meta=meta, cases=cases), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"saved {len(cases)} cheap preds -> {out_path}")
    acc = meta["base_f_accuracy"]
    cst = meta["base_f_cost_mean"]
    print(
        f"  base f-accuracy={acc:.3f}  base f-cost mean=${cst:.5f}"
        if acc is not None and cst is not None
        else f"  base f-accuracy={acc}  base f-cost mean={cst}"
    )
    return out_path


def build_cache(benchmark: str, n: int | None, timeout: int, workers: int) -> Path:
    cfg = BENCHMARKS[benchmark]
    if cfg["mode"] != "rollout":
        sys.exit(f"benchmark {benchmark} mode={cfg['mode']} not supported here")

    n = n if n is not None else cfg["default_n"]
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit(
            "GEMINI_API_KEY is not set in this shell.\n"
            '  bash:  export GEMINI_API_KEY="<your key>"'
        )

    csv_path = _run_rollout(cfg, n, timeout, workers)
    return reshape_csv_to_cache(benchmark, csv_path, n)


def load_cache(benchmark: str) -> dict:
    path = CACHE_DIR / f"cheap_preds_{benchmark}.json"
    if not path.exists():
        raise FileNotFoundError(f"no cheap cache for {benchmark}: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", choices=list(BENCHMARKS), default="musr_team")
    ap.add_argument("--n", type=int, default=None, help="num cases (default = benchmark default)")
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--workers", type=int, default=1, help="parallel eval workers (1 on Windows; >1 needs SIGALRM)")
    ap.add_argument("--results-csv", default=None,
                    help="skip the rollout and reshape this existing results.csv into the cache")
    args = ap.parse_args()
    if args.results_csv:
        reshape_csv_to_cache(args.benchmark, Path(args.results_csv), args.n)
    else:
        build_cache(args.benchmark, args.n, args.timeout, args.workers)


if __name__ == "__main__":
    main()
