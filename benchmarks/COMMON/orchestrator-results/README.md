# Orchestrator Results

This directory keeps the orchestrator result summaries by workflow family. Non-MedCalc benchmarks retain their original sibling layout. MedCalc is split into paper-facing formula and rules partitions so it matches the sibling benchmark shape.

MedCalc paper-facing result sets:

- `existing_workflow/medcalc_formulas/results/20260504.025838.test_deepseek_v3_1`
- `existing_workflow/medcalc_rules/results/20260504.025838.test_deepseek_v3_1`
- `seed_from_ptools/medcalc_formulas/results/20260504.084524.test_deepseek_v3_1`
- `seed_from_ptools/medcalc_rules/results/20260504.084524.test_deepseek_v3_1`

Each selected result directory keeps:

- `results.csv`
- `results.jsonl`
- `config.yaml`
- `split_info.json`

Archived material is under `archive/20260506_medcalc_paper_reorg/`. That archive includes older top-level benchmark result buckets, backup copies of non-MedCalc benchmark summaries, the old nested MedCalc layout, full/overall MedCalc results, and old local orchestration scripts/logs.

The old `_train_dirs/` operational index is not kept at the paper-facing root because symlink-style indexes cause commit issues. Its target paths are recorded in `TRAIN_DIRS_MANIFEST.md`, and the old text-file index is archived under `archive/20260506_medcalc_paper_reorg/operational_manifests/`.
