# FinQA — run from benchmarks/finqa
#
# Override model / size:
#   make react MODEL=claude-haiku-4-5-20251001 N=100
#
# Data (large; gitignored): make download && make build

MODEL ?= together_ai/deepseek-ai/DeepSeek-V3.1
N ?= 300

DOT_N := $(if $(N),dataset.n=$(N),)
IFACE  = ptools.answer_finqa
CLI    = uv run python -m secretagent.cli.expt run --interface $(IFACE) --evaluator evaluator.FinQAEvaluator

.PHONY: download build build-small help \
	structured_baseline unstructured_baseline pot react workflow quick-test \
	basics test export plot \
	list avg compare costs

help:
	@echo "Data:  download | build | build-small"
	@echo ""
	@echo "Experiments (all on valid split):"
	@echo "  workflow              = main result (hand-coded workflow + ptools)"
	@echo "  pot                   = ablation: drop workflow, keep ptools (program of thought)"
	@echo "  react                 = ablation: drop workflow, keep ptools (ReAct agent)"
	@echo "  structured_baseline   = ablation: drop workflow and ptools (simulate)"
	@echo "  unstructured_baseline = ablation: drop everything (zero-shot prompt)"
	@echo ""
	@echo "  basics = run all five"
	@echo "  export = copy latest results to benchmarks/COMMON/results/finqa/finqa/"
	@echo "  test   = run pytest suite"
	@echo "  plot   = generate results_plot.png"
	@echo ""
	@echo "Debug: quick-test | Meta: list | avg | compare | costs"
	@echo "Vars:  MODEL=$(MODEL)  N=$(N) (default 300; N= for full split)"

basics: structured_baseline unstructured_baseline workflow pot react

download:
	uv run python data/download.py

build:
	uv run python data/build_datasets.py

build-small:
	uv run python data/build_datasets.py --max-per-split 30

# --- Main result ---

workflow:
	$(CLI) evaluate.expt_name=workflow llm.model=$(MODEL) $(DOT_N) \
	  ptools.parse_table.method=direct \
	  ptools.compute.method=direct \
	  ptools.extract_reasoning_plan.method=simulate \
	  ptools.extract_final_number.method=simulate \
	  ptools.answer_finqa.method=direct \
	  ptools.answer_finqa.fn=ptools.answer_finqa_workflow

# --- Ablation 1: drop workflow, keep ptools ---

pot:
	$(CLI) evaluate.expt_name=pot llm.model=$(MODEL) $(DOT_N) \
	  ptools.parse_table.method=direct \
	  ptools.compute.method=direct \
	  ptools.answer_finqa.method=program_of_thought \
	  ptools.answer_finqa.tools=[ptools.parse_table,ptools.compute] \
	  ptools.answer_finqa.inject_args=true \
	  ptools.answer_finqa.additional_imports=[re]

react:
	$(CLI) evaluate.expt_name=react llm.model=$(MODEL) $(DOT_N) \
	  ptools.parse_table.method=direct \
	  ptools.lookup_cell.method=direct \
	  ptools.compute.method=direct \
	  ptools.extract_reasoning_plan.method=simulate \
	  ptools.extract_final_number.method=simulate \
	  ptools.answer_finqa.method=simulate_pydantic \
	  ptools.answer_finqa.tools=[ptools.call_parse_table,ptools.call_lookup_cell,ptools.call_compute,ptools.call_extract_reasoning_plan]

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