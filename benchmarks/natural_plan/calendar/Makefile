-include ../../../.env
export

# Optional: set DATASET_PARTITION=test (or =valid, =train) to run on a
# pre-split file (data/calendar_{partition}.json) and write outputs to
# results-<partition>/. Defaults: full data + dataset.shuffle_seed/n, results/.
PARTITION_OVERRIDE =
EXPORT_SRC = results
ifdef DATASET_PARTITION
  PARTITION_OVERRIDE = dataset.partition=$(DATASET_PARTITION) evaluate.result_dir=results-$(DATASET_PARTITION)
  EXPORT_SRC = results-$(DATASET_PARTITION)
endif

CAL_N ?= 100
CAL_BASE = uv run python ../expt.py run --config-file conf/calendar.yaml dataset.n=$(CAL_N) $(PARTITION_OVERRIDE)

workflow:
	$(CAL_BASE) evaluate.expt_name=workflow \
	  ptools.calendar_scheduling.method=direct \
	  ptools.calendar_scheduling.fn=ptools.calendar_workflow

pot:
	$(CAL_BASE) evaluate.expt_name=pot \
	  ptools.calendar_scheduling.method=program_of_thought \
	  ptools.calendar_scheduling.tools=[ptools.parse_schedules,ptools.find_available_slots,ptools.select_and_format]

react:
	$(CAL_BASE) evaluate.expt_name=react \
	  ptools.calendar_scheduling.method=simulate_pydantic \
	  ptools.calendar_scheduling.tools=[ptools.parse_schedules,ptools.find_available_slots,ptools.select_and_format]

structured_baseline:
	$(CAL_BASE) evaluate.expt_name=structured_baseline \
	  ptools.calendar_scheduling.method=simulate

unstructured_baseline:
	$(CAL_BASE) evaluate.expt_name=unstructured_baseline \
	  ptools.calendar_scheduling.method=prompt_llm \
	  ptools.calendar_scheduling.prompt_template_file=prompt_templates/zeroshot_calendar.txt

smoke:
	$(MAKE) CAL_N=5 workflow
	$(MAKE) CAL_N=5 structured_baseline
	$(MAKE) CAL_N=5 unstructured_baseline
	$(MAKE) CAL_N=5 pot
	$(MAKE) CAL_N=5 react

parallel:
	mkdir -p logs
	nohup $(MAKE) workflow              > logs/workflow.log              2>&1 &
	nohup $(MAKE) structured_baseline   > logs/structured_baseline.log   2>&1 &
	nohup $(MAKE) unstructured_baseline > logs/unstructured_baseline.log 2>&1 &
	nohup $(MAKE) pot                   > logs/pot.log                   2>&1 &
	nohup $(MAKE) react                 > logs/react.log                 2>&1 &
	@echo "launched 5 calendar jobs in background, logs in logs/*.log"

export:
	uv run python -m secretagent.cli.results export \
	  --check dataset.split=calendar \
	  --as natural_plan/calendar \
	  $(EXPORT_SRC)/*

# --- View results ---

list:
	uv run python -m secretagent.cli.results list results/*

avg:
	uv run python -m secretagent.cli.results average --metric correct --metric cost results/*

pair:
	uv run python -m secretagent.cli.results pair --metric correct --metric cost results/*

compare:
	uv run python -m secretagent.cli.results compare-configs results/*

# --- Plot from paper/results ---

RESULTS_ROOT = ../../../paper/results/results/natural_plan

plot:
	uv run python -m secretagent.cli.results plot --metric cost- --metric correct \
	  --output plot_calendar.png $(RESULTS_ROOT)/calendar/*

# --- Pareto sweep ---

N_PARETO ?= 5
TIMEOUT_PARETO ?= 600

pareto:
	uv run python ../run_pareto.py --domain calendar --dataset-n $(N_PARETO) --timeout $(TIMEOUT_PARETO)
