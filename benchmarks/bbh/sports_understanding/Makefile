#
# Run experiments - all on the validation data
#

DOTPAIRS ?=

basics: unstructured_baseline structured_baseline workflow pot react

plot:
	sar plot --metric cost- --metric correct results/*; open plot_results.png

# zero-shot unstructured queries with a vanilla prompt
# technically the vanilla prompt returns a string, which is then coerced to a bool
# in the second stage of a very simple workflow

unstructured_baseline: 
	uv run python -m secretagent.cli.expt run evaluate.expt_name=unstructured_baseline \
	  ptools.are_sports_in_sentence_consistent.method=direct \
	  ptools.are_sports_in_sentence_consistent.fn=ptools.zeroshot_unstructured_workflow \
	  $(DOTPAIRS)

# zero-shot structured queries - i.e. the old ptool LLM / PTP call
structured_baseline: 
	uv run python -m secretagent.cli.expt run evaluate.expt_name=structured_baseline \
	  ptools.are_sports_in_sentence_consistent.method=simulate \
	  $(DOTPAIRS)

# the hand-coded workflow
workflow:
	uv run python -m secretagent.cli.expt run evaluate.expt_name=workflow \
	  ptools.are_sports_in_sentence_consistent.method=direct \
	  ptools.are_sports_in_sentence_consistent.fn=ptools.sports_understanding_workflow \
	  $(DOTPAIRS)

# program of thoughts
pot:
	uv run python -m secretagent.cli.expt run evaluate.expt_name=pot \
	  ptools.are_sports_in_sentence_consistent.method=program_of_thought \
	  ptools.are_sports_in_sentence_consistent.tools=[ptools.analyze_sentence,ptools.sport_for,ptools.consistent_sports] \
	  $(DOTPAIRS)

# ReAct using simulate_pydantic (which runs ReAct if there are tools)
react:
	uv run python -m secretagent.cli.expt run evaluate.expt_name=react \
	  ptools.are_sports_in_sentence_consistent.method=simulate_pydantic \
	  ptools.are_sports_in_sentence_consistent.tools=[ptools.analyze_sentence,ptools.sport_for,ptools.consistent_sports] \
	  $(DOTPAIRS)

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

