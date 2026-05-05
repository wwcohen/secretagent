# seed_from_ptools/medcalc

## results/

### learned_from_all_traces/
- `learned_from_all_traces/formulas/20260504.084524.test_deepseek_v3_1/` -- n=660, acc=80.15%
- `learned_from_all_traces/overall/20260504.084524.test_deepseek_v3_1/` -- n=1100, acc=71.36%
- `learned_from_all_traces/rules/20260504.084524.test_deepseek_v3_1/` -- n=380, acc=52.11%

## What 'learned from X traces' means

- **all_traces**: orch_learner trained on the full medcalc training set
  (mixed formula + rule categories). One workflow handles every case.
- **formula_traces** *(existing_workflow only)*: orch_learner ran with
  `seed_orchestrate=False` against `induced_orch_formula.yaml`, training
  on only the formula categories (dosage, lab test, physical). The
  `overall/` test set is the 660-case formula partition of medcalc test.
- **rules_traces** *(existing_workflow only)*: orch_learner ran with
  `seed_orchestrate=False` against `induced_orch_rule.yaml`, training on
  only the rules categories (diagnosis, risk, severity). The `overall/`
  test set is the 380-case rules partition of medcalc test.

The `formulas/` and `rules/` subdirs under `learned_from_all_traces/`
are post-hoc category filters of the 1100-case `overall/` run, so they
are directly comparable in case count to the per-trace runs above.
