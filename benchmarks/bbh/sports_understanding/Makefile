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
	uv run python -m secretagent.cli.expt run --interface ptools.are_sports_in_sentence_consistent evaluate.expt_name=unstructured_baseline \
	  ptools.are_sports_in_sentence_consistent.method=direct \
	  ptools.are_sports_in_sentence_consistent.fn=ptools.zeroshot_unstructured_workflow \
	  $(DOTPAIRS)

# zero-shot structured queries - i.e. the old ptool LLM / PTP call
structured_baseline: 
	uv run python -m secretagent.cli.expt run --interface ptools.are_sports_in_sentence_consistent evaluate.expt_name=structured_baseline \
	  ptools.are_sports_in_sentence_consistent.method=simulate \
	  $(DOTPAIRS)

# the hand-coded workflow
workflow:
	uv run python -m secretagent.cli.expt run --interface ptools.are_sports_in_sentence_consistent evaluate.expt_name=workflow \
	  ptools.are_sports_in_sentence_consistent.method=direct \
	  ptools.are_sports_in_sentence_consistent.fn=ptools.sports_understanding_workflow \
	  $(DOTPAIRS)

# program of thoughts
pot:
	uv run python -m secretagent.cli.expt run --interface ptools.are_sports_in_sentence_consistent evaluate.expt_name=pot \
	  ptools.are_sports_in_sentence_consistent.method=program_of_thought \
	  ptools.are_sports_in_sentence_consistent.tools=[ptools.analyze_sentence,ptools.sport_for,ptools.consistent_sports] \
	  $(DOTPAIRS)

# ReAct using simulate_pydantic (which runs ReAct if there are tools)
react:
	uv run python -m secretagent.cli.expt run --interface ptools.are_sports_in_sentence_consistent evaluate.expt_name=react \
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

#
# Learning is a pipeline, documented below  
#

# 1) 'record' detailed traces of an implementation strategy, put them in recordings
#    Recordings are just like evaluations but keep some extra information around.
#

learn_pipeline: record_workflow learn_consistent_sports evaluate_learned_consistent_sports avg

RECORD_OPTS = dataset.split=train evaluate.record_details=true evaluate.result_dir=recordings

record_workflow:
	uv run python -m secretagent.cli.expt run --interface ptools.are_sports_in_sentence_consistent evaluate.expt_name=workflow \
	  ptools.are_sports_in_sentence_consistent.method=direct \
	  ptools.are_sports_in_sentence_consistent.fn=ptools.sports_understanding_workflow \
	  $(RECORD_OPTS)	

# 2) Then run the learner - right now that's a rote learner - for some
# interface.  A learner loads the recordings and saves stuff to a
# training directory, learned-dir, in this case to be filed under
# consistent_sports__rote

learn_consistent_sports:
	uv run python -m secretagent.cli.learn rote --interface consistent_sports --learned-dir learned recordings/*

# 3) Now we can configure the learned implementation 

evaluate_learned_consistent_sports:
	uv run python -m secretagent.cli.expt run --interface ptools.are_sports_in_sentence_consistent evaluate.expt_name=workflow_with_learning \
	  learn.train_dir=learned \
	  ptools.consistent_sports.method=learned_code \
	  ptools.consistent_sports.learner=rote \
	  ptools.consistent_sports.backoff=True \
	  ptools.are_sports_in_sentence_consistent.method=direct \
	  ptools.are_sports_in_sentence_consistent.fn=ptools.sports_understanding_workflow

#
# example of creating new ptools and then using them
#

# toy example: edit an existing list of ptools, store them 'learned',
# a directory of learned implementations

edit_ptools:
	uv run python -m secretagent.cli.learn edit-ptools --interface are_sports_in_sentence_consistent \
	  --ptool ptools.analyze_sentence --ptool ptools.sport_for --ptool ptools.consistent_sports \
	  --pattern Western --replacement Eastern \
	  --learned-dir learned recordings/*

# run reAct using all the tools in the module produced by 'cli.learn edit-ptools'

eval_edited_ptools:
	uv run python -m secretagent.cli.expt run --interface ptools.are_sports_in_sentence_consistent evaluate.expt_name=learned_ptool_react \
	  learn.train_dir=learned dataset.n=10\
	  ptools.are_sports_in_sentence_consistent.method=simulate_pydantic \
	    ptools.are_sports_in_sentence_consistent.tool_module=__learned__ \
	    ptools.are_sports_in_sentence_consistent.learner=ptool_editer\
	    ptools.are_sports_in_sentence_consistent.tools=__all__

