# Orchestrator-results

Test-set re-evaluation of the eight orchestration_learner workflows
documented in `docs/orchestration_learner_sweep_results.md`. Every cell
was run on the held-out test split with
`together_ai/deepseek-ai/DeepSeek-V3.1`.

```bash
# Print the two summary tables (handcrafted vs orchestrator-generated):
bash benchmarks/COMMON/orchestrator-results/show_summary.sh
```

See `RESULTS_LAYOUT.md` for the directory layout and the meaning of the
`with_rulebook` / `without_rulebook` and `learned_from_*_traces`
variants.

Helper scripts and infra dirs live under `scripts/`.
