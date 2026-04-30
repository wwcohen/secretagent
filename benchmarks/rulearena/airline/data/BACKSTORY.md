Data from the RuleArena benchmark (Zhou et al., ACL 2025):

  https://github.com/SkyRiver-2000/RuleArena

Domain: American Airlines baggage fee calculation. Each problem gives a
passenger itinerary (class, route, bags with dimensions/weights) plus the
full AA fee rule document, and asks for the total cost (ticket + baggage
fees) as an integer dollar amount.

300 problems across 3 complexity levels (l0/l1/l2), controlling how many
interacting rules are needed.

Data pipeline (two stages):
1. `make prepare` from `benchmarks/rulearena/` — vendors raw .jsonl + fee
   tables + rules text from a RuleArena clone into `data/airline/`, with an
   initial 60/20/20 split per level.
2. `make resplit && make partition` from `benchmarks/rulearena/airline/` —
   resplit.py reshuffles to target sizes (test:100, train:150, valid:50)
   with stratified level balance; partition.py converts .jsonl to
   Dataset-format .json files using the Python calculator for ground truth.

Splits (random.seed(137), stratified by level):
- train: 150
- valid: 50
- test: 100

Ground truth is computed by a deterministic Python calculator
(calculators/airline.py) using author-provided parameters. Fee tables
are in data/fee_tables/.
