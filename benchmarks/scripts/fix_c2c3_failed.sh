#!/bin/bash
# Fix the failed Class 2 distill (musr object/team, tabmwp) — they bombed because
# raw data files are not in Dataset-model JSON format.
# Then re-run Class 2 val + Class 3 val correctly (induced ptools as simulate, not learned_code).
set +e
ROOT="/Users/yanjiarui/Desktop/Will_research/secretagent"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
mkdir -p "$LOG_DIR"
set -a; source "$ROOT/.env"; set +a
CD_MODEL="${CD_MODEL:-claude-opus-4-6}"
DS_V3="together_ai/deepseek-ai/DeepSeek-V3"
DS_V31="together_ai/deepseek-ai/DeepSeek-V3.1"

# Convert raw musr/tabmwp data → Dataset-format JSON (cached in /tmp/)
prep_musr_dataset() {
  local task="$1"  # object | team
  local split_train=object_placements_train
  [ "$task" = "team" ] && split_train=team_allocation_train
  local out="/tmp/musr_${task}_train_dataset.json"
  uv run python -c "
import sys, json
sys.path.insert(0, '$ROOT/benchmarks/musr')
import expt
ds = expt.load_dataset('$split_train')
print(ds.model_dump_json(indent=2), file=open('$out', 'w'))
print('wrote $out: n=', len(ds.cases))
" 2>&1 | grep -v warning
  echo "$out"
}

prep_tabmwp_dataset() {
  local out="/tmp/tabmwp_train_dataset.json"
  uv run python -c "
import sys, json
sys.path.insert(0, '$ROOT/benchmarks/tabmwp')
import expt
ds = expt.load_dataset('train')
# limit to 100 cases for distill speed
from secretagent.dataset import Dataset, Case
import random
rng = random.Random(42)
cases = list(ds.cases)
rng.shuffle(cases)
cases = cases[:100]
ds2 = Dataset(name=ds.name, split=ds.split, cases=cases)
print(ds2.model_dump_json(indent=2), file=open('$out', 'w'))
print('wrote $out: n=', len(ds2.cases))
" 2>&1 | grep -v warning
  echo "$out"
}

echo "[$(date)] === STEP 1: prepare Dataset-format files ==="
DS_OBJECT=$(prep_musr_dataset object | tail -1)
DS_TEAM=$(prep_musr_dataset team   | tail -1)
DS_TABMWP=$(prep_tabmwp_dataset | tail -1)

# ========== STEP 2: re-run Class 2 distill (sequential, not parallel) ==========
echo "[$(date)] === STEP 2: Class 2 distill (sequential) ==="

# musr object
TRACE_OBJ=$(ls -d "$ROOT/benchmarks/musr/recordings_full/"*musr_object_train_full 2>/dev/null | tail -1)
TRACE_MURDER=$(ls -d "$ROOT/benchmarks/musr/recordings_full/"*musr_murder_train_train_full 2>/dev/null | tail -1)
echo "[$(date)] musr_object class2 distill rebuild"
cd "$ROOT/benchmarks/musr"
uv run -m secretagent.cli.learn workflow-codedistill \
  --interface answer_question_workflow \
  --dataset-file "$DS_OBJECT" \
  --output-field answer_index \
  --tool-module ptools_object \
  --conf-file conf/object_workflow.yaml \
  --reference-file ptools_team.py --reference-file ptools_murder.py \
  ${TRACE_OBJ:+--trace-dir "$TRACE_OBJ"} \
  ${TRACE_MURDER:+--cross-trace-dir "$TRACE_MURDER"} \
  --learned-dir learned_class2_v4_object --model "$CD_MODEL" \
  --backoff true --backoff-method simulate \
  > "$LOG_DIR/class2v4_musr_object_v2.log" 2>&1
echo "[$(date)] musr_object class2 done rc=$?"

# musr team
TRACE_TEAM=$(ls -d "$ROOT/benchmarks/musr/recordings_full/"*musr_team_train_full 2>/dev/null | tail -1)
echo "[$(date)] musr_team class2 distill rebuild"
uv run -m secretagent.cli.learn workflow-codedistill \
  --interface answer_question_workflow \
  --dataset-file "$DS_TEAM" \
  --output-field answer_index \
  --tool-module ptools_team \
  --conf-file conf/team_workflow.yaml \
  --reference-file ptools_object.py --reference-file ptools_murder.py \
  ${TRACE_TEAM:+--trace-dir "$TRACE_TEAM"} \
  ${TRACE_MURDER:+--cross-trace-dir "$TRACE_MURDER"} \
  --learned-dir learned_class2_v4_team --model "$CD_MODEL" \
  --backoff true --backoff-method simulate \
  > "$LOG_DIR/class2v4_musr_team_v2.log" 2>&1
echo "[$(date)] musr_team class2 done rc=$?"

# tabmwp
TRACE_TM=$(ls -d "$ROOT/benchmarks/tabmwp/recordings_full/"*tabmwp_train_full 2>/dev/null | tail -1)
echo "[$(date)] tabmwp class2 distill rebuild"
cd "$ROOT/benchmarks/tabmwp"
uv run -m secretagent.cli.learn workflow-codedistill \
  --interface tabmwp_solve \
  --dataset-file "$DS_TABMWP" \
  --output-field answer \
  --tool-module ptools \
  --conf-file conf/workflow_incontext.yaml \
  ${TRACE_TM:+--trace-dir "$TRACE_TM"} \
  --learned-dir learned_class2_v4 --model "$CD_MODEL" \
  --backoff true --backoff-method simulate \
  > "$LOG_DIR/class2v4_tabmwp_v2.log" 2>&1
echo "[$(date)] tabmwp class2 done rc=$?"

# ========== STEP 3: re-run Class 2 vals ==========
echo "[$(date)] === STEP 3: Class 2 vals ==="

# musr object class2 val
cd "$ROOT/benchmarks/musr"
uv run python expt.py run --config-file conf/object_workflow.yaml \
  "dataset.split=object_placements_val" "dataset.n=75" \
  "evaluate.expt_name=object_val_full_class2v4" \
  evaluate.record_details=true evaluate.result_dir=val_results_full \
  "llm.model=$DS_V3" \
  "ptools.answer_question_workflow.method=learned_code" \
  "ptools.answer_question_workflow.learner=workflow_distill" \
  "ptools.answer_question_workflow.backoff=true" \
  "learn.train_dir=$ROOT/benchmarks/musr/learned_class2_v4_object" \
  > "$LOG_DIR/musr_object_class2_val_v2.log" 2>&1
echo "[$(date)] musr_object class2 val rc=$?"

# musr team class2 val
uv run python expt.py run --config-file conf/team_workflow.yaml \
  "dataset.split=team_allocation_val" "dataset.n=75" \
  "evaluate.expt_name=team_val_full_class2v4" \
  evaluate.record_details=true evaluate.result_dir=val_results_full \
  "llm.model=$DS_V3" \
  "ptools.answer_question_workflow.method=learned_code" \
  "ptools.answer_question_workflow.learner=workflow_distill" \
  "ptools.answer_question_workflow.backoff=true" \
  "learn.train_dir=$ROOT/benchmarks/musr/learned_class2_v4_team" \
  > "$LOG_DIR/musr_team_class2_val_v2.log" 2>&1
echo "[$(date)] musr_team class2 val rc=$?"

# tabmwp class2 val
cd "$ROOT/benchmarks/tabmwp"
uv run python expt.py run --config-file conf/workflow_incontext.yaml \
  "dataset.split=dev1k" "dataset.n=100" \
  "evaluate.expt_name=tabmwp_val_full_class2v4" \
  evaluate.record_details=true evaluate.result_dir=val_results_full \
  "llm.model=$DS_V31" \
  "ptools.tabmwp_solve.method=learned_code" \
  "ptools.tabmwp_solve.learner=workflow_distill" \
  "ptools.tabmwp_solve.backoff=true" \
  "learn.train_dir=$ROOT/benchmarks/tabmwp/learned_class2_v4" \
  > "$LOG_DIR/tabmwp_class2_val_v2.log" 2>&1
echo "[$(date)] tabmwp class2 val rc=$?"

# ========== STEP 4: re-run Class 3 vals (DON'T pass induced ptools as learned_code) ==========
echo "[$(date)] === STEP 4: Class 3 vals (induced ptools = simulate, not learned_code) ==="

# musr object class3 val — find induced ptools and set them to simulate
cd "$ROOT/benchmarks/musr"
INDUCED_OBJ_DIR=$(ls -d "$ROOT/benchmarks/musr/learned_class3_v4/"*"answer_question__ptool_inducer" 2>/dev/null | tail -1)
if [ -n "$INDUCED_OBJ_DIR" ] && [ -f "$INDUCED_OBJ_DIR/learned_ptools.py" ]; then
  declare -a OBJ_PT_OVERRIDES=()
  while IFS= read -r name; do
    [ -z "$name" ] && continue
    OBJ_PT_OVERRIDES+=("ptools.${name}.method=simulate")
  done < <(grep -E "^def [a-z_]+\(" "$INDUCED_OBJ_DIR/learned_ptools.py" | sed -E 's/^def ([a-z_]+).*/\1/')
  echo "[$(date)] musr_object class3 val (${#OBJ_PT_OVERRIDES[@]} induced ptools as simulate)"
  uv run python expt.py run --config-file conf/object_workflow.yaml \
    "dataset.split=object_placements_val" "dataset.n=75" \
    "evaluate.expt_name=object_val_full_class3v4" \
    evaluate.record_details=true evaluate.result_dir=val_results_full \
    "llm.model=$DS_V3" \
    "${OBJ_PT_OVERRIDES[@]}" \
    "ptools.answer_question.method=learned_code" \
    "ptools.answer_question.learner=workflow_distill" \
    "ptools.answer_question.backoff=true" \
    "learn.train_dir=$ROOT/benchmarks/musr/learned_class3_v4" \
    > "$LOG_DIR/musr_object_class3_val_v2.log" 2>&1
  echo "[$(date)] musr_object class3 val rc=$?"
fi

# musr team class3 val
INDUCED_TEAM_DIR=$(ls -d "$ROOT/benchmarks/musr/learned_class3_v4/"*"answer_question__ptool_inducer" 2>/dev/null | tail -1)
if [ -n "$INDUCED_TEAM_DIR" ] && [ -f "$INDUCED_TEAM_DIR/learned_ptools.py" ]; then
  declare -a TEAM_PT_OVERRIDES=()
  while IFS= read -r name; do
    [ -z "$name" ] && continue
    TEAM_PT_OVERRIDES+=("ptools.${name}.method=simulate")
  done < <(grep -E "^def [a-z_]+\(" "$INDUCED_TEAM_DIR/learned_ptools.py" | sed -E 's/^def ([a-z_]+).*/\1/')
  echo "[$(date)] musr_team class3 val (${#TEAM_PT_OVERRIDES[@]} induced ptools as simulate)"
  uv run python expt.py run --config-file conf/team_workflow.yaml \
    "dataset.split=team_allocation_val" "dataset.n=75" \
    "evaluate.expt_name=team_val_full_class3v4" \
    evaluate.record_details=true evaluate.result_dir=val_results_full \
    "llm.model=$DS_V3" \
    "${TEAM_PT_OVERRIDES[@]}" \
    "ptools.answer_question.method=learned_code" \
    "ptools.answer_question.learner=workflow_distill" \
    "ptools.answer_question.backoff=true" \
    "learn.train_dir=$ROOT/benchmarks/musr/learned_class3_v4" \
    > "$LOG_DIR/musr_team_class3_val_v2.log" 2>&1
  echo "[$(date)] musr_team class3 val rc=$?"
fi

# tabmwp class3 val
cd "$ROOT/benchmarks/tabmwp"
INDUCED_TM_DIR=$(ls -d "$ROOT/benchmarks/tabmwp/learned_class3_v4/"*"tabmwp_solve__ptool_inducer" 2>/dev/null | tail -1)
if [ -n "$INDUCED_TM_DIR" ] && [ -f "$INDUCED_TM_DIR/learned_ptools.py" ]; then
  declare -a TM_PT_OVERRIDES=()
  while IFS= read -r name; do
    [ -z "$name" ] && continue
    TM_PT_OVERRIDES+=("ptools.${name}.method=simulate")
  done < <(grep -E "^def [a-z_]+\(" "$INDUCED_TM_DIR/learned_ptools.py" | sed -E 's/^def ([a-z_]+).*/\1/')
  echo "[$(date)] tabmwp class3 val (${#TM_PT_OVERRIDES[@]} induced ptools as simulate)"
  uv run python expt.py run --config-file conf/workflow_incontext.yaml \
    "dataset.split=dev1k" "dataset.n=100" \
    "evaluate.expt_name=tabmwp_val_full_class3v4" \
    evaluate.record_details=true evaluate.result_dir=val_results_full \
    "llm.model=$DS_V31" \
    "${TM_PT_OVERRIDES[@]}" \
    "ptools.tabmwp_solve.method=learned_code" \
    "ptools.tabmwp_solve.learner=workflow_distill" \
    "ptools.tabmwp_solve.backoff=true" \
    "learn.train_dir=$ROOT/benchmarks/tabmwp/learned_class3_v4" \
    > "$LOG_DIR/tabmwp_class3_val_v2.log" 2>&1
  echo "[$(date)] tabmwp class3 val rc=$?"
fi

echo "[$(date)] === ALL FIXES DONE ==="
