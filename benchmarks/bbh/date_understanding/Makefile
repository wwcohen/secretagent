#
# Run experiments - all on the validation data
#

# zero-shot structured queries - i.e. the old ptool LLM / PTP call
EVALUATOR = --evaluator ptools.DateUnderstandingEvaluator

basics: unstructured_baseline structured_baseline workflow pot react

# the hand-coded workflow
workflow:
	uv run python -m secretagent.cli.expt run $(EVALUATOR) evaluate.expt_name=workflow \
	  ptools.answer_date_question.method=direct \
	  ptools.answer_date_question.fn=ptools.date_understanding_workflow

structured_baseline:
	uv run python -m secretagent.cli.expt run $(EVALUATOR) evaluate.expt_name=structured_baseline \
	  ptools.answer_date_question.method=simulate

# zero-shot unstructured queries with a vanilla prompt
unstructured_baseline:
	uv run python -m secretagent.cli.expt run $(EVALUATOR) evaluate.expt_name=unstructured_baseline \
	  ptools.answer_date_question.method=direct \
	  ptools.answer_date_question.fn=ptools.zeroshot_unstructured_workflow

# program of thought
pot:
	uv run python -m secretagent.cli.expt run $(EVALUATOR) evaluate.expt_name=pot \
	  ptools.answer_date_question.method=program_of_thought \
	  ptools.answer_date_question.tools=[ptools.extract_options,ptools.extract_date_facts,ptools.extract_question,ptools.make_inference,ptools.answer_question,ptools.match_option]

# ReAct using simulate_pydantic (which runs ReAct if there are tools),
# wrapped with extract_option_letter so the final output is the bare letter.
react:
	uv run python -m secretagent.cli.expt run $(EVALUATOR) evaluate.expt_name=react \
	  ptools.answer_date_question.method=direct \
	  ptools.answer_date_question.fn=ptools.date_understanding_react_workflow \
	  ptools.react_answer_date_question.method=simulate_pydantic \
	  ptools.react_answer_date_question.tools=[ptools.extract_options,ptools.extract_date_facts,ptools.extract_question,ptools.make_inference,ptools.answer_question,ptools.match_option]

# quick test of react on a single example
quick-test-react:
	uv run python -m secretagent.cli.expt quick-test \
	  ptools.answer_date_question.method=direct \
	  ptools.answer_date_question.fn=ptools.date_understanding_react_workflow \
	  ptools.react_answer_date_question.method=simulate_pydantic \
	  ptools.react_answer_date_question.tools=[ptools.extract_options,ptools.extract_date_facts,ptools.extract_question,ptools.make_inference,ptools.answer_question,ptools.match_option]

#
# Summarize results of past experiments
#

CHECK ?=

list:
	uv run python -m secretagent.cli.results list $(CHECK) results/*

avg:
	uv run python -m secretagent.cli.results average --metric correct --metric cost $(CHECK) results/*

pair:
	uv run python -m secretagent.cli.results pair --metric correct --metric cost $(CHECK) results/*

compare:
	uv run python -m secretagent.cli.results compare-configs $(CHECK) results/*

#
# track costs so far
#

costs:
	uv run python -m secretagent.cli.costs llm_cache
