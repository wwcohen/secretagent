# Class 1 — Ptool Codedistill Results

This directory holds the **paper-frozen Class 1 (ptool codedistill) results**
for the opus / gemini experiments. See [docs/code_distillation_results_v2.md](../../../docs/code_distillation_results_v2.md)
for the headline result table and analysis, and [docs/code_distillation_results_v2_gemini.md](../../../docs/code_distillation_results_v2_gemini.md)
for the gemini (Gemini-as-learner) version.

## What's here

```
<bench>/                              # 16 sub-benchmarks
  learned_opus/                         # Opus-as-learner generated ptools (Apr 29)
    codedistill_config.yaml           # merged ENABLED list
    <ts>.<ptool>__codedistill/        # one dir per distilled ptool
      learned.py                      # generated Python implementation
      implementation.yaml             # method=learned_code, learner=codedistill, backoff=true
      data.json                       # train cases used
      source_configs/                 # source recording configs
  learned_gemini/                        # Gemini-as-learner (May 1)
  val_results_full/                   # end-to-end val on dataset.split=valid
    *_class1_opus/results.csv            # Opus c1 val results
    *_class1_gemini/results.csv           # Gemini c1 val results
  test_results_full/                  # end-to-end on dataset.split=test (May 2)
    *_class1_opus/  *_class1_gemini/
```

`benchmarks/<bench>/recordings_full/` (the train rollouts used as distill input)
stay in their per-bench location — they're intermediate inputs, not Class 1 outputs.

## Method

```bash
uv run -m secretagent.cli.learn codedistill-all \
  --learned-dir learned_opus --model claude-opus-4-6 \
  --max-wrong-rate 0.20 \
  benchmarks/<bench>/recordings_full/<ts>.<bench>_train_full
```

For Gemini variant, `--model gemini/gemini-3.1-pro-preview` and `--learned-dir learned_gemini`.

Generated CLI commands lived in `benchmarks/jerry/class1_iters/run_class1_v4_full_codedistill.sh`
and `run_class1_v4g_gemini.sh`.

## Headline numbers

See [REPRODUCE.md](REPRODUCE.md) for the per-benchmark reproduce commands.
For the full table see [code_distillation_results_v2.md](../../../docs/code_distillation_results_v2.md).
