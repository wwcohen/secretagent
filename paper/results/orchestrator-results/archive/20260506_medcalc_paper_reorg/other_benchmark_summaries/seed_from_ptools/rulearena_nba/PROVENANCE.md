# seed_from_ptools/rulearena_nba

## results/

### without_rulebook/
- `20260504.005211.test_deepseek_v3_1/` — n=46, acc=26.09%, exc=0, cost=$0.022
  The orch_learner-generated seed workflow as-is. The NBA branch passes only
  the raw `problem_text` to `extract_nba_params`, with no CBA rules text and
  no structured metadata. avg_input_tokens ~507.

### with_rulebook/
- `20260504.121504.test_deepseek_v3_1/` — n=46, acc=65.22%, exc=1, cost=$0.653
  Manual patch: in `compute_rulearena_answer_orchestrated_seed`, the NBA
  branch was rewritten to build the same rich query the existing-workflow's
  `_build_nba_query` constructs — CBA rules text + structured team /
  player / operations metadata. avg_input_tokens ~22,696 (matches the
  existing workflow). Patched ptools_evolved.py lives in
  `scripts/_patched_artifacts/seed_from_ptools_nba_fix/.../ptools_evolved.py`
  with PATCH_NOTES.md alongside.

  1 persistent exception (`nba_2_31`): pydantic-ai schema-validation
  failure even with `pydantic.retries=3` — the LLM consistently emits
  malformed output for that one case.

## archive/
Older runs preserved under `archive/{without_rulebook,with_rulebook}/`.
