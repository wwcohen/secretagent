#
# Run experiments — MUSR murder mysteries
#
# Usage: make workflow, make simplified_unstructured_baseline, etc.
# Override model: make workflow MODEL=together_ai/deepseek-ai/DeepSeek-V3
# Override n: make workflow N=75
#

MODEL ?= together_ai/deepseek-ai/DeepSeek-V3
N ?= 75

# --- Murder mysteries (best: 3-step workflow, 72%) ---

workflow:
	uv run python ../expt.py run --config-file conf/murder.yaml \
	  evaluate.expt_name=murder_workflow llm.model=$(MODEL) dataset.n=$(N) \
	  evaluate.entry_point=answer_question_workflow

# --- Simplified unstructured baseline (true zero-shot, no CoT phrasing) ---

simplified_unstructured_baseline:
	uv run python ../expt.py run --config-file conf/murder_simplified_unstructured_baseline.yaml \
	  llm.model=$(MODEL) dataset.n=$(N)

# --- View results ---

list:
	uv run python -m secretagent.cli.results list results/*

avg:
	uv run python -m secretagent.cli.results average --metric correct --metric cost results/*

compare:
	uv run python -m secretagent.cli.results compare-configs results/*

costs:
	uv run python -m secretagent.cli.costs llm_cache

# --- Pareto sweep (exhaustive: levels x models) ---

N_PARETO ?= 5
TIMEOUT_PARETO ?= 600

pareto:
	uv run python ../run_pareto.py --domain murder --dataset-n $(N_PARETO) --timeout $(TIMEOUT_PARETO)
