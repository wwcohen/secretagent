# FinQA — run from benchmarks/finqa
#
# Override model / size:
#   make react MODEL=claude-haiku-4-5-20251001 N=100
#
# Data (large; gitignored): make download && make build

MODEL ?= together_ai/deepseek-ai/DeepSeek-V3.1
N ?= 300

# Iteration knobs:
#   SPLIT  = which dataset split to use   (valid | train | test)
#   RECORD = record per-case rollouts in results.jsonl (true|false)
#   SUFFIX = appended to evaluate.expt_name as `<expt>_<suffix>`
#            so successive iterations produce distinct result dirs
SPLIT  ?= valid
RECORD ?= false
SUFFIX ?=

DOT_N      := $(if $(N),dataset.n=$(N),)
DOT_SPLIT  := dataset.split=$(SPLIT)
DOT_RECORD := evaluate.record_details=$(RECORD)
expt = $(1)$(if $(SUFFIX),_$(SUFFIX),)

IFACE  = ptools.answer_finqa
CLI    = uv run python -m secretagent.cli.expt run --interface $(IFACE) --evaluator evaluator.FinQAEvaluator

.PHONY: download build build-small help \
	structured_baseline unstructured_baseline pot react workflow workflow-lookup quick-test \
	basics test export plot \
	list avg compare costs

help:
	@echo "Data:  download | build | build-small"
	@echo ""
	@echo "Experiments (default split=valid, N=300):"
	@echo "  workflow              = main result (hand-coded workflow + ptools)"
	@echo "  workflow-lookup       = variant: workflow using only pot/react primitives (negative result, kept for reproducibility)"
	@echo "  pot                   = ablation: drop workflow, keep ptools (program of thought)"
	@echo "  react                 = ablation: drop workflow, keep ptools (ReAct agent)"
	@echo "  structured_baseline   = ablation: drop workflow and ptools (simulate)"
	@echo "  unstructured_baseline = ablation: drop everything (zero-shot prompt)"
	@echo ""
	@echo "  basics = run all five base experiments"
	@echo "  export = copy latest results to benchmarks/results/finqa/finqa/"
	@echo "  test   = run pytest suite"
	@echo "  plot   = generate results_plot.png"
	@echo ""
	@echo "Debug: quick-test | Meta: list | avg | compare | costs"
	@echo "Vars:  MODEL=$(MODEL)  N=$(N)  SPLIT=$(SPLIT)  RECORD=$(RECORD)  SUFFIX=$(SUFFIX)"

basics: structured_baseline unstructured_baseline workflow pot react

download:
	uv run python data/download.py

build:
	uv run python data/build_datasets.py

build-small:
	uv run python data/build_datasets.py --max-per-split 30

workflow:
	$(CLI) evaluate.expt_name=$(call expt,workflow) llm.model=$(MODEL) \
	  $(DOT_N) $(DOT_SPLIT) $(DOT_RECORD) \
	  ptools.answer_finqa.method=direct \
	  ptools.answer_finqa.fn=ptools.answer_finqa_workflow

# Variant of workflow that uses ONLY the pot/react primitives
# {extract_reasoning_plan, lookup_cell, compute} for value resolution
# (no new helpers). Same prompt + plan extraction as `workflow`; only
# value resolution differs. DOCUMENTED NEGATIVE RESULT — ~2.7pp worse
# than `workflow` on N=300 valid; see ptools.py section header for the
# full diagnosis. Kept here so the comparison is reproducible.
workflow-lookup:
	$(CLI) evaluate.expt_name=$(call expt,workflow_lookup) llm.model=$(MODEL) \
	  $(DOT_N) $(DOT_SPLIT) $(DOT_RECORD) \
	  ptools.answer_finqa.method=direct \
	  ptools.answer_finqa.fn=ptools.answer_finqa_workflow_lookup

# --- Ablation 1: drop workflow, keep ptools ---

# pot and react share the same toolset {parse_table, lookup_cell, compute,
# extract_reasoning_plan} so only the orchestration mechanism (PoT vs
# ReAct) differs between the two. Targets only override what differs
# from conf.yaml: extract_reasoning_plan is bound to simulate (looser
# than conf.yaml's prompt_llm, which targets the workflow's strict
# plan format) and answer_finqa is bound to the appropriate agent
# (program_of_thought for pot; direct -> react_workflow for react,
# which wraps react_solve_finqa with extract_final_number for output
# cleanup, matching the standard post-processing pattern across
# benchmarks). The primitive bindings (parse_table, lookup_cell,
# compute) are inherited from conf.yaml.

pot:
	$(CLI) evaluate.expt_name=pot llm.model=$(MODEL) $(DOT_N) \
	  ptools.extract_reasoning_plan.method=simulate \
	  ptools.answer_finqa.method=program_of_thought \
	  ptools.answer_finqa.tools=[ptools.parse_table,ptools.lookup_cell,ptools.compute,ptools.extract_reasoning_plan] \
	  ptools.answer_finqa.inject_args=true \
	  ptools.answer_finqa.additional_imports=[re]

react:
	$(CLI) evaluate.expt_name=react llm.model=$(MODEL) $(DOT_N) \
	  ptools.extract_reasoning_plan.method=simulate \
	  ptools.react_solve_finqa.method=simulate_pydantic \
	  ptools.react_solve_finqa.tools=[ptools.call_parse_table,ptools.call_lookup_cell,ptools.call_compute,ptools.call_extract_reasoning_plan] \
	  ptools.answer_finqa.method=direct \
	  ptools.answer_finqa.fn=ptools.react_workflow

# --- Ablation 2: drop workflow and ptools ---

structured_baseline:
	$(CLI) evaluate.expt_name=structured_baseline llm.model=$(MODEL) $(DOT_N) \
	  ptools.answer_finqa.method=simulate

# --- Ablation 3: drop workflow, ptools, and structured prompt ---

unstructured_baseline:
	$(CLI) evaluate.expt_name=unstructured_baseline llm.model=$(MODEL) $(DOT_N) \
	  ptools.answer_finqa.method=direct \
	  ptools.answer_finqa.fn=ptools.unstructured_baseline_workflow

# --- Utilities ---

quick-test:
	uv run python expt.py quick-test --config-file conf/conf.yaml \
	  dataset.n=1 llm.model=$(MODEL)

test:
	cd ../tests && uv run python -m pytest test_finqa.py -v

export:
	uv run python -m secretagent.cli.results export --as finqa/finqa results/*

plot:
	uv run python -m secretagent.cli.results plot --latest 1 --metric cost- --metric correct --output results_plot.png results/*/

list:
	uv run python -m secretagent.cli.results list results/*

avg:
	uv run python -m secretagent.cli.results average --metric correct --metric cost results/*

compare:
	uv run python -m secretagent.cli.results compare-configs results/*

costs:
	uv run python -m secretagent.cli.costs llm_cache
