status:
	uv run benchmark_status.py

hero_table:
	uv run hero_table.py --min-cols 3

latex_correct:
	uv run hero_table.py --min-cols 3 --format latex-correct > hero.tex

summarize:
	uv run hero_table.py --min-cols 3 --format plot-correct --x react --output summary/correct_react.png; open summary/correct_react.png
	uv run hero_table.py --min-cols 3 --format plot-correct --x pot --output summary/correct_pot.png; open summary/correct_pot.png
	uv run hero_table.py --min-cols 3 --format plot-correct --x structured_baseline --output summary/correct_structured_baseline.png; open summary/correct_structured_baseline.png
	uv run hero_table.py --min-cols 3 --format plot-correct --x unstructured_baseline --output summary/correct_unstructured_baseline.png; open summary/correct_unstructured_baseline.png
	uv run hero_table.py --min-cols 3 --format plot-correct --x structured_baseline --y unstructured_baseline --output summary/correct_baselines; open summary/correct_baselines.png

summarize-cost:
	uv run hero_table.py --min-cols 3 --format plot-cost --x react --output summary/correct_react.png; open summary/correct_react.png
	uv run hero_table.py --min-cols 3 --format plot-cost --x pot --output summary/correct_pot.png; open summary/correct_pot.png
	uv run hero_table.py --min-cols 3 --format plot-cost --x structured_baseline --output summary/correct_structured_baseline.png; open summary/correct_structured_baseline.png
	uv run hero_table.py --min-cols 3 --format plot-cost --x unstructured_baseline --output summary/correct_unstructured_baseline.png; open summary/correct_unstructured_baseline.png

check_models:
	uv run benchmark_config.py --check llm.model

count_ptools:
	uv run benchmark_config.py --strategy react --check '*.tools' --len
