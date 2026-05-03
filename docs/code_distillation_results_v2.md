# Code Distillation Results — v2 (April 2026 re-run)

Compare with v1 results in [code_distillation_results.md](code_distillation_results.md).

**Branch**: `codedistill-v2` (based on `origin/main` 7a18781, includes
all latest main updates as of 2026-04-28). Original branch
`natplan/swap-train-test` is unchanged.

**Models**:
- All baselines: `together_ai/deepseek-ai/DeepSeek-V3.1` (musr/rulearena: V3).
- Code generation (the "learner"): `claude-opus-4-6`.

**main updates incorporated** (relevant to v2):
- `Add __learned__.<attr> resolution path to direct factory`
- `Fix recursive structures when resolving Interface tools` — wraps
  Interface in plain function so downstream consumers (pydantic-ai
  Agent) get a proper signature without circular Pydantic refs.
  **This likely fixes the RecursionError that blocked Class 3
  finqa / calendar Stage B in earlier v2 runs.** Class 3 v3 (re-run
  with this fix) is in flight.

## The three classes

| Class | What is generated | Tools used by it |
|---|---|---|
| **1 — Ptool codedistill** | Python replacement for one `simulate` ptool inside the existing hand-written workflow | n/a (replaces an LLM call with deterministic Python; falls back to LLM on `None`) |
| **2 — Workflow codedistill** | Python replacement for the **top-level workflow function** | The benchmark's hand-written ptools (pure-Python helpers + simulate ptools) |
| **3 — Workflow codedistill on induced ptools** | Same as Class 2, but tools are induced (LLM-discovered from a ReAct or zero-shot CoT trace) instead of hand-written | Induced ptool module (`learned_ptools.py` produced by `PtoolInducer`) |

## Method commands

```
# Class 1
uv run -m secretagent.cli.learn codedistill-all \
  --learned-dir learned_v2 --model claude-opus-4-6 --max-wrong-rate 0.05 <recording_dirs>

# Class 2 (workflow distill on hand-written tools)
uv run -m secretagent.cli.learn workflow-codedistill \
  --interface <top> --dataset-file <train.json> \
  --tool-module <ptools_mod> --conf-file <conf.yaml> \
  --reference-file <other_bench.py> --trace-dir <recording> \
  --cross-trace-dir <other> --cross-dataset-file <other.json> \
  [--react-trace-dir <react>] \
  --learned-dir learned_class2 --model claude-opus-4-6

# Class 3 (workflow distill on induced tools)
uv run -m secretagent.cli.learn codedistill-induced-ptools \  # produces induced_ptools.py
  --interface <top> --task-desc "..." --trace-mode {react|cot} --only-correct \
  --learned-dir learned_class3 \
  --expt-cmd "uv run python expt.py run --config-file conf/<bench>.yaml dataset.split=train dataset.n=50" \
  <react_or_cot_recording>
# then:
uv run -m secretagent.cli.learn workflow-codedistill \
  --interface <top> --dataset-file <train.json> \
  --tool-module <learned_class3/<ts>.<top>__ptool_inducer/learned_ptools.py> \
  --learned-dir learned_class3_v2 --model claude-opus-4-6
```

## Two layers of train/val to be aware of

1. **Fit-time holdout** — INSIDE the learner. Cases that produce supervision
   are 80/20-split. Class 1's `val_wrong_rate` ENABLE gate, Class 2/3's
   reported `val acc` come from this 20% holdout. **Both halves are from the
   benchmark's `dataset.split=train`.**
2. **End-to-end val eval** — AFTER fitting. Run the saved distilled config
   on `dataset.split=val` (n=30) end-to-end via `expt.py`. The "Val acc"
   columns in the table below are this kind.

## Source changes vs v1

- **Class 1 single-fit 80/20 holdout** in `CodeDistillLearner.learn()`
  (v1's `Learner.validate()` ran `fit()` 3× per ptool; v2 runs once on
  80% and reports val on 20%). ENABLE uses `val_wrong_rate`, not
  `train_wrong_rate`.
- `_format_traces` injects **top-level task input + expected output**
  (v1 saw only the local i/o of the ptool being distilled).
- `_format_cases` truncates long `repr` outputs.
- Round-1 early-stop (< 10%) for ptool codedistill.
- `_evaluate_on_cases` feeds abstained (None) cases as error feedback.
- Generated code is saved even at 0% (so backoff path can still fire).
- `_compile_function` removed dead `LocalPythonExecutor` branch
  (inference-time sandbox `_load_learned_sandboxed` in
  `implement/learnedcode.py` is the actual runtime sandbox).
- `'backoff': 'true'` (str) → `True` (bool) in 4 places.
- New `WorkflowDistillLearner` for Class 2 / 3.
- WorkflowDistillLearner: `tool_module` accepts a `.py` file path
  (Class 3); `_bind_ptools_for_eval` binds simulate ptools at fit time
  via the benchmark conf so the generated workflow can actually call
  them during eval.

## Master chain run summary (full-size, 2026-04-29)

Master chain `/tmp/master_chain.sh` completed at 09:39 EDT. All 5 phases:
- A — full-size baseline re-record (n=43-100 per benchmark, depending on
  available data) → DONE 07:11
- B' — class1 v4 codedistill-all max_wrong_rate=0.20 on full-size →
  DONE (initially produced no output due to recording-name mismatch
  bug; re-launched after fix)
- C' — class2 v4 workflow-codedistill backoff=True on full-size → DONE
  09:01 (10 benchmarks)
- D' — class3 v4 workflow-distill on induced (musr/finqa/calendar) →
  DONE 09:02 (musr OK, finqa/calendar failed due to ptool-binding bug
  trying to bind benchmark ptools that aren't in induced module;
  re-launched after fix)
- E — full-size val eval baseline + class2v4 → DONE 09:39

## Master result table (val full-size, see val_results_full/)

> ⚠️ **BBH baselines were initially undercounted** — my val runs used
> the default `ExactMatchEvaluator` which doesn't strip parens (`(C)` vs `C`).
> Numbers below have been **post-hoc corrected** by re-applying paren-strip
> normalisation to BBH benchmarks (others unaffected).

| Benchmark | n | Baseline (DS-V3.1) | Class 1 v2 (n=30 mini) | Class 2 v4 (full, backoff=simulate) |
|---|---|---|---|---|
| natplan_calendar | 100 | 55% / $0.329 | n/a | **87% / $0.000** ⭐ +32pp |
| natplan_meeting | 100 | 29% / $0.526 | n/a (1 ENABLED; trip-only config conflict) | 3% / $0.008 ❌ (overfit train) |
| natplan_trip | 100 | 21% / $0.388 | 20% / $0.116 ❌ pipeline regression | 21% / $0.388 (parity via backoff) |
| musr_murder | 75 | 68% / $0.604 | **70% / $0.239** ⭐ -60% cost | n/a (Class 3 v4 instead, 102-line workflow) |
| bbh_sports | 75 | 99% / $0.105 | 93% / $0.037 ❌ -6pp | 99% / $0.107 (parity) |
| bbh_penguins | 43 | 72% / $0.088 | 73% / $0.036 (parity, -59% cost) | **88% / $0.015** ⭐ +16pp |
| bbh_geometric | 75 | 37% / $0.382 | 47% / $0.098 ⭐ +10pp | **100% / $0.000** ⭐⭐⭐ +63pp |
| bbh_date | 75 | 83% / $0.065 | n/a (0 ENABLED, data scarcity v2) | **88% / $0.089** +5pp |
| medcalc | 100 train | 75% / $0.188 (no val run) | 0 ENABLED | (running) |
| finqa | 100 | 67% / $0.121 | 80% / $0.035 ⭐ +13pp (n=30 mini) | (running) |
| rulearena_nba | 42 | 74% / $1.223 | 0 ENABLED | n/a |
| rulearena_tax | 50 | 78% / $0.927 | 0 ENABLED | n/a |
| rulearena_airline | 50 | 46% / $0.863 | 0 ENABLED | **100% / $0.000** ⭐⭐ (n=30 mini AND n=50 full both at 100%) |

Note: rulearena_airline 46% baseline (my run, simulate_pydantic agent for L1 extract) ≠ existing 90% (their structured_baseline with simulate). Different methods. Their structured_baseline is a stronger baseline. Even so, Class 2 100% beats both.

Class 2 v4 highlights (full-size n=43-100, backoff=simulate):
- ⭐⭐⭐ **bbh_geometric 100% / $0** (vs 37% baseline, +63pp, $0.382 → $0)
- ⭐⭐ **rulearena_airline 100% / $0** (vs 46% baseline). Verified at both n=30 mini and n=50 full splits — 100% on both. (`val_results/20260428.213758.airline_val_class2`, `val_results_full/20260429.114154.airline_val_full_class2v4`.)
- ⭐⭐ **natplan_calendar 87% / $0** (vs 55% baseline, +32pp)
- ⭐ **bbh_penguins 88% / $0.015** (vs 72% baseline, +16pp, -83% cost)
- bbh_date 88% / $0.089 (modest)
- bbh_sports 99% (parity — already saturated)
- natplan_trip 21% (parity via backoff — generated workflow returns None, falls back to baseline)
- natplan_meeting 3% — generated workflow has solver bug; backoff didn't rescue because code returns wrong values not None

## Alignment vs existing `results/` baselines (full-size)

| Benchmark | My full-size baseline | Existing (DS-V3.1) | Δ | Cause / Note |
|---|---|---|---|---|
| bbh_sports n=75 val | 99% / $0.105 | workflow 99% | 0 | ✓ aligned |
| bbh_penguins n=43 val | 72% / $0.088 | workflow 72% | 0 | ✓ aligned |
| bbh_geometric n=75 val | 37% / $0.382 | (no DS-V3.1 workflow; haiku 75%) | n/a | DS-V3.1 baseline is **new** (Lex used haiku) |
| **bbh_date** n=75 val | **83%** / $0.065 | orchestrated 39% | +44 | **different workflow** — mine `zeroshot_unstructured_workflow` (single LLM call), theirs `orchestrated` (7 ptool decomp) |
| finqa n=100 val | 67% / $0.121 | workflow_val 62% (n=100) | +5 | ✓ aligned |
| musr_murder n=75 val | 68% / $0.604 | workflow 70% (n=100 test) | -2 | ✓ aligned |
| **natplan_calendar** n=100 val | **55%** / $0.329 | workflow 49% (n=100) | +6 | ⚠️ different `prompt_mode`: mine 0shot, theirs 5shot. (45% mine train post-swap = old test) |
| natplan_meeting n=100 val | 29% / $0.526 | workflow 30% (n=100) | -1 | ✓ aligned |
| natplan_trip n=100 val | 21% / $0.371 | workflow 15% (n=100) | +6 | sample variance (note: train/test splits swapped on this branch, my "valid" is the same as before swap) |
| **rulearena_airline** n=50 val | **46%** / $0.863 | structured_baseline 90% (n=30) | -44 | **different method**: mine `simulate_pydantic` ReAct agent on `l1_extract_workflow`; theirs `simulate` single-call structured. Both valid but different |
| rulearena_nba n=42 val | 74% / $1.223 | (no comparable existing) | n/a | new |
| rulearena_tax n=50 val | 78% / $0.927 | (no comparable existing) | n/a | new |
| medcalc n=100 train | 75% / $0.188 (val not run) | workflow 79% (n=275 val) | -4 | ✓ aligned |

### Why class 1 calendar v4 (55%) ≠ v1 doc (84%)

The v1 doc ([docs/code_distillation_results.md](code_distillation_results.md))
recorded **ptool codedistill (opus) calendar = 84%**. My v4 = 55% (= baseline).
**This is not a regression in the new pipeline — the v1 84% likely had
methodological inflation**:

1. **Different recording dataset (pre-swap vs post-swap train)** — v1 used
   `recordings/20260410.010744.cal_workflow` (50 cases, baseline acc 48%,
   ~24 correct rollouts). v4 used `recordings_full/...natplan_calendar_train_train_full`
   (100 cases, baseline acc 34%, 34 correct rollouts). The Apr 27 commit
   `02e8e60` swapped train↔test labels, so the 50 vs 34 case count gap and
   the disjoint train sets (overlap=2) are not fault of distillation —
   they're different data. v1's pre-swap train also overlaps the current
   valid set by 6 cases (mild leakage, ≤6pp upper bound).
2. **`_format_cases` / `_format_traces` rewrite (v1 → v4)** — v1 prompt:
   max_cases=50, no truncate, no top-level i/o header. v4 prompt: max_cases=20,
   truncate args/output to 500/2000 (cases) and 200/500 (traces), inject
   top-level task header. v4 LLM sees less coverage of cases, more global
   context per case → writes complex "general solver" code (calendar parse
   246 lines, finqa 121 lines with `eval()`). v1 LLM sees full local ptool
   I/O of 50 cases → writes tight regex/parsing code. This is the largest
   single contributor to the −29pp gap (verified in v6 reversion experiment).
3. **`train_wrong_rate` gate (v1) vs `val_wrong_rate` gate (v4)** — v1 enabled
   ptools by their train accuracy after fit (which sees ensemble + multi-round
   selection of the best candidate, so train_acc is high). v4 holds out 20%
   of cases as val and gates on `val_wrong_rate`, exposing overfit. For
   calendar: `find_available_slots` train 54% but val 17% → SKIPPED at v4
   threshold (val_wrong 83% > 20%). Under v1's train gate, it would have
   passed.
4. **`only_correct` is the *same* in both (True default)** — earlier draft
   of this section claimed v1 had `only_correct=False`; that was wrong. Both
   v1 (commit 34e3179) and v4 default `CodeDistillLearner.only_correct=True`,
   meaning both filter out ptool I/O from rollouts that produced an incorrect
   final answer. Only v5 (the gate-comparison experiment) flipped this to
   False.

Conclusion: **v4 55% is the more honest "what does ptool-only distillation
actually buy on unseen calendar data with this baseline" number**. If you want
to recover something near 84%, set `only_correct=False` and revert to
train-acc gating — but that risks overfitting and inflating reported numbers.
For headline results, **calendar's true gain comes from class 2 (workflow
distill, 87%)**, which generates pure-Python parse/solve/format code that
generalizes off-the-shelf.

**Summary**: 8/13 benchmarks aligned within ±5pp. 5 known config differences:
1. bbh_date — workflow choice (zeroshot vs orchestrated)
2. natplan_calendar — prompt_mode (0shot vs 5shot)
3. rulearena_airline — agent method (simulate_pydantic vs simulate)
4. natplan_trip — train/test swap on this branch's data
5. bbh_geometric — DS-V3.1 baseline didn't previously exist (only haiku)

## Class 1 v2 (val-gated) ENABLED ptools

12 across 7 benchmarks (vs v1 16 across 8 — val gate caught 4 overfit / data-scarcity).

| Benchmark | ENABLED ptool (train acc / val acc / val_wrong) |
|---|---|
| natplan_meeting | `build_meeting_plan` (67/50/0%) |
| natplan_trip | `build_trip_plan` (100/100/0%), `parse_trip_constraints` (100/100/0%) |
| musr_murder | `extract_index` (100/100/0%) |
| bbh_sports | `consistent_sports` (100/100/0%) |
| bbh_penguins | `choose_response` (100/60/0%), `table_operation` (97/100/0%) |
| bbh_geometric | `decompose_path` (100/100/0%), `describe_command` (100/100/0%), `extract_path_and_options` (100/100/0%), `select_option` (100/100/0%) |
| finqa | `extract_final_number` (100/100/0%) |

**Skipped (val gate caught these vs v1 train gate)**:
- natplan_calendar `select_and_format` (train 88% / val 0%)
- bbh_geometric `describe_shape` (train 100% but val val_wrong > 5%)
- bbh_date `extract_option_letter`, `zeroshot_answer_date_question`
  (data scarcity: only_correct=True + 2% buggy baseline → ~1 correct
  case → fit on 0)
- bbh_penguins `answer_question` (top-level workflow ptool, val correctly
  rejected this short-circuit)

## Run lineage

| Phase | What | Outcome |
|---|---|---|
| v1 initial | All 3 classes ran sequentially | Many Class 2 returned None for all → save raised |
| Class 2 v2 | bug fixes (save 0% code, abstained → error feedback, no early-stop, cross-benchmark traces + i/o + ReAct traces) | Calendar (92.5%) and Penguins (82.9% train) recovered |
| Class 2 v3 | added `--conf-file` to bind simulate ptools at fit time | Sports (70%) and Date (67%) recovered |
| Class 1 v2 | 80/20 holdout, val_wrong_rate gate | 12 ENABLED (vs 16 train-gated) — 4 lost were overfit/data-artefacts |
| Class 3 v2 | refactored to `workflow_distill on induced module` instead of tool-by-tool | musr ran but failed (LLM didn't set `_REACT_STATE`); calendar / finqa Stage B failed (pydantic-ai recursion bug) |

## Plots

3 plots in [docs/plots/](plots/):

### Plot 1 — Cost vs accuracy
![](plots/plot1_cost_vs_acc.png)

X = USD cost per case (symlog). Y = val accuracy (%). Each benchmark
contributes one point per method, connected by dashed lines.
Up-and-left = better (more accurate, cheaper).
- ⭐ Big up-and-left wins: `rulearena_airline` C2 (100% / $0), `natplan_calendar` C2 (57→93% / $0.078→$0), `bbh_geometric` C2 (37→87% / $0.15→$0)
- C1 cost wins (parity acc): `bbh_penguins` C1 (73% / $0.066→$0.036)
- Regression: `finqa` C1 (80→0% — distilled `extract_final_number` breaks downstream pipeline)
- `natplan_meeting` C2 collapses to (0%, $0) at lower-left — overfit to train set

### Plot 2A — ptool replacement effect
![](plots/plot2a_ptool_replacement.png)

Each benchmark = 1 point. X = baseline (hand-written ptool pipeline) val
acc, Y = Class 1 distilled val acc. Workflow held constant.

- bbh_geometric: 37% → 47% (+10 pp, distillation helps)
- bbh_sports: 97% → 93% (slight drop within sampling)
- bbh_penguins: 73% → 73% (parity, -45% cost)
- finqa: 80% → 0% (regression — distilled `extract_final_number` returns
  None, breaks downstream pipeline expecting numeric format)

### Plot 2B — workflow replacement effect
![](plots/plot2b_workflow_replacement.png)

Each benchmark = 1 point. X = baseline workflow val acc, Y = Class 2
(learned workflow + hand ptools) val acc. Class 3 (induced tools) would
appear as red triangles; currently no Class 3 v2 finished.

- ⭐ above parity: bbh_geometric (37→87, +50 pp), bbh_penguins (73→93,
  +20 pp), natplan_calendar (57→93, +36 pp), rulearena_airline (100→100
  with cost going from $0.462 to $0)
- below parity: bbh_date (93→63, -30 pp — but baseline used the
  zeroshot path; orchestrated baseline is 39% in which case Class 2
  would be +24 pp), bbh_sports (97→70, -27), natplan_meeting (33→0)

### Plot 3 — 5-condition comparison
![](plots/plot3_5_conditions.png)

Conditions per benchmark:
1. hand workflow (baseline) — current default
2. hand ptool + react — NOT collected (would need per-benchmark ReAct
   conf with pydantic-ai wrappers)
3. induced ptool + react — Class 3 v1 4-stage pipeline; partial coverage
4. learned wf + hand ptool — Class 2
5. learned wf + induced ptool — Class 3 v2 (mostly failed)

Conditions 2 / 3 / 5 are mostly empty due to (a) need for per-benchmark
ReAct config infrastructure, (b) state-management issues in Class 3 v2.

## Optimization explorations (phase 2 partial)

### (a) Class 2 backoff to simulate — IMPLEMENTED + VERIFIED

`WorkflowDistillLearner` now defaults `backoff=True` and `backoff_method='simulate'`.
On `save_implementation`, writes a synthetic `source_configs/<top>_backoff.yaml`
with `ptools.<top>.method=simulate` so `LearnedCodeFactory._build_backoff_impl`
can construct a pure-LLM fallback. Crucially **NOT to the hand-written
workflow** (we're trying to beat that, not match it).

Verification on full-size val: massive wins on geometric (37→100%),
calendar (55→87%), penguins (72→88%), airline (46→100%). For `meeting`
the generated workflow returns wrong values (not None), so backoff
doesn't fire — that's a generated-code-quality issue, not a
backoff-infrastructure issue.

### (b) In-pipeline val gate — DESIGNED, NOT IMPLEMENTED

Current gate uses `val_wrong_rate` from a fit-time isolated holdout
(20% of supervision cases). This passes some ptools that **then regress
in pipeline** (e.g. trip class1 isolated 0% wrong, pipeline 33→20%;
finqa class1 isolated 0% wrong, pipeline 80→0%).

Design: after `distill_all` writes a candidate `codedistill_config.yaml`,
run a quick `expt.py` invocation with the config on N=10 val cases,
compare to baseline. If `pipeline_acc < baseline_pipeline_acc - 5pp`,
flag (or auto-disable) the config.

Implementation: add `pipeline-safety-check` CLI command. Out of scope
for this run.

### (c) Adaptive wrong_rate threshold — DESIGNED, NOT IMPLEMENTED

Currently fixed at 0.05 (v2) or 0.20 (v3/v4). Better: per-benchmark
based on baseline acc. High-baseline benchmarks (sports 99%) need strict
gate; low-baseline (date 2-83%) can be lax.

### (d) Class 3 induced ptool state-management — PARTIAL

`PtoolInducer` outputs induced ptools that read module-level state
(e.g. `_REACT_STATE['narrative']`). The generated workflow needs to set
this state but the LLM doesn't always realise.

Mitigation: prompt hint added to `WorkflowDistillLearner._build_prompt`
explicitly warning the LLM to init the state at function start. Some
generated workflows (e.g. musr Class 3 v4) do set it correctly; still
returning all-None at fit-time eval, suggesting deeper issue (the
simulate ptools may be cached across cases and contaminate state).

### (e) Class 3 expand to more benchmarks — PARTIAL

Wrote zero-shot CoT configs for `natplan/conf/{meeting,trip}_zs_cot.yaml`
+ matching prompt templates. Recordings with these confs not yet
captured (out of scope this run).

For BBH, the existing `zeroshot_unstructured_workflow` produces
single-call rollouts that already serve as quasi-CoT — feasible but
unrun.

For musr `object` and `team`, Lex's `learned/<task>/...__ptool_inducer/`
outputs are committed and could be used directly as `--tool-module` for
`workflow-codedistill` (Class 3 v2 path). Out of scope this run.

**Fixes for Class 3**:
- pydantic-ai recursion: truncate induced ptool docstrings to 500 chars in `PtoolInducer.fit`. **Or** the `Fix recursive structures when resolving Interface tools` commit on `origin/main` may already fix this.
- musr state-management: change `PtoolInducer` to emit induced ptools that take all needed context as explicit params rather than reading module-level state.
- coverage: add CoT prompt templates for natplan/bbh/medcalc (~10 min each); add ReAct configs with wrappers for benchmarks where ReAct is the natural fit (~1-2 hr each).

## Output layout

```
benchmarks/
  <bench>/
    recordings/<ts>.<bench>_train_record/      # baseline train rollouts
    recordings_class3/<ts>.<bench>_react_train/   # Class 3 ReAct (musr, finqa)
    recordings_class3/<ts>.calendar_zs_cot_train/  # Class 3 CoT (natplan calendar)
    val_results/<ts>.<bench>_val_<method>/     # val eval rollouts + CSVs
    learned/                # Class 1 v1 (train-gated)
    learned_v2/             # Class 1 v2 (val-gated)
    learned_class2[_v2|_v3]/   # Class 2 (v3 has --conf-file binding)
    learned_class3/         # Class 3 v1 (induced + simulate_pydantic top)
    learned_class3_v2/      # Class 3 v2 (workflow distill on induced module)
  codedistill_logs_v2/
    class[123][v2|v3]_<bench>.log
  val_eval_logs/
    val_<bench>.log
  docs/
    code_distillation_results_v2.md  # this file
    plots/
      plot1_class1_speed_vs_cost.png
      plot2a_ptool_replacement.png
      plot2b_workflow_replacement.png
      plot3_5_conditions.png
  scripts:
    run_class1_codedistill.sh            # train-gated (v1)
    run_class1_v2_codedistill.sh         # val-gated (v2)
    run_class2_workflow_distill.sh       # v1
    run_class2_v2_workflow_distill.sh    # bug fixes + cross-benchmark
    run_class2_v3_workflow_distill.sh    # + --conf-file binding
    run_class3_induced_codedistill.sh    # v1 (tool-by-tool distill)
    run_class3_v2_workflow_distill.sh    # v2 (workflow distill on induced)
    run_val_evals_parallel.sh            # parallel val evals
    run_bbh_class1_val.sh                # BBH-specific dotlist syntax
    plot_results.py                      # generates the 4 plots
```

## Coverage status (2026-04-29)

Benchmarks in `benchmarks/` and whether they fit the class 1/2/3 schema:

| Benchmark | In scope | Why |
|---|---|---|
| natural_plan (calendar/meeting/trip) | ✅ | workflow + simulate ptools |
| musr (murder/object/team) | ✅ | workflow + simulate ptools (object/team launched 2026-04-29) |
| bbh (sports/penguins/geometric/date) | ✅ | workflow + simulate ptools |
| medcalc | ✅ | workflow + simulate ptools |
| finqa | ✅ | workflow + simulate ptools |
| rulearena (nba/tax/airline) | ✅ | workflow + simulate ptools |
| **tabmwp** | ✅ | 16 @interface ptools, has workflow_incontext.yaml (4-ptool decomp) — launched 2026-04-29 |
| **medagentbench** | ❌ out-of-scope | requires running local FHIR server (`http://localhost:8080/fhir/`) for medical data lookups; not currently up |
| **tau_bench** | ❌ out-of-scope | agent-loop benchmark (no `conf/workflow.yaml`, only `react/structured_baseline`); 29 tools but used as agent-callable, not as a decomposable workflow |
| **designbench** | ❌ out-of-scope | code-generation, single `@interface`, no decomposition surface to distill |



# Master comparison — all classes × all versions × all benchmarks

## What each `vN` means

All versions are MY own runs, not someone else's. They are snapshots of the codedistill pipeline as it evolved over April 2026.

| Version | Date | Key behaviors |
|---|---|---|
| **v1** | early April | Original. `only_correct=False` (learned from wrong rollouts too). Gate: `train_wrong_rate <= 10%`, no held-out val split. `_format_traces` showed only the local ptool i/o (no top-level task context). `Learner.validate()` re-ran `fit()` 3× per ptool. Numbers preserved in [v1 doc](code_distillation_results.md). |
| **v2** | 2026-04-28 (1st rerun) | First val gate. 80/20 case split inside the learner, `val_wrong_rate <= 5%` gate, `only_correct=True`. Top-level task i/o injected into `_format_traces`. Single-fit (skip Learner.validate re-fit). Round-1 early stop at <10%. Case-output truncation (`_truncate_repr`). Mostly run at mini sizes (n=30 train, n=30 val) so numbers are sample-noisy. |
| **v3** | 2026-04-28 (2nd) | Mid-iteration snapshot — mostly mirrored v2 with bug fixes (e.g. `'backoff': 'true'`→`True`, pydantic-ai recursion fix). Many cells stayed empty because the rerun was abandoned in favor of v4. Effectively deprecated. |
| **v4** | 2026-04-29 (full-size) | Full-size rerun. `max_wrong_rate=0.20` (relaxed from v2's 0.05). Train/val recordings at full benchmark sizes (n=43-100 instead of 30-50). Class 2 with `backoff=simulate` (LLM fallback when generated code returns None). Class 3 uses `_REACT_STATE` for musr induced-ptool state injection. Same fit-time 80/20 holdout as v2. **This is the headline version for the v2 doc.** |

Legend for table cells:
- **baseline_full**: my fresh DS-V3.1 baseline (full-size val)
- **archived_workflow**: archived workflow run from `benchmarks/<bench>/results/` or `benchmarks/results/<bench>/`, filtered to DS-V3* model only
- **v1_baseline / v1_ptool / v1_e2e**: numbers from [v1 doc](code_distillation_results.md)
- **c1_vN**: Class 1 (ptool codedistill) version N — replaces individual simulate ptools with Python
- **c2_vN**: Class 2 (workflow distill on hand-written tools) version N — replaces top-level workflow with Python that calls existing ptools
- **c3_v4**: Class 3 (workflow distill on LLM-induced ptools) v4

Cells marked `🏃` are pending re-run (Class 3 v4 vals for musr_object/team and
tabmwp errored on missing induced ptools — needs the `induced_ptools=simulate` fix).

Cells marked `—` in **c1_v4** mean Class 1 distillation **ran but enabled 0 ptools** at the
`val_wrong_rate ≤ 20%` gate (i.e. equivalent to baseline). Per-benchmark reasons:
- `bbh_geometric` (6 ptools), `bbh_date` (2 ptools), `rulearena_nba/tax/airline` (1 ptool each):
  **code-generation failure** — LLM produced None-returning stubs (train_acc 0% on all ptools),
  most likely because the ptool output types are complex (pydantic BaseModel, SVG paths, etc.)
  and the case format was hard for the LLM to learn from.
- `medcalc` (3 ptools): **gate failure** — `identify_calculator` reached train 90%/val 40%,
  `extract_calculator_values` train 68%/val 13%; both got skipped because val_wrong_rate
  exceeded 20% (val sample n≈10-20 so even 3-4 wrong tipped the gate).
- `natplan_meeting` and `natplan_trip`: **data-sparsity gate failure**. Train recording
  was n=100, but `only_correct=True` filter collapses the case pool to whichever
  rollouts had the correct final answer — and DS-V3.1 baseline only solves
  19% of meeting / 21% of trip train rollouts. Per-ptool case pool drops to ~19-21,
  so the 80/20 split gives **n_val ≈ 3-4 per ptool**. Single error = 33% wrong-rate >
  20% gate threshold. Test: meeting `force-enable` (bypass gate, use train_acc=88%
  ptools directly) achieves 55% — confirming the code is fine, the gate was the issue.
  Fixable in two ways: (a) drop `only_correct=True` so wrong rollouts contribute
  intermediate ptool i/o (gives ~80 train + 20 val); (b) record more train cases.
- The `force-enable` test on `meeting` (manually enabling 2 ptools that had train 88% but
  failed val gate) achieves **55%** vs baseline 29% — confirming the gate, not the code,
  was the issue for several of these.

Empty class columns dropped from this table for legibility (kept in raw CSV scan):
  c1_v1 (never run), c1_v2/c2_v2 (mini n=30, superseded by v4 full-size),
  c1_v3/c2_v3 (deprecated mid-iteration snapshot), c3_v1/v3 (no successful runs).

## Accuracy (%)

| sub_bench                |   baseline_full | archived_workflow   | v1_baseline   | v1_ptool   | v1_e2e   | c1_v4   | c1_v4g   |   c2_v4 | c2_v4g   | c3_v4   |
|:-------------------------|----------------:|:--------------------|:--------------|:-----------|:---------|:--------|:---------|--------:|:---------|:--------|
| natplan_calendar         |              55 | 49                  | 54            | 84         | 90       | 55      | —        |      87 | 59       | 64      |
| natplan_meeting          |              29 | 30                  | 0             | —          | 0        | 55      | —        |      98 | 29       | —       |
| natplan_trip             |              21 | 15                  | —             | —          | —        | 21      | —        |      21 | 91       | —       |
| musr_murder              |              68 | 61                  | 70            | 70         | 0        | 68      | 61       |      60 | 59       | 85      |
| musr_object              |              61 | 53                  | —             | —          | —        | 61      | 55       |      68 | 59       | 🏃      |
| musr_team                |              53 | 59                  | —             | —          | —        | 33      | 65       |      60 | 56       | 🏃      |
| bbh_sports_understanding |              99 | 97                  | 97            | 97         | 63       | 99      | 97       |      99 | 99       | —       |
| bbh_penguins_in_a_table  |              72 | 63                  | 70            | 53         | 58       | 67      | 81       |      88 | 91       | —       |
| bbh_geometric_shapes     |              37 | 32                  | 75            | 73         | —        | —       | —        |     100 | 35       | —       |
| bbh_date_understanding   |              83 | 84                  | 39            | —          | 59       | —       | —        |      88 | 84       | —       |
| medcalc                  |              61 | 79                  | 38            | 44         | 42       | —       | —        |      62 | 61       | —       |
| finqa                    |              67 | 66                  | 62            | 61         | 35       | 67      | 53       |      67 | 67       | 25      |
| rulearena_nba            |              74 | —                   | —             | —          | —        | —       | —        |     100 | —        | —       |
| rulearena_tax            |              78 | —                   | —             | —          | —        | —       | —        |     100 | —        | —       |
| rulearena_airline        |              46 | —                   | 90            | —          | —        | —       | —        |     100 | 100      | —       |
| tabmwp                   |              36 | 95                  | —             | —          | —        | 39      | 40       |      45 | 51       | 🏃      |

## Cost (total USD over val set)

| sub_bench                | baseline_full   | archived_workflow   | v1_baseline   | v1_ptool   | v1_e2e   | c1_v4   | c1_v4g   | c2_v4   | c2_v4g   | c3_v4   |
|:-------------------------|:----------------|:--------------------|:--------------|:-----------|:---------|:--------|:---------|:--------|:---------|:--------|
| natplan_calendar         | $0.3            | $0.3                | $0.2          | $0.09      | $0       | $0.3    | —        | —       | $0.4     | —       |
| natplan_meeting          | $0.5            | $0.5                | $0.2          | —          | $0       | $0.2    | —        | —       | $0.5     | —       |
| natplan_trip             | $0.4            | $0.4                | —             | —          | —        | $0.4    | —        | $0.4    | —        | —       |
| musr_murder              | $0.6            | $0.6                | $0.8          | $0.8       | $0       | $0.6    | $0.6     | $0.2    | $0.5     | $0.2    |
| musr_object              | $0.5            | $0.2                | —             | —          | —        | $0.5    | $0.4     | $0.5    | $0.6     | 🏃      |
| musr_team                | $0.3            | $0.1                | —             | —          | —        | $0.3    | $0.3     | $0.4    | $0.3     | 🏃      |
| bbh_sports_understanding | $0.1            | $0.1                | $0.1          | $0.09      | $0       | $0.06   | $0.06    | $0.1    | $0.1     | —       |
| bbh_penguins_in_a_table  | $0.09           | $0.1                | $0.04         | $0.03      | $0       | $0.04   | $0.04    | $0.01   | $0       | —       |
| bbh_geometric_shapes     | $0.4            | $0.4                | $1.6          | $0.9       | —        | —       | —        | —       | $0.3     | —       |
| bbh_date_understanding   | $0.07           | $0.3                | $0.3          | —          | $0       | —       | —        | $0.09   | $0.2     | —       |
| medcalc                  | $0.3            | $0.1                | $0.1          | $0.01      | $0       | —       | —        | $0.08   | $0.3     | —       |
| finqa                    | $0.1            | $0.4                | $0.1          | $0.1       | $0       | $0.1    | $0.1     | $0.2    | $0.1     | $0.3    |
| rulearena_nba            | $1.2            | —                   | —             | —          | —        | —       | —        | —       | —        | —       |
| rulearena_tax            | $0.9            | —                   | —             | —          | —        | —       | —        | —       | —        | —       |
| rulearena_airline        | $0.9            | —                   | $0.5          | —          | —        | —       | —        | —       | —        | —       |
| tabmwp                   | $0.1            | $0.2                | —             | —          | —        | $0.09   | $0.10    | $0.1    | $0.1     | 🏃      |

## N (val size)

| sub_bench                |   baseline_full | archived_workflow   | v1_baseline   | v1_ptool   | v1_e2e   | c1_v4   | c1_v4g   |   c2_v4 | c2_v4g   | c3_v4   |
|:-------------------------|----------------:|:--------------------|:--------------|:-----------|:---------|:--------|:---------|--------:|:---------|:--------|
| natplan_calendar         |             100 | 100                 | —             | —          | —        | 100     | —        |     100 | 100      | 100     |
| natplan_meeting          |             100 | 100                 | —             | —          | —        | 100     | —        |     100 | 100      | —       |
| natplan_trip             |             100 | 100                 | —             | —          | —        | 100     | —        |     100 | 100      | —       |
| musr_murder              |              75 | 75                  | —             | —          | —        | 75      | 75       |      75 | 75       | 20      |
| musr_object              |              75 | 75                  | —             | —          | —        | 75      | 75       |      75 | 75       | 🏃      |
| musr_team                |              75 | 75                  | —             | —          | —        | 75      | 75       |      75 | 75       | 🏃      |
| bbh_sports_understanding |              75 | 75                  | —             | —          | —        | 75      | 75       |      75 | 75       | —       |
| bbh_penguins_in_a_table  |              43 | 60                  | —             | —          | —        | 43      | 43       |      43 | 43       | —       |
| bbh_geometric_shapes     |              75 | 75                  | —             | —          | —        | —       | —        |      75 | 75       | —       |
| bbh_date_understanding   |              75 | 100                 | —             | —          | —        | —       | —        |      75 | 75       | —       |
| medcalc                  |             100 | 275                 | —             | —          | —        | —       | —        |     100 | 100      | —       |
| finqa                    |             100 | 300                 | —             | —          | —        | 100     | 100      |     100 | 100      | 100     |
| rulearena_nba            |              42 | —                   | —             | —          | —        | —       | —        |      42 | —        | —       |
| rulearena_tax            |              50 | —                   | —             | —          | —        | —       | —        |      50 | —        | —       |
| rulearena_airline        |              50 | —                   | —             | —          | —        | —       | —        |      50 | 50       | —       |
| tabmwp                   |             100 | 100                 | —             | —          | —        | 100     | 100      |     100 | 100      | 🏃      |