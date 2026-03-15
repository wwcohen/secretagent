test:
	uv run pytest tests/ -v

wc:
	wc src/secretagent/*.py

cloc:	
	cloc src/secretagent

quickstart:
	uv run examples/quickstart.py

examples: quickstart
	uv run examples/sports_understanding.py
	uv run examples/sports_understanding_pydantic.py

expt:
	time uv run benchmarks/sports_understanding/expt.py run

costs:
	uv run -m secretagent.cli.costs benchmarks/sports_understanding/llm_cache

