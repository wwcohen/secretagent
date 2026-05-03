# Code Distillation Results — gemini (Gemini 3.1 Pro Preview as learner)

**Branch**: `codedistill-v2` · **Date**: 2026-05-01

This is the Gemini-as-learner counterpart to
[code_distillation_results_v2.md](code_distillation_results_v2.md). Same
benchmarks, same recordings, same val splits, same `--max-wrong-rate 0.20`
gate. The **only** change is the LLM that generates Python code:

| | opus | gemini |
|---|---|---|
| Learner (writes Python) | `claude-opus-4-6` | `gemini/gemini-3.1-pro-preview` |
| Baseline (simulate ptool, runs in workflow) | `together_ai/deepseek-ai/DeepSeek-V3.1` (V3 for musr/rulearena) | unchanged |

Pipeline:
- [run_class1_gemini_distill.sh](../benchmarks/jerry/class1_iters/run_class1_gemini_distill.sh)
- [run_class2_gemini_distill.sh](../benchmarks/jerry/class2_iters/run_class2_gemini_distill.sh)
- [run_gemini_vals_watcher.sh](../benchmarks/jerry/class2_iters/run_gemini_vals_watcher.sh) — auto-launches val per benchmark as distill completes

---

## Headline result table — opus (Opus) vs gemini (Gemini Pro)

Cells marked `—` mean **distill ran but the gate enabled 0 applicable
ptools** (or the ENABLED ptools live in a different sub-benchmark's ptool
module). Effectively `c1 ≡ baseline` for those cells.

| benchmark | n | baseline | c1_opus | c1_gemini | c2_opus | c2_gemini | Δ c2 (gemini − opus) |
|---|---|---|---|---|---|---|---|
| natplan_calendar | 100 | 55% | 54% | — (a) | **87%** | 59% | -28pp ❌ |
| natplan_meeting | 100 | 29% | — | — (a) | **98%** | 29% | -69pp ❌ collapses |
| **natplan_trip** | 100 | 21% | 21% | **82%** ⭐ | 21% | **91%** | **+70pp** ⭐⭐⭐ |
| musr_murder | 75 | 68% | 68% | 61% | 60% | 59% | -1pp |
| musr_object | 75 | 61% | 61% | 55% | 68% | 59% | -9pp |
| musr_team | 75 | 53% | 33% | **65%** ⭐ | 60% | 56% | -4pp |
| bbh_sports | 75 | 99% | 99% | 97% | 99% | 99% | 0 (saturated) |
| bbh_penguins | 43 | 72% | 67% | **81%** | 88% | 91% | +3pp |
| bbh_geometric | 75 | 37% | — | — | **100%** | 35% | -65pp ❌ |
| bbh_date | 75 | 83% | — | — | 88% | 84% | -4pp |
| medcalc | 100 | 61% | — | — | 62% | 61% | -1pp |
| finqa | 100 | 67% | 67% | 53% | 67% | 67% | 0 (parity) |
| rulearena_airline | 50 | 46% | — | — | **100%** | **100%** | 0 (saturated) |
| tabmwp | 100 | 36% | 39% | 40% | 45% | **51%** | +6pp |

**(a)** natplan_calendar/meeting c1_gemini are blank because the ONLY ptool
that passed Gemini's c1_gemini gate was `build_trip_plan` — which lives in
`ptools_trip` only, doesn't apply to calendar or meeting.

---

## Same numbers on the held-out TEST split (no re-distill)

Re-ran each cached distill (`learned_opus/`, `learned_gemini/`,
`learned_class2_opus/`, `learned_class2_gemini/`) on each benchmark's held-out
**test split** (`dataset.split=test` / `dataset.partition=test` /
`dataset.split=test1k` for tabmwp). No new training — just inference, with
`backoff=true` → DeepSeek when generated code returns None. Most rankings
hold; trip and penguins **widen** their Gemini margins, geometric/meeting
keep collapsing for gemini.

| benchmark | n | baseline | c1_opus | c1_gemini | c2_opus | c2_gemini | Δ c2 (gemini − opus) |
|---|---|---|---|---|---|---|---|
| natplan_calendar | 100 | 55% | 55% | — (a) | **90%** | 53% | -37pp ❌ |
| natplan_meeting | 100 | 25% | — | — (a) | **99%** | 27% | -72pp ❌ |
| **natplan_trip** | 100 | 8% | 24% | **90%** ⭐ | 10% | **97%** | **+87pp** ⭐⭐⭐ |
| musr_murder | 75 | 52% | 64% | **67%** | **69%** | 64% | -5pp |
| musr_object | 75 | 56% | 60% | 59% | 60% | 61% | +1pp |
| musr_team | 75 | 57% | 40% | 61% | 64% | **67%** | +3pp |
| bbh_sports | 75 | 76% | 81% | 79% | 84% | 83% | -1pp |
| bbh_penguins | 43 | 56% | 58% | 63% | 81% | **93%** | +12pp ⭐ |
| bbh_geometric | 75 | 31% | — | — | **100%** | 25% | -75pp ❌ |
| bbh_date | 75 | 89% | — | — | 91% | 89% | -2pp |
| medcalc | 100 | 61% | — | — | 62% | 61% | -1pp |
| rulearena_nba | 46 | 65% | — | — | — | — | n/a |
| rulearena_tax | 50 | 64% | — | — | — | — | n/a |
| rulearena_airline | 50 | 38% | — | — | **100%** | **100%** | 0 (saturated) |
| tabmwp | 100 | 47% | 51% | 48% | **59%** | 57% | -2pp |

**finqa** has no test split (only train + valid) so it's not in this table.

---

## Plot — Cost vs accuracy (gemini)

![](plots/plot1_gemini_cost_vs_acc.png)

X = USD cost per case (symlog). Y = val accuracy. Up to 3 points per
benchmark connected by gray arrows: ● baseline, ■ c1_gemini, ▲ c2_gemini.
Up-and-left = better. Same layout as `plot1_cost_vs_acc.png` in the
Opus doc, with gemini data.

---

## Headline observations

### 1. Trip planning — Gemini's biggest win (+70pp on c2, +61pp on c1)

Class 2 opus (Opus) wrote a **68-line wrapper** that just falls back to
baseline LLM (acc = 21%, parity).

Class 2 gemini (Gemini Pro) wrote a **176-line real backtracking solver**:
parses cities/durations/events/flight-graph with regex, runs graph DFS
with day-window constraints. End-to-end val acc = **91%** on n=100
disjoint val split.

Class 1 gemini also: `build_trip_plan` was the only ENABLED ptool, and it
got 82% on val (vs Opus 21%).

**Verified non-leak**: train (n=100) and valid (n=100) have 0 overlap on
both case names AND input prompts.

### 2. Geometric / meeting / calendar — Gemini's biggest losses (−28 to −69 pp)

| | Opus c2_opus | Gemini c2_gemini | Opus generated | Gemini generated |
|---|---|---|---|---|
| bbh_geometric | 100% | 35% | 255-line pure-Python SVG classifier | 133-line wrapper that delegates to LLM ptools |
| natplan_meeting | 98% | 29% | 440-line DP scheduling solver | thin wrapper, returns SOLUTION-format str but content from LLM ptools |
| natplan_calendar | 87% | 59% | ~330-line solver | mid-length wrapper |

Gemini consistently **delegates to existing simulate ptools** (LLM calls)
where Opus rewrites in pure Python. When the underlying LLM ptool is
weak (e.g. shape classification), Gemini's wrapper inherits the
weakness; Opus's pure-Python solution doesn't.

### 3. Style finding — code length correlates with win

```
                  Opus avg lines    Gemini avg lines
when Opus wins:        328               118
when Gemini wins:       95               152
when tied/saturated:   ~80               ~70
```

The asymmetry is strategic:
- **Opus heuristic**: "rewrite the whole task in pure Python; don't trust LLM ptools"
- **Gemini heuristic**: "use the existing LLM ptools as building blocks; write thin orchestration"

Both are reasonable on different tasks. Trip favored Gemini's deeper
code; geometric / meeting / calendar favored Opus's algorithmic rewrite.

### 4. Class 1 gemini shows similar pattern

Big wins for Gemini c1: **musr_team 65% (vs Opus 33%, +32pp)**, **trip
82% (vs Opus 21%, +61pp)**, **penguins 81% (vs 67%, +14pp)**.

Loss for Gemini c1: **finqa 53% (vs 67%, -14pp)**.

`bbh_geometric` / `bbh_date` / `medcalc` / `rulearena_*` — both Opus and
Gemini distilled these but **0 ENABLED** ptools made it through the
`val_wrong_rate ≤ 20%` gate. Effectively c1 = baseline for both versions.

---

## When to use which (suggested heuristic)

| Task type | Recommend |
|---|---|
| Codeable algorithmic task (DP, graph, regex parse) | Either, but **prompt them to "rewrite in pure Python"** explicitly |
| Knowledge-heavy task (sports facts, medical formulas) | Opus (better at hardcoded knowledge tables) |
| Structured-format extraction | Mixed; case-by-case |
| Already-saturated tasks (sports 99%, airline 100%) | Either |

The natural follow-up: **prompt Gemini explicitly to prefer pure-Python
over LLM ptool delegation** — likely closes most of the gap on geometric
/ meeting / calendar.

---

## Class 3 gemini — workflow distill on **induced** ptools (Gemini learner)

**Date**: 2026-05-03 · pipeline:
[run_class3_gemini_distill.sh](../benchmarks/jerry/class3_iters/run_class3_gemini_distill.sh)
+ [run_class3_gemini_vals.sh](../benchmarks/jerry/class3_iters/run_class3_gemini_vals.sh)
+ [run_class3_gemini_tests.sh](../benchmarks/jerry/class3_iters/run_class3_gemini_tests.sh)

### How this differs from c2_gemini

Both classes run **the same `workflow-codedistill` learning algorithm**:
the LLM (Gemini 3.1 Pro Preview here) writes Python that replaces the
top-level workflow function. The single difference is **what `--tool-module`
points to** — i.e. the building blocks the generated workflow can call.

| | c2_gemini (already in this doc) | **c3_gemini (this section)** |
|---|---|---|
| Algorithm | workflow-codedistill | workflow-codedistill |
| Learner LLM | gemini/gemini-3.1-pro-preview | gemini/gemini-3.1-pro-preview |
| Baseline simulate (backoff target) | DS-V3.1 / DS-V3 | DS-V3.1 / DS-V3 |
| `--tool-module` source | **hand-written** ptools (`benchmarks/<bench>/ptools*.py`) | **LLM-induced** ptools (prof's `src/secretagent/learn/inducer_results/<bench>/induced_ptools_seed42_correct_*.py`) |
| What "induced" means | n/a | 4-stage pipeline (load thoughts → categorize → merge → synthesize) discovers ptools from a ReAct trace; output is a `learned_ptools.py` of `@implement_via('simulate')` stubs. Prof ran this with seed=42 and curated the "correct" subset of ptools. |
| Output dir | `learned_class2_gemini[/_sub]/` | `learned_class3_gemini_<sub>/` |

So c3_gemini is the **same Gemini-as-learner experiment as c2_gemini**, just
with the toolbox swapped from human-written to LLM-discovered. Anywhere
c2_gemini and c3_gemini diverge below, that gap is attributable to the
toolbox, not the algorithm or learner.

6 benchmarks have an induced module available (musr × 3, natplan × 2,
rulearena_nba) — those are the ones reported here.

### Results (val splits, n disjoint from distill train)

| benchmark | n | baseline | c2_gemini (hand ptools) | **c3_gemini (induced ptools)** | Δ vs baseline |
|---|---|---|---|---|---|
| musr_murder | 75 | 68% | 59% | **71%** | +3pp ✅ |
| musr_object | 75 | 61% | 59% | 52% | -9pp ❌ |
| musr_team | 75 | 53% | 56% | **61%** | +8pp ✅ |
| **natplan_meeting** | 100 | 29% | 29% | **100%** ⭐⭐⭐ | +71pp |
| **natplan_trip** | 100 | 21% | 91% | **70%** | +49pp ✅ (but -21pp vs c2_gemini) |
| **rulearena_nba** | 42 | 74% | n/a | **76%** | +2pp ✅ |

5 of 6 beat baseline. Only musr_object regressed (-9pp).

### Highlights

**natplan_meeting 100% (vs 29% baseline, +71pp)** — Gemini wrote a
425-line **pure-Python DFS scheduler** that parses the prompt with regex,
runs depth-first search with day-window/duration constraints, and emits
the SOLUTION-format string directly. Zero LLM calls at val time
(`total_cost_usd: 0`). The natural_plan eval calls `eval_meeting_single`
which checks the SOLUTION text against constraints — Gemini's solver
satisfies all 100. Mirrors what Opus did on the same benchmark in
class 2 opus (98% with a 440-line solver).

**natplan_trip 70%** — same induced module, Gemini wrote a backtracking
trip planner. Less polished than class 2 gemini's 91% (different code path,
different prompts) but still +49pp over baseline.

**musr_murder 71%** — Gemini's workflow uses `evaluate_suspect_evidence`
(an induced simulate ptool) for both suspects, then reasons via a fresh
`_extract_suspect_index` simulate stub to pick the killer. Notable: the
generated code initially used `@implement_via('simulate_from_stub')` (not
a real factory — Gemini hallucinated it). Patched to `'simulate'` before
val. With backoff=true, the workflow falls back to baseline when the
extract simulate returns garbage.

### Failure modes

- **musr_object regressed (-9pp)** — induced ptools for object_placements
  apparently don't compose into a clean workflow; Gemini wrapped them
  but didn't beat baseline.
- **natplan_trip below c2_gemini** — class 2 gemini's hand-written `ptools_trip`
  apparently makes a stronger building block than the induced trip ptools.

### Distill cost

All 6 distills ran with `--max-rounds 2 --n-candidates 5`, total wall
time ~45 min for the longest (musr_team). Each one's cache + intermediate
data is in `benchmarks/COMMON/codedistill-workflow-results/<bench>/learned_class3_gemini_<sub>/`.

### Caveats

- Induced ptool modules import `from ptools.ptools_common import _REACT_STATE`
  (prof's repo convention). The orchestrator script patches this to
  `from ptools_common import` for our repo, and we added shim
  `ptools_common.py` files (with `_REACT_STATE: dict = {}`) under
  `benchmarks/natural_plan/` and `benchmarks/rulearena/nba/` since those
  benchmarks didn't have one.
- `benchmarks/rulearena/nba/data/{train,valid,test}.json` was cp1252-encoded
  with curly quotes. Converted in-place to utf-8 to fix
  `setup_and_load_dataset`'s utf-8-only read.
- `natplan_meeting`'s 100% should be cross-checked on test split before
  declaring a clean win — class 2 opus (Opus) similarly hit 98% on val and
  99% on test, so the pattern is consistent.

### Class 3 gemini — held-out TEST split (cache reuse)

Re-ran each cached learner on the test split, no re-distill. Same flags
as val except `dataset.partition=test` / `dataset.split=*_test`. Outputs
under `benchmarks/COMMON/codedistill-workflow-results/<bench>/test_results_full/`.

| benchmark | n | val (c3_gemini) | **test (c3_gemini)** | Δ test−val |
|---|---|---|---|---|
| musr_murder | 75 | 71% | **69%** | -2pp |
| musr_object | 75 | 52% | 48% | -4pp |
| musr_team | 75 | 61% | **67%** | +6pp |
| **natplan_meeting** | 100 | 100% | **100%** ⭐ | 0 |
| **natplan_trip** | 100 | 70% | **78%** | +8pp |
| rulearena_nba | 46 | 76% | 72% | -4pp |

natplan_meeting holds at 100% on test (same pure-Python solver, different
input cases), confirming the win is real. Trip widens to 78%. musr_object
weakens further but the order-of-magnitude is preserved. Pattern matches
the opus/gemini class 1+2 test-split observations: rankings are mostly stable,
big effects (meeting/trip) widen rather than collapse.
