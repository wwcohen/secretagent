# Archive: 20260506 MedCalc Paper Reorg

This archive was created while reorganizing `benchmarks/COMMON/orchestrator-results` around the MedCalc paper-facing rules/formulas results.

Contents:

- `root_result_buckets/`: old top-level aggregate benchmark result buckets (`medcalc`, `musr`, `natural_plan`, `rulearena`).
- `old_medcalc_layout/`: previous nested MedCalc layout, including full/overall results and non-selected trace-specific result groupings.
- `other_benchmark_summaries/`: backup copies of non-MedCalc summaries. These were restored to the live `existing_workflow/` and `seed_from_ptools/` sibling layout after the MedCalc-only cleanup was corrected.
- `old_orchestrator_scripts/`: old scripts, logs, patched artifacts, replay patches, and train-dir indexes that were local to the old results bundle.
- `operational_manifests/`: old operational train-dir index files moved out of the paper-facing root to avoid symlink-style commit issues.

Nothing was deleted during the reorg; selected MedCalc rules/formulas results were copied into the clean paper-facing layout before the old layout was moved here.
