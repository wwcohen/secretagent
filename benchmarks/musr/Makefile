#
# Run experiments — MUSR benchmark (murder, object, team splits)
#
# Usage: make murder_workflow, make object, etc.
# Override model: make murder_workflow MODEL=together_ai/deepseek-ai/DeepSeek-V3
# Override n: make murder_workflow N=75
#

MODEL ?= together_ai/deepseek-ai/DeepSeek-V3
N ?= 75

# --- Murder mysteries (best: 3-step workflow, 72%) ---

murder_workflow:
	uv run python expt.py run --config-file conf/murder.yaml \
	  evaluate.expt_name=murder_workflow llm.model=$(MODEL) dataset.n=$(N) \
	  evaluate.entry_point=answer_question_workflow

# --- Object placement (best: infer_belief + thinking, 72%) ---

object:
	uv run python expt.py run --config-file conf/object.yaml \
	  evaluate.expt_name=object llm.model=$(MODEL) dataset.n=$(N)

# --- Team allocation (best: single ptool + thinking, 84%) ---

team:
	uv run python expt.py run --config-file conf/team.yaml \
	  evaluate.expt_name=team llm.model=$(MODEL) dataset.n=$(N)

# --- Simplified unstructured baselines (true zero-shot, no CoT phrasing) ---

murder_simplified_unstructured_baseline:
	uv run python expt.py run --config-file conf/murder_simplified_unstructured_baseline.yaml \
	  llm.model=$(MODEL) dataset.n=$(N)

object_simplified_unstructured_baseline:
	uv run python expt.py run --config-file conf/object_simplified_unstructured_baseline.yaml \
	  llm.model=$(MODEL) dataset.n=$(N)

team_simplified_unstructured_baseline:
	uv run python expt.py run --config-file conf/team_simplified_unstructured_baseline.yaml \
	  llm.model=$(MODEL) dataset.n=$(N)

# --- Run all ---

all: murder_workflow object team

#
# View results of past experiments
#

list:
	uv run python -m secretagent.cli.results list results/*

avg:
	uv run python -m secretagent.cli.results average --metric correct --metric cost results/*

compare:
	uv run python -m secretagent.cli.results compare-configs results/*

costs:
	uv run python -m secretagent.cli.costs llm_cache

#
# Pareto sweep (exhaustive: levels x models per domain)
#

N_PARETO ?= 5
TIMEOUT_PARETO ?= 600

pareto_murder:
	uv run python run_pareto.py --domain murder --dataset-n $(N_PARETO) --timeout $(TIMEOUT_PARETO)

pareto_object:
	uv run python run_pareto.py --domain object --dataset-n $(N_PARETO) --timeout $(TIMEOUT_PARETO)

pareto_team:
	uv run python run_pareto.py --domain team --dataset-n $(N_PARETO) --timeout $(TIMEOUT_PARETO)

pareto_all: pareto_murder pareto_object pareto_team
