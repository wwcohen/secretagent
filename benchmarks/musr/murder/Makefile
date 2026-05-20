#
# Run experiments - all on the validation data
#

DOTPAIRS ?=

EXPT = uv run python -m secretagent.cli.expt
SAR = uv run python -m secretagent.cli.results

basics: unstructured_baseline structured_baseline workflow pot react

# the hand-coded workflow
workflow:
	$(EXPT) run evaluate.expt_name=workflow $(DOTPAIRS) \
	  ptools.answer_question.method=direct \
	  ptools.answer_question.fn=ptools.answer_question_workflow

# zero-shot structured queries
structured_baseline:
	$(EXPT) run evaluate.expt_name=structured_baseline $(DOTPAIRS) \
	  ptools.answer_question.method=simulate

# zero-shot unstructured queries with a vanilla prompt
unstructured_baseline:
	$(EXPT) run evaluate.expt_name=unstructured_baseline $(DOTPAIRS) \
	  ptools.answer_question.method=prompt_llm \
	  ptools.answer_question.prompt_template_file='../prompt_templates/simplified_unstructured.txt'

# program of thought
pot:
	$(EXPT) run evaluate.expt_name=pot $(DOTPAIRS) \
	  ptools.answer_question.method=program_of_thought \
	  ptools.answer_question.tools=__all__


# react
react:
	$(EXPT) run evaluate.expt_name=react $(DOTPAIRS) \
	  ptools.answer_question.method=simulate_pydantic \
	  ptools.answer_question.tools=__all__

CHECK = ?


plot:
	$(SAR) plot --metric cost- --metric correct results/*; open results_plot.png

list:
	$(SAR) list $(CHECK) results/*

avg:
	$(SAR) average --metric correct --metric cost $(CHECK) results/*

pair:
	$(SAR) pair --metric correct --metric cost $(CHECK) results/*

compare:
	$(SAR) compare-configs $(CHECK) results/*

#
# track costs so far
#

costs:
	uv run python -m secretagent.cli.costs llm_cache

