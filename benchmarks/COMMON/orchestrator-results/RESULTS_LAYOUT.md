# Results layout

```
orchestrator-results/
├── README.md
├── RESULTS_LAYOUT.md         (this file)
├── show_summary.sh           (run this — prints two tables to terminal)
├── existing_workflow/<bench>/...   # "handcrafted workflow" — orch_learner ran with seed_orchestrate=False
├── seed_from_ptools/<bench>/...    # "orchestrator-generated workflow" — seed_orchestrate=True
└── scripts/                  # all helper scripts + infra dirs (logs, train_dirs, etc.)
```

Each cell sits at `<class>/<bench>/` and contains:

```
<cell>/
├── results/                         # canonical results
│   └── <TS>.test_deepseek_v3_1/
│       ├── results.csv              # one row per case
│       ├── results.jsonl            # full per-case rollouts
│       └── config.yaml              # exact config used
├── archive/                         # older runs (pre-replay, smoke, etc.)
│   └── <TS>.test_deepseek_v3_1/
└── PROVENANCE.md                    # which run is canonical and why
```

## Variants inside `results/`

A few cells have multiple meaningful variants; their `results/` is split
into named subdirs:

### medcalc (under both classes)
```
medcalc/results/
├── learned_from_all_traces/
│   ├── overall/<TS>/    # full 1100-case test set
│   ├── formulas/<TS>/   # 660 cases (post-hoc filter: dosage/lab test/physical)
│   └── rules/<TS>/      # 380 cases (post-hoc filter: diagnosis/risk/severity)
├── learned_from_formula_traces/    # existing_workflow only
│   └── overall/<TS>/    # 660-case formula partition; orch_learner trained
│                        # only on formula categories
└── learned_from_rules_traces/      # existing_workflow only
    └── overall/<TS>/    # 380-case rules partition; orch_learner trained
                         # only on rules categories
```

### seed_from_ptools/rulearena_nba
```
rulearena_nba/results/
├── without_rulebook/<TS>/   # the orch_learner-generated seed as-is — NBA branch
│                            # passes only raw problem_text to extract_nba_params,
│                            # no CBA rules text or structured metadata
│                            # (acc 26.1%, ~507 input tokens/case)
└── with_rulebook/<TS>/      # manual patch: NBA branch builds the same rich
                             # query the existing-workflow's _build_nba_query
                             # constructs (rules + team/player/operations metadata)
                             # (acc 65.2%, ~22,696 input tokens/case)
```

The patched `ptools_evolved.py` for the with_rulebook variant lives at
`scripts/_patched_artifacts/seed_from_ptools_nba_fix/.../ptools_evolved.py`
with PATCH_NOTES.md alongside.

## Helper scripts (under `scripts/`)

- `run_test_eval.sh` — single-cell driver
- `run_parallel.sh` — multi-lane orchestrator
- `show_results.py` — summary table over canonical `results/` runs
- `show_summary.py` — backing impl for the top-level `show_summary.sh`
- `_replay_failed_cases.py` — surgical rerun of just exception-row cases
- `_resume_*.sh`, `_bump_*.sh` — watchers used during the main run
- `_reorganize.py`, `_reorganize_medcalc.py` — one-shot reorganization tools
- `_train_dirs/`, `_patched_artifacts/`, `_replay_patches/`, `_logs/` — infrastructure
