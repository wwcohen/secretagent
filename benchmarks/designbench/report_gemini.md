# DesignBench — Gemini 3 Flash

Summary of **Gemini 3 Flash** runs (`gemini/gemini-3-flash-preview`, `GEMINI_API_KEY` / LiteLLM). **Angular is omitted** (DesignBench Angular harness is brittle for HTML-only model output).

**Repo snapshot:** `aa8b8f25` (regenerate metrics after new runs).

**Where results live:** canonical copies under `benchmarks/COMMON/results/designbench/<vanilla|vue|react.js>/<timestamp>.<kind>/`. The same experiments are often mirrored under `benchmarks/designbench/results/` with a longer timestamp + `expt_name` in the folder name.

**Metrics:** Avg CLIP / SSIM / MAE are means over rows with a non-null value for that column. **Total $** is the sum of per-row `cost` (missing costs treated as 0). **$/case** is Total $ ÷ row count.

**Configs (Gemini variants):**

| Mode | Typical config |
|------|----------------|
| **Unstructured_baseline** | `conf/unstructured_gemini_flash.yaml` |
| **Structured_baseline** | `conf/structured_gemini_flash.yaml` |
| **ReAct** | `conf/react_gemini_echo_all_ptools.yaml` (`generate_code` method `react` + tools) |
| **Workflow** | `conf/refine_loop_gemini.yaml` (`propose_then_refine_loop`: propose → render/fix loop) |

COMMON directory suffixes (`.unstructured_baseline`, `.structured_baseline`, `.react`, `.workflow`) match the rows below.

---

## Vanilla

### Unstructured_baseline

| n | Avg CLIP | Avg SSIM | Avg MAE | Total $ | $/case |
|--:|---------:|---------:|--------:|--------:|-------:|
| 120 | 0.773 | 0.727 | 55.03 | 1.444 | 0.0120 |

**Directory:** `benchmarks/COMMON/results/designbench/vanilla/20260501.091139.unstructured_baseline/`

### Structured_baseline

| n | Avg CLIP | Avg SSIM | Avg MAE | Total $ | $/case |
|--:|---------:|---------:|--------:|--------:|-------:|
| 120 | 0.782 | 0.730 | 56.52 | 1.438 | 0.0120 |

**Directory:** `benchmarks/COMMON/results/designbench/vanilla/20260501.235701.structured_baseline/`  
(`expt_name`: `structured_gemini3_flash_vanilla_noleak`)

### ReAct

| n | Avg CLIP | Avg SSIM | Avg MAE | Total $ | $/case |
|--:|---------:|---------:|--------:|--------:|-------:|
| 120 | 0.749 | 0.717 | 60.93 | 9.230 | 0.0769 |

**Directory:** `benchmarks/COMMON/results/designbench/vanilla/20260502.141147.20260502.141144.react/`  
Mirror: `benchmarks/designbench/results/20260502.141147.20260502.141144.react_gemini3fw_vanilla/`

### Workflow

| n | Avg CLIP | Avg SSIM | Avg MAE | Total $ | $/case |
|--:|---------:|---------:|--------:|--------:|-------:|
| 120 | 0.793 | 0.724 | 57.89 | 13.451 | 0.1121 |

**Directory:** `benchmarks/COMMON/results/designbench/vanilla/20260504.133859.workflow/`  
(`expt_name`: `refine_loop_gemini_vanilla`)

---

## Vue

### Unstructured_baseline

| n | Avg CLIP | Avg SSIM | Avg MAE | Total $ | $/case |
|--:|---------:|---------:|--------:|--------:|-------:|
| 118 | 0.820 | 0.668 | 59.97 | 1.989 | 0.0169 |

**Directory:** `benchmarks/COMMON/results/designbench/vue/20260501.110553.unstructured_baseline/`

### Structured_baseline

| n | Avg CLIP | Avg SSIM | Avg MAE | Total $ | $/case |
|--:|---------:|---------:|--------:|--------:|-------:|
| 118 | 0.799 | 0.630 | 68.14 | 2.236 | 0.0190 |

**Directory:** `benchmarks/COMMON/results/designbench/vue/20260502.014433.structured_baseline/`  
(`expt_name`: `structured_gemini3_flash_vue_noleak`)

### ReAct

| n | Avg CLIP | Avg SSIM | Avg MAE | Total $ | $/case |
|--:|---------:|---------:|--------:|--------:|-------:|
| 118 | 0.772 | 0.665 | 67.54 | 13.329 | 0.1130 |

**Directory:** `benchmarks/COMMON/results/designbench/vue/20260502.141144.react/`  
Mirror: `benchmarks/designbench/results/20260503.180756.20260502.141144.react_gemini3fw_vue/`

### Workflow

| n | Avg CLIP | Avg SSIM | Avg MAE | Total $ | $/case |
|--:|---------:|---------:|--------:|--------:|-------:|
| 118 | 0.831 | 0.739 | 53.99 | 22.918 | 0.1942 |

**Directory:** `benchmarks/COMMON/results/designbench/vue/20260504.203008.workflow/`  
(`expt_name`: `refine_loop_gemini_vue`)

---

## React.js

### Unstructured_baseline

| n | Avg CLIP | Avg SSIM | Avg MAE | Total $ | $/case |
|--:|---------:|---------:|--------:|--------:|-------:|
| 109 | 0.838 | 0.651 | 62.08 | 1.571 | 0.0144 |

**Directory:** `benchmarks/COMMON/results/designbench/react.js/20260501.100746.unstructured_baseline/`

### Structured_baseline

| n | Avg CLIP | Avg SSIM | Avg MAE | Total $ | $/case |
|--:|---------:|---------:|--------:|--------:|-------:|
| 109 | 0.842 | 0.647 | 67.10 | 1.667 | 0.0153 |

**Directory:** `benchmarks/COMMON/results/designbench/react.js/20260502.004515.structured_baseline/`

### ReAct

| n | Avg CLIP | Avg SSIM | Avg MAE | Total $ | $/case |
|--:|---------:|---------:|--------:|--------:|-------:|
| 109 | 0.813 | 0.598 | 72.47 | 8.208 | 0.0753 |

**Directory:** `benchmarks/COMMON/results/designbench/react.js/20260502.141144.react/`  
A merged primary+retry snapshot also exists at `benchmarks/designbench/results/20260505.combined.react_gemini3fw_react_plus_retry/` (same row count and means within rounding).

### Workflow

**No usable visual metrics** in the checked-in snapshot: `benchmarks/COMMON/results/designbench/react.js/20260504.202238.workflow/results.csv` has rows but no CLIP/SSIM/MAE/cost columns populated (failed / partial run). Re-run with `conf/refine_loop_gemini.yaml`, `dataset.framework=react`, `evaluate.expt_name=refine_loop_gemini_react`, then refresh this section.

---

## Notes

- **CLIP** is the primary visual metric in these runs.
- **ReAct** and **Workflow** are much more expensive per case than one-shot unstructured/structured generation.
- **Qwen / Together** structured baseline uses `conf/structured_baseline.yaml` (not listed here; this doc is Gemini-focused).
- **`expt.load_dataset`** passes only `(reference_html, framework)` into `generate_code` so `Interface.format_args` matches the stub (no extra `metadata` positional).
