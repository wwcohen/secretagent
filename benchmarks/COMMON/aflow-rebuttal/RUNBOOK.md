# AFlow rebuttal runbook

External workflow-optimizer baseline (reviewer 5qsk W1). Dates: 2026-07-27/28.

## Setup

- FoundationAgents/AFlow @ `3f457218` (2025-12-25); Python 3.9.22; `requirements.txt` + `requests` (missing from their pins).
- Models via Gemini OpenAI-compat endpoint, temperature 0: optimizer `gemini-3.1-pro-preview`, executor `gemini-2.5-flash-lite`.
- Prices added to `ModelPricing.PRICES` from litellm model_cost (same source as the secretagent harness). Caveat: the endpoint's usage field omits 3.1-pro thinking tokens, so optimizer-side cost is an under-count; executor costs are exact.

## Datasets (exported by secretagent `scripts/export_aflow_datasets.py`)

Subsetting via `secretagent.dataset.Dataset.configure` — bit-identical to the paper's sweep cells.

| file | rows | selection |
|---|---|---|
| sportsunderstanding_validate | 50 | valid, shuffle_seed=137, head-50 |
| sportsunderstanding_test | 100 | full test split |
| finqa_validate | 50 | valid, unshuffled head-50 |
| finqa_test | 300 | test, unshuffled head-300 |

Scoring: sports = AFlow's stock `benchmarks/bbh.py` exact match; FinQA = new `benchmarks/finqa.py`, matcher ported verbatim from secretagent `benchmarks/finqa/evaluator.py`.

## Deliberate deviations (disclose)

1. Sports round-1 seed prompt = "Answer with only 'yes' or 'no'." — the canonical empty seed scores 0.00 under exact match (verbose answers), a degenerate search signal; every baseline arm's prompts carry equivalent format instructions.
2. FinQA operators = `[Custom, ScEnsemble]`. `Programmer` is parse-dead with this executor (verified standalone: model emits valid code in markdown fences, the code_fill extractor returns nothing — not OS-related); `AnswerGenerate` does not exist in the math template.
3. `--validation_rounds` 3→1 mid-run (resumed `--initial_round 3`): temperature-0 repeats are byte-identical (0.52x3, 0.26x3, 0.72x3; sports 0.76x3), so repeats add cost, not information. Rounds 1-3 keep 3 repeats in results.json.
4. Held-out testing via `test_pass.py` (best round by mean validation score, one pass on `*_test.jsonl`) instead of `optimizer.test()` (hardcodes rounds=[1]).

## Search runs (`--sample 4 --max_rounds 15`, early stop after 5 flat rounds)

- **Sports**: converged round 9/15. Round means: .76 (seed) .76 .44 .76 .74 .56 .76 .76 .54. Best = round 1 (the seed; ties break to earliest). 8 generated candidates (ensembles, CoT, review steps) never beat it. Test n=100: **0.75**, 0 infra failures, $0.000003/case. Search spend $0.59.
- **FinQA attempt 1** (operators incl. Programmer): round-2 candidate structurally broken (score 0); round-3 candidate used dead Programmer 3x/problem — killed (guaranteed 0 at ~90 min/round). $3.5 spent.
- **FinQA attempt 2** (operators incl. AnswerGenerate): every round errored — the operator is absent from the math template. ~$0.02.
- **FinQA attempt 3** (final): converged round 12/15. Round means: .52 (seed) .26 .72 .72 .02 .64 .72 .66 .36 .72 .68 .72. Best = round 3, a **Solve -> Review** two-call chain (+20pp over seed). Failed directions in processed_experience.json: 3x/5x ensembles, self-refine, format-extraction step. Test n=300: **0.67**, 0 infra failures, $0.0011/case. Search spend $5.93 final ($9.40 incl. attempts 1-2).

## Reference cells (secretagent harness, same executor/subsets/scorer; serial on Windows — SIGALRM)

- Sports valid50/test100: workflow .94/.81, structured .90/.85, react .86/.59, zeroshot .74/.82.
- FinQA valid50/test300: workflow .84/.7567, zeroshot .54/.39, structured .30/.25, react .12/.07. The react/structured collapses are genuine (predictions inspected: real wrong numerics; react also hits pydantic-ai output-validation failures at the paper's retries=1).
- `conf/zeroshot_prompt.yaml` is stale (missing the `zeroshot_answer_finqa` binding — every case errors); zeroshot cells use CLI overrides on the base conf, per the archived EXPERIMENT_CMDS form. First broken zeroshot runs deleted.
- FinQA test-pass note: 12 rows merely contain the word "error" in legitimate review prose; strict exception-signature check = 0 infra failures.

## Regenerate

`bash collect.sh` (artifact collection) then `uv run make_summary.py [--format latex]` — see README.md.
