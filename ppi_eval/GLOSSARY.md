# Glossary — PPI-in-optimizer project

Shared vocabulary for discussions with Prof Cohen and Koushik. Grouped by area.
"Our usage" notes flag how a term is used specifically in this project.

## A. Prediction-Powered Inference (PPI) and statistics

- **Estimand (theta, θ)** — the population quantity you want to know. Here:
  E[Y] = a workflow's true accuracy (or true cost) over the whole case
  distribution. You never see it directly; you estimate it from a sample.
- **Labeled set (n)** — the cases where you paid to get the expensive true
  outcome Y (e.g. n=25 real workflow rollouts).
- **Unlabeled set (N)** — the (large) set of cases where you only have the cheap
  prediction f, not the true Y (e.g. N=125 or 150).
- **Cheap predictor (f)** — a cheap, noisy guess at Y available on every case.
  Our f = correctness of the BASELINE workflow run under a cheap model
  (flash-lite). See **autorater** for the alternative form.
- **Autorater / LLM-as-judge** — a cheap model that *rates* an output's quality/
  correctness, used as f. Classic in PPI-for-LLM-eval. We are NOT using one yet;
  our f is a cheap *rollout*, and grading is exact-match against gold labels.
  An autorater becomes mandatory on free-form tasks with no gold label (then the
  judge produces both the cheap f and is corrected toward expensive human/strong
  labels). Natural input to **Bayesian PPI** (R4).
- **Prediction-Powered Inference (PPI)** — estimate theta by averaging the cheap
  f over the large unlabeled set, then correcting that average using the measured
  gap (Y - f) on the small labeled set. Unbiased for any f; lower variance when
  f correlates with Y. (Angelopoulos et al., 2023.)
- **PPI++ / power tuning (lambda, λ)** — the tuned version: theta = mean_L(Y) +
  λ·(mean_U(f) - mean_L(f)). λ∈[0,1] is a "trust dial" set to λ* =
  Cov(Y,f)/(Var(f)(1+n/N)). λ→0 recovers naive (ignore f); λ→1 is full PPI.
  This is what we use (via `ppi_py`).
- **Rectifier** — our name for the *functional form of the predictor* h plugged
  into PPI. R0: h=f (constant/PPI++). R1: piecewise/stratified recalibration
  (**StratPPI**). R2: regression on features. R3: matrix factorization across
  configs. R4: Bayesian/discrete-judge. Prof's "vary the rectifier" ask.
- **Control variate** — the classical-statistics ancestor of PPI: subtract a
  correlated, known-mean quantity to cut variance. PPI is a control variate where
  the control's mean is estimated from unlabeled data. Useful framing for Prof.
- **Unbiased** — the estimator's average equals the truth. PPI is unbiased for
  ANY predictor; predictor quality affects only variance, never bias.
- **Variance reduction** — the point of PPI. With correlation ρ=corr(f,Y) and
  N>>n, PPI variance ≈ naive·(1-ρ²), so the **CI width shrinks by √(1-ρ²)**.
- **Confidence interval (CI)** — a range that should contain theta with stated
  probability (95%). Two properties:
  - **Coverage** — how often the CI actually contains the truth across repeats.
    0.95 = honest; <0.95 = overconfident (too narrow); >0.95 = conservative.
  - **Width** — how precise the estimate is. Narrower = more informative. The
    game: narrower than naive *without* coverage dropping below 0.95.
- **Bias** — average(estimate) - truth. Want ≈ 0.
- **Standard error (SE)** — the standard deviation of an estimator; CI width ≈
  2·z·SE. Naive accuracy SE on n cases ≈ √(p(1-p)/n) (~0.10 at n=25).
- **Correlation (ρ, corr(f,Y))** — how well the cheap predictor tracks the truth
  for a given candidate. Drives λ* and √(1-ρ²). The central quantity in our
  decorrelation story.
- **Cross-fitting / sample splitting** — when the rectifier h is *learned* from
  labeled data, predict each labeled point from the *other* points (out-of-fold)
  so residuals aren't optimistically small. Needed to keep R1/R2/R3 CIs
  calibrated. We use leave-one-out / K-fold.
- **StratPPI** — stratified PPI: partition cases into strata and apply PPI within
  each; variance reduction when strata are informative. (arXiv 2406.04291.) = R1.
- **Bayesian PPI** — Bayesian treatment of PPI, incl. a discrete-judge variant
  for autorater scores. (arXiv 2405.06034.) = R4 (stretch).
- **PEMC (Prediction-Enhanced Monte Carlo)** — use cheap parallel *simulations*
  of a system as features/predictors. Our cheap baseline rollout is a PEMC-style
  f. (arXiv 2412.11257.)

## B. Optimization and selection

- **Generalization gap (valid→test)** — difference between performance measured
  during search (valid) and true held-out (test). The core problem.
- **Winner's curse / selection bias** — selecting the max over noisy estimates
  biases the winner's estimate upward, even if each estimate is individually
  unbiased. Worse with more noise and more candidates. Our "valid→test gap"
  metric measures it.
- **Rank inversion** — the config that ranks best on valid is genuinely not best
  on test (a stronger failure than winner's curse). Documented in the prior
  DeepSeek musr_team sweep (pot best valid, wf_orch best test); did NOT reproduce
  under gemini in our run.
- **Hill climbing / greedy step** — an optimizer move that accepts a change if it
  improves the measured metric. An **incorrect step** accepts a change that
  actually hurts (or rejects one that helps) because the measurement was noisy.
  Prof's main RQ targets the *rate* of incorrect steps.
- **Incremental / iterative workflow optimization** — methods that build or
  improve an agentic workflow step by step, each step judged on a small eval set
  (e.g. AFlow, orchestrator, DSPy optimizers, self-improvement loops).
- **AFlow** — automated agentic-workflow generation via Monte-Carlo Tree Search
  over code-represented workflows, scored on a validation set. (arXiv 2410.10762.)
  A canonical "incremental optimizer on small evals" to study.
- **Orchestrator / orch_learner** — our learner that synthesizes an orchestration
  ("seed") workflow; the `wf_orch` config comes from it. An incremental method.
- **NSGA-II** — a multi-objective evolutionary algorithm; maintains a population,
  uses non-dominated sorting + crowding distance to evolve a Pareto front.
- **Pareto frontier / dominance** — config A dominates B if A is ≥ on every
  objective and > on one. The frontier = the non-dominated set. Our objectives:
  accuracy (max) and cost-per-question (min).
- **Hypervolume** — the area/volume of objective space dominated by a frontier
  relative to a reference point; a single-number quality score for a whole front
  (higher = better). We report TEST-set hypervolume of the selected front.
- **Gene / chromosome / crossover / mutation** — GA encoding: a chromosome is a
  vector of integer genes (one per categorical choice: method, model, ...).
  Crossover swaps genes between configs; mutation resets a gene at random.
- **Exhaustive vs NSGA-II** — when the space is small (≤ threshold) the optimizer
  enumerates all configs; otherwise it searches with NSGA-II. We fixed the model
  so the space was small → exhaustive (cleaner A/B; only scoring differs).

## C. Agentic workflows / methods (the search space)

- **Workflow / agentic workflow** — the pipeline of LLM calls (and tools/code)
  that turns an input into an answer. The thing being optimized.
- **structured_baseline** — single LLM call predicting the answer (`simulate`).
  The cheapest workflow; what our cheap predictor f imitates.
- **zs_cot (zero-shot chain-of-thought)** — prompt the model to reason step by
  step, then answer. (Broken/0% under gemini in our run.)
- **CoT (Chain of Thought)** — eliciting intermediate reasoning before the answer.
- **workflow (decomposition)** — explicit multi-step pipeline (extract
  requirements → score assignments → choose).
- **PoT (Program of Thought)** — the LLM writes code that is executed; the code's
  output is the answer. Good for combinatorial/constraint tasks.
- **ReAct** — agent loop alternating Thought/Action with tools
  (search/lookup/finish).
- **wf_orch** — a learned orchestration workflow (from orch_learner). Best config
  in our run; structurally farthest from baseline → lowest corr(f,Y)=0.10.

## D. secretagent framework terms

- **Interface** — a typed Python stub (signature + docstring) decorated with
  `@interface`; the unit of behavior.
- **Implementation / Factory** — how an interface is realized; built by a
  registered `Implementation.Factory` (e.g. `simulate`, `program_of_thought`).
- **Strategy** — the full binding of all interfaces to implementations; the
  serializable description of the system's behavior (a config).
- **Learner** — a component that generates new implementations (prompt tuning,
  tool induction, orchestration). Tracked via savefile.
- **savefile** — utility that tags every experimental result with the full
  strategy + date for reproducibility.
- **Minibatch / eval pool** — the small/large case sets a benchmark exposes for
  quick vs full evaluation.

## E. Benchmark terms

- **MUSR** — Multistep Soft Reasoning benchmark (murder mysteries, object
  placements, team allocation).
- **Team allocation** — assign described people to tasks given soft constraints;
  multiple-choice, answer = index, scored by exact match.
- **Exact match** — correct = (predicted == expected). Our grader (no judge).
- **valid / test split** — valid (our trainval, 150) is what the optimizer scores
  on; test (100) is held out for generalization measurement.
