#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas"]
# ///
"""Print accuracy + cost tables for both workflow types to the terminal.

Two tables:
  - Handcrafted workflow         (existing_workflow class)
  - Orchestrator-generated workflow (seed_from_ptools class)

NBA fix appears as an extra row in the Orchestrator-generated table
(seed_from_ptools_nba_fix is not a separate class in the eyes of this
report, just a patched variant of seed/rulearena_nba).

medcalc breaks out into its three trained-on-which-traces variants in
the Handcrafted table (where they all live).
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]  # orchestrator-results/


def cell_stats(csv: Path) -> tuple[int, float, float]:
    """Return (n_rows, accuracy_pct, total_cost). NaN cost stays NaN."""
    if not csv.exists():
        return (0, float("nan"), float("nan"))
    df = pd.read_csv(csv)
    n = len(df)
    acc = df["correct"].mean() * 100.0 if "correct" in df else float("nan")
    cost = df["cost"].sum() if "cost" in df else float("nan")
    return n, acc, cost


def find_run(*parts: str) -> Path | None:
    """Locate the latest <TS>.test_deepseek_v3_1 dir under the given path
    (or the user's full_test_eval naming for medcalc per-trace runs)."""
    base = ROOT.joinpath(*parts)
    if not base.is_dir():
        return None
    runs = [p for p in base.iterdir() if p.is_dir() and (p / "results.csv").exists()]
    if not runs:
        return None
    return sorted(runs, key=lambda p: p.name)[-1]


def row(label: str, *parts: str) -> tuple[str, int, float, float]:
    run = find_run(*parts)
    if run is None:
        return (label, 0, float("nan"), float("nan"))
    n, acc, cost = cell_stats(run / "results.csv")
    return (label, n, acc, cost)


def fmt_cost(c: float) -> str:
    if pd.isna(c):
        return "—"
    if c == 0.0:
        return "$0.00 (no LLM)"
    return f"${c:.2f}"


def render_table(title: str, rows: list[tuple[str, int, float, float]]) -> str:
    out = []
    bar = "=" * 76
    out.append(bar)
    out.append(f"  {title}")
    out.append(bar)
    out.append(f"  {'Benchmark':<48}  {'n':>5}  {'Accuracy':>9}  {'Cost':>14}")
    out.append("  " + "-" * 84)
    for label, n, acc, cost in rows:
        acc_s = f"{acc:.1f}%" if not pd.isna(acc) else "—"
        out.append(f"  {label:<48}  {n:>5}  {acc_s:>9}  {fmt_cost(cost):>14}")
    return "\n".join(out)


def render_delta_table(title: str, rows: list[tuple[str, tuple[int, float, float], tuple[int, float, float]]]) -> str:
    """rows: (label, (n_e, acc_e, cost_e), (n_s, acc_s, cost_s))"""
    out = []
    bar = "=" * 90
    out.append(bar)
    out.append(f"  {title}")
    out.append(bar)
    out.append(f"  {'Benchmark':<48}  {'existing':>8}  {'seed':>8}  {'Δacc':>8}  {'Δcost':>9}")
    out.append("  " + "-" * 88)
    for label, (n_e, acc_e, cost_e), (n_s, acc_s, cost_s) in rows:
        if pd.isna(acc_e) or pd.isna(acc_s):
            d_acc = "—"
        else:
            dval = acc_s - acc_e
            d_acc = f"{dval:+.1f}pp"
        if pd.isna(cost_e) or pd.isna(cost_s):
            d_cost = "—"
        else:
            dc = cost_s - cost_e
            d_cost = f"{dc:+.2f}"
        acc_e_s = f"{acc_e:.1f}%" if not pd.isna(acc_e) else "—"
        acc_s_s = f"{acc_s:.1f}%" if not pd.isna(acc_s) else "—"
        out.append(f"  {label:<48}  {acc_e_s:>8}  {acc_s_s:>8}  {d_acc:>8}  ${d_cost:>8}")
    return "\n".join(out)


def main() -> None:
    handcrafted = [
        # medcalc — split by formula vs rule partition. We never report the
        # 1100-case "overall" mix because the categories have very different
        # difficulty profiles.
        row("medcalc/formulas  (learned: all traces)",
            "existing_workflow", "medcalc", "results", "learned_from_all_traces", "formulas"),
        row("medcalc/formulas  (learned: formula only)",
            "existing_workflow", "medcalc", "results", "learned_from_formula_traces", "overall"),
        row("medcalc/rules     (learned: all traces)",
            "existing_workflow", "medcalc", "results", "learned_from_all_traces", "rules"),
        row("medcalc/rules     (learned: rules only)",
            "existing_workflow", "medcalc", "results", "learned_from_rules_traces", "overall"),
        row("musr_murder",      "existing_workflow", "musr_murder", "results"),
        row("musr_object",      "existing_workflow", "musr_object", "results"),
        row("musr_team",        "existing_workflow", "musr_team", "results"),
        row("natplan_calendar", "existing_workflow", "natplan_calendar", "results"),
        row("natplan_meeting",  "existing_workflow", "natplan_meeting", "results"),
        row("natplan_trip",     "existing_workflow", "natplan_trip", "results"),
        row("rulearena_nba",    "existing_workflow", "rulearena_nba", "results"),
    ]
    orchestrator = [
        # medcalc: only learned_from_all_traces exists under seed (we did not
        # run per-trace orch_learner with seed_orchestrate=True).
        row("medcalc/formulas  (learned: all traces)",
            "seed_from_ptools", "medcalc", "results", "learned_from_all_traces", "formulas"),
        row("medcalc/rules     (learned: all traces)",
            "seed_from_ptools", "medcalc", "results", "learned_from_all_traces", "rules"),
        row("musr_murder",      "seed_from_ptools", "musr_murder", "results"),
        row("musr_object",      "seed_from_ptools", "musr_object", "results"),
        row("musr_team",        "seed_from_ptools", "musr_team", "results"),
        row("natplan_calendar", "seed_from_ptools", "natplan_calendar", "results"),
        row("natplan_meeting",  "seed_from_ptools", "natplan_meeting", "results"),
        row("natplan_trip",     "seed_from_ptools", "natplan_trip", "results"),
        row("rulearena_nba (without rulebook in query)",
            "seed_from_ptools", "rulearena_nba", "results", "without_rulebook"),
        row("rulearena_nba (with rulebook in query)",
            "seed_from_ptools", "rulearena_nba", "results", "with_rulebook"),
    ]
    # Build deltas: pair each existing-workflow row with the matching seed row.
    def _stat(*parts: str) -> tuple[int, float, float]:
        run = find_run(*parts)
        return cell_stats(run / "results.csv") if run else (0, float("nan"), float("nan"))

    delta_rows = [
        # Compare like-for-like on the same partition. We only have seed runs
        # for learned_from_all_traces, so the delta uses that variant on both
        # sides.
        ("medcalc/formulas  (learned: all traces)",
         _stat("existing_workflow", "medcalc", "results", "learned_from_all_traces", "formulas"),
         _stat("seed_from_ptools",  "medcalc", "results", "learned_from_all_traces", "formulas")),
        ("medcalc/rules     (learned: all traces)",
         _stat("existing_workflow", "medcalc", "results", "learned_from_all_traces", "rules"),
         _stat("seed_from_ptools",  "medcalc", "results", "learned_from_all_traces", "rules")),
        ("musr_murder",
         _stat("existing_workflow", "musr_murder", "results"),
         _stat("seed_from_ptools",  "musr_murder", "results")),
        ("musr_object",
         _stat("existing_workflow", "musr_object", "results"),
         _stat("seed_from_ptools",  "musr_object", "results")),
        ("musr_team",
         _stat("existing_workflow", "musr_team", "results"),
         _stat("seed_from_ptools",  "musr_team", "results")),
        ("natplan_calendar",
         _stat("existing_workflow", "natplan_calendar", "results"),
         _stat("seed_from_ptools",  "natplan_calendar", "results")),
        ("natplan_meeting †",
         _stat("existing_workflow", "natplan_meeting", "results"),
         _stat("seed_from_ptools",  "natplan_meeting", "results")),
        ("natplan_trip †",
         _stat("existing_workflow", "natplan_trip", "results"),
         _stat("seed_from_ptools",  "natplan_trip", "results")),
        ("rulearena_nba (seed: with rulebook) ‡",
         _stat("existing_workflow", "rulearena_nba", "results"),
         _stat("seed_from_ptools",  "rulearena_nba", "results", "with_rulebook")),
        ("rulearena_nba (seed: without rulebook) ‡",
         _stat("existing_workflow", "rulearena_nba", "results"),
         _stat("seed_from_ptools",  "rulearena_nba", "results", "without_rulebook")),
    ]

    print()
    print(render_table("Handcrafted workflow  (class: existing_workflow)", handcrafted))
    print()
    print(render_table("Orchestrator-generated workflow  (class: seed_from_ptools)", orchestrator))
    print()
    print(render_delta_table("Δ (seed_from_ptools − existing_workflow)", delta_rows))
    print()
    print(_FOOTNOTES)
    print()


_FOOTNOTES = """  Footnotes
  ---------
  †  Pure Python algorithmic solver (no LLM calls, cost = 0):
       • existing_workflow/natplan_meeting → meeting_workflow(prompt) is just
         return solve_meeting(prompt) — a 100-line deterministic graph search.
       • seed_from_ptools/natplan_trip → trip_workflow is similarly a pure-Python
         solver. The orch_learner discovered both could be solved without any LLM.

  ‡  rulearena_nba seed variants:
       • without_rulebook: the orch_learner-generated seed as-is. Its NBA branch
         calls extract_nba_params(problem_text) — passing only the raw problem
         text, no rules, no structured metadata. avg_input_tokens ≈ 507/case.
         Result: 26.1% accuracy (12/46), $0.02 total cost.
       • with_rulebook: manual patch in compute_rulearena_answer_orchestrated_seed
         that rebuilds the same query the existing-workflow's _build_nba_query
         uses — CBA rules text + structured team/player/operations metadata.
         avg_input_tokens ≈ 22,696/case (≈45× more context). Result: 65.2%
         accuracy (30/46), $0.65 total cost. That's +39.1pp over the seed
         without_rulebook variant and +13.0pp over the existing workflow.
         Patched ptools_evolved.py lives in
         scripts/_patched_artifacts/seed_from_ptools_nba_fix/.../ptools_evolved.py
         with PATCH_NOTES.md alongside.
       Conclusion: the seed workflow's control flow isn't the problem — it just
       needs the same reference material the existing workflow already plumbs in."""


if __name__ == "__main__":
    main()
