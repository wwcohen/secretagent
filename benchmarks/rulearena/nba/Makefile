#
# Run experiments - all on the validation data
#

.PHONY: basics unstructured_baseline structured_baseline workflow pot react \
        list avg pair compare plot costs resplit partition \
        record_react induce_ptools evaluate_ptool_inducer learn_ptool_pipeline \
        record_workflow codedistill evaluate_codedistill learn_codedistill_pipeline \
        orchestrated quick-test-orchestrated

DOTPAIRS ?=

basics: unstructured_baseline structured_baseline workflow pot react

# zero-shot unstructured queries with a vanilla prompt
# the prompt returns True/False which is parsed by _parse_verdict_answer
unstructured_baseline:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_nba_answer --evaluator evaluator.NbaEvaluator evaluate.expt_name=unstructured_baseline \
	  ptools.compute_nba_answer.method=direct \
	  ptools.compute_nba_answer.fn=ptools.unstructured_workflow \
	  $(DOTPAIRS)

# Same as unstructured_baseline but with a clean prompt that drops the
# "Analyze each operation step by step" CoT instruction.
# See conf/simplified_unstructured_baseline.yaml for the documented run config.
simplified_unstructured_baseline:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_nba_answer --evaluator evaluator.NbaEvaluator evaluate.expt_name=simplified_unstructured_baseline \
	  ptools.compute_nba_answer.method=direct \
	  ptools.compute_nba_answer.fn=ptools.unstructured_workflow \
	  ptools.zeroshot_nba.method=prompt_llm \
	  ptools.zeroshot_nba.prompt_template_file=prompt_templates/simplified_unstructured.txt \
	  ptools.zeroshot_nba.answer_pattern=null \
	  $(DOTPAIRS)

# zero-shot structured queries - the top-level stub is simulated by the LLM
structured_baseline:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_nba_answer --evaluator evaluator.NbaEvaluator evaluate.expt_name=structured_baseline \
	  ptools.compute_nba_answer.method=simulate \
	  $(DOTPAIRS)

# the hand-coded workflow: LLM extracts NbaResult via simulate_pydantic,
# then return float(verdict). No calculator - extraction IS the answer.
workflow:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_nba_answer --evaluator evaluator.NbaEvaluator evaluate.expt_name=workflow \
	  ptools.compute_nba_answer.method=direct \
	  ptools.compute_nba_answer.fn=ptools.nba_workflow \
	  $(DOTPAIRS)

# program of thoughts; inject_args keeps problem_text/rules_text as sandbox
# variables so the LLM doesn't re-transcribe rules into code literals.
# No tools - NBA has no calculator to call.
pot:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_nba_answer --evaluator evaluator.NbaEvaluator evaluate.expt_name=pot \
	  ptools.compute_nba_answer.method=program_of_thought \
	  ptools.compute_nba_answer.inject_args=true \
	  llm.max_tokens=16384 \
	  $(DOTPAIRS)

# ReAct using simulate_pydantic (which runs ReAct if there are tools).
# extract_nba_params overridden to `simulate` so pydantic-ai's agent-as-tool
# registration doesn't trip on a nested simulate_pydantic tool.
# Only extract tool - NBA has no calculator.
react:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_nba_answer --evaluator evaluator.NbaEvaluator evaluate.expt_name=react \
	  ptools.compute_nba_answer.method=simulate_pydantic \
	  ptools.compute_nba_answer.tools=[ptools.extract_nba_params] \
	  ptools.extract_nba_params.method=simulate \
	  $(DOTPAIRS)

#
# Learning pipeline: ptool_inducer (record react → induce → evaluate)
#

RECORD_OPTS = dataset.split=train evaluate.record_details=true evaluate.result_dir=recordings

record_react:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_nba_answer --evaluator evaluator.NbaEvaluator evaluate.expt_name=react \
	  ptools.compute_nba_answer.method=simulate_pydantic \
	  "ptools.compute_nba_answer.tools=[ptools.extract_nba_params]" \
	  ptools.extract_nba_params.method=simulate \
	  $(RECORD_OPTS)

induce_ptools:
	uv run -m secretagent.cli.learn induce-ptools \
	  --interface compute_nba_answer \
	  --task-desc "Determine whether NBA operations violate CBA salary-cap rules; identify the first violating operation and which team is responsible" \
	  --trace-mode react \
	  --learned-dir learned \
	  recordings/*

evaluate_ptool_inducer:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_nba_answer --evaluator evaluator.NbaEvaluator evaluate.expt_name=ptool_inducer \
	  ptools.compute_nba_answer.method=simulate_pydantic \
	  ptools.compute_nba_answer.tool_module=__learned__ \
	  ptools.compute_nba_answer.learner=ptool_inducer \
	  "ptools.compute_nba_answer.tools=__all__" \
	  learn.train_dir=learned

learn_ptool_pipeline: record_react induce_ptools evaluate_ptool_inducer

#
# Learning pipeline: codedistill (record workflow → distill → evaluate)
#

record_workflow:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_nba_answer --evaluator evaluator.NbaEvaluator evaluate.expt_name=workflow \
	  ptools.compute_nba_answer.method=direct \
	  ptools.compute_nba_answer.fn=ptools.nba_workflow \
	  $(RECORD_OPTS)

codedistill:
	uv run -m secretagent.cli.learn codedistill \
	  --interface compute_nba_answer \
	  --learned-dir learned_codedistill \
	  recordings/*

evaluate_codedistill:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_nba_answer --evaluator evaluator.NbaEvaluator evaluate.expt_name=codedistill \
	  ptools.compute_nba_answer.method=learned_code \
	  ptools.compute_nba_answer.learner=codedistill \
	  ptools.compute_nba_answer.backoff=true \
	  learn.train_dir=learned_codedistill

learn_codedistill_pipeline: record_workflow codedistill evaluate_codedistill

#
# Orchestrated: LLM auto-generates a workflow composing all sub-tools
#

ORCH_TASK_DESC = "Determine whether NBA team operations violate CBA salary-cap rules. Extract team situations, player contracts, and proposed operations. Analyze each operation against CBA rules. Return 1.0 if any violation exists, 0.0 if compliant."

orchestrated:
	uv run python -m secretagent.cli.expt run --interface ptools.compute_nba_answer_orchestrated \
	  --evaluator evaluator.NbaEvaluator \
	  evaluate.expt_name=orchestrated \
	  echo.orchestrate=true \
	  orchestrate.model=together_ai/deepseek-ai/DeepSeek-V3.1 \
	  orchestrate.max_retries=3 \
	  ptools.compute_nba_answer.method=simulate \
	  ptools.compute_nba_answer_orchestrated.method=orchestrate \
	  "ptools.compute_nba_answer_orchestrated.task_description=$(ORCH_TASK_DESC)" \
	  "ptools.compute_nba_answer_orchestrated.exclude=[compute_nba_answer]"

quick-test-orchestrated:
	uv run python -m secretagent.cli.expt quick-test --interface ptools.compute_nba_answer_orchestrated \
	  echo.orchestrate=true \
	  orchestrate.model=together_ai/deepseek-ai/DeepSeek-V3.1 \
	  orchestrate.max_retries=3 \
	  ptools.compute_nba_answer.method=simulate \
	  ptools.compute_nba_answer_orchestrated.method=orchestrate \
	  "ptools.compute_nba_answer_orchestrated.task_description=$(ORCH_TASK_DESC)" \
	  "ptools.compute_nba_answer_orchestrated.exclude=[compute_nba_answer]"

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
