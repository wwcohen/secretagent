# MedCalc Class 1 Stratified-100 DeepSeek Runs From Caches

Run only DeepSeek V3.1 inference on the frozen 100-example stratified
MedCalc test slice.

Opus and Gemini are not runtime models for these evaluations. They are only
the already-created Class 1 codedistill artifact directories:

- `benchmarks/COMMON/codedistill-ptools-results/medcalc/learned_opus`
- `benchmarks/COMMON/codedistill-ptools-results/medcalc/learned_gemini`

Runtime LLM for all simulate/backoff calls:

```text
together_ai/deepseek-ai/DeepSeek-V3.1
```

Dataset settings:

```text
dataset.split=test
dataset.stratified=true
dataset.n=100
dataset.shuffle_seed=42
```

## Run Directory

Run both commands from:

```bash
cd /mnt/d/Aditya/CMU/Research/William_Cohen_Group/Codebase/secretagent/benchmarks/medcalc
```

Common paths:

```bash
ROOT=/mnt/d/Aditya/CMU/Research/William_Cohen_Group/Codebase/secretagent
OUT=$ROOT/benchmarks/COMMON/codedistill-ptools-results/medcalc/test_results_full/overall
```

## Opus-Cache DeepSeek Test Run

```bash
uv run python expt.py run --config-file conf/workflow.yaml \
  llm.model=together_ai/deepseek-ai/DeepSeek-V3.1 \
  llm.max_tokens=65536 \
  cachier.cache_dir=llm_cache \
  cachier.enable_caching=true \
  evaluate.result_dir=$OUT \
  evaluate.expt_name=medcalc_test_full_class1_opus_cache \
  evaluate.entry_point=calculate_medical_value \
  evaluate.record_details=true \
  dataset.split=test \
  dataset.stratified=true \
  dataset.n=100 \
  dataset.shuffle_seed=42 \
  ptools.identify_calculator.method=learned_code \
  ptools.identify_calculator.learner=codedistill \
  ptools.identify_calculator.backoff=true \
  ptools.extract_calculator_values.method=learned_code \
  ptools.extract_calculator_values.learner=codedistill \
  ptools.extract_calculator_values.backoff=true \
  learn.train_dir=$ROOT/benchmarks/COMMON/codedistill-ptools-results/medcalc/learned_opus
```

## Gemini-Cache DeepSeek Test Run

```bash
uv run python expt.py run --config-file conf/workflow.yaml \
  llm.model=together_ai/deepseek-ai/DeepSeek-V3.1 \
  llm.max_tokens=65536 \
  cachier.cache_dir=llm_cache \
  cachier.enable_caching=true \
  evaluate.result_dir=$OUT \
  evaluate.expt_name=medcalc_test_full_class1_gemini_cache \
  evaluate.entry_point=calculate_medical_value \
  evaluate.record_details=true \
  dataset.split=test \
  dataset.stratified=true \
  dataset.n=100 \
  dataset.shuffle_seed=42 \
  ptools.identify_calculator.method=learned_code \
  ptools.identify_calculator.learner=codedistill \
  ptools.identify_calculator.backoff=true \
  ptools.analyze_scoring_conditions.method=learned_code \
  ptools.analyze_scoring_conditions.learner=codedistill \
  ptools.analyze_scoring_conditions.backoff=true \
  learn.train_dir=$ROOT/benchmarks/COMMON/codedistill-ptools-results/medcalc/learned_gemini
```

## Expected Output

```text
benchmarks/COMMON/codedistill-ptools-results/medcalc/test_results_full/overall/
  <TS>.medcalc_test_full_class1_opus_cache/
  <TS>.medcalc_test_full_class1_gemini_cache/
```

Each run should contain:

- `config.yaml`
- `results.csv`
- `results.jsonl`

## Verification

Run from repo root:

```bash
cd /mnt/d/Aditya/CMU/Research/William_Cohen_Group/Codebase/secretagent
uv run python - <<'PY'
import pandas as pd
import yaml
from pathlib import Path

base = Path("benchmarks/COMMON/codedistill-ptools-results/medcalc/test_results_full/overall")
for run in sorted(base.glob("*.medcalc_test_full_class1_*_cache")):
    cfg = yaml.safe_load((run / "config.yaml").read_text())
    df = pd.read_csv(run / "results.csv")
    print(run.name)
    print("  model:", cfg["llm"]["model"])
    print("  split:", cfg["dataset"]["split"])
    print("  stratified:", cfg["dataset"]["stratified"])
    print("  n:", cfg["dataset"]["n"])
    print("  train_dir:", cfg["learn"]["train_dir"])
    print("  rows:", len(df), "acc:", df["correct"].mean())
PY
```

Acceptance criteria:

- Opus-cache and Gemini-cache runs both exist.
- `llm.model` is `together_ai/deepseek-ai/DeepSeek-V3.1` in both configs.
- No Opus/Gemini API model is used during evaluation.
- `learn.train_dir` points to the corresponding cached learned artifacts.
- Each `results.csv` has exactly 100 rows.
