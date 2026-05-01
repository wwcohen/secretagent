# Code Distillation Results — v4g (Gemini 3.1 Pro Preview as learner)

**Branch**: `codedistill-v2` · **Commit**: `74ddb50` · **Date**: 2026-05-01

This is the Gemini-as-learner counterpart to
[code_distillation_results_v2.md](code_distillation_results_v2.md). Same
benchmarks, same recordings, same val splits, same `--max-wrong-rate 0.20`
gate. The **only** change is the LLM that generates Python code:

| | v4 | v4g |
|---|---|---|
| Learner (writes Python) | `claude-opus-4-6` | `gemini/gemini-3.1-pro-preview` |
| Baseline (simulate ptool, runs in workflow) | `together_ai/deepseek-ai/DeepSeek-V3.1` (V3 for musr/rulearena) | unchanged |

So a v4 vs v4g comparison cleanly answers: **does Gemini Pro write better
distilled code than Claude Opus?** Answer: **mixed — different strengths.**

Pipeline:
- [run_class1_v4g_gemini.sh](../benchmarks/jerry/class1_iters/run_class1_v4g_gemini.sh)
- [run_class2_v4g_gemini.sh](../benchmarks/jerry/class2_iters/run_class2_v4g_gemini.sh)
- [run_v4g_vals_watcher.sh](../benchmarks/jerry/class2_iters/run_v4g_vals_watcher.sh)
  — auto-launches val per benchmark as distill completes (poll every 60s)

---

## Headline result table — v4 (Opus) vs v4g (Gemini Pro)

Full-size val acc on each benchmark's `valid` split (or `test` for medcalc /
`dev1k` for tabmwp). All `c1_v4` / `c2_v4` come from
[code_distillation_results_v2.md](code_distillation_results_v2.md); `c1_v4g` /
`c2_v4g` are new.

| benchmark | n | baseline | c1_v4 | c1_v4g | c2_v4 | c2_v4g | Δ c2 (v4g vs v4) |
|---|---|---|---|---|---|---|---|
| natplan_calendar | 100 | 55% | 54% | — | **87%** | 59% | -28pp ❌ |
| natplan_meeting | 100 | 29% | — | — | **98%** | 29% | -69pp ❌ collapses |
| **natplan_trip** | 100 | 21% | 21% | — | 21% | **91%** | **+70pp** ⭐⭐⭐ |
| musr_murder | 75 | 68% | 68% | 61% | 60% | 59% | -1pp |
| musr_object | 75 | 61% | 61% | 55% | 68% | 59% | -9pp |
| musr_team | 75 | 53% | 33% | **65%** ⭐ | 60% | 56% | -4pp |
| bbh_sports | 75 | 99% | 99% | 97% | 99% | 99% | 0 (saturated) |
| bbh_penguins | 43 | 72% | 67% | **81%** ⭐ | 88% | 91% | +3pp |
| bbh_geometric | 75 | 37% | — | — | **100%** | 35% | -65pp ❌ |
| bbh_date | 75 | 83% | — | — | 88% | 84% | -4pp |
| medcalc | 100 | 61% | — | — | 62% | 61% | -1pp |
| finqa | 100 | 67% | 67% | 53% | 67% | 67% | 0 (parity) |
| rulearena_nba | 42 | 74% | — | — | — | — | — |
| rulearena_tax | 50 | 78% | — | — | — | — | — |
| rulearena_airline | 50 | 46% | — | — | **100%** | **100%** | 0 (both saturate) |
| tabmwp | 100 | 36% | 39% | **40%** | 45% | **51%** ⭐ | +6pp |

**Cells marked `—`**: distill ran but enabled 0 ptools (gate failure or
0% train acc). Effectively ≡ baseline.

## Headline observations

### 1. Trip planning (Gemini's biggest win, +70pp)

Class 2 v4 (Opus) wrote a 68-line wrapper that just falls back to baseline
LLM (acc = 21%, parity).

Class 2 v4g (Gemini Pro) wrote a **176-line real backtracking solver** that
parses the prompt (cities, durations, events, flight graph) with regex and
runs graph-DFS with day-window constraints. End-to-end val acc = 91% on
n=100 disjoint val split.

**Verified non-leak**: train (n=100) and valid (n=100) have 0 overlap on
both case names AND input prompts. Trip is a codeable task; Gemini just
chose to actually code it.

### 2. Geometric / meeting / calendar (Gemini's biggest losses)

| | Opus c2 | Gemini c2 | Opus generated | Gemini generated |
|---|---|---|---|---|
| bbh_geometric | 100% | 35% | 255-line pure-Python SVG classifier | 133-line wrapper that delegates to LLM ptools |
| natplan_meeting | 98% | 29% | 440-line DP scheduling solver | thin wrapper, returns SOLUTION-format str but content from LLM |
| natplan_calendar | 87% | 59% | 336-line solver | mid-length wrapper |

Gemini consistently **delegates to existing simulate ptools** (LLM calls)
where Opus rewrites in pure Python. When the underlying LLM ptool is
weak (e.g. shape classification, schedule reasoning), Gemini's wrapper
inherits the weakness; Opus's pure-Python solution doesn't.

### 3. Style finding — code length correlates with win

Across the 14 benchmarks, line counts of `learned.py`:

```
                  Opus avg lines    Gemini avg lines
when Opus wins:        328               118
when Gemini wins:       95               152
when tied/saturated:   ~80               ~70
```

The asymmetry is strategic, not capability:
- **Opus heuristic**: "rewrite the whole task in pure Python; don't trust LLM ptools"
- **Gemini heuristic**: "use the existing LLM ptools as building blocks; write thin orchestration"

Both are reasonable on different tasks. Trip favored Gemini's deeper code;
geometric/meeting favored Opus's algorithmic rewrite.

### 4. Class 1 v4g shows similar pattern

`musr_team` c1_v4g 65% (vs c1_v4 33%, +32pp), `bbh_penguins` c1_v4g 81%
(vs 67%, +14pp), `tabmwp` c1_v4g 40% (vs 39%, +1pp). On the other side,
`finqa` c1_v4g 53% (vs 67%, -14pp).

`bbh_geometric` / `bbh_date` / `medcalc` / `rulearena_*` — both Opus and
Gemini distilled these but **0 ENABLED** ptools made it through the
`val_wrong_rate ≤ 20%` gate (small holdout n=3-15, single error tips the
gate). Effectively c1 = baseline for both versions.

---

## Plots

(All plots show both v4 and v4g where available — class2 marker picks
LATEST timestamp, so post-2026-05-01 the green ▲ is v4g.)

### Plot 1 — Cost vs accuracy
![](plots/plot1_cost_vs_acc.png)

X = USD cost per case (symlog). Y = val accuracy. Up-and-left = better.
3 points per benchmark: ● baseline, ■ c1_v4 (latest), ▲ c2 (latest).

### Plot 2A — ptool replacement effect (Class 1)
![](plots/plot2a_ptool_replacement.png)

X = baseline acc, Y = Class 1 distilled acc. Above diagonal = distill helped.

### Plot 2B — workflow replacement effect (Class 2)
![](plots/plot2b_workflow_replacement.png)

X = baseline acc, Y = Class 2 acc. Star points are top performers.

---

## Cost / time

- v4 (Opus, full distill): ~6 hours total, ~$50-100 in API costs (estimate)
- v4g (Gemini Pro Preview, full distill): ~10 hours total, ~$3-6 estimated cost
  (Gemini Pro ~5-10x cheaper per token than Opus, slower per call due to
  thinking). Real cost not aggregated.

## When to use which

| Task type | Recommend |
|---|---|
| Codeable algorithmic task (DP, graph, regex parse) | Either Opus or Gemini, but **prompt them to "rewrite in pure Python"** explicitly |
| Knowledge-heavy task (sports facts, medical formulas) | Opus tends to write better hardcoded knowledge tables; Gemini delegates more |
| Structured-format extraction (penguins table, finqa) | Mixed; needs case-by-case |
| Already-saturated tasks (sports 99%) | Either, no headroom |

The natural follow-up: **prompt Gemini explicitly to prefer pure-Python over
LLM ptool delegation** — likely closes most of the gap on geometric / meeting
/ calendar. Not done yet in this run.
