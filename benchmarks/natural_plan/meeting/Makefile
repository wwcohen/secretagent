EXPT = uv run python -m secretagent.cli.expt run --config conf/meeting.yaml --evaluator evaluator.MeetingEvaluator 

basics: structured_baseline unstructured_baseline workflow pot react 

workflow:
	$(EXPT) evaluate.expt_name=workflow \
	  ptools.meeting_planning.method=direct \
	  ptools.meeting_planning.fn=ptools.meeting_workflow

pot:
	$(EXPT) evaluate.expt_name=pot \
	  ptools.meeting_planning.method=program_of_thought \
	  ptools.meeting_planning.tools=[ptools.parse_meeting_info,ptools.plan_visit_order,ptools.build_meeting_plan]

react:
	$(EXPT) evaluate.expt_name=react \
	  ptools.meeting_planning.method=simulate_pydantic \
	  ptools.meeting_planning.tools=[ptools.parse_meeting_info,ptools.plan_visit_order,ptools.build_meeting_plan]

structured_baseline:
	$(EXPT) evaluate.expt_name=structured_baseline \
	  ptools.meeting_planning.method=simulate

unstructured_baseline:
	$(EXPT) evaluate.expt_name=unstructured_baseline \
	  ptools.meeting_planning.method=prompt_llm \
	  ptools.meeting_planning.prompt_template_file=prompt_templates/zeroshot_meeting.txt


list:
	uv run python -m secretagent.cli.results list results/*

avg:
	uv run python -m secretagent.cli.results average --metric correct --metric cost results/*

pair:
	uv run python -m secretagent.cli.results pair --metric correct --metric cost results/*

compare:
	uv run python -m secretagent.cli.results compare-configs results/*

