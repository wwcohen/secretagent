#
# Run experiments - all on the validation data
#

# zero-shot structured queries - i.e. the old ptool LLM / PTP call
EVALUATOR = --evaluator ptools.DateUnderstandingEvaluator

basics: unstructured_baseline structured_baseline workflow pot react

# the hand-coded workflow
workflow:
	uv run python -m secretagent.cli.expt run --interface ptools.answer_date_question $(EVALUATOR) evaluate.expt_name=workflow \
	  ptools.answer_date_question.method=direct \
	  ptools.answer_date_question.fn=ptools.date_understanding_workflow

structured_baseline:
	uv run python -m secretagent.cli.expt run --interface ptools.answer_date_question $(EVALUATOR) evaluate.expt_name=structured_baseline \
	  ptools.answer_date_question.method=simulate

ORCH_TASK_DESC = "Answer a date understanding multiple-choice question. Extract the answer options and the background date facts from the input. For each fact, make a date inference (passing prior facts as context). Extract the question, answer it from the accumulated inferences, then match the answer to one of the options. Return the matching option letter in parentheses, e.g. '(A)'."

# orchestrated: LLM auto-generates a workflow composing all sub-tools
orchestrated:
	uv run python -m secretagent.cli.expt run --interface ptools.answer_date_question_orchestrated $(EVALUATOR) \
	  evaluate.expt_name=orchestrated \
	  echo.orchestrate=true \
	  orchestrate.model=together_ai/deepseek-ai/DeepSeek-V3.1 \
	  orchestrate.max_retries=3 \
	  ptools.answer_date_question.method=simulate \
	  ptools.answer_date_question_orchestrated.method=orchestrate \
	  ptools.answer_date_question_orchestrated.task_description=$(ORCH_TASK_DESC) \
	  ptools.answer_date_question_orchestrated.exclude=[answer_date_question]

# quick test of orchestrated on a single example
quick-test-orchestrated:
	uv run python -m secretagent.cli.expt quick-test --interface ptools.answer_date_question_orchestrated \
	  echo.orchestrate=true \
	  orchestrate.model=together_ai/deepseek-ai/DeepSeek-V3.1 \
	  orchestrate.max_retries=3 \
	  ptools.answer_date_question.method=simulate \
	  ptools.answer_date_question_orchestrated.method=orchestrate \
	  ptools.answer_date_question_orchestrated.task_description=$(ORCH_TASK_DESC) \
	  ptools.answer_date_question_orchestrated.exclude=[answer_date_question]

# zero-shot unstructured queries with a vanilla prompt
unstructured_baseline:
	uv run python -m secretagent.cli.expt run --interface ptools.answer_date_question $(EVALUATOR) evaluate.expt_name=unstructured_baseline \
	  ptools.answer_date_question.method=direct \
	  ptools.answer_date_question.fn=ptools.zeroshot_unstructured_workflow

# program of thought
pot:
	uv run python -m secretagent.cli.expt run --interface ptools.answer_date_question $(EVALUATOR) evaluate.expt_name=pot \
	  ptools.answer_date_question.method=program_of_thought \
	  ptools.answer_date_question.tools=[ptools.extract_options,ptools.extract_date_facts,ptools.extract_question,ptools.make_inference,ptools.answer_question,ptools.match_option]

# ReAct using simulate_pydantic (which runs ReAct if there are tools),
# wrapped with extract_option_letter so the final output is the bare letter.
react:
	uv run python -m secretagent.cli.expt run --interface ptools.answer_date_question $(EVALUATOR) evaluate.expt_name=react \
	  ptools.answer_date_question.method=direct \
	  ptools.answer_date_question.fn=ptools.date_understanding_react_workflow \
	  ptools.react_answer_date_question.method=simulate_pydantic \
	  ptools.react_answer_date_question.tools=[ptools.extract_options,ptools.extract_date_facts,ptools.extract_question,ptools.make_inference,ptools.answer_question,ptools.match_option]

# quick test of react on a single example
quick-test-react:
	uv run python -m secretagent.cli.expt quick-test --interface ptools.answer_date_question \
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
