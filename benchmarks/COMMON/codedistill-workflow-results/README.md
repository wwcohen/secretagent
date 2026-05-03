# Class 2 — Workflow Codedistill Results

This directory holds the **paper-frozen Class 2 (workflow distill on hand-written
ptools) and Class 3 (workflow distill on induced ptools) results** for the
v4 / v4g experiments. See [docs/code_distillation_results_v2.md](../../../docs/code_distillation_results_v2.md)
for the headline result table and analysis, and [docs/code_distillation_results_v2_gemini.md](../../../docs/code_distillation_results_v2_gemini.md)
for the v4g (Gemini-as-learner) version.

## What's here

```
<bench>/                              # 16 sub-benchmarks
  learned_class2_v4/                  # Opus: top-level workflow distilled
    <ts>.<top_iface>__workflow_distill/
      learned.py                      # generated workflow function
      implementation.yaml             # method=learned_code, learner=workflow_distill, backoff=true
      data.json
      source_configs/
  learned_class2_v4g/                 # Gemini variant
  # for musr (object/team/murder share `answer_question_workflow` iface name):
  learned_class2_v4_object/           # Opus per-task to avoid same-iface collision
  learned_class2_v4_team/
  learned_class2_v4_murder/
  learned_class2_v4g_object/  ...     # Gemini per-task
  learned_class3_v4/                  # Class 3 (workflow on induced ptools)
    <ts>.<top>__ptool_inducer/
      learned_ptools.py               # induced ptool stubs
    <ts>.<top>__codedistill/          # codedistill on induced ptools
    <ts>.<top>__workflow_distill/     # workflow over induced
    codedistill_config.yaml           # merged
  val_results_full/                   # *_class2v4 / *_class2v4g / *_class3v4 results
  test_results_full/                  # test split results
```

## Method (Class 2)

```bash
uv run -m secretagent.cli.learn workflow-codedistill \
  --interface <top_iface> --dataset-file data/<bench>_train.json \
  --output-field <gold_field> \
  --tool-module <ptools_module> --conf-file conf/<bench>.yaml \
  --reference-file <other_bench>/ptools.py \
  --trace-dir recordings_full/<latest>.<bench>_train_full \
  --learned-dir learned_class2_v4 --model claude-opus-4-6 \
  --backoff true --backoff-method simulate
```

For Gemini: `--model gemini/gemini-3.1-pro-preview` and `--learned-dir learned_class2_v4g`.

For musr where 3 sub-tasks share the same top-level interface name
(`answer_question_workflow`), use separate output dirs (`_object`/`_team`/`_murder`)
to avoid distill-time collision.

## Method (Class 3 — workflow on induced ptools)

Two-stage:

```bash
# Stage A: induce ptools from ReAct trace + codedistill them
uv run -m secretagent.cli.learn codedistill-induced-ptools \
  --interface <top> --task-desc "<one-line>" --trace-mode react --only-correct \
  --learned-dir learned_class3_v4 --model claude-opus-4-6 \
  --expt-cmd "uv run python expt.py run --config-file conf/<bench>_react.yaml dataset.n=100" \
  --cwd "$ROOT/benchmarks/<bench>" \
  recordings_full/<latest>.<bench>_react_train_full

# Stage B: distill the workflow that uses the induced ptools
uv run -m secretagent.cli.learn workflow-codedistill \
  --interface <top> --dataset-file data/<bench>_train.json \
  --tool-module <learned_class3_v4/<ts>.<top>__ptool_inducer/learned_ptools.py> \
  --learned-dir learned_class3_v4 --model claude-opus-4-6 --backoff true
```

## Headline numbers

See [REPRODUCE.md](REPRODUCE.md) for end-to-end reproduce commands.
Full results in [docs/code_distillation_results_v2.md](../../../docs/code_distillation_results_v2.md)
and [docs/code_distillation_results_v2_gemini.md](../../../docs/code_distillation_results_v2_gemini.md).
