-include ../../../.env
export

PARTITION_OVERRIDE =
EXPORT_SRC = results
ifdef DATASET_PARTITION
  PARTITION_OVERRIDE = dataset.partition=$(DATASET_PARTITION) evaluate.result_dir=results-$(DATASET_PARTITION)
  EXPORT_SRC = results-$(DATASET_PARTITION)
endif

MEET_N ?= 100
MEET_BASE = uv run python ../expt.py run --config-file conf/meeting.yaml dataset.n=$(MEET_N) $(PARTITION_OVERRIDE)

workflow:
	$(MEET_BASE) evaluate.expt_name=workflow \
	  ptools.meeting_planning.method=direct \
	  ptools.meeting_planning.fn=ptools.meeting_workflow

pot:
	$(MEET_BASE) evaluate.expt_name=pot \
	  ptools.meeting_planning.method=program_of_thought \
	  ptools.meeting_planning.tools=[ptools.parse_meeting_info,ptools.plan_visit_order,ptools.build_meeting_plan]

react:
	$(MEET_BASE) evaluate.expt_name=react \
	  ptools.meeting_planning.method=simulate_pydantic \
	  ptools.meeting_planning.tools=[ptools.parse_meeting_info,ptools.plan_visit_order,ptools.build_meeting_plan]

structured_baseline:
	$(MEET_BASE) evaluate.expt_name=structured_baseline \
	  ptools.meeting_planning.method=simulate

unstructured_baseline:
	$(MEET_BASE) evaluate.expt_name=unstructured_baseline \
	  ptools.meeting_planning.method=prompt_llm \
	  ptools.meeting_planning.prompt_template_file=prompt_templates/zeroshot_meeting.txt

parallel:
	mkdir -p logs
	nohup $(MAKE) workflow              > logs/workflow.log              2>&1 &
	nohup $(MAKE) structured_baseline   > logs/structured_baseline.log   2>&1 &
	nohup $(MAKE) unstructured_baseline > logs/unstructured_baseline.log 2>&1 &
	nohup $(MAKE) pot                   > logs/pot.log                   2>&1 &
	nohup $(MAKE) react                 > logs/react.log                 2>&1 &
	@echo "launched 5 meeting jobs in background, logs in logs/*.log"

export:
	uv run python -m secretagent.cli.results export \
	  --check dataset.split=meeting \
	  --as natural_plan/meeting \
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
	  --output plot_meeting.png $(RESULTS_ROOT)/meeting/*

N_PARETO ?= 5
TIMEOUT_PARETO ?= 600

pareto:
	uv run python ../run_pareto.py --domain meeting --dataset-n $(N_PARETO) --timeout $(TIMEOUT_PARETO)
