# DesignBench Report

Use this file to track the benchmark runs you want to keep.

## Environment

- Date: 2026-04-06
- Commit: `81321af` (`vlm_implementation`)
- Hardware: local workstation (fill in GPU/CPU details if needed)
- API provider/model: Together API with `llm.model=Qwen/Qwen3.5-9B` (from `conf/conf.yaml`)

## Dataset Setup

- DesignBench root (default lookup): `/Users/goku/Work/Spring_26/IS/DesignBench` (exists)
- Local benchmark data path required by `expt.py`: `benchmarks/designbench/designbench/data/generation/<framework>`
- Local data status in this repo: **present** (`vanilla/react/vue/angular` dirs available)
- Source dataset stats (from sibling DesignBench repo):
  - `vanilla`: 120 valid cases (120 with reference image)
  - `react`: 109 valid cases (109 with reference image)
  - `vue`: 118 valid cases (118 with reference image)
  - `angular`: 83 valid cases (83 with reference image)
- Visual eval enabled (`benchmark.skip_eval=false`): yes (default)

## Experiments

### Vanilla

| Method | Expt name | Avg CLIP | Avg SSIM | Avg MAE | Avg cost | Notes |
|---|---|---:|---:|---:|---:|---|
| Baseline | pending | pending | pending | pending | pending | fill from baseline run |
| ptools | `db_vanilla_default` | 0.7648 | 0.6891 | 52.6364 | 0.000875 | from `results/20260413.011823.db_vanilla_default/results.csv` (120/120) |
| react | pending | pending | pending | pending | pending | fill from react-method run on vanilla split |
| deterministic pipeline | pending | pending | pending | pending | pending | fill from deterministic run |

### React

| Method | Expt name | Avg CLIP | Avg SSIM | Avg MAE | Avg cost | Notes |
|---|---|---:|---:|---:|---:|---|
| Baseline | pending | pending | pending | pending | pending | fill from baseline run |
| ptools | `db_react_default` | 0.7652 | 0.4911 | 95.4064 | 0.001143 | from `results/20260413.050528.db_react_default/results.csv` (109 rows, 89 scored CLIP) |
| react | pending | pending | pending | pending | pending | fill from react-method run |
| deterministic pipeline | pending | pending | pending | pending | pending | fill from deterministic run |

### Vue

| Method | Expt name | Avg CLIP | Avg SSIM | Avg MAE | Avg cost | Notes |
|---|---|---:|---:|---:|---:|---|
| Baseline | pending | pending | pending | pending | pending | fill from baseline run |
| ptools | `db_vue_default` | 0.6409 | 0.3974 | 114.7826 | 0.000775 | from `results/20260416.201407.db_vue_default/results.csv` (118 rows, 112 scored CLIP) |
| react | pending | pending | pending | pending | pending | fill from react-method run |
| deterministic pipeline | pending | pending | pending | pending | pending | fill from deterministic run |

### Angular

| Method | Expt name | Avg CLIP | Avg SSIM | Avg MAE | Avg cost | Notes |
|---|---|---:|---:|---:|---:|---|
| Baseline | pending | pending | pending | pending | pending | fill from baseline run |
| ptools | `db_angular_default` | NA | NA | NA | 0.000955 | from `results/20260413.193147.db_angular_default/results.csv` (83 rows, no CLIP/SSIM/MAE scored) |
| react | pending | pending | pending | pending | pending | fill from react-method run |
| deterministic pipeline | pending | pending | pending | pending | pending | fill from deterministic run |

## Commands To Run (Overnight)

```bash
# 0) Prepare local dataset expected by expt.py
#    (Run from secretagent root)
mkdir -p benchmarks/designbench/designbench/data
cp -R ../DesignBench/data/generation benchmarks/designbench/designbench/data/

# 1) Move into benchmark dir
cd benchmarks/designbench

# 2) Full-framework baseline sweep (model from conf/conf.yaml)
uv run python expt.py run dataset.framework=vanilla evaluate.expt_name=db_vanilla_default
uv run python expt.py run dataset.framework=react   evaluate.expt_name=db_react_default
uv run python expt.py run dataset.framework=vue     evaluate.expt_name=db_vue_default
uv run python expt.py run dataset.framework=angular evaluate.expt_name=db_angular_default

# 3) Summarize in the morning
uv run python -m secretagent.cli.results average --metric clip_similarity --metric ssim --metric mae --metric cost results/*
uv run python -m secretagent.cli.results pair --metric clip_similarity --metric cost results/*
uv run python -m secretagent.cli.results compare-configs results/*
```

## Notes

- Current local benchmark status: baseline `ptools` runs exist for all 4 frameworks; Vue required reruns due timeout instability.
- If visual deps fail at runtime, rerun with `benchmark.skip_eval=true` to at least collect generation outputs and token/cost stats.

