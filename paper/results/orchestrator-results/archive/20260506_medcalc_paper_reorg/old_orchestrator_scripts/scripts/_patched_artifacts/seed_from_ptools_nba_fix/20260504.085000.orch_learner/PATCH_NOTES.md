# Patched seed/rulearena_nba ptools_evolved.py

Source: `benchmarks/rulearena/results/orchestration_learner/20260427.080244.orch_learner/`

Patch: in `compute_rulearena_answer_orchestrated_seed`, the NBA branch
originally called `extract_nba_params(problem_text)` — no rules text, no
structured metadata. This drove avg_input_tokens down to ~507 and accuracy
down to 26.1% on the test set, vs the existing-workflow's `l1_extract_workflow`
which builds a rich query with rules + metadata (avg_input_tokens ~23k, 52.2%).

The patch rebuilds the query the same way the existing workflow does
(`_build_nba_query` shape) before calling `extract_nba_params`.
