EXPT = uv run python -m secretagent.cli.expt run --config conf/calendar.yaml --evaluator evaluator.CalendarEvaluator

basics: structured_baseline unstructured_baseline workflow pot react 

workflow:
	$(EXPT) evaluate.expt_name=workflow \
	  ptools.calendar_scheduling.method=direct \
	  ptools.calendar_scheduling.fn=ptools.calendar_workflow

pot:
	$(EXPT) evaluate.expt_name=pot \
	  ptools.calendar_scheduling.method=program_of_thought \
	  ptools.calendar_scheduling.tools=[ptools.parse_schedules,ptools.find_available_slots,ptools.select_and_format]

react:
	$(EXPT) evaluate.expt_name=react \
	  ptools.calendar_scheduling.method=simulate_pydantic \
	  ptools.calendar_scheduling.tools=[ptools.parse_schedules,ptools.find_available_slots,ptools.select_and_format]

structured_baseline:
	$(EXPT) evaluate.expt_name=structured_baseline \
	  ptools.calendar_scheduling.method=simulate

unstructured_baseline:
	$(EXPT) evaluate.expt_name=unstructured_baseline \
	  ptools.calendar_scheduling.method=prompt_llm \
	  ptools.calendar_scheduling.prompt_template_file=prompt_templates/zeroshot_calendar.txt


# --- View results ---

list:
	uv run python -m secretagent.cli.results list results/*

avg:
	uv run python -m secretagent.cli.results average --metric correct --metric cost results/*

pair:
	uv run python -m secretagent.cli.results pair --metric correct --metric cost results/*

compare:
	uv run python -m secretagent.cli.results compare-configs results/*

