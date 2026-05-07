#
# Run experiments — TabMWP benchmark
#
# Usage: make unstructured_baseline, make workflow, etc.
# Override model: make workflow MODEL=together_ai/openai/gpt-oss-20b
# Override n: make workflow N=50
#

MODEL ?= together_ai/deepseek-ai/DeepSeek-V3.1
N ?= 100

# --- Run targets (one per method) ---

unstructured_baseline:
	uv run python expt.py run --config-file conf/unstructured_baseline.yaml \
	  llm.model=$(MODEL) dataset.n=$(N)

structured_baseline:
	uv run python expt.py run --config-file conf/structured_baseline.yaml \
	  llm.model=$(MODEL) dataset.n=$(N)

workflow:
	uv run python expt.py run --config-file conf/workflow.yaml \
	  llm.model=$(MODEL) dataset.n=$(N)

pot:
	uv run python expt.py run --config-file conf/pot.yaml \
	  llm.model=$(MODEL) dataset.n=$(N)

react:
	uv run python expt.py run --config-file conf/react.yaml \
	  llm.model=$(MODEL) dataset.n=$(N)

all: unstructured_baseline structured_baseline workflow pot react

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

costs:
	uv run python -m secretagent.cli.costs llm_cache

#
# Pareto sweep (exhaustive: levels x models)
#

N_PARETO ?= 5
TIMEOUT_PARETO ?= 600

pareto:
	uv run python run_pareto.py --dataset-n $(N_PARETO) --timeout $(TIMEOUT_PARETO)
