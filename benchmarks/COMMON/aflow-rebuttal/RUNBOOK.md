# AFlow rebuttal runs — runbook / reproducibility trail

Rebuttal baseline for NeurIPS response (reviewer 5qsk W1: external workflow-optimizer
comparison). Owner: Joshua. Date started: 2026-07-27.

## Setup

- Code: FoundationAgents/AFlow @ `3f457218fc716093fe53f6df8a5d5e6379d66346` (2025-12-25), shallow clone.
- Env: Python 3.9.22 (uv venv), `requirements.txt` + `requests` (missing from their pins).
- Models (config/config2.yaml, Gemini OpenAI-compat endpoint
  https://generativelanguage.googleapis.com/v1beta/openai/):
  - optimizer: `gemini-3.1-pro-preview` (temperature 0)
  - executor:  `gemini-2.5-flash-lite` (temperature 0)
- Pricing added to `scripts/async_llm.py::ModelPricing.PRICES` from litellm model_cost
  (same price source as the secretagent harness): flash-lite 0.0001/0.0004 per 1K,
  3.1-pro-preview 0.002/0.012 per 1K.
  CAVEAT: the compat endpoint's usage field appears to exclude 3.1-pro thinking tokens,
  so tracked optimizer cost is an under-count. Executor (flash-lite, non-thinking) is exact.

## Datasets (exported by secretagent scripts/export_aflow_datasets.py)

Subsetting reproduced via secretagent.dataset.Dataset.configure (same code path as
cli.expt), so validation sets are bit-identical to the paper's NSGA-II sweep cells:

| file | rows | selection |
|---|---|---|
| sportsunderstanding_validate.jsonl | 50 | valid split, shuffle_seed=137, head-50 |
| sportsunderstanding_test.jsonl | 100 | full test split (seed-137 order) |
| finqa_validate.jsonl | 50 | valid split, unshuffled head-50 |
| finqa_test.jsonl | 300 | test split, unshuffled head-300 |

## Benchmark classes

- SportsUnderstanding -> AFlow's stock `benchmarks/bbh.py` (normalized exact match).
- FinQA -> new `benchmarks/finqa.py`; matching functions ported VERBATIM from
  secretagent `benchmarks/finqa/evaluator.py` (identical scoring across arms).
- Registered in `scripts/evaluator.py` (DatasetType + class map) and `run.py`
  (SportsUnderstanding: qa, [Custom, AnswerGenerate, ScEnsemble];
   FinQA: math, [Custom, ScEnsemble, Programmer]).

## Deliberate deviations (disclose in the response)

1. Sports round_1 seed prompt is `"Answer with only 'yes' or 'no'."` instead of the
   canonical empty instruction: the empty seed scores 0.00 under exact match
   (verbose answers), giving the optimizer a degenerate uniform-zero signal.
   Equivalent format instructions are present in every baseline arm's prompts.
   FinQA keeps the canonical empty seed (2/4 on seed sanity check).
2. Final test pass uses `test_pass.py` (this repo), not optimizer.test(): best round
   selected by mean VALIDATION score in results.json, then scored once on *_test.jsonl.

## Search runs

- Sports: `PYTHONUTF8=1 PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe run.py
  --dataset SportsUnderstanding --sample 4 --max_rounds 15 --validation_rounds 3
  --opt_model_name gemini-3.1-pro-preview --exec_model_name gemini-2.5-flash-lite`
  -> sports_search.log.
  DONE 2026-07-27 17:27: converged (top-3 flat 5 rounds) at round 9/15.
  Val means (3x50 each): r1 .76 r2 .76 r3 .44 r4 .76 r5 .74 r6 .56 r7 .76 r8 .76 r9 .54.
  Best-by-validation = round 1 (the seed single call; ties broken to earliest/cheapest).
  8 generated candidates never beat the seed. Failures during search: a handful of
  KeyError 'thought' skips (candidate fragility, scored against candidates) + one 503.
  TEST (n=100, test_pass.py): round 1 -> 0.75, $0.000003/case, $0.0003 total;
  100 rows, 0 exception rows (test_logs/SportsUnderstanding/round_1/0.75000_*.csv).
- FinQA: same with --dataset FinQA -> finqa_search.log.
  STATUS: launched 2026-07-27 ~17:50 (serialized after sports).
  Observed: round 2 candidate broken by construction (referenced undefined
  ANALYSIS_PROMPT -> all samples fail -> scores 0; optimizer's known format
  fragility, cf. AFlow issues #22/#29/#40). Round 3 uses Programmer 3x/problem;
  standalone test shows Programmer is parse-dead with flash-lite: the model
  emits valid code in a markdown fence, the code_fill parser extracts nothing,
  operator returns "No code generated" (~3s, no crash). NOT a Windows issue.
  Left unpatched deliberately: operator fragility is part of the
  baseline-as-shipped; the search self-penalizes and routes around it.
  Same class as sports' sporadic KeyError 'thought' (AnswerGenerate tag omission).
  Attempt 2 (operators Custom/AnswerGenerate/ScEnsemble) failed instantly every
  round: the math template defines NO AnswerGenerate (absent from operator.py,
  operator_an.py, operator.json) -> KeyError in load_operators_description; all
  15 rounds scored None (~$0.02 wasted). Logs: finqa_search_attempt2_answergen.log.
  ATTEMPT 3 (the paper-facing run): operators=["Custom","ScEnsemble"], workspace
  reset to round_1 seed only. Launched 21:41. Round means: r1 0.52 (seed), r2 0.26,
  r3 0.72 (beats seed; a fast single-call-style candidate).
  SETTING CHANGE mid-run (disclosed): rounds 1-3 ran --validation_rounds 3, but all
  repeats are byte-identical at temperature 0 (0.52x3, 0.26x3, 0.72x3; sports same),
  and round-2's candidate took 15.5 min/repeat -> 46 min/round of pure duplication.
  Killed after round 3 fully persisted; resumed with --initial_round 3
  --validation_rounds 1 --max_rounds 12 (15 total rounds cap unchanged). Repeats
  add no information for deterministic configs; scores unaffected by construction.
  DONE 2026-07-28 00:15: converged (window rounds 7-11) at round 12/15.
  Round means: r1 0.52 (seed) r2 0.26 r3 0.72 r4 0.72 r5 0.02 r6 0.64 r7 0.72
  r8 0.66 r9 0.36 r10 0.72 r11 0.68 r12 0.72. Best-by-validation = round 3:
  a Solve -> Review two-call chain (solve with tuned prompt, then a verification
  call re-checking extraction/arithmetic). Search DID improve over the seed here
  (+20pp val). Failed directions logged in processed_experience.json: 3x/5x
  ensembles (0.26/0.66), self-refine (0.72 tie), format-extraction step (0.36).

## Reference cells (secretagent harness, gemini-2.5-flash-lite, serial on Windows)

- Sports (valid50 = AFlow's exact search subset / test100): workflow .94/.81,
  structured .90/.85, react .86/.59, unstructured .74/.82.
- FinQA (valid50 / test300): workflow .84/.7567 (matches DeepSeek workflow's .7533
  on the same test-300); structured .30/.25 and react .12/.07 are GENUINE flash-lite
  collapses (real wrong numerics; react additionally hits pydantic-ai output-validation
  retries=1 failures on long contexts) - verified by reading predictions.
- FinQA zeroshot: first run was a harness misconfig (conf/zeroshot_prompt.yaml is
  stale, lacks the zeroshot_answer_finqa binding -> every case
  "no implementation registered"); deleted, rerun via CLI overrides on conf/conf.yaml
  (the paper's EXPERIMENT_CMDS form). run_gemlite_reference_cells.sh fixed accordingly.
- FinQA test pass note: 12 rows contain the word "error" in legitimate review prose;
  strict exception-signature check shows 0 infra failures.

## Post-search

- Test pass: `.venv/Scripts/python.exe test_pass.py --dataset <D>` (auto-picks best val round).
- Reference cells (secretagent repo): `bash scripts/run_gemlite_reference_cells.sh all`
  — flash-lite workflow/react/structured/unstructured on the same valid subsets + test splits.
  Sports valid-n=75 all-method cells also exist from Cassie's basics grid (upstream/clean,
  CASSIE_STATUS.md) on gemini-3.1-pro-preview + gemini-2.5-flash-lite.
- Cost accounting: executor-side from workspace results.json (per-round avg/total cost);
  optimizer-side = sum of printed "Cost: $" lines in *_search.log minus executor share;
  cross-check vs Google AI Studio billing.
