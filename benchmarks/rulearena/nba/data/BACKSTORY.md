Data from the RuleArena benchmark (Zhou et al., ACL 2025):

  https://github.com/SkyRiver-2000/RuleArena

Domain: NBA Collective Bargaining Agreement salary cap compliance. Each
problem describes a proposed trade with player salaries and team cap
figures, asks whether the trade is compliant (True/False) under CBA rules.

216 problems across 3 complexity levels (l0/l1/l2).

Data pipeline (two stages):
1. `make prepare` from `benchmarks/rulearena/` — vendors raw .jsonl + rules
   text from a RuleArena clone into `data/nba/`, with an initial 60/20/20
   split per level.
2. `make resplit && make partition` from `benchmarks/rulearena/nba/` —
   resplit.py reshuffles to target sizes (test:46, train:128, valid:42)
   with stratified level balance; partition.py converts .jsonl to
   Dataset-format .json files using author-labeled ground truth.

Splits (random.seed(137), stratified by level):
- train: 128
- valid: 42
- test: 46

Note: no deterministic Python calculator for NBA (binary classification,
ground truth is author-labeled). Class distribution is heavily skewed
positive (~86% True in valid split), so F1 macro is more informative
than accuracy.
