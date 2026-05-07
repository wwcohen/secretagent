status:
	uv run benchmark_status.py

hero_table:
	uv run hero_table.py --min-cols 3

learning_table:
	uv run learning_table.py

latex_correct:
	uv run hero_table.py --min-cols 3 --format latex-correct > hero.tex

latex_cost:
	uv run hero_table.py --min-cols 3 --format latex-cost > hero-cost.tex

latex_compact:
	uv run hero_table.py --min-cols 3 --format latex-compact > hero-compact.tex

latex_learning_correct:
	uv run learning_table.py  --format latex-correct > learning-correct.tex

latex_learning_cost:
	uv run learning_table.py  --format latex-cost > learning-cost.tex

summarize:
	uv run hero_table.py --min-cols 3 --format plot-correct --x react --output summary/correct_react.png; open summary/correct_react.png
	uv run hero_table.py --min-cols 3 --format plot-correct --x pot --output summary/correct_pot.png; open summary/correct_pot.png
	uv run hero_table.py --min-cols 3 --format plot-correct --x structured_baseline --output summary/correct_structured_baseline.png; open summary/correct_structured_baseline.png
	uv run hero_table.py --min-cols 3 --format plot-correct --x unstructured_thinking --output summary/correct_thinking; open summary/correct_thinking.png
	uv run hero_table.py --min-cols 3 --format plot-correct --x unstructured_baseline --output summary/correct_unstructured_baseline.png; open summary/correct_unstructured_baseline.png
	uv run hero_table.py --min-cols 3 --format plot-correct --x unstructured_thinking --output summary/correct_unstructured_thinking.png; open summary/correct_unstructured_thinking.png
	uv run hero_table.py --min-cols 3 --format plot-correct --x structured_baseline --y unstructured_baseline --output summary/correct_baselines; open summary/correct_baselines.png

pareto-all: pareto-nba pareto-murder pareto-tabwmp pareto-finqa pareto-sports

#NBA_LABELS=--points-of-interest 4 --spacer 0.1 --label m=DS3.a=G25.tk=Ind.wf:ReA m=GPT20B.a=DS3.tk=h.wf=h m=DS3.a=G25.wf=ub  m=DS31.a=GPT20B.hf=h
#NBA_LABELS=--points-of-interest 4 --spacer 0.1 --label 'ptool ind, DS3/Gem2.5'  'eng, GPT20B/DS3.1' 'eng, DS3.1/GPT20B'  'eng, GPT20B'
NBA_LABELS=--points-of-interest 4 --spacer 0.1 

pareto-nba:
	uv run optimize_plot.py rulearena_nba $(NBA_LABELS); open rulearena_nba_optimize.png 

MURDER_LABELS=--points-of-interest 3 --spacer 0.1 
pareto-murder:
	uv run optimize_plot.py musr_murder $(MURDER_LABELS); open musr_murder_optimize.png 

TABMWP_LABELS=--points-of-interest 3 --spacer 0.1 
pareto-tabwmp:
	uv run optimize_plot.py tabmwp $(TABMWP_LABELS); open tabmwp_optimize.png 

FINQA_LABELS=--points-of-interest 3 --spacer 0.1 
pareto-finqa:
	uv run optimize_plot.py finqa $(FINQA_LABELS); open finqa_optimize.png 

summarize-cost:
	uv run hero_table.py --min-cols 3 --format plot-cost --x react --output summary/cost_react.png --suppress tau_bench/retail; open summary/cost_react.png
	uv run hero_table.py --min-cols 3 --format plot-cost --x pot --output summary/cost_pot.png --suppress tau_bench/retail; open summary/cost_pot.png
	uv run hero_table.py --min-cols 3 --format plot-cost --x structured_baseline --output summary/cost_structured_baseline.png --suppress tau_bench/retail; open summary/cost_structured_baseline.png
	uv run hero_table.py --min-cols 3 --format plot-cost --x unstructured_baseline --output summary/cost_unstructured_baseline.png  --suppress tau_bench/retail; open summary/cost_unstructured_baseline.png

check_models:
	uv run benchmark_config.py --check llm.model

count_ptools:
	uv run benchmark_config.py --strategy react --check '*.tools' --len

check_splits:
	uv run benchmark_config.py --check dataset.split

amz_fig:
	uv run hero_table.py --min-cols 3 --format plot-correct --x react pot --output tmp-correct.png; open tmp-correct.png
	uv run hero_table.py --min-cols 3 --format plot-cost --x react pot --output tmp-cost.png; open tmp-cost.png
