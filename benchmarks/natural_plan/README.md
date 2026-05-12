# NaturalPlan Benchmark

Calendar scheduling, meeting planning, trip planning — 3 tasks × 5 baselines.

## Quick Start

```bash
cd secretagent && uv sync
export TOGETHER_AI_API_KEY="your-key"
cd benchmarks/natural_plan
```

API keys can also be stored in `secretagent/.env` (auto-loaded by Makefile).

## Run Baselines

```bash
# Single experiment
make cal_workflow

# All 15 (3 tasks × 5 levels), default n=50
make run_all_15

# Quick test (n=5)
uv run python scripts/run_all_15.py -n 5

# 5-shot mode
uv run python scripts/run_all_15.py -n 5 --prompt-mode 5shot

# With prompt traces
make run_all_15_trace
```

## Results

```bash
make report          # → report.md
make plot            # → plot_calendar.png, plot_meeting.png, plot_trip.png
make export          # copy to paper/results/results/natural_plan/
```

## Test

```bash
make test
```

15 tests (3 tasks × 5 baselines), 2 samples each. Mirrors `test_sports_understanding.py`.

## Config

| Param | Default | Description |
|-------|---------|-------------|
| `llm.model` | `together_ai/deepseek-ai/DeepSeek-V3.1` | LLM model (litellm) |
| `dataset.split` | — | `calendar` / `meeting` / `trip` |
| `dataset.n` | 4 | Sample limit |
| `dataset.prompt_mode` | 5shot | `5shot` / `0shot` |
| `dataset.stratified` | false | Stratified sampling |
| `dataset.sample_n` | 50 | Samples when stratified |
| `ptools.{entry}.method` | — | `simulate` / `direct` / `prompt_llm` / `program_of_thought` / `simulate_pydantic` |
