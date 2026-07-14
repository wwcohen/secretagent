"""A/B experiment: naive vs PPI scoring inside the optimizer.

Two phases.

PHASE 1 -- collect (EXPENSIVE, real LLM calls):
  Run each candidate workflow (the yaml `methods`, at a fixed candidate model)
  on the FULL trainval pool (150) and the held-out test split (100), and cache
  the per-case ground-truth outcome Y (correct, cost, tokens) per config.
    uv run python -m ppi_eval.ab_experiment collect --split team_allocation_trainval
    uv run python -m ppi_eval.ab_experiment collect --split team_allocation_test

PHASE 2 -- report (CHEAP, no LLM calls):
  From the collected truth + the cheap-prediction cache, produce both layers of
  the result, averaged over many random n-labeled subsamples (the "fixed
  expensive-eval budget"):
    (a) ESTIMATOR layer -- per config: corr(f, Y), and naive vs R0 vs R1 bias,
        CI coverage (vs the full-pool theta_star) and CI width.
    (b) OPTIMIZER layer -- per scoring rule (naive, R0, R1): the Pareto front it
        selects on the subsample, the TEST accuracy / cost of the selected
        best-accuracy config, the valid->test generalization gap, and the
        TEST-set hypervolume of the selected front.
    uv run python -m ppi_eval.ab_experiment report

The optimizer simulation scores each config with exactly the estimators the
pareto.py hook uses, so it is the same embedded-PPI logic driven over many
subsamples instead of one subprocess NSGA-II run. The literal hook can still be
exercised end-to-end via the optimize CLI with SECRETAGENT_USE_PPI=1 (see
RESULTS.md).
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

REPO = Path(__file__).resolve().parents[1]
CACHE_DIR = Path(__file__).resolve().parent / "cache"
MUSR = REPO / "benchmarks" / "musr"
SPACE_FILE = MUSR / "nsga2_team.yaml"

# Candidate workflows to evaluate (subset of the yaml `methods`). The rank
# inversion of interest is pot vs wf_orch; structured_baseline is the anchor the
# cheap predictor is built from.
DEFAULT_CONFIGS = ["structured_baseline", "zs_cot", "workflow", "pot", "wf_orch"]

CANDIDATE_MODEL = "gemini/gemini-2.5-flash"
# Robust, non-thinking overrides: short outputs, hard per-call timeout (the
# serial eval loop has no watchdog on Windows), consistent with the cheap cache.
ROBUST_OVERRIDES = ["llm.thinking=false", "llm.timeout=120", "llm.max_tokens=4096"]


def _method_overrides() -> dict[str, list[str]]:
    spec = yaml.safe_load(SPACE_FILE.read_text(encoding="utf-8"))
    return spec["methods"]


def _truth_path(split: str) -> Path:
    return CACHE_DIR / f"truth_{split}.json"


# ---------------------------------------------------------------------------
# Phase 1: collect ground-truth Y per config
# ---------------------------------------------------------------------------

def _run_config(method: str, overrides: list[str], split: str, n: int,
                model: str, timeout: int) -> pd.DataFrame:
    result_dir = CACHE_DIR / "truth_runs" / split / method
    cmd = (
        ["uv", "run", "python", "expt.py", "run", "--config-file", "conf/team.yaml"]
        + [f"llm.model={model}"]
        + ROBUST_OVERRIDES
        + overrides
        + [
            f"dataset.split={split}",
            f"dataset.n={n}",
            f"evaluate.expt_name=truth_{method}",
            f"evaluate.result_dir={result_dir}",
        ]
    )
    print(f"\n  === [{method}] {split} (n<={n}) ===", flush=True)
    # Stream the child's output (tqdm progress visible live); locate the saved
    # results.csv by globbing the result dir afterwards.
    proc = subprocess.run(cmd, cwd=str(MUSR), timeout=timeout, env=os.environ.copy())
    if proc.returncode != 0:
        print(f"    FAILED ({method}, exit {proc.returncode})")
        return pd.DataFrame()
    csvs = sorted(result_dir.glob("*/results.csv"), key=lambda p: p.stat().st_mtime)
    if not csvs:
        print(f"    no results.csv for {method}")
        return pd.DataFrame()
    return pd.read_csv(csvs[-1])


def collect(split: str, configs: list[str], model: str, n: int, timeout: int):
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit('GEMINI_API_KEY not set. bash: export GEMINI_API_KEY="<key>"')
    overrides = _method_overrides()
    path = _truth_path(split)
    truth = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    for method in configs:
        if method in truth:
            print(f"  [{method}] already collected ({len(truth[method])} cases) -- skip")
            continue
        if method not in overrides:
            print(f"  [{method}] not in yaml methods -- skip")
            continue
        df = _run_config(method, overrides[method], split, n, model, timeout)
        if df.empty:
            continue
        cases = {}
        for _, r in df.iterrows():
            cases[str(r["case_name"])] = dict(
                correct=1.0 if str(r.get("correct")).strip().lower() in ("true", "1", "1.0") else 0.0,
                cost=(None if pd.isna(r.get("cost")) else float(r["cost"])),
                input_tokens=(None if pd.isna(r.get("input_tokens")) else float(r["input_tokens"])),
            )
        truth[method] = cases
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(truth, indent=2), encoding="utf-8")
        acc = np.mean([c["correct"] for c in cases.values()])
        print(f"  [{method}] saved {len(cases)} cases, full-pool acc={acc:.3f}")
    print(f"truth -> {path}")


# ---------------------------------------------------------------------------
# Phase 2: report (estimator + optimizer layers), simulated over subsamples
# ---------------------------------------------------------------------------

def _aligned(truth_cfg: dict, cheap: dict, names: list[str], field: str, cheap_field: str):
    """Return (Y, f, x) arrays aligned over names for one config."""
    y, f, x = [], [], []
    for nm in names:
        tc = truth_cfg.get(nm)
        cc = cheap.get(nm)
        if tc is None or cc is None:
            continue
        v = tc.get(field)
        y.append(np.nan if v is None else float(v))
        f.append(cc.get(cheap_field))
        x.append(cc.get("narrative_chars"))
    return np.array(y, float), np.array(f, float), np.array(x, float)


def _dominates(a, b):
    # a=(acc, cost): higher acc, lower cost
    return (a[0] >= b[0] and a[1] <= b[1]) and (a[0] > b[0] or a[1] < b[1])


def _pareto(points: dict):
    """points: {config: (acc, cost)} -> set of non-dominated configs."""
    front = []
    items = list(points.items())
    for i, (ci, pi) in enumerate(items):
        if any(j != i and _dominates(pj, pi) for j, (cj, pj) in enumerate(items)):
            continue
        front.append(ci)
    return front


def _hypervolume(front_pts, ref):
    """2D HV for (accuracy maximize, cost minimize) vs reference (acc0, cost0)."""
    pts = sorted(front_pts, key=lambda p: -p[0])  # by accuracy desc
    hv = 0.0
    prev_cost = ref[1]
    for acc, cost in pts:
        if acc <= ref[0] or cost >= ref[1]:
            continue
        hv += max(0.0, (acc - ref[0])) * max(0.0, (prev_cost - cost))
        prev_cost = cost
    return hv


def report(n_label: int, trials: int, alpha: float, seed: int, rectifiers: list[str]):
    from ppi_eval.estimators import ppi_estimate, naive_estimate, corr

    cheap = json.loads((CACHE_DIR / "cheap_preds_musr_team.json").read_text(encoding="utf-8"))["cases"]
    tv = json.loads(_truth_path("team_allocation_trainval").read_text(encoding="utf-8"))
    te_path = _truth_path("team_allocation_test")
    te = json.loads(te_path.read_text(encoding="utf-8")) if te_path.exists() else {}

    configs = [c for c in tv]
    pool = sorted(set(cheap) & set.intersection(*[set(tv[c]) for c in configs]))
    print(f"configs={configs}")
    print(f"aligned trainval pool size = {len(pool)}  (cheap {len(cheap)})")

    # Full-pool ground truth per config (the estimand theta_star).
    theta = {c: float(np.mean([tv[c][nm]["correct"] for nm in pool])) for c in configs}
    cost_star = {c: float(np.nanmean([tv[c][nm]["cost"] for nm in pool if tv[c][nm]["cost"] is not None])) for c in configs}
    test_acc = {c: (float(np.mean([te[c][nm]["correct"] for nm in te[c]])) if c in te and te[c] else float("nan")) for c in configs}
    test_cost = {c: (float(np.nanmean([te[c][nm]["cost"] for nm in te[c] if te[c][nm]["cost"] is not None])) if c in te and te[c] else float("nan")) for c in configs}

    # corr(f, Y) per config -- the decorrelation signal.
    corrs = {}
    for c in configs:
        y, f, _ = _aligned(tv[c], cheap, pool, "correct", "f_correct")
        corrs[c] = corr(y, f)

    rng = np.random.default_rng(seed)
    P = len(pool)
    methods = ["naive"] + list(rectifiers)

    # --- estimator layer accumulators ---
    est = {c: {m: dict(bias=0.0, width=0.0, cover=0.0) for m in methods} for c in configs}
    # --- optimizer layer accumulators ---
    opt = {m: dict(test_acc_sel=0.0, gap=0.0, hv=0.0, picks={}) for m in methods}

    # reference point for hypervolume: worst accuracy, max cost over configs
    ref_acc = min(theta.values())
    ref_cost = max(cost_star.values()) * 1.1

    for t in range(trials):
        perm = rng.permutation(P)
        lab_idx, unlab_idx = perm[:n_label], perm[n_label:]
        lab_names = [pool[i] for i in lab_idx]
        unlab_names = [pool[i] for i in unlab_idx]

        # Per-case cheap features, shared across configs in this subsample.
        # R1 stratifies on narrative_chars (column 0); R2 uses the full matrix.
        FEATS = ["narrative_chars", "input_tokens", "output_tokens", "question_chars"]
        x1_L = np.array([cheap[nm]["narrative_chars"] for nm in lab_names], float)
        x1_U = np.array([cheap[nm]["narrative_chars"] for nm in unlab_names], float)
        xM_L = np.array([[cheap[nm][k] for k in FEATS] for nm in lab_names], float)
        xM_U = np.array([[cheap[nm][k] for k in FEATS] for nm in unlab_names], float)

        def _x(rect, labeled):
            if rect == "R2":
                return xM_L if labeled else xM_U
            if rect == "R1":
                return x1_L if labeled else x1_U
            return None

        scored = {m: {} for m in methods}  # method -> config -> (acc_est, cost_est)
        for c in configs:
            yL = np.array([tv[c][nm]["correct"] for nm in lab_names], float)
            fL = np.array([cheap[nm]["f_correct"] for nm in lab_names], float)
            fU = np.array([cheap[nm]["f_correct"] for nm in unlab_names], float)
            cL = np.array([(tv[c][nm]["cost"] if tv[c][nm]["cost"] is not None else np.nan) for nm in lab_names], float)
            cfL = np.array([cheap[nm]["f_cost"] for nm in lab_names], float)
            cfU = np.array([cheap[nm]["f_cost"] for nm in unlab_names], float)

            naive_a = naive_estimate(yL, alpha)
            naive_c = float(np.nanmean(cL)) if np.isfinite(cL).any() else ref_cost
            scored["naive"][c] = (naive_a.estimate, naive_c)
            est[c]["naive"]["bias"] += naive_a.estimate - theta[c]
            est[c]["naive"]["width"] += 2 * naive_a.half_width
            est[c]["naive"]["cover"] += naive_a.ci_lo <= theta[c] <= naive_a.ci_hi

            for rect in rectifiers:
                ra = ppi_estimate(yL, fL, fU, rectifier=rect, x_lab=_x(rect, True), x_unlab=_x(rect, False), alpha=alpha)
                rc = ppi_estimate(cL, cfL, cfU, rectifier=rect, x_lab=_x(rect, True), x_unlab=_x(rect, False), alpha=alpha)
                a_est = ra.estimate if np.isfinite(ra.estimate) else naive_a.estimate
                c_est = rc.estimate if np.isfinite(rc.estimate) else naive_c
                scored[rect][c] = (a_est, c_est)
                est[c][rect]["bias"] += a_est - theta[c]
                est[c][rect]["width"] += 2 * ra.half_width
                est[c][rect]["cover"] += ra.ci_lo <= theta[c] <= ra.ci_hi

        # optimizer layer: each scoring picks a Pareto front; the "selected"
        # config maximizes estimated accuracy on the front.
        for m in methods:
            pts = scored[m]
            front = _pareto(pts)
            sel = max(front, key=lambda c: pts[c][0])
            opt[m]["test_acc_sel"] += test_acc.get(sel, np.nan)
            opt[m]["gap"] += pts[sel][0] - test_acc.get(sel, np.nan)
            opt[m]["picks"][sel] = opt[m]["picks"].get(sel, 0) + 1
            front_test = [(test_acc[c], test_cost[c]) for c in front
                          if np.isfinite(test_acc.get(c, np.nan))]
            opt[m]["hv"] += _hypervolume(front_test, (ref_acc, ref_cost))

    T = trials
    # ---- print + collect report ----
    out = dict(meta=dict(configs=configs, n_label=n_label, trials=T, alpha=alpha,
                         pool=len(pool), candidate_model=CANDIDATE_MODEL),
               theta_star=theta, test_acc=test_acc, corr_f_y=corrs)

    print("\n=== ESTIMATOR LAYER (per config; averaged over %d subsamples, n=%d) ===" % (T, n_label))
    print(f"{'config':<20}{'corr':>7}{'theta*':>8}  " + "".join(f"{m+'_bias':>11}{m+'_wid':>9}{m+'_cov':>8}" for m in methods))
    est_report = {}
    for c in configs:
        row = f"{c:<20}{corrs[c]:>7.3f}{theta[c]:>8.3f}  "
        est_report[c] = {}
        for m in methods:
            b = est[c][m]["bias"] / T
            w = est[c][m]["width"] / T
            cv = est[c][m]["cover"] / T
            est_report[c][m] = dict(bias=b, width=w, coverage=cv)
            row += f"{b:>11.4f}{w:>9.3f}{cv:>8.3f}"
        print(row)
    out["estimator"] = est_report

    print("\n=== OPTIMIZER LAYER (averaged over %d subsamples) ===" % T)
    print(f"{'scoring':<8}{'test_acc_sel':>14}{'valid-test_gap':>16}{'test_HV':>10}  picks")
    opt_report = {}
    for m in methods:
        ta = opt[m]["test_acc_sel"] / T
        gp = opt[m]["gap"] / T
        hv = opt[m]["hv"] / T
        picks = {k: round(v / T, 3) for k, v in sorted(opt[m]["picks"].items(), key=lambda kv: -kv[1])}
        opt_report[m] = dict(test_acc_selected=ta, valid_test_gap=gp, test_hypervolume=hv, pick_freq=picks)
        print(f"{m:<8}{ta:>14.3f}{gp:>16.3f}{hv:>10.5f}  {picks}")
    out["optimizer"] = opt_report

    out_path = CACHE_DIR / "ab_report.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nreport -> {out_path}")
    return out


# ---------------------------------------------------------------------------
# Phase A: per-STEP analysis -- the wrong-step rate (RQ1) from existing truth
# ---------------------------------------------------------------------------
#
# A "step" is an accept/reject decision between a current config A and a neighbor
# B: "is B better than A?". Ground truth = sign(theta*_B - theta*_A) on the full
# pool. Under a fixed labeled budget we estimate A and B on the SAME n-case
# subsample and decide B>A iff est_B > est_A. A WRONG step is a disagreement with
# ground truth:
#   - false ACCEPT: truth says the move A->B hurts, but we accept it (degrades).
#   - false REJECT: truth says A->B helps, but we reject it (missed improvement).
# We compare naive scoring vs PPI rectifiers over all ordered config pairs and
# many subsamples -- zero new LLM calls.

def _acc_scores(configs, tv, cheap, lab_names, unlab_names, methods, rectifiers, alpha):
    """Return {method: {config: accuracy estimate}} for one labeled subsample."""
    from ppi_eval.estimators import ppi_estimate, naive_estimate

    x1_L = np.array([cheap[nm]["narrative_chars"] for nm in lab_names], float)
    x1_U = np.array([cheap[nm]["narrative_chars"] for nm in unlab_names], float)
    FEATS = ["narrative_chars", "input_tokens", "output_tokens", "question_chars"]
    xM_L = np.array([[cheap[nm][k] for k in FEATS] for nm in lab_names], float)
    xM_U = np.array([[cheap[nm][k] for k in FEATS] for nm in unlab_names], float)

    def _x(rect, labeled):
        if rect == "R2":
            return xM_L if labeled else xM_U
        if rect == "R1":
            return x1_L if labeled else x1_U
        return None

    out = {m: {} for m in methods}
    for c in configs:
        yL = np.array([tv[c][nm]["correct"] for nm in lab_names], float)
        fL = np.array([cheap[nm]["f_correct"] for nm in lab_names], float)
        fU = np.array([cheap[nm]["f_correct"] for nm in unlab_names], float)
        out["naive"][c] = naive_estimate(yL, alpha).estimate
        for rect in rectifiers:
            r = ppi_estimate(yL, fL, fU, rectifier=rect,
                             x_lab=_x(rect, True), x_unlab=_x(rect, False), alpha=alpha)
            out[rect][c] = r.estimate if np.isfinite(r.estimate) else out["naive"][c]
    return out


def steps(n_label, trials, alpha, seed, rectifiers, include_broken=False, low_corr_tau=0.2):
    from ppi_eval.estimators import corr

    cheap = json.loads((CACHE_DIR / "cheap_preds_musr_team.json").read_text(encoding="utf-8"))["cases"]
    tv = json.loads(_truth_path("team_allocation_trainval").read_text(encoding="utf-8"))

    configs = list(tv)
    pool = sorted(set(cheap) & set.intersection(*[set(tv[c]) for c in configs]))
    # Drop degenerate (zero-variance, e.g. the broken 0% config) unless asked.
    theta_all = {c: float(np.mean([tv[c][nm]["correct"] for nm in pool])) for c in configs}
    if not include_broken:
        configs = [c for c in configs
                   if np.std([tv[c][nm]["correct"] for nm in pool]) > 0]
    theta = {c: theta_all[c] for c in configs}
    corrs = {c: corr(np.array([tv[c][nm]["correct"] for nm in pool], float),
                     np.array([cheap[nm]["f_correct"] for nm in pool], float)) for c in configs}
    low = {c for c in configs if corrs[c] < low_corr_tau}

    methods = ["naive"] + list(rectifiers)
    P = len(pool)
    rng = np.random.default_rng(seed)

    # Stratify by the TRUE accuracy gap of the pair (the real driver of step
    # difficulty), not by correlation (which is confounded with gap here).
    GAP_CUT = 0.10
    agg = {m: dict(wrong=0, fa=0, fr=0) for m in methods}
    agg_close = {m: dict(wrong=0, tot=0) for m in methods}   # |gap| < GAP_CUT (hard)
    agg_clear = {m: dict(wrong=0, tot=0) for m in methods}   # |gap| >= GAP_CUT (easy)

    pairs = [(a, b) for a in configs for b in configs if a != b and abs(theta[a] - theta[b]) > 1e-9]

    for t in range(trials):
        perm = rng.permutation(P)
        lab = [pool[i] for i in perm[:n_label]]
        unlab = [pool[i] for i in perm[n_label:]]
        est = _acc_scores(configs, tv, cheap, lab, unlab, methods, rectifiers, alpha)
        for a, b in pairs:
            truth_up = theta[b] > theta[a]          # is move A->B truly an improvement?
            close = abs(theta[a] - theta[b]) < GAP_CUT
            for m in methods:
                dec_up = est[m][b] > est[m][a]
                wrong = dec_up != truth_up
                if wrong:
                    agg[m]["wrong"] += 1
                    if truth_up and not dec_up:
                        agg[m]["fr"] += 1            # missed a good move
                    else:
                        agg[m]["fa"] += 1            # took a bad move
                bucket = agg_close if close else agg_clear
                bucket[m]["wrong"] += wrong
                bucket[m]["tot"] += 1

    npairs = len(pairs)
    denom = trials * npairs
    print(f"configs={configs}")
    print(f"corr(f,Y): " + "  ".join(f"{c}={corrs[c]:.2f}" for c in configs))
    print(f"\n=== WRONG-STEP RATE  (n={n_label}, {trials} subsamples x {npairs} ordered pairs = {denom} decisions) ===")
    print(f"{'scoring':<8}{'wrong%':>9}{'false-accept%':>15}{'false-reject%':>15}"
          f"{'wrong%|close-gap':>18}{'wrong%|clear-gap':>18}")
    rep = {}
    for m in methods:
        wr = 100 * agg[m]["wrong"] / denom
        fa = 100 * agg[m]["fa"] / denom
        fr = 100 * agg[m]["fr"] / denom
        wc = 100 * agg_close[m]["wrong"] / max(agg_close[m]["tot"], 1)
        we = 100 * agg_clear[m]["wrong"] / max(agg_clear[m]["tot"], 1)
        rep[m] = dict(wrong_pct=wr, false_accept_pct=fa, false_reject_pct=fr,
                      wrong_close_gap_pct=wc, wrong_clear_gap_pct=we)
        print(f"{m:<8}{wr:>9.2f}{fa:>15.2f}{fr:>15.2f}{wc:>18.2f}{we:>18.2f}")
    print(f"(close-gap = true |Δacc| < {GAP_CUT}; the hard hill-climbing decisions)")

    out = dict(meta=dict(n_label=n_label, trials=trials, configs=configs,
                         corr_f_y=corrs, n_pairs=npairs, gap_cut=GAP_CUT), wrong_step=rep)
    p = CACHE_DIR / "step_report.json"
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nstep report -> {p}")
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("collect", help="run candidates on a split to collect ground-truth Y")
    c.add_argument("--split", required=True)
    c.add_argument("--configs", nargs="*", default=DEFAULT_CONFIGS)
    c.add_argument("--model", default=CANDIDATE_MODEL)
    c.add_argument("--n", type=int, default=1000, help="cases (>= split size = all)")
    c.add_argument("--timeout", type=int, default=3600)

    r = sub.add_parser("report", help="estimator + optimizer layers from collected truth")
    r.add_argument("--n-label", type=int, default=25)
    r.add_argument("--trials", type=int, default=300)
    r.add_argument("--alpha", type=float, default=0.05)
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--rectifiers", nargs="*", default=["R0", "R1"])

    s = sub.add_parser("steps", help="wrong-step rate (RQ1): naive vs PPI accept/reject decisions")
    s.add_argument("--n-label", type=int, default=25)
    s.add_argument("--trials", type=int, default=500)
    s.add_argument("--alpha", type=float, default=0.05)
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--rectifiers", nargs="*", default=["R0", "R1", "R2"])
    s.add_argument("--include-broken", action="store_true",
                   help="keep zero-variance configs (e.g. the broken 0%% zs_cot)")

    args = ap.parse_args()
    if args.cmd == "collect":
        collect(args.split, args.configs, args.model, args.n, args.timeout)
    elif args.cmd == "steps":
        steps(args.n_label, args.trials, args.alpha, args.seed, args.rectifiers,
              include_broken=args.include_broken)
    else:
        report(args.n_label, args.trials, args.alpha, args.seed, args.rectifiers)


if __name__ == "__main__":
    main()
