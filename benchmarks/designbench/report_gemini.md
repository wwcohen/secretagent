# DesignBench — Gemini 3 Flash (unstructured)

Short report for **unstructured** VLM runs using **Gemini 3 Flash** (`gemini/gemini-3-flash-preview` via LiteLLM, `conf/unstructured_gemini_flash.yaml`). **Angular is omitted** here: the DesignBench Angular harness is fragile for model-only HTML (Material imports, `new.component.ts` shell, template typing), so we focus on **vanilla / React / Vue**.

## Environment

- **Model:** `gemini/gemini-3-flash-preview` (Google AI Studio / `GEMINI_API_KEY`)
- **Prompt:** `ptools.generate_code` with `prompt_mode: unstructured`, `output_mode: freeform`
- **Repo snapshot:** commit `2388640` (update if you regenerate this doc)
- **Visual eval:** enabled (`benchmark.skip_eval: false`) where runs completed

## Results summary

Means below are **per-case averages** over rows in each `results.csv` (missing metrics excluded from that column’s mean).

| Split   | Expt directory | Rows | Avg CLIP | Avg SSIM | Avg MAE | Total cost (USD) | Avg cost / case |
|---------|----------------|-----:|---------:|---------:|--------:|-------------------:|----------------:|
| Vanilla | `results/20260501.091139.unstructured_gemini3_flash_vanilla` | 120 | 0.773 | 0.727 | 55.03 | 1.444 | 0.0120 |
| React   | `results/20260501.100746.unstructured_gemini3_flash_react`   | 109 | 0.838 | 0.651 | 62.08 | 1.571 | 0.0144 |
| Vue     | `results/20260501.110553.unstructured_gemini3_flash_vue`     | 118 | 0.820 | 0.668 | 59.97 | 1.989 | 0.0169 |

**Paths:** all under `benchmarks/designbench/` (e.g. `…/results.csv`, `…/artifacts/`).

## Notes

- **CLIP** is the primary visual metric in these runs; SSIM / MAE come from the same eval pipeline when renders succeed.
- **Cost** is summed from per-row `cost` in `results.csv` (LiteLLM/Gemini where available); per-case average = total / row count.
- **Angular:** if you revisit it later, fix the DesignBench app shell (`new.component.ts` + Material / template typing) and keep `ptools.prepare_code_for_render` for `@scope/pkg` and `*ngFor` loosening when injecting HTML only.

## Re-run commands (unstructured Gemini)

```bash
cd benchmarks/designbench
for fw in vanilla react vue; do
  uv run python expt.py run --config-file conf/unstructured_gemini_flash.yaml \
    dataset.framework=$fw \
    evaluate.expt_name=unstructured_gemini3_flash_${fw}
done
```

## Structured + Gemini (recommended if you want “Gemini only”)

Use **`conf/structured_gemini_flash.yaml`**: same **Gemini 3 Flash** VLM stack as unstructured (`GEMINI_API_KEY`, `vlm.provider: gemini`), with **`prompt_mode: structured`** and **`output_mode: answer_tag`**.

```bash
cd benchmarks/designbench
for fw in vanilla react vue; do
  uv run python expt.py run --config-file conf/structured_gemini_flash.yaml \
    dataset.framework=$fw \
    evaluate.expt_name=structured_gemini3_flash_${fw}
done
```

## Structured baseline (Qwen, simulate prompt)

For **Together / Qwen** only, use **`conf/structured_baseline.yaml`**.

```bash
cd benchmarks/designbench
for fw in vanilla react vue; do
  uv run python expt.py run --config-file conf/structured_baseline.yaml \
    dataset.framework=$fw \
    evaluate.expt_name=structured_baseline_${fw}
done
```

**Note:** `expt.load_dataset` passes only `(reference_html, framework)` into `generate_code` so `Interface.format_args` matches the stub’s type hints (no stray `metadata` positional).

After runs finish:

```bash
uv run python -m secretagent.cli.results average --metric clip_similarity --metric ssim --metric mae --metric cost results/structured_gemini3_flash_*
# Qwen structured runs:
# uv run python -m secretagent.cli.results average --metric clip_similarity --metric ssim --metric mae --metric cost results/structured_baseline_*
```
