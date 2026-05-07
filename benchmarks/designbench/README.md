# DesignBench Benchmark

DesignBench evaluates code generation quality for UI reconstruction tasks.
This benchmark loads DesignBench HTML/metadata examples, generates frontend code,
and (optionally) computes visual similarity metrics against reference screenshots.

## Prerequisites

- From the project root, run `uv sync`.
- Ensure a local DesignBench repository is available:
  - Default lookup path is `../DesignBench` (sibling of this repo), or
  - set `designbench.root=/absolute/path/to/DesignBench` in config/CLI overrides.
- Install DesignBench evaluator dependencies in your environment if you want visual metrics (`clip_similarity`, `mae`, `ssim`).

## Quick Start

```bash
cd secretagent
uv sync
cd benchmarks/designbench
```

Run with default config:

```bash
uv run python expt.py run
```

Run a small sample:

```bash
uv run python expt.py run dataset.n=10
```

Switch framework (model stays from `conf/conf.yaml`):

```bash
uv run python expt.py run dataset.framework=react
```

Skip visual evaluation (generation only):

```bash
uv run python expt.py run benchmark.skip_eval=true
```

## Makefile Helpers

- `make model` - run one experiment with configurable `FRAMEWORK`, `MODEL`, `N`, and `EXPT`.
- `make list` - list available result directories.
- `make avg` - summarize means for `correct`, `clip_similarity`, and `cost`.
- `make pair` - paired statistical comparisons.
- `make compare` - compare config differences across runs.

## Key Config Options

| Key | Default | Description |
|---|---|---|
| `llm.model` | `Qwen/Qwen3-VL-8B-Instruct` | Model passed to litellm |
| `evaluate.expt_name` | `designbench_ptool` | Run tag used in output directory names |
| `evaluate.result_dir` | `results` | Where run outputs are stored |
| `evaluate.entry_point` | `generate_code` | Interface called for each case |
| `dataset.framework` | `vanilla` | Input split/framework (`vanilla`, `react`, `vue`, `angular`) |
| `dataset.n` | unset | Optional max number of examples |
| `dataset.max_reference_chars` | `20000` | Prompt truncation limit for long HTML |
| `benchmark.output_framework` | `null` | Output rendering framework override |
| `benchmark.skip_eval` | `false` | Disable screenshot rendering + visual metrics |

## Outputs

Each run writes to `results/<timestamp>.<expt_name>/`:

- `results.csv` - tabular metrics and artifact paths.
- `results.jsonl` - per-example full rows.
- `config.yaml` - resolved configuration snapshot.
- `artifacts/` - generated code, screenshots, and per-item metric JSON files.

