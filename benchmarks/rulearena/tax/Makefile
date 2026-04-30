#
# Run experiments - all on the validation data
#

.PHONY: basics unstructured_baseline structured_baseline workflow pot react \
        react_two_phase list avg pair compare plot costs resplit partition \
        record_react induce_ptools evaluate_ptool_inducer learn_ptool_pipeline \
        record_workflow codedistill evaluate_codedistill learn_codedistill_pipeline \
        orchestrated quick-test-orchestrated

DOTPAIRS ?=

basics: unstructured_baseline structured_baseline workflow pot react react_two_phase

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

# Two-phase react: simulate_pydantic extraction first, then react compute only.
react_two_phase:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_tax_answer --evaluator evaluator.TaxEvaluator evaluate.expt_name=react_two_phase \
	  ptools.compute_tax_answer.method=direct \
	  ptools.compute_tax_answer.fn=ptools.two_phase_react_workflow \
	  ptools.compute_tax_answer_react.method=simulate_pydantic \
	  ptools.compute_tax_answer_react.tools=[ptools.compute_tax_calculator] \
	  $(DOTPAIRS)

#
# Learning pipeline: ptool_inducer (record react → induce → evaluate)
#

RECORD_OPTS = dataset.split=train evaluate.record_details=true evaluate.result_dir=recordings

record_react:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_tax_answer --evaluator evaluator.TaxEvaluator evaluate.expt_name=react \
	  ptools.compute_tax_answer.method=simulate_pydantic \
	  "ptools.compute_tax_answer.tools=[ptools.extract_tax_params,ptools.compute_tax_calculator]" \
	  ptools.extract_tax_params.method=simulate \
	  $(RECORD_OPTS)

induce_ptools:
	uv run -m secretagent.cli.learn induce-ptools \
	  --interface compute_tax_answer \
	  --task-desc "Compute total US federal income tax owed from filled IRS forms" \
	  --trace-mode react \
	  --learned-dir learned \
	  recordings/*

evaluate_ptool_inducer:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_tax_answer --evaluator evaluator.TaxEvaluator evaluate.expt_name=ptool_inducer \
	  ptools.compute_tax_answer.method=simulate_pydantic \
	  ptools.compute_tax_answer.tool_module=__learned__ \
	  ptools.compute_tax_answer.learner=ptool_inducer \
	  "ptools.compute_tax_answer.tools=__all__" \
	  learn.train_dir=learned

learn_ptool_pipeline: record_react induce_ptools evaluate_ptool_inducer

#
# Learning pipeline: codedistill (record workflow → distill → evaluate)
#

record_workflow:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_tax_answer --evaluator evaluator.TaxEvaluator evaluate.expt_name=workflow \
	  ptools.compute_tax_answer.method=direct \
	  ptools.compute_tax_answer.fn=ptools.tax_workflow \
	  $(RECORD_OPTS)

codedistill:
	uv run -m secretagent.cli.learn codedistill \
	  --interface compute_tax_answer \
	  --learned-dir learned_codedistill \
	  recordings/*

evaluate_codedistill:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_tax_answer --evaluator evaluator.TaxEvaluator evaluate.expt_name=codedistill \
	  ptools.compute_tax_answer.method=learned_code \
	  ptools.compute_tax_answer.learner=codedistill \
	  ptools.compute_tax_answer.backoff=true \
	  learn.train_dir=learned_codedistill

learn_codedistill_pipeline: record_workflow codedistill evaluate_codedistill

#
# Orchestrated: LLM auto-generates a workflow composing all sub-tools
#

ORCH_TASK_DESC = "Compute total federal income tax owed from filled IRS forms. Extract filing status, income, deductions, and credits. Apply the correct tax brackets and rules. Return the total tax owed as a number."

orchestrated:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_tax_answer_orchestrated \
	  --evaluator evaluator.TaxEvaluator \
	  evaluate.expt_name=orchestrated \
	  echo.orchestrate=true \
	  orchestrate.model=together_ai/deepseek-ai/DeepSeek-V3.1 \
	  orchestrate.max_retries=3 \
	  ptools.compute_tax_answer.method=simulate \
	  ptools.compute_tax_answer_orchestrated.method=orchestrate \
	  "ptools.compute_tax_answer_orchestrated.task_description=$(ORCH_TASK_DESC)" \
	  "ptools.compute_tax_answer_orchestrated.exclude=[compute_tax_answer]"

quick-test-orchestrated:
	uv run python -m secretagent.cli.expt quick-test --interface ptools.compute_tax_answer_orchestrated \
	  echo.orchestrate=true \
	  orchestrate.model=together_ai/deepseek-ai/DeepSeek-V3.1 \
	  orchestrate.max_retries=3 \
	  ptools.compute_tax_answer.method=simulate \
	  ptools.compute_tax_answer_orchestrated.method=orchestrate \
	  "ptools.compute_tax_answer_orchestrated.task_description=$(ORCH_TASK_DESC)" \
	  "ptools.compute_tax_answer_orchestrated.exclude=[compute_tax_answer]"

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
