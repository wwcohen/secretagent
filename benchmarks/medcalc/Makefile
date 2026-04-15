#
# Run experiments — MedCalc benchmark
#
# Usage: make baseline, make simulate, etc.
# Override model: make baseline MODEL=together_ai/deepseek-ai/DeepSeek-V3.1
# Override n: make baseline N=50
#

MODEL ?= together_ai/Qwen/Qwen3.5-9B
N ?= 5

# --- Run targets (one per level) ---

baseline:
	uv run python expt.py run --config-file conf/baseline.yaml \
	  llm.model=$(MODEL) dataset.n=$(N)

simulate:
	uv run python expt.py run --config-file conf/simulate.yaml \
	  llm.model=$(MODEL) dataset.n=$(N)

distilled:
	uv run python expt.py run --config-file conf/distilled.yaml \
	  llm.model=$(MODEL) dataset.n=$(N)

pot:
	uv run python expt.py run --config-file conf/pot.yaml \
	  llm.model=$(MODEL) dataset.n=$(N)

workflow:
	uv run python expt.py run --config-file conf/workflow.yaml \
	  llm.model=$(MODEL) dataset.n=$(N)

pipeline: workflow  # backward compat alias

all: baseline simulate distilled pot workflow

#
# View results of past experiments
#

list:
	uv run python -m secretagent.cli.results list results/*

avg:
	uv run python -m secretagent.cli.results average --metric correct --metric cost results/*

pair:
	uv run python -m secretagent.cli.results pair --metric correct --metric cost results/*

compare:
	uv run python -m secretagent.cli.results compare-configs results/*

plot:
	uv run python -m secretagent.cli.results plot --metric cost- --metric correct --output plot_medcalc.png results/*

costs:
	uv run python -m secretagent.cli.costs llm_cache

#
# Pareto sweep (exhaustive: levels x models)
#

N_PARETO ?= 5
TIMEOUT_PARETO ?= 600

pareto:
	uv run python run_pareto.py --dataset-n $(N_PARETO) --timeout $(TIMEOUT_PARETO)
