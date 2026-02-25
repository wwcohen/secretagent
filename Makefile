test:
	uv run pytest tests/test_config.py -v
	uv run pytest tests/test_record.py -v

quickstart:
	uv run examples/quickstart.py

examples: quickstart
	uv run examples/sports_understanding.py
