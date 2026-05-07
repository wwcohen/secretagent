# Results Layout

```
orchestrator-induced-ptools-results/
├── README.md
├── RESULTS_LAYOUT.md
├── show_summary.sh
├── medcalc/formulas/results.csv
├── medcalc/rules/results.csv
├── musr/test_results_full/...
├── natural_plan/test_results_full/...
├── rulearena/test_results_full/...
└── scripts/
```

Canonical non-MedCalc cells sit at `<bench>/test_results_full/<run>/`,
matching the COMMON codedistill result shape:

```
<bench>/
└── test_results_full/
    └── <TS>.<subbench>_test_full_orch_induced_seed_ptools/
        ├── results.csv
        ├── results.jsonl
        └── config.yaml
```

Condition:

- `orch_induced_seed_ptools`: orchestrator-generated workflow + induced seed ptools

Canonical rows:

- `medcalc_formulas`
- `medcalc_rules`
- `musr_murder`
- `musr_object`
- `musr_team`
- `natplan_meeting`
- `natplan_trip`
- `rulearena_nba`

MedCalc is reported as `medcalc/formulas/results.csv` and
`medcalc/rules/results.csv`. The mixed `medcalc/overall/results.csv` file is
preserved but intentionally excluded from the headline summary table.

Source benchmark-local final eval directories:

- `benchmarks/musr/test_results_full/20260505.034352.musr_murder_induced_seed_ptools_deepseek_v3_1`
- `benchmarks/musr/test_results_full/20260505.042822.musr_object_induced_seed_ptools_deepseek_v3_1`
- `benchmarks/musr/test_results_full/20260505.061622.musr_team_induced_seed_ptools_deepseek_v3_1`
- `benchmarks/natural_plan/test_results_full/20260505.091232.natplan_meeting_induced_seed_ptools_deepseek_v3_1`
- `benchmarks/natural_plan/test_results_full/20260505.091654.natplan_trip_induced_seed_ptools_deepseek_v3_1`
- `benchmarks/rulearena/test_results_full/20260505.092056.rulearena_nba_induced_seed_ptools_deepseek_v3_1`

The learner outputs are not duplicated here. They remain in each benchmark's
`results/orchestration_learner/*.orch_learner/` directories; the final evolved
workflows are the `ptools_evolved.py` files inside those learner dirs.

The old `_train_dirs/induced_seed_from_ptools` symlink index under
`orchestrator-results` was only used to locate learner run dirs during final
eval. No canonical result depends on that symlink index after these test runs
have been copied here.
