# Collaboration contract: the PPI evaluation plug-in

This document is the seam between the three people working on this project. It
fixes the *interfaces* we agree on so each of us can plug in different tasks,
platforms, and statistics behind the same code, without stepping on each other.

Read `GLOSSARY.md` for vocabulary and `RESULTS.md` for what the first
(musr_team) experiment found. This file defines the contract; those describe the
science.

## 1. The three lanes

We are building one thing -- a task-agnostic **evaluation plug-in for existing
agent optimizers** -- from three sides:

| lane | owner | responsibility |
|---|---|---|
| estimators / statistics | Joshua | `ppi_estimate` + the rectifier registry; bigger-N, Bayesian PPI, matrix factorization; the N-advisor |
| platforms / tasks | Koushik | wire real agent-optimization platforms (ADAS / AFLOW / DSPy) and their tasks in as data providers; continuous LLM-judge scores (coherence, reliability, truthfulness) |
| pairwise statistics | William | pairwise-comparison estimators for accept/reject decisions between two candidates |

The lanes meet at exactly two interfaces: the **per-case data format** (section 2)
and the **`ppi_estimate` function** (section 3). Everything else is private to a
lane. If a change would alter either interface, it is a group decision.

## 2. The per-case data format (the shared harness)

Every task provider reduces to two aligned tables keyed by a stable `case_id`.

### 2a. Cheap-prediction table (one per task, built once)

The large "unlabeled" pool: cheap predictions `f` plus per-case features, for
*every* case in the scoring pool. Built once, reused for every candidate.

```
cheap_preds_<task>.json
{
  "meta":  { task, model, split, n, base_f_accuracy, ... },
  "cases": {
    "<case_id>": {
      "f_score":   <float>,     # cheap predictor of the expensive metric y
      "f_cost":    <float>,     # cheap predictor of per-case cost (optional)
      "<feature>": <float>,     # any number of numeric per-case features
      ...
    },
    ...
  }
}
```

- `f_score` is the cheap predictor of whatever the expensive metric `y` is. It
  does **not** have to be binary. For a correctness task it is 0/1; for an
  LLM-judge coherence score it is a real number on the judge's scale.
- Historically this field was named `f_correct` (binary-only framing). New
  providers should write `f_score`; the hook accepts either via the
  `optimize.ppi_acc_pred` config key (default tries `f_score` then `f_correct`).
- Features are arbitrary numeric columns. Rectifiers name the ones they use
  (R1 stratifies on one; R2 regresses on a list) via config, so no feature name
  is baked into the estimator or the hook.

### 2b. Expensive-truth table (one per candidate, collected on demand)

The small "labeled" set: the real expensive outcome `y` per case, per candidate
config. In live search this is just the candidate's own run (the rows in its
`results.csv`); in offline A/B analysis we cache it per config:

```
truth_<split>.json
{
  "<config>": {
    "<case_id>": { "y": <float>, "cost": <float>, ... },
    ...
  },
  ...
}
```

- `y` is the expensive per-case metric. **Continuous is allowed** -- it is any
  real number (accuracy 0/1 is the special case). This is the single most
  important thing for Koushik's lane: the same estimator path serves a
  continuous coherence score with no code change, because PPI estimates a *mean*
  and never assumes `y` is binary.
- Alignment is by `case_id` only. The cheap table's `case_id` set must be a
  superset of any candidate's labeled `case_id` set (deterministic case sampling
  guarantees this in the musr provider).

### 2c. Invariants everyone relies on

1. `case_id` is stable across the cheap table and every truth table for a task.
2. `y` and `f_score` are on the *same scale* and mean the *same quantity* (both
   estimate the metric); PPI corrects `f` toward `y`, so a scale mismatch would
   bias nothing (PPI is unbiased regardless) but waste all variance reduction.
3. Missing values are `null`/`NaN` and are dropped pairwise by the estimator;
   they never crash it.

## 3. The single statistical interface

All statistics enter through one function. This is the contract William and
Koushik code against; the internals (which rectifier, how it is tuned) are
Joshua's lane and can change without breaking callers.

```python
from ppi_eval.estimators import ppi_estimate, naive_estimate, corr

result = ppi_estimate(
    y_lab,          # (n,)  expensive metric on the labeled cases   -- continuous ok
    f_lab,          # (n,)  cheap predictor on the same labeled cases
    f_unlab,        # (N,)  cheap predictor on the unlabeled pool
    rectifier="R0", # which rectifier (see section 4)
    x_lab=None,     # (n,) or (n,d) optional features for R1+/R2
    x_unlab=None,   # (N,) or (N,d) aligned features on the pool
    alpha=0.05,     # 1 - confidence level
)
result.estimate            # unbiased point estimate of E[y]
result.ci_lo, result.ci_hi # confidence interval
result.as_tuple()          # (estimate, ci_lo, ci_hi)
```

Guarantees the callers may assume:

- **Unbiased for any `f`.** Predictor quality changes only the CI width, never
  the point estimate's expectation. Safe to plug in a bad cheap predictor.
- **Honest widening.** When `f` stops predicting `y` (decorrelation), the tuned
  weight collapses toward zero and the estimator degrades gracefully to the
  naive labeled mean with its wider CI -- it never manufactures false
  confidence.
- **Degenerate-safe.** Fewer than 2 labeled pairs, zero-variance `y` or `f`, or
  a missing `ppi_py` all fall back to `naive_estimate`; the call returns a valid
  `PPIResult`, never an exception.

## 4. The rectifier registry

A **rectifier** is the functional form of the predictor plugged into PPI. It is
the one place the statistics vary. Registered in `estimators.py::RECTIFIERS`:

| id | name | idea | status |
|---|---|---|---|
| R0 | constant / PPI++ | `h = f`, globally power-tuned (this is `ppi_py`) | done |
| R1 | stratified / StratPPI | recalibrate `f` within feature strata | done |
| R2 | regression | `h = ridge(f, features)`, cross-fit | done |
| R3 | matrix factorization | impute a candidate's hard per-case `y` from other configs' observed cells | planned (Task 5) |
| R4 | Bayesian / discrete-judge | Bayesian PPI variant for autorater scores | planned (Task 6) |

### Adding a rectifier

1. Subclass `Rectifier` in `estimators.py`, implement `estimate(y_lab, f_lab,
   f_unlab, x_lab, x_unlab, alpha) -> PPIResult`.
2. If it *learns* `h` from labeled data, cross-fit the labeled predictions
   (leave-one-out or K-fold) so residuals stay honest and the CI keeps coverage.
   Reuse the shared `_rectified_ppi(...)` engine -- it power-tunes lambda and
   forms the pooled-residual CI for you.
3. Register it in `RECTIFIERS` under its id. It is now selectable everywhere by
   string: the hook (`optimize.ppi_rectifier`), `ab_experiment`, and any caller.

## 5. Adding a new task provider

A task provider supplies the section-2 tables. To add one:

1. **Cheap table.** Produce `cheap_preds_<task>.json` in the section-2a format.
   For a "rollout" task (run a cheap baseline over the pool), add an entry to
   `BENCHMARKS` in `cheap_predictor.py` -- it subprocess-runs the baseline under
   a cheap model and reshapes the results into the cache. For any other source
   (a platform's own logs, an LLM judge), write the JSON directly; the estimator
   path does not care how `f_score` was produced.
2. **Truth table.** Provide the candidate's per-case `y` (its `results.csv` in
   live search, or `truth_<split>.json` for offline A/B via
   `ab_experiment collect`).
3. **Features (optional).** Add any numeric per-case features to the cheap
   table. Point the rectifiers at them by config (`optimize.ppi_feature` for R1,
   a feature list for R2); no feature name is hardcoded in the estimator.
4. **Nothing in `estimators.py` changes.** A new task never touches the
   statistics lane -- that is the whole point of the seam.

## 6. What is intentionally NOT in the contract

- *How* a cheap predictor is produced (rollout, judge, logged) -- provider's
  choice.
- *Which* optimizer consumes the estimate (NSGA-II here; AFLOW/DSPy later) --
  the plug-in exposes `estimate + CI`, `should_accept`, `labels_to_resolve`
  (Task 7); the optimizer decides how to use them.
- *How* pairwise accept/reject decisions are made (William's lane) -- may bypass
  the mean estimator entirely with a paired statistic; it still consumes the
  section-2 tables.
