#
# Run experiments - all on the validation data
#

EXPT = uv run python -m secretagent.cli.expt
INTERFACE = --interface ptools.answer_penguin_question
EVALUATOR = --evaluator ptools.PenguinsEvaluator
DOTPAIRS ?=

basics: unstructured_baseline structured_baseline workflow pot react

# the hand-coded workflow
workflow:
	$(EXPT) run $(INTERFACE) $(EVALUATOR) evaluate.expt_name=workflow $(DOTPAIRS) \
	  ptools.answer_penguin_question.method=direct \
	  ptools.answer_penguin_question.fn=ptools.penguins_workflow

# program of thought
pot:
	$(EXPT) run $(INTERFACE) $(EVALUATOR) evaluate.expt_name=pot $(DOTPAIRS) \
	  ptools.answer_penguin_question.method=program_of_thought \
	  ptools.answer_penguin_question.tools=[ptools.analyze_input,ptools.table_operation,ptools.answer_question,ptools.choose_response]

# ReAct using simulate_pydantic (which runs ReAct if there are tools),
# wrapped with extract_option_letter so the final output is the bare letter.
react:
	$(EXPT) run $(INTERFACE) $(EVALUATOR) evaluate.expt_name=react $(DOTPAIRS) \
	  ptools.answer_penguin_question.method=direct \
	  ptools.answer_penguin_question.fn=ptools.penguins_react_workflow \
	  ptools.react_answer_penguin_question.method=simulate_pydantic \
	  ptools.react_answer_penguin_question.tools=[ptools.analyze_input,ptools.table_operation,ptools.answer_question,ptools.choose_response]

# quick test of react on a single example
quick-test-react:
	$(EXPT) quick-test $(INTERFACE) \
	  ptools.answer_penguin_question.method=direct \
	  ptools.answer_penguin_question.fn=ptools.penguins_react_workflow \
	  ptools.react_answer_penguin_question.method=simulate_pydantic \
	  ptools.react_answer_penguin_question.tools=[ptools.analyze_input,ptools.table_operation,ptools.answer_question,ptools.choose_response]

# zero-shot structured queries
structured_baseline:
	$(EXPT) run $(INTERFACE) $(EVALUATOR) evaluate.expt_name=structured_baseline $(DOTPAIRS) \
	  ptools.answer_penguin_question.method=simulate

# zero-shot unstructured queries with a vanilla prompt
unstructured_baseline:
	$(EXPT) run $(INTERFACE) $(EVALUATOR) evaluate.expt_name=unstructured_baseline $(DOTPAIRS) \
	  ptools.answer_penguin_question.method=direct \
	  ptools.answer_penguin_question.fn=ptools.zeroshot_unstructured_workflow

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

costs:
	uv run python -m secretagent.cli.costs llm_cache
