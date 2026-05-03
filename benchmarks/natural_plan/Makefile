-include ../../.env
export

#
# Run experiments — 5 conditions x 3 tasks
#
# Stratified 50 samples (AgentProject-compatible): add dataset.stratified=true dataset.sample_n=50 dataset.n=50
# Sample 50 more (seed 43): add dataset.sample_seed=43
#

# Optional: set DATASET_PARTITION=test (or =valid, =train) to run on a
# pre-split file (data/{task}_{partition}.json) and write outputs to
# results-<partition>/. Defaults: full data + dataset.shuffle_seed/n,
# results/.
PARTITION_OVERRIDE =
EXPORT_SRC = results
ifdef DATASET_PARTITION
  PARTITION_OVERRIDE = dataset.partition=$(DATASET_PARTITION) evaluate.result_dir=results-$(DATASET_PARTITION)
  EXPORT_SRC = results-$(DATASET_PARTITION)
endif

# ── Calendar ── (standard expt_names for scripts/benchmark_status.py)

CAL_N ?= 100
CAL_BASE = uv run python expt.py run --config-file conf/calendar.yaml dataset.n=$(CAL_N) $(PARTITION_OVERRIDE)

calendar_workflow:
	$(CAL_BASE) evaluate.expt_name=workflow \
	  ptools.calendar_scheduling.method=direct \
	  ptools.calendar_scheduling.fn=ptools_calendar.calendar_workflow

calendar_pot:
	$(CAL_BASE) evaluate.expt_name=pot \
	  ptools.calendar_scheduling.method=program_of_thought \
	  ptools.calendar_scheduling.tools=[ptools_calendar.parse_schedules,ptools_calendar.find_available_slots,ptools_calendar.select_and_format]

calendar_react:
	$(CAL_BASE) evaluate.expt_name=react \
	  ptools.calendar_scheduling.method=simulate_pydantic \
	  ptools.calendar_scheduling.tools=[ptools_calendar.parse_schedules,ptools_calendar.find_available_slots,ptools_calendar.select_and_format]

calendar_structured_baseline:
	$(CAL_BASE) evaluate.expt_name=structured_baseline \
	  ptools.calendar_scheduling.method=simulate

calendar_unstructured_baseline:
	$(CAL_BASE) evaluate.expt_name=unstructured_baseline \
	  ptools.calendar_scheduling.method=prompt_llm \
	  ptools.calendar_scheduling.prompt_template_file=prompt_templates/zeroshot_calendar.txt

# Smoke test: N=5, all 5 strategies sequentially
calendar_smoke:
	$(MAKE) CAL_N=5 calendar_workflow
	$(MAKE) CAL_N=5 calendar_structured_baseline
	$(MAKE) CAL_N=5 calendar_unstructured_baseline
	$(MAKE) CAL_N=5 calendar_pot
	$(MAKE) CAL_N=5 calendar_react

# Parallel launch via nohup. Each strategy runs independently, logs go to logs/
calendar_parallel:
	mkdir -p logs
	nohup $(MAKE) calendar_workflow              > logs/cal_workflow.log              2>&1 &
	nohup $(MAKE) calendar_structured_baseline   > logs/cal_structured_baseline.log   2>&1 &
	nohup $(MAKE) calendar_unstructured_baseline > logs/cal_unstructured_baseline.log 2>&1 &
	nohup $(MAKE) calendar_pot                   > logs/cal_pot.log                   2>&1 &
	nohup $(MAKE) calendar_react                 > logs/cal_react.log                 2>&1 &
	@echo "launched 5 calendar jobs in background, logs in logs/cal_*.log"
	@echo "monitor with: tail -f logs/cal_*.log  |  ps aux | grep expt.py"

# Copy latest calendar results (filtered by dataset.split) to benchmarks/COMMON/results/natural_plan/calendar/
calendar_export:
	uv run python -m secretagent.cli.results export \
	  --check dataset.split=calendar \
	  --as natural_plan/calendar \
	  $(EXPORT_SRC)/*

# Legacy cal_* aliases (deprecated, kept for back-compat with existing scripts)
cal_zeroshot_structured: calendar_structured_baseline
cal_zeroshot_unstructured: calendar_unstructured_baseline
cal_workflow: calendar_workflow
cal_pot: calendar_pot
cal_react: calendar_react

# ── Meeting ── (standard expt_names for scripts/benchmark_status.py)

MEET_N ?= 100
MEET_BASE = uv run python expt.py run --config-file conf/meeting.yaml dataset.n=$(MEET_N) $(PARTITION_OVERRIDE)

meeting_workflow:
	$(MEET_BASE) evaluate.expt_name=workflow \
	  ptools.meeting_planning.method=direct \
	  ptools.meeting_planning.fn=ptools_meeting.meeting_workflow

meeting_pot:
	$(MEET_BASE) evaluate.expt_name=pot \
	  ptools.meeting_planning.method=program_of_thought \
	  ptools.meeting_planning.tools=[ptools_meeting.parse_meeting_info,ptools_meeting.plan_visit_order,ptools_meeting.build_meeting_plan]

meeting_react:
	$(MEET_BASE) evaluate.expt_name=react \
	  ptools.meeting_planning.method=simulate_pydantic \
	  ptools.meeting_planning.tools=[ptools_meeting.parse_meeting_info,ptools_meeting.plan_visit_order,ptools_meeting.build_meeting_plan]

meeting_structured_baseline:
	$(MEET_BASE) evaluate.expt_name=structured_baseline \
	  ptools.meeting_planning.method=simulate

meeting_unstructured_baseline:
	$(MEET_BASE) evaluate.expt_name=unstructured_baseline \
	  ptools.meeting_planning.method=prompt_llm \
	  ptools.meeting_planning.prompt_template_file=prompt_templates/zeroshot_meeting.txt

meeting_parallel:
	mkdir -p logs
	nohup $(MAKE) meeting_workflow              > logs/meet_workflow.log              2>&1 &
	nohup $(MAKE) meeting_structured_baseline   > logs/meet_structured_baseline.log   2>&1 &
	nohup $(MAKE) meeting_unstructured_baseline > logs/meet_unstructured_baseline.log 2>&1 &
	nohup $(MAKE) meeting_pot                   > logs/meet_pot.log                   2>&1 &
	nohup $(MAKE) meeting_react                 > logs/meet_react.log                 2>&1 &
	@echo "launched 5 meeting jobs in background, logs in logs/meet_*.log"

meeting_export:
	uv run python -m secretagent.cli.results export \
	  --check dataset.split=meeting \
	  --as natural_plan/meeting \
	  $(EXPORT_SRC)/*

# Legacy meet_* aliases (deprecated)
meet_zeroshot_structured: meeting_structured_baseline
meet_zeroshot_unstructured: meeting_unstructured_baseline
meet_workflow: meeting_workflow
meet_pot: meeting_pot
meet_react: meeting_react

# ── Trip ── (standard expt_names for scripts/benchmark_status.py)

TRIP_N ?= 100
TRIP_BASE = uv run python expt.py run --config-file conf/trip.yaml dataset.n=$(TRIP_N) $(PARTITION_OVERRIDE)

trip_workflow:
	$(TRIP_BASE) evaluate.expt_name=workflow \
	  ptools.trip_planning.method=direct \
	  ptools.trip_planning.fn=ptools_trip.trip_workflow

trip_pot:
	$(TRIP_BASE) evaluate.expt_name=pot \
	  ptools.trip_planning.method=program_of_thought \
	  ptools.trip_planning.tools=[ptools_trip.parse_trip_constraints,ptools_trip.find_valid_route,ptools_trip.build_trip_plan]

trip_react:
	$(TRIP_BASE) evaluate.expt_name=react \
	  ptools.trip_planning.method=simulate_pydantic \
	  ptools.trip_planning.tools=[ptools_trip.parse_trip_constraints,ptools_trip.find_valid_route,ptools_trip.build_trip_plan]

trip_structured_baseline:
	$(TRIP_BASE) evaluate.expt_name=structured_baseline \
	  ptools.trip_planning.method=simulate

trip_unstructured_baseline:
	$(TRIP_BASE) evaluate.expt_name=unstructured_baseline \
	  ptools.trip_planning.method=prompt_llm \
	  ptools.trip_planning.prompt_template_file=prompt_templates/zeroshot_trip.txt

trip_parallel:
	mkdir -p logs
	nohup $(MAKE) trip_workflow              > logs/trip_workflow.log              2>&1 &
	nohup $(MAKE) trip_structured_baseline   > logs/trip_structured_baseline.log   2>&1 &
	nohup $(MAKE) trip_unstructured_baseline > logs/trip_unstructured_baseline.log 2>&1 &
	nohup $(MAKE) trip_pot                   > logs/trip_pot.log                   2>&1 &
	nohup $(MAKE) trip_react                 > logs/trip_react.log                 2>&1 &
	@echo "launched 5 trip jobs in background, logs in logs/trip_*.log"

trip_export:
	uv run python -m secretagent.cli.results export \
	  --check dataset.split=trip \
	  --as natural_plan/trip \
	  $(EXPORT_SRC)/*

# Legacy trip_zs_* aliases (deprecated)
trip_zeroshot_structured: trip_structured_baseline
trip_zeroshot_unstructured: trip_unstructured_baseline

#
# Stratified 50 samples (same IDs as AgentProject seed=42)
#

cal_50_workflow:
	uv run python expt.py run --config-file conf/calendar.yaml \
	  evaluate.expt_name=cal_workflow \
	  ptools.calendar_scheduling.method=direct \
	  ptools.calendar_scheduling.fn=ptools_calendar.calendar_workflow \
	  dataset.stratified=true dataset.sample_n=50 dataset.n=50

cal_50_more_workflow:
	uv run python expt.py run --config-file conf/calendar.yaml \
	  evaluate.expt_name=cal_workflow_more \
	  ptools.calendar_scheduling.method=direct \
	  ptools.calendar_scheduling.fn=ptools_calendar.calendar_workflow \
	  dataset.stratified=true dataset.sample_n=50 dataset.sample_seed=43 dataset.n=50

# Quick view: table by task (accuracy, cost, time, reproduce cmd) -> report.md
report:
	uv run python scripts/report.py -o report.md

# Run all 15 (3 tasks × 5 levels) with n=5 each
run_all_15:
	uv run python scripts/run_all_15.py

# Same + save prompt_trace.jsonl per run for inspection
run_all_15_trace:
	uv run python scripts/run_all_15.py --trace

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

export:
	uv run python -m secretagent.cli.results export results/*

plot: plot_cal plot_meet plot_trip

RESULTS_ROOT = ../../benchmarks/COMMON/results/natural_plan

plot_cal:
	uv run python -m secretagent.cli.results plot --metric cost- --metric correct \
	  --output plot_calendar.png $(RESULTS_ROOT)/calendar/*

plot_meet:
	uv run python -m secretagent.cli.results plot --metric cost- --metric correct \
	  --output plot_meeting.png $(RESULTS_ROOT)/meeting/*

plot_trip:
	uv run python -m secretagent.cli.results plot --metric cost- --metric correct \
	  --output plot_trip.png $(RESULTS_ROOT)/trip/*

test:
	uv run python -m pytest ../../benchmarks/tests/test_natural_plan.py -v

#
# Pareto sweep (exhaustive: methods x models per domain)
#

N_PARETO ?= 5
TIMEOUT_PARETO ?= 600

pareto_calendar:
	uv run python run_pareto.py --domain calendar --dataset-n $(N_PARETO) --timeout $(TIMEOUT_PARETO)

pareto_meeting:
	uv run python run_pareto.py --domain meeting --dataset-n $(N_PARETO) --timeout $(TIMEOUT_PARETO)

pareto_trip:
	uv run python run_pareto.py --domain trip --dataset-n $(N_PARETO) --timeout $(TIMEOUT_PARETO)

pareto_all: pareto_calendar pareto_meeting pareto_trip
