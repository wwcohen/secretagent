#
# Oolong benchmark
#

# Quick run (10 examples, default config)
run:
	uv run expt.py run

# Full validation set (1300 examples)
run_full:
	uv run expt.py run dataset.n=1300 dataset.split=validation evaluate.expt_name=oolong_validation_full

# Zero-shot simulate (single LLM call)
zeroshot:
	uv run expt.py run evaluate.expt_name=oolong_zeroshot ptools.answer_question.method=simulate

# Quick test with tracing
quick_test:
	uv run expt.py quick_test dataset.n=1

#
# View results
#

list:
	uv run python -m secretagent.cli.results list results/*

avg:
	uv run python -m secretagent.cli.results average --metric correct --metric cost results/*

costs:
	uv run python -m secretagent.cli.costs llm_cache
