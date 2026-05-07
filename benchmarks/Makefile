# Global results operations — run from benchmarks/
SAR = uv run python -m secretagent.cli.results

# All exported results
ALL = results/bbh/sports_understanding/* results/rulearena/* results/natural_plan/*

# Per-benchmark shortcuts
SPORT = results/bbh/sports_understanding/*
NATURAL = results/natural_plan/*
RULE = results/rulearena/*

plot:
	$(SAR) plot --metric cost- --metric correct --output results_all.png $(ALL)

plot_sport:
	$(SAR) plot --metric cost- --metric correct --output plot_sport.png $(SPORT)

plot_natural:
	$(SAR) plot --metric cost- --metric correct --output plot_natural.png $(NATURAL)

plot_rule:
	$(SAR) plot --metric cost- --metric correct --output plot_rule.png $(RULE)
