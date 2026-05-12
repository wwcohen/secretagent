# musr_murder NSGA-II sweep snapshot

Frozen on 2026-05-04 from commit dccdcac8.

## Command

```
uv run -m secretagent.cli.optimize nsga2 \
  --space-file benchmarks/musr/nsga2.yaml \
  --cwd benchmarks/musr \
  --pop-size 12 --n-gen 5 --timeout 1200 \
  <dataset overrides — see EXPERIMENT_CMDS.md Phase 1 for the exact split>
```

## Methods searched

`structured_baseline`, `workflow`, `pot`, `react`, `react_learned`
(RQ1; if applicable), `wf_orch` (RQ2). See `benchmarks/musr/nsga2.yaml` for the exact
dotlist expansions per method.

## Files

- `nsga2_summary.csv` — one row per evaluated config
- `nsga2_generations.csv` — per-generation convergence stats
- `nsga2.png` — Pareto plot (cost vs correctness)
- `nsga_runs/<TS>.nsga_NNN/` — per-config rollout dirs (0 total)
