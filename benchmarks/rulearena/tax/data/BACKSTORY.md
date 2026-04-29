Data from the RuleArena benchmark (Zhou et al., ACL 2025):

  https://github.com/SkyRiver-2000/RuleArena

Domain: US federal income tax computation. Each problem provides filled
IRS tax forms and asks for a specific tax line-item value as a dollar
amount (float).

300 problems across 3 complexity levels (l0/l1/l2), controlling how many
form sections and cross-references are needed.

Data pipeline (two stages):
1. `make prepare` from `benchmarks/rulearena/` — vendors raw .jsonl + Python
   tax modules from a RuleArena clone into `data/tax/`, with an initial
   60/20/20 split per level.
2. `make resplit && make partition` from `benchmarks/rulearena/tax/` —
   resplit.py reshuffles to target sizes (test:100, train:150, valid:50)
   with stratified level balance; partition.py converts .jsonl to
   Dataset-format .json files using the Python tax modules for ground truth.

Splits (random.seed(137), stratified by level):
- train: 150
- valid: 50
- test: 100

Ground truth is computed by deterministic Python tax modules
(data/structured_forms.py, data/micro_evaluation.py) using
author-provided form data.
