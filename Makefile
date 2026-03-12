test:
	uv run pytest tests/ -v

wc:
	wc src/secretagent/*.py

quickstart:
	uv run examples/quickstart.py

examples: quickstart
	uv run examples/sports_understanding.py
	uv run examples/sports_understanding_pydantic.py
