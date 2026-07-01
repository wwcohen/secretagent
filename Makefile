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

#
# run the "basics" strategy grid from the repo root (see RUNNING.md)
#
# Wraps secretagent.cli.basics: runs model x task x strategy cells and writes
# results under overall_results/ (nothing is written into the task dirs).
#
# Knobs (set on the command line; unset = driver default):
#   MODELS      comma-separated llm.model ids
#   TASKS       comma-separated task ids (see `make basics-list`)
#   STRATEGIES  comma-separated strategy names
#   N           dataset.n (minibatch size); full pool if unset
#   OUT         output root (default: overall_results)
#   DOTPAIRS    extra dotlist overrides applied to every cell
#
# Examples:
#   make basics                                   # all tasks/strategies, default models, full pools
#   make basics MODELS=gemini/gemini-2.5-flash    # one model
#   make basics MODELS=gemini/gemini-3.1-pro-preview,gemini/gemini-2.5-flash-lite
#   make basics TASKS=bbh/penguins_in_a_table,natural_plan/trip
#   make basics STRATEGIES=structured_baseline,react
#   make basics N=25                              # 25-example minibatch
#   make basics-mini TASKS=natural_plan/trip      # quick N=10 pass on one task
#   make basics OUT=/tmp/scratch_results          # write results elsewhere
#   make basics DOTPAIRS="pydantic.retries=2 llm.timeout=180"
#   make basics-dry TASKS=bbh/sports_understanding  # preview commands, run nothing
#

BASICS     = uv run python -m secretagent.cli.basics
MODELS     ?=
TASKS      ?=
STRATEGIES ?=
N          ?=
OUT        ?=
DOTPAIRS   ?=

# set knobs become flags; unset ones are omitted so the driver default applies
_BASE = $(if $(MODELS),--models $(MODELS)) $(if $(TASKS),--tasks $(TASKS)) $(if $(STRATEGIES),--strategies $(STRATEGIES)) $(if $(OUT),--out $(OUT))

basics-help:
	@echo "run the basics grid from the repo root (see RUNNING.md):"
	@echo "  make basics-list      - show discovered tasks and their strategies"
	@echo "  make basics-dry       - print the assembled commands, run nothing"
	@echo "  make basics           - run the grid (full pools)"
	@echo "  make basics-mini      - quick pass (N=10 unless N= is set)"
	@echo "  make basics-summary   - print overall_results/summary.csv"
	@echo "  knobs: MODELS= TASKS= STRATEGIES= N= OUT= DOTPAIRS="

basics-list:
	$(BASICS) list

basics-dry:
	$(BASICS) run --dry-run $(_BASE) $(if $(N),--n $(N)) $(DOTPAIRS)

basics:
	$(BASICS) run $(_BASE) $(if $(N),--n $(N)) $(DOTPAIRS)

basics-mini:
	$(BASICS) run $(_BASE) --n $(if $(N),$(N),10) $(DOTPAIRS)

basics-summary:
	@uv run python -c "import pandas as pd; print(pd.read_csv('overall_results/summary.csv').to_string(index=False))" 2>/dev/null || echo "no overall_results/summary.csv yet"

