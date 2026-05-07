# Path to the RuleArena repo clone — only needed to run 'make prepare'
RULEARENA_DIR ?= ../../../RuleArena
DOTPAIRS ?=

.PHONY: prepare resplit_all partition_all data_all \
        bench_airline bench_nba bench_tax bench_all \
        pareto_airline pareto_nba pareto_tax pareto_all \
        list avg pair compare costs

#
# One-time data preparation (run before any experiment)
#

prepare:
	uv run python data/prepare.py $(RULEARENA_DIR)

#
# Per-domain data re-splitting and partitioning
# (run after prepare, or after changing split targets)
#

resplit_all:
	cd airline && make resplit
	cd nba && make resplit
	cd tax && make resplit

partition_all:
	cd airline && make partition
	cd nba && make partition
	cd tax && make partition

data_all: resplit_all partition_all

#
# Run experiments via bench.py infrastructure
#

bench_airline:
	uv run -m secretagent.cli.bench run rulearena_airline $(DOTPAIRS)

bench_nba:
	uv run -m secretagent.cli.bench run rulearena_nba $(DOTPAIRS)

bench_tax:
	uv run -m secretagent.cli.bench run rulearena_tax $(DOTPAIRS)

bench_all: bench_airline bench_nba bench_tax

#
# Pareto sweep (exhaustive: workflows x models per domain)
#

N_PARETO ?= 5
TIMEOUT_PARETO ?= 600

pareto_airline:
	uv run python run_pareto.py --domain airline --dataset-n $(N_PARETO) --timeout $(TIMEOUT_PARETO)

pareto_nba:
	uv run python run_pareto.py --domain nba --dataset-n $(N_PARETO) --timeout $(TIMEOUT_PARETO)

pareto_tax:
	uv run python run_pareto.py --domain tax --dataset-n $(N_PARETO) --timeout $(TIMEOUT_PARETO)

pareto_all: pareto_airline pareto_nba pareto_tax

#
# Cross-domain results summary (delegates to each domain's Makefile)
#

list:
	@echo "=== airline ==="
	cd airline && make list
	@echo "=== nba ==="
	cd nba && make list
	@echo "=== tax ==="
	cd tax && make list

avg:
	@echo "=== airline ==="
	cd airline && make avg
	@echo "=== nba ==="
	cd nba && make avg
	@echo "=== tax ==="
	cd tax && make avg

pair:
	@echo "=== airline ==="
	cd airline && make pair
	@echo "=== nba ==="
	cd nba && make pair
	@echo "=== tax ==="
	cd tax && make pair

compare:
	@echo "=== airline ==="
	cd airline && make compare
	@echo "=== nba ==="
	cd nba && make compare
	@echo "=== tax ==="
	cd tax && make compare

costs:
	@echo "=== airline ==="
	cd airline && make costs
	@echo "=== nba ==="
	cd nba && make costs
	@echo "=== tax ==="
	cd tax && make costs
