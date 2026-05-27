EXPT = uv run python -m secretagent.cli.expt run --config conf/trip.yaml --evaluator evaluator.TripEvaluator

basics: workflow pot react structured_baseline unstructured_baseline

workflow:
	$(EXPT) evaluate.expt_name=workflow \
	  ptools.trip_planning.method=direct \
	  ptools.trip_planning.fn=ptools.trip_workflow

pot:
	$(EXPT) evaluate.expt_name=pot \
	  ptools.trip_planning.method=program_of_thought \
	  ptools.trip_planning.tools=[ptools.parse_trip_constraints,ptools.find_valid_route,ptools.build_trip_plan]

react:
	$(EXPT) evaluate.expt_name=react \
	  ptools.trip_planning.method=simulate_pydantic \
	  ptools.trip_planning.tools=[ptools.parse_trip_constraints,ptools.find_valid_route,ptools.build_trip_plan]

structured_baseline:
	$(EXPT) evaluate.expt_name=structured_baseline \
	  ptools.trip_planning.method=simulate

unstructured_baseline:
	$(EXPT) evaluate.expt_name=unstructured_baseline \
	  ptools.trip_planning.method=prompt_llm \
	  ptools.trip_planning.prompt_template_file=prompt_templates/zeroshot_trip.txt

list:
	uv run python -m secretagent.cli.results list results/*

avg:
	uv run python -m secretagent.cli.results average --metric correct --metric cost results/*

pair:
	uv run python -m secretagent.cli.results pair --metric correct --metric cost results/*

compare:
	uv run python -m secretagent.cli.results compare-configs results/*

