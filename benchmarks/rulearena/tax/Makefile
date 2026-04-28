#
# Run experiments - all on the validation data
#

.PHONY: basics unstructured_baseline structured_baseline workflow pot react \
        list avg pair compare plot costs resplit partition

DOTPAIRS ?=

basics: unstructured_baseline structured_baseline workflow pot react

# zero-shot unstructured queries with a vanilla prompt
# the prompt returns a numeric string which is parsed to a float by parse_numeric_answer
unstructured_baseline:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_tax_answer --evaluator evaluator.TaxEvaluator evaluate.expt_name=unstructured_baseline \
	  ptools.compute_tax_answer.method=direct \
	  ptools.compute_tax_answer.fn=ptools.unstructured_workflow \
	  $(DOTPAIRS)

# zero-shot structured queries - the top-level stub is simulated by the LLM
structured_baseline:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_tax_answer --evaluator evaluator.TaxEvaluator evaluate.expt_name=structured_baseline \
	  ptools.compute_tax_answer.method=simulate \
	  $(DOTPAIRS)

# the hand-coded workflow
workflow:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_tax_answer --evaluator evaluator.TaxEvaluator evaluate.expt_name=workflow \
	  ptools.compute_tax_answer.method=direct \
	  ptools.compute_tax_answer.fn=ptools.tax_workflow \
	  $(DOTPAIRS)

# program of thoughts; inject_args keeps forms_text as a sandbox variable so
# the LLM doesn't re-transcribe forms into code literals
pot:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_tax_answer --evaluator evaluator.TaxEvaluator evaluate.expt_name=pot \
	  ptools.compute_tax_answer.method=program_of_thought \
	  ptools.compute_tax_answer.tools=[ptools.extract_tax_params,ptools.compute_tax_calculator] \
	  ptools.compute_tax_answer.inject_args=true \
	  llm.max_tokens=16384 \
	  $(DOTPAIRS)

# ReAct using simulate_pydantic (which runs ReAct if there are tools).
# extract_tax_params overridden to `simulate` so pydantic-ai's agent-as-tool
# registration doesn't trip on a nested simulate_pydantic tool.
react:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_tax_answer --evaluator evaluator.TaxEvaluator evaluate.expt_name=react \
	  ptools.compute_tax_answer.method=simulate_pydantic \
	  ptools.compute_tax_answer.tools=[ptools.extract_tax_params,ptools.compute_tax_calculator] \
	  ptools.extract_tax_params.method=simulate \
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

plot:
	uv run python -m secretagent.cli.results plot --metric cost- --metric correct $(CHECK) results/* --output plot_results.png

#
# track costs so far
#

costs:
	uv run python -m secretagent.cli.costs llm_cache

#
# Data preparation - resplit pools and rewrites .jsonl (destructive); partition
# builds Dataset-format .json files. Typical flow: resplit once, partition on demand.
#

resplit:
	uv run python data/resplit.py

partition:
	uv run python data/partition.py
