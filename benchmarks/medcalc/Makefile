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

#
# Ptool induction pipeline (DeepSeek for traces, gemini-flash-lite for inducer/eval)
#

INDUCER_MODEL ?= gemini/gemini-3.1-flash-lite-preview
TASK_DESC ?= Solve a medical-calculator question by extracting clinical values from a patient note and applying the right formula or score.

# Step 3: generate train/eval traces (4 configs, sequential)
traces: traces-react-train traces-react-eval traces-react-state-train traces-react-state-eval

traces-react-train:
	uv run python expt.py run --config-file conf/react_induct.yaml

traces-react-eval:
	uv run python expt.py run --config-file conf/react_eval.yaml

traces-react-state-train:
	uv run python expt.py run --config-file conf/react_state_induct.yaml

traces-react-state-eval:
	uv run python expt.py run --config-file conf/react_state_eval.yaml

# Step 4: induction matrix
# Variants: state {stateless, state} x only-correct {0, 1} x max-ptools {3, 5, 8} = 12 runs
induce-matrix:
	@for STATE in stateless state ; do \
	  for OC in 0 1 ; do \
	    for MP in 3 5 8 ; do \
	      EXTRA="" ; \
	      SRC="results/*.react_train" ; \
	      [ "$$STATE" = "state" ] && EXTRA="--state-module ptools --state-expr _REACT_STATE[\"patient_note\"]" && SRC="results/*.react_state_train" ; \
	      [ "$$OC" = "1" ] && EXTRA="$$EXTRA --only-correct" ; \
	      echo "===== STATE=$$STATE OC=$$OC MAX=$$MP =====" ; \
	      uv run python run_inducer.py \
	        --interface calculate_medical_value \
	        --task-desc "$(TASK_DESC)" \
	        --trace-mode react \
	        --max-ptools $$MP --min-count 3 \
	        --model $(INDUCER_MODEL) \
	        --learned-dir learned/$$STATE-oc$$OC-mp$$MP \
	        $$EXTRA \
	        $$SRC ; \
	    done ; \
	  done
