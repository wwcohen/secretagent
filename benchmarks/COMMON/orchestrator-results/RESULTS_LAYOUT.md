# Results layout

```
orchestrator-results/
├── README.md
├── RESULTS_LAYOUT.md         (this file)
├── show_summary.sh           (run this — prints two tables to terminal)
├── medcalc/test_results_full/...       # canonical COMMON-style test results
├── musr/test_results_full/...
├── natural_plan/test_results_full/...
├── rulearena/test_results_full/...
├── existing_workflow/<bench>/...   # preserved legacy/provenance layout
├── seed_from_ptools/<bench>/...    # preserved legacy/provenance layout
└── scripts/                  # all helper scripts + infra dirs (logs, train_dirs, etc.)
```

## Canonical layout

Canonical cells sit at `<bench>/test_results_full/<run>/`, matching the
COMMON codedistill result shape:

```
<bench>/
└── test_results_full/
    ├── <TS>.<subbench>_test_full_orch_existing_workflow/
    │   ├── results.csv
    │   ├── results.jsonl
    │   ├── config.yaml
    │   └── run_summary.json  # where produced by the benchmark
    └── <TS>.<subbench>_test_full_orch_seed_from_ptools/
        ├── results.csv
        ├── results.jsonl
        └── config.yaml
```

Conditions:

- `orch_existing_workflow`: hand workflow + orchestrator-improved ptools
- `orch_seed_from_ptools`: orchestrator-generated workflow + orchestrator-improved ptools

Canonical rows:

- `medcalc_formulas`
- `medcalc_rules`
- `musr_murder`
- `musr_object`
- `musr_team`
- `natplan_calendar`
- `natplan_meeting`
- `natplan_trip`
- `rulearena_nba`

`medcalc` is intentionally split into formulas and rules. The overall mixed
run is preserved in the legacy tree but is not used for headline tables. The
canonical `rulearena_nba` seed result uses the default `without_rulebook` run;
the manual rulebook fix remains preserved but is excluded by default.

## Preserved legacy layout

The original layout remains in place. Each legacy cell sits at
`<class>/<bench>/` and contains:

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

### Variants inside legacy `results/`

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
- `show_results.py` — summary table over canonical `test_results_full/` runs
- `show_summary.py` — backing impl for the top-level `show_summary.sh`
- `_replay_failed_cases.py` — surgical rerun of just exception-row cases
- `_resume_*.sh`, `_bump_*.sh` — watchers used during the main run
- `_reorganize.py`, `_reorganize_medcalc.py` — one-shot reorganization tools
- `_train_dirs/`, `_patched_artifacts/`, `_replay_patches/`, `_logs/` — infrastructure

`_train_dirs` entries are portable `*.orch_learner` pointer files, not
committed directory symlinks. Each pointer file contains a repo-relative path to
the real learner output directory. `run_test_eval.sh` and the benchmark-level
induced-seed test runner resolve both pointer files and real symlinks.
