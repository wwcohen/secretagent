-include ../../../.env
export

PARTITION_OVERRIDE =
EXPORT_SRC = results
ifdef DATASET_PARTITION
  PARTITION_OVERRIDE = dataset.partition=$(DATASET_PARTITION) evaluate.result_dir=results-$(DATASET_PARTITION)
  EXPORT_SRC = results-$(DATASET_PARTITION)
endif

TRIP_N ?= 100
TRIP_BASE = uv run python ../expt.py run --config-file conf/trip.yaml dataset.n=$(TRIP_N) $(PARTITION_OVERRIDE)

workflow:
	$(TRIP_BASE) evaluate.expt_name=workflow \
	  ptools.trip_planning.method=direct \
	  ptools.trip_planning.fn=ptools.trip_workflow

pot:
	$(TRIP_BASE) evaluate.expt_name=pot \
	  ptools.trip_planning.method=program_of_thought \
	  ptools.trip_planning.tools=[ptools.parse_trip_constraints,ptools.find_valid_route,ptools.build_trip_plan]

react:
	$(TRIP_BASE) evaluate.expt_name=react \
	  ptools.trip_planning.method=simulate_pydantic \
	  ptools.trip_planning.tools=[ptools.parse_trip_constraints,ptools.find_valid_route,ptools.build_trip_plan]

structured_baseline:
	$(TRIP_BASE) evaluate.expt_name=structured_baseline \
	  ptools.trip_planning.method=simulate

unstructured_baseline:
	$(TRIP_BASE) evaluate.expt_name=unstructured_baseline \
	  ptools.trip_planning.method=prompt_llm \
	  ptools.trip_planning.prompt_template_file=prompt_templates/zeroshot_trip.txt

parallel:
	mkdir -p logs
	nohup $(MAKE) workflow              > logs/workflow.log              2>&1 &
	nohup $(MAKE) structured_baseline   > logs/structured_baseline.log   2>&1 &
	nohup $(MAKE) unstructured_baseline > logs/unstructured_baseline.log 2>&1 &
	nohup $(MAKE) pot                   > logs/pot.log                   2>&1 &
	nohup $(MAKE) react                 > logs/react.log                 2>&1 &
	@echo "launched 5 trip jobs in background, logs in logs/*.log"

export:
	uv run python -m secretagent.cli.results export \
	  --check dataset.split=trip \
	  --as natural_plan/trip \
	  $(EXPORT_SRC)/*

list:
	uv run python -m secretagent.cli.results list results/*

avg:
	uv run python -m secretagent.cli.results average --metric correct --metric cost results/*

pair:
	uv run python -m secretagent.cli.results pair --metric correct --metric cost results/*

compare:
	uv run python -m secretagent.cli.results compare-configs results/*

RESULTS_ROOT = ../../../paper/results/results/natural_plan

plot:
	uv run python -m secretagent.cli.results plot --metric cost- --metric correct \
	  --output plot_trip.png $(RESULTS_ROOT)/trip/*

N_PARETO ?= 5
TIMEOUT_PARETO ?= 600

pareto:
	uv run python ../run_pareto.py --domain trip --dataset-n $(N_PARETO) --timeout $(TIMEOUT_PARETO)
