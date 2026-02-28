test:
	uv run pytest tests/ -v

quickstart:
	uv run examples/quickstart.py

examples: quickstart
	uv run examples/sports_understanding.py
