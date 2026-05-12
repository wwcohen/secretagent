#
# DesignBench benchmark helpers
#

CONFIG ?= conf/conf.yaml
N ?= 4
FRAMEWORK ?= vanilla
MODEL ?= together_ai/Qwen/Qwen3-VL-9B-Instruct
EXPT ?= designbench_ptool

model:
	uv run python expt.py run --config-file $(CONFIG) \
	  dataset.framework=$(FRAMEWORK) \
	  dataset.n=$(N) \
	  llm.model=$(MODEL) \
	  evaluate.expt_name=$(EXPT)_model

list:
	uv run python -m secretagent.cli.results list results/*

avg:
	uv run python -m secretagent.cli.results average --metric correct --metric clip_similarity --metric cost results/*

pair:
	uv run python -m secretagent.cli.results pair --metric correct --metric clip_similarity --metric cost results/*

compare:
	uv run python -m secretagent.cli.results compare-configs results/*
