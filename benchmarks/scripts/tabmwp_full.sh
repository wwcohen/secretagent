#!/bin/bash
# tabmwp full pipeline: baseline + class 1, 2, 3
# Uses workflow_incontext.yaml as decomposable baseline (4 sub-ptools simulate
# + tabmwp_solve = direct: ptools.incontext_workflow).
set +e
ROOT="/Users/anon/Desktop/anon_research/secretagent"
TM="$ROOT/benchmarks/tabmwp"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
mkdir -p "$LOG_DIR"
set -a; source "$ROOT/.env"; set +a
CD_MODEL="${CD_MODEL:-claude-opus-4-6}"
DS="together_ai/deepseek-ai/DeepSeek-V3.1"
N_TRAIN=100
N_VAL=100

cd "$TM"

LOG="$LOG_DIR/tabmwp_master.log"
exec >> "$LOG" 2>&1

# ---------- Phase A: baseline recordings ----------
echo "[$(date)] === tabmwp Phase A start ==="

# A1: workflow_incontext train (uses train split, n=100)
uv run python expt.py run --config-file conf/workflow_incontext.yaml \
  "dataset.split=train" "dataset.n=$N_TRAIN" \
  "evaluate.expt_name=tabmwp_train_full" \
  evaluate.record_details=true evaluate.result_dir=recordings_full \
  "llm.model=$DS"
echo "[$(date)] tabmwp train_full rc=$?"

# A2: val baseline on dev1k
uv run python expt.py run --config-file conf/workflow_incontext.yaml \
  "dataset.split=dev1k" "dataset.n=$N_VAL" \
  "evaluate.expt_name=tabmwp_val_full_baseline" \
  evaluate.record_details=true evaluate.result_dir=val_results_full \
  "llm.model=$DS"
echo "[$(date)] tabmwp val_baseline rc=$?"

# A3: react train (for class 3)
if [ -f conf/react.yaml ]; then
  uv run python expt.py run --config-file conf/react.yaml \
    "dataset.split=train" "dataset.n=$N_TRAIN" \
    "evaluate.expt_name=tabmwp_react_train_full" \
    evaluate.record_details=true evaluate.result_dir=recordings_full \
    "llm.model=$DS"
  echo "[$(date)] tabmwp react_train rc=$?"
else
  echo "[$(date)] no react.yaml — class 3 will be skipped"
fi
echo "[$(date)] === Phase A done ==="

# ---------- Phase B: Class 1 codedistill-all ----------
REC=$(ls -d recordings_full/*."tabmwp_train_full" 2>/dev/null | sort | tail -1)
if [ -n "$REC" ]; then
  echo "[$(date)] === Phase B (class 1) on $REC ==="
  uv run -m secretagent.cli.learn codedistill-all \
    --learned-dir learned_opus --model "$CD_MODEL" \
    --max-wrong-rate 0.20 "$REC"
  echo "[$(date)] === Phase B rc=$? ==="
fi

# ---------- Phase C: Class 2 workflow-codedistill ----------
DATA_TRAIN="data/problems_train.json"
echo "[$(date)] === Phase C (class 2) ==="
uv run -m secretagent.cli.learn workflow-codedistill \
  --interface tabmwp_solve \
  --dataset-file "$DATA_TRAIN" \
  --output-field answer \
  --tool-module ptools \
  --conf-file conf/workflow_incontext.yaml \
  ${REC:+--trace-dir "$REC"} \
  --learned-dir learned_class2_opus --model "$CD_MODEL" \
  --backoff true --backoff-method simulate
echo "[$(date)] === Phase C rc=$? ==="

# ---------- Phase D: Class 3 codedistill-induced-ptools ----------
REC_REACT=$(ls -d recordings_full/*."tabmwp_react_train_full" 2>/dev/null | sort | tail -1)
if [ -n "$REC_REACT" ]; then
  echo "[$(date)] === Phase D (class 3) on $REC_REACT ==="
  uv run -m secretagent.cli.learn codedistill-induced-ptools \
    --interface tabmwp_solve \
    --task-desc "Solve a tabular math word problem given a question, a pipe-delimited table, and optional answer choices" \
    --trace-mode react --only-correct \
    --learned-dir learned_class3_opus --model "$CD_MODEL" \
    --expt-cmd "uv run python expt.py run --config-file conf/react.yaml dataset.n=$N_TRAIN" \
    --cwd "$TM" \
    "$REC_REACT"
  echo "[$(date)] === Phase D rc=$? ==="
else
  echo "[$(date)] === Phase D skipped (no react train recording) ==="
fi

# ---------- Phase E: vals ----------
echo "[$(date)] === Phase E vals ==="

# Class 1 val
if [ -f learned_opus/codedistill_config.yaml ]; then
  declare -a PT=()
  while IFS= read -r line; do PT+=("$line"); done < <(uv run python -c "
import yaml
cfg = yaml.safe_load(open('learned_opus/codedistill_config.yaml'))
for n, kvs in (cfg.get('ptools', {}) or {}).items():
    for k, v in (kvs or {}).items():
        v = repr(v) if isinstance(v, bool) else v
        print(f'ptools.{n}.{k}={v}')
")
  uv run python expt.py run --config-file conf/workflow_incontext.yaml \
    "dataset.split=dev1k" "dataset.n=$N_VAL" \
    "evaluate.expt_name=tabmwp_val_full_class1_opus" \
    evaluate.record_details=true evaluate.result_dir=val_results_full \
    "llm.model=$DS" \
    "${PT[@]}" learn.train_dir=learned_opus
  echo "[$(date)] class 1 val rc=$?"
fi

# Class 2 val
uv run python expt.py run --config-file conf/workflow_incontext.yaml \
  "dataset.split=dev1k" "dataset.n=$N_VAL" \
  "evaluate.expt_name=tabmwp_val_full_class2_opus" \
  evaluate.record_details=true evaluate.result_dir=val_results_full \
  "llm.model=$DS" \
  "ptools.tabmwp_solve.method=learned_code" \
  "ptools.tabmwp_solve.learner=workflow_distill" \
  "ptools.tabmwp_solve.backoff=true" \
  learn.train_dir=learned_class2_opus
echo "[$(date)] class 2 val rc=$?"

# Class 3 val
if [ -f learned_class3_opus/codedistill_config.yaml ]; then
  declare -a PT3=()
  while IFS= read -r line; do PT3+=("$line"); done < <(uv run python -c "
import yaml
cfg = yaml.safe_load(open('learned_class3_opus/codedistill_config.yaml'))
for n, kvs in (cfg.get('ptools', {}) or {}).items():
    for k, v in (kvs or {}).items():
        v = repr(v) if isinstance(v, bool) else v
        print(f'ptools.{n}.{k}={v}')
")
  uv run python expt.py run --config-file conf/workflow_incontext.yaml \
    "dataset.split=dev1k" "dataset.n=$N_VAL" \
    "evaluate.expt_name=tabmwp_val_full_class3_opus" \
    evaluate.record_details=true evaluate.result_dir=val_results_full \
    "llm.model=$DS" \
    "${PT3[@]}" \
    "ptools.tabmwp_solve.method=learned_code" \
    "ptools.tabmwp_solve.learner=workflow_distill" \
    "ptools.tabmwp_solve.backoff=true" \
    learn.train_dir=learned_class3_opus
  echo "[$(date)] class 3 val rc=$?"
fi

echo "[$(date)] === ALL DONE ==="
