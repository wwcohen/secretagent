#
# code quality checks
#

test:
	uv run pytest tests/ -v

benchmark_status:
	uv run scripts/benchmark_status.py --full

benchmark_tests:
	uv run pytest benchmarks/tests/test_sports_understanding.py -v
	uv run pytest benchmarks/tests/test_designbench.py -v
	uv run pytest benchmarks/tests/test_finqa.py -v
	uv run pytest benchmarks/tests/test_natural_plan.py -v
	uv run pytest benchmarks/tests/test_rulearena.py -v
	uv run pytest benchmarks/tests/test_tabmwp.py -v

lint:
	uv run ruff check src 

typehints:
	time uv run mypy src --ignore-missing-imports

wc:
	wc src/secretagent/*.py
	echo 
	cloc src/secretagent/*.py

prechecks: test lint typehints


srctree:
	tree -d -I '*results*' -I llm_cache -I 'learned*' -I 'recordings*' -I __pycache__  -I logs -I data

#
# examples
#

quickstart:
	uv run examples/quickstart.py

examples: quickstart
	uv run examples/sports_understanding.py
	uv run examples/sports_understanding_pydantic.py

