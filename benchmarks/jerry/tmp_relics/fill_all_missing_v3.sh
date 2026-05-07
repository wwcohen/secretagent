#!/bin/bash
# Fill all missing full-size cells. Designed to NOT get stuck on slow LLM:
# - Pass --max-rounds 2 (instead of default 3) so distill caps at ~30 min
# - Pass --n-candidates 5 (instead of 9) so each round is faster
# - Run all distills in parallel (different cwd / output dirs)
set +e
ROOT="/Users/anon/Desktop/anon_research/secretagent"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
mkdir -p "$LOG_DIR"
set -a; source "$ROOT/.env"; set +a
CD_MODEL="${CD_MODEL:-claude-opus-4-6}"
DS_V3="together_ai/deepseek-ai/DeepSeek-V3"
DS_V31="together_ai/deepseek-ai/DeepSeek-V3.1"

# ========== STEP 0: medcalc baseline_full + class 2 val (split=test, no valid) ==========
echo "[$(date)] === STEP 0: medcalc baseline + class 2 (split=test) ==="
(
  cd "$ROOT/benchmarks/medcalc"
  uv run python expt.py run --config-file conf/workflow.yaml \
    "dataset.split=test" "dataset.n=100" \
    "evaluate.expt_name=medcalc_val_full_baseline" \
    evaluate.record_details=true evaluate.result_dir=val_results_full \
    "llm.model=$DS_V31" > "$LOG_DIR/fill_medcalc_baseline_v3.log" 2>&1
  echo "[$(date)] medcalc baseline rc=$?"

  uv run python expt.py run --config-file conf/workflow.yaml \
    "dataset.split=test" "dataset.n=100" \
    "evaluate.expt_name=medcalc_val_full_class2_opus" \
    evaluate.record_details=true evaluate.result_dir=val_results_full \
    "llm.model=$DS_V31" \
    "ptools.calculate_medical_value.method=learned_code" \
    "ptools.calculate_medical_value.learner=workflow_distill" \
    "ptools.calculate_medical_value.backoff=true" \
    "learn.train_dir=$ROOT/benchmarks/medcalc/learned_class2_opus" > "$LOG_DIR/fill_medcalc_class2_opus_v3.log" 2>&1
  echo "[$(date)] medcalc class2 opus val rc=$?"
) &
P0=$!

# ========== STEP 1: musr_object class 2 distill (DIFFERENT output dir to avoid collision) ==========
echo "[$(date)] === STEP 1: musr class 2 distills (parallel) ==="
prep_musr() {
  local task=$1
  local split_train=object_placements_train
  [ "$task" = team ] && split_train=team_allocation_train
  [ "$task" = murder ] && split_train=murder_mysteries_train
  local out="/tmp/musr_${task}_train_dataset.json"
  uv run python -c "
import sys; sys.path.insert(0, '$ROOT/benchmarks/musr')
import expt
ds = expt.load_dataset('$split_train')
print(ds.model_dump_json(indent=2), file=open('$out', 'w'))
" 2>/dev/null
  echo "$out"
}

DS_OBJ=$(prep_musr object | tail -1)
DS_TEAM=$(prep_musr team | tail -1)
DS_MURDER=$(prep_musr murder | tail -1)
echo "[$(date)] prepped: $DS_OBJ $DS_TEAM $DS_MURDER"

(
  cd "$ROOT/benchmarks/musr"
  TRACE_OBJ=$(ls -d recordings_full/*musr_object_train_full 2>/dev/null | tail -1)
  TRACE_MURDER=$(ls -d recordings_full/*musr_murder_train_train_full 2>/dev/null | tail -1)
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface answer_question_workflow \
    --dataset-file "$DS_OBJ" \
    --output-field answer_index \
    --tool-module ptools_object \
    --conf-file conf/object_workflow.yaml \
    --reference-file ptools_team.py --reference-file ptools_murder.py \
    --max-rounds 2 --n-candidates 5 \
    ${TRACE_OBJ:+--trace-dir "$TRACE_OBJ"} \
    ${TRACE_MURDER:+--cross-trace-dir "$TRACE_MURDER"} \
    --learned-dir learned_class2_opus_object --model "$CD_MODEL" \
    --backoff true --backoff-method simulate \
    > "$LOG_DIR/class2_opus_musr_object_v3.log" 2>&1
  echo "[$(date)] musr_object class2 distill rc=$?"
) &
P1=$!

(
  cd "$ROOT/benchmarks/musr"
  TRACE_TEAM=$(ls -d recordings_full/*musr_team_train_full 2>/dev/null | tail -1)
  TRACE_MURDER=$(ls -d recordings_full/*musr_murder_train_train_full 2>/dev/null | tail -1)
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface answer_question_workflow \
    --dataset-file "$DS_TEAM" \
    --output-field answer_index \
    --tool-module ptools_team \
    --conf-file conf/team_workflow.yaml \
    --reference-file ptools_object.py --reference-file ptools_murder.py \
    --max-rounds 2 --n-candidates 5 \
    ${TRACE_TEAM:+--trace-dir "$TRACE_TEAM"} \
    ${TRACE_MURDER:+--cross-trace-dir "$TRACE_MURDER"} \
    --learned-dir learned_class2_opus_team --model "$CD_MODEL" \
    --backoff true --backoff-method simulate \
    > "$LOG_DIR/class2_opus_musr_team_v3.log" 2>&1
  echo "[$(date)] musr_team class2 distill rc=$?"
) &
P2=$!

# musr_murder class 2 distill (was missing!)
(
  cd "$ROOT/benchmarks/musr"
  TRACE_MURDER=$(ls -d recordings_full/*musr_murder_train_train_full 2>/dev/null | tail -1)
  TRACE_OBJ=$(ls -d recordings_full/*musr_object_train_full 2>/dev/null | tail -1)
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface answer_question_workflow \
    --dataset-file "$DS_MURDER" \
    --output-field answer_index \
    --tool-module ptools_murder \
    --conf-file conf/murder_workflow.yaml \
    --reference-file ptools_object.py --reference-file ptools_team.py \
    --max-rounds 2 --n-candidates 5 \
    ${TRACE_MURDER:+--trace-dir "$TRACE_MURDER"} \
    ${TRACE_OBJ:+--cross-trace-dir "$TRACE_OBJ"} \
    --learned-dir learned_class2_opus_murder --model "$CD_MODEL" \
    --backoff true --backoff-method simulate \
    > "$LOG_DIR/class2_opus_musr_murder_v3.log" 2>&1
  echo "[$(date)] musr_murder class2 distill rc=$?"
) &
P3=$!

# ========== STEP 2: tabmwp class 2 distill ==========
prep_tabmwp() {
  local out="/tmp/tabmwp_train_dataset.json"
  uv run python -c "
import sys; sys.path.insert(0, '$ROOT/benchmarks/tabmwp')
import expt
ds = expt.load_dataset('train')
import random
rng = random.Random(42); cases = list(ds.cases); rng.shuffle(cases); cases = cases[:100]
from secretagent.dataset import Dataset
ds2 = Dataset(name=ds.name, split=ds.split, cases=cases)
print(ds2.model_dump_json(indent=2), file=open('$out', 'w'))
" 2>/dev/null
  echo "$out"
}
DS_TABMWP=$(prep_tabmwp | tail -1)
echo "[$(date)] tabmwp dataset: $DS_TABMWP"

(
  cd "$ROOT/benchmarks/tabmwp"
  TRACE_TM=$(ls -d recordings_full/*tabmwp_train_full 2>/dev/null | tail -1)
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface tabmwp_solve \
    --dataset-file "$DS_TABMWP" \
    --output-field answer \
    --tool-module ptools \
    --conf-file conf/workflow_incontext.yaml \
    --max-rounds 2 --n-candidates 5 \
    ${TRACE_TM:+--trace-dir "$TRACE_TM"} \
    --learned-dir learned_class2_opus --model "$CD_MODEL" \
    --backoff true --backoff-method simulate \
    > "$LOG_DIR/class2_opus_tabmwp_v3.log" 2>&1
  echo "[$(date)] tabmwp class2 distill rc=$?"
) &
P4=$!

# Wait for all 4 distills
wait $P1 $P2 $P3 $P4
echo "[$(date)] === STEP 2 DONE: all class 2 distills ==="

# ========== STEP 3: vals (class 2 + class 3) ==========
echo "[$(date)] === STEP 3: vals (parallel) ==="

# musr_object class 2 val
(
  cd "$ROOT/benchmarks/musr"
  uv run python expt.py run --config-file conf/object_workflow.yaml \
    "dataset.split=object_placements_val" "dataset.n=75" \
    "evaluate.expt_name=object_val_full_class2_opus" \
    evaluate.record_details=true evaluate.result_dir=val_results_full \
    "llm.model=$DS_V3" \
    "ptools.answer_question_workflow.method=learned_code" \
    "ptools.answer_question_workflow.learner=workflow_distill" \
    "ptools.answer_question_workflow.backoff=true" \
    "learn.train_dir=$ROOT/benchmarks/musr/learned_class2_opus_object" \
    > "$LOG_DIR/musr_object_class2_val_v3.log" 2>&1
  echo "[$(date)] object class2 val rc=$?"
) &

(
  cd "$ROOT/benchmarks/musr"
  uv run python expt.py run --config-file conf/team_workflow.yaml \
    "dataset.split=team_allocation_val" "dataset.n=75" \
    "evaluate.expt_name=team_val_full_class2_opus" \
    evaluate.record_details=true evaluate.result_dir=val_results_full \
    "llm.model=$DS_V3" \
    "ptools.answer_question_workflow.method=learned_code" \
    "ptools.answer_question_workflow.learner=workflow_distill" \
    "ptools.answer_question_workflow.backoff=true" \
    "learn.train_dir=$ROOT/benchmarks/musr/learned_class2_opus_team" \
    > "$LOG_DIR/musr_team_class2_val_v3.log" 2>&1
  echo "[$(date)] team class2 val rc=$?"
) &

(
  cd "$ROOT/benchmarks/musr"
  uv run python expt.py run --config-file conf/murder_workflow.yaml \
    "dataset.split=murder_mysteries_val" "dataset.n=75" \
    "evaluate.expt_name=murder_val_full_class2_opus" \
    evaluate.record_details=true evaluate.result_dir=val_results_full \
    "llm.model=$DS_V3" \
    "ptools.answer_question_workflow.method=learned_code" \
    "ptools.answer_question_workflow.learner=workflow_distill" \
    "ptools.answer_question_workflow.backoff=true" \
    "learn.train_dir=$ROOT/benchmarks/musr/learned_class2_opus_murder" \
    > "$LOG_DIR/musr_murder_class2_val_v3.log" 2>&1
  echo "[$(date)] murder class2 val rc=$?"
) &

(
  cd "$ROOT/benchmarks/tabmwp"
  uv run python expt.py run --config-file conf/workflow_incontext.yaml \
    "dataset.split=dev1k" "dataset.n=100" \
    "evaluate.expt_name=tabmwp_val_full_class2_opus" \
    evaluate.record_details=true evaluate.result_dir=val_results_full \
    "llm.model=$DS_V31" \
    "ptools.tabmwp_solve.method=learned_code" \
    "ptools.tabmwp_solve.learner=workflow_distill" \
    "ptools.tabmwp_solve.backoff=true" \
    "learn.train_dir=$ROOT/benchmarks/tabmwp/learned_class2_opus" \
    > "$LOG_DIR/tabmwp_class2_val_v3.log" 2>&1
  echo "[$(date)] tabmwp class2 val rc=$?"
) &

wait
echo "[$(date)] === STEP 3 DONE: all vals ==="
echo "[$(date)] === ALL FILL_v3 DONE ==="
