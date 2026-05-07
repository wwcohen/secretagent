This benchmark is based on the RuleArena dataset:

    Zhou, R., Hua, W., Pan, L., Cheng, S., Wu, X., Yu, E., & Wang, W. Y. (2025).
    RULEARENA: A Benchmark for Rule-Guided Reasoning with LLMs in Real-World Scenarios.
    Proceedings of the 63rd Annual Meeting of the Association for Computational Linguistics, 550-572.

Source repository: https://github.com/SkyRiver-2000/RuleArena

The benchmark covers three domains:
- airline: 300 problems across 3 complexity levels, American Airlines baggage fee calculation
- nba: 216 problems, NBA CBA salary cap rule compliance checking
- tax: 300 problems, US federal income tax computation

Problem data, rules text, airline fee tables, and tax Python modules are
vendored locally under data/{domain}/ and committed to this repo. You do
not need to clone RuleArena to run experiments.

To regenerate the local data from a fresh RuleArena clone (e.g. after an
upstream update), run from benchmarks/rulearena/:

    git clone https://github.com/SkyRiver-2000/RuleArena ../../../RuleArena
    make prepare

prepare.py splits each domain+level 60/20/20 into train/valid/test using
random.seed(137), preserving the original per-level instance indices.
