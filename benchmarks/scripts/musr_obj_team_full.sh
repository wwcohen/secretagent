#!/bin/bash
# Run class 1, 2, 3 full pipeline for musr object_placements + team_allocation.
# Phases:
#   A: record train workflow + train react + val baseline (object + team)
#   B: class 1 codedistill-all on workflow train
#   C: class 2 workflow-codedistill on dataset
#   D: class 3 codedistill-induced-ptools 4-stage on react train
#   E: val for each class
set +e
ROOT="/Users/yanjiarui/Desktop/Will_research/secretagent"
MUSR="$ROOT/benchmarks/musr"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
mkdir -p "$LOG_DIR"
set -a; source "$ROOT/.env"; set +a
CD_MODEL="${CD_MODEL:-claude-opus-4-6}"
DS="together_ai/deepseek-ai/DeepSeek-V3"
N_TRAIN=75
N_VAL=75

cd "$MUSR"

# ---------- Phase A: record train (workflow + react) + val baseline ----------
phaseA_one() {
  local task="$1"  # object | team
  local split_train="${task}_${task#?*_}_train"
  if [ "$task" = "object" ]; then split_train=object_placements_train; split_val=object_placements_val; conf_wf=object_workflow.yaml; conf_react=object_react_train.yaml; fi
  if [ "$task" = "team" ];   then split_train=team_allocation_train;   split_val=team_allocation_val;   conf_wf=team_workflow.yaml;   conf_react=team_react_train.yaml;   fi
  local log="$LOG_DIR/musr_${task}_phaseA.log"
  echo "[$(date)] $task phaseA start" | tee "$log"

  # workflow train
  uv run python expt.py run --config-file "conf/$conf_wf" \
    "dataset.split=$split_train" "dataset.n=$N_TRAIN" \
    "evaluate.expt_name=musr_${task}_train_full" \
    evaluate.record_details=true evaluate.result_dir=recordings_full \
    "llm.model=$DS" >> "$log" 2>&1
  echo "[$(date)] $task workflow_train rc=$?" | tee -a "$log"

  # workflow val baseline
  uv run python expt.py run --config-file "conf/$conf_wf" \
    "dataset.split=$split_val" "dataset.n=$N_VAL" \
    "evaluate.expt_name=${task}_val_full_baseline" \
    evaluate.record_details=true evaluate.result_dir=val_results_full \
    "llm.model=$DS" >> "$log" 2>&1
  echo "[$(date)] $task workflow_val rc=$?" | tee -a "$log"

  # react train (for class 3)
  uv run python expt.py run --config-file "conf/$conf_react" \
    "dataset.split=$split_train" "dataset.n=$N_TRAIN" \
    "evaluate.expt_name=musr_${task}_react_train_full" \
    evaluate.record_details=true evaluate.result_dir=recordings_full \
    "llm.model=$DS" >> "$log" 2>&1
  echo "[$(date)] $task react_train rc=$?" | tee -a "$log"
}

# ---------- Phase B: class 1 codedistill-all ----------
phaseB_one() {
  local task="$1"
  local log="$LOG_DIR/class1v4_musr_${task}.log"
  local rec=$(ls -d "$MUSR/recordings_full/"*."musr_${task}_train_full" 2>/dev/null | sort | tail -1)
  if [ -z "$rec" ]; then echo "[$task] phaseB: no train recording — skip" | tee -a "$log"; return; fi
  echo "[$(date)] $task class1 distill rec=$rec" | tee -a "$log"
  uv run -m secretagent.cli.learn codedistill-all \
    --learned-dir learned_v4 --model "$CD_MODEL" \
    --max-wrong-rate 0.20 "$rec" >> "$log" 2>&1
  echo "[$(date)] $task class1 done rc=$?" | tee -a "$log"
}

# ---------- Phase C: class 2 workflow-codedistill ----------
phaseC_one() {
  local task="$1"
  local log="$LOG_DIR/class2v4_musr_${task}.log"
  local trace=$(ls -d "$MUSR/recordings_full/"*."musr_${task}_train_full" 2>/dev/null | sort | tail -1)
  local cross_trace=$(ls -d "$MUSR/recordings_full/"*."musr_murder_train_train_full" 2>/dev/null | sort | tail -1)
  local data_train="data/${task}_placements_train.json"
  [ "$task" = "team" ] && data_train="data/team_allocation_train.json"
  local conf="conf/${task}_workflow.yaml"
  local refs=()
  if [ "$task" = "object" ]; then refs+=(--reference-file ptools_team.py --reference-file ptools_murder.py); fi
  if [ "$task" = "team" ];   then refs+=(--reference-file ptools_object.py --reference-file ptools_murder.py); fi
  echo "[$(date)] $task class2 distill trace=$trace cross=$cross_trace" | tee "$log"
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface answer_question_workflow \
    --dataset-file "$data_train" \
    --output-field answer_index \
    --tool-module "ptools_${task}" \
    --conf-file "$conf" \
    "${refs[@]}" \
    ${trace:+--trace-dir "$trace"} \
    ${cross_trace:+--cross-trace-dir "$cross_trace"} \
    --learned-dir learned_class2_v4 --model "$CD_MODEL" \
    --backoff true --backoff-method simulate >> "$log" 2>&1
  echo "[$(date)] $task class2 done rc=$?" | tee -a "$log"
}

# ---------- Phase D: class 3 codedistill-induced-ptools ----------
phaseD_one() {
  local task="$1"
  local log="$LOG_DIR/class3v4_musr_${task}.log"
  local rec_react=$(ls -d "$MUSR/recordings_full/"*."musr_${task}_react_train_full" 2>/dev/null | sort | tail -1)
  if [ -z "$rec_react" ]; then echo "[$task] phaseD: no react recording — skip" | tee -a "$log"; return; fi
  local desc
  if [ "$task" = "object" ]; then desc="Determine where target person believes target object is located in a story with object movements and theory-of-mind reasoning"; fi
  if [ "$task" = "team" ];   then desc="Choose the best team allocation given role requirements, hard/soft constraints, synergies, and conflicts"; fi
  echo "[$(date)] $task class3 induced rec=$rec_react" | tee "$log"
  uv run -m secretagent.cli.learn codedistill-induced-ptools \
    --interface answer_question \
    --task-desc "$desc" \
    --trace-mode react --only-correct \
    --state-module ptools_common --state-expr '_REACT_STATE["narrative"]' \
    --learned-dir learned_class3_v4 --model "$CD_MODEL" \
    --expt-cmd "uv run python expt.py run --config-file conf/${task}_react_train.yaml dataset.n=$N_TRAIN" \
    --cwd "$MUSR" \
    "$rec_react" >> "$log" 2>&1
  echo "[$(date)] $task class3 done rc=$?" | tee -a "$log"
}

# ---------- Phase E: val each class ----------
phaseE_one() {
  local task="$1"
  local log="$LOG_DIR/musr_${task}_phaseE.log"
  local split_val=object_placements_val
  [ "$task" = "team" ] && split_val=team_allocation_val
  local conf="conf/${task}_workflow.yaml"

  # Class 1 val: read learned_v4 ptool config; pass each enabled override
  local class1_cfg="$MUSR/learned_v4/codedistill_config.yaml"
  if [ -f "$class1_cfg" ]; then
    declare -a PT=()
    while IFS= read -r line; do PT+=("$line"); done < <(uv run python -c "
import yaml
cfg = yaml.safe_load(open('$class1_cfg'))
for n, kvs in (cfg.get('ptools', {}) or {}).items():
    for k, v in (kvs or {}).items():
        v = repr(v) if isinstance(v, bool) else v
        print(f'ptools.{n}.{k}={v}')
")
    echo "[$(date)] $task class1 val PT=${PT[@]}" | tee "$log"
    uv run python expt.py run --config-file "$conf" \
      "dataset.split=$split_val" "dataset.n=$N_VAL" \
      "evaluate.expt_name=${task}_val_full_class1v4" \
      evaluate.record_details=true evaluate.result_dir=val_results_full \
      "llm.model=$DS" \
      "${PT[@]}" learn.train_dir=learned_v4 >> "$log" 2>&1
    echo "[$(date)] $task class1 val rc=$?" | tee -a "$log"
  fi

  # Class 2 val: workflow_distill on answer_question_workflow
  echo "[$(date)] $task class2 val" | tee -a "$log"
  uv run python expt.py run --config-file "$conf" \
    "dataset.split=$split_val" "dataset.n=$N_VAL" \
    "evaluate.expt_name=${task}_val_full_class2v4" \
    evaluate.record_details=true evaluate.result_dir=val_results_full \
    "llm.model=$DS" \
    "ptools.answer_question_workflow.method=learned_code" \
    "ptools.answer_question_workflow.learner=workflow_distill" \
    "ptools.answer_question_workflow.backoff=true" \
    learn.train_dir=learned_class2_v4 >> "$log" 2>&1
  echo "[$(date)] $task class2 val rc=$?" | tee -a "$log"

  # Class 3 val: workflow_distill on answer_question (induced) + sub-ptools as simulate
  local class3_dir=$(ls -d "$MUSR/learned_class3_v4/"*"answer_question__workflow_distill" 2>/dev/null | tail -1)
  if [ -n "$class3_dir" ]; then
    local merged="$MUSR/learned_class3_v4/codedistill_config.yaml"
    declare -a PT3=()
    if [ -f "$merged" ]; then
      while IFS= read -r line; do PT3+=("$line"); done < <(uv run python -c "
import yaml
cfg = yaml.safe_load(open('$merged'))
for n, kvs in (cfg.get('ptools', {}) or {}).items():
    for k, v in (kvs or {}).items():
        v = repr(v) if isinstance(v, bool) else v
        print(f'ptools.{n}.{k}={v}')
")
    fi
    echo "[$(date)] $task class3 val class3_dir=$class3_dir PT3=${PT3[@]}" | tee -a "$log"
    uv run python expt.py run --config-file "$conf" \
      "dataset.split=$split_val" "dataset.n=$N_VAL" \
      "evaluate.expt_name=${task}_val_full_class3v4" \
      evaluate.record_details=true evaluate.result_dir=val_results_full \
      "llm.model=$DS" \
      "${PT3[@]}" \
      "ptools.answer_question.method=learned_code" \
      "ptools.answer_question.learner=workflow_distill" \
      "ptools.answer_question.backoff=true" \
      learn.train_dir=learned_class3_v4 >> "$log" 2>&1
    echo "[$(date)] $task class3 val rc=$?" | tee -a "$log"
  else
    echo "[$task] class3 val: no learned_class3_v4 answer_question dir — skip" | tee -a "$log"
  fi
}

echo "=== musr object/team full pipeline START $(date) ==="

# Phase A: object + team in parallel (each task does workflow_train -> val -> react_train sequentially)
phaseA_one object & PA1=$!
phaseA_one team   & PA2=$!
wait $PA1 $PA2
echo "=== Phase A done $(date) ==="

# Phase B: class 1 (parallel)
phaseB_one object & PB1=$!
phaseB_one team   & PB2=$!
wait $PB1 $PB2
echo "=== Phase B done $(date) ==="

# Phase C: class 2 (parallel)
phaseC_one object & PC1=$!
phaseC_one team   & PC2=$!
wait $PC1 $PC2
echo "=== Phase C done $(date) ==="

# Phase D: class 3 (parallel)
phaseD_one object & PD1=$!
phaseD_one team   & PD2=$!
wait $PD1 $PD2
echo "=== Phase D done $(date) ==="

# Phase E: vals (sequential within task to avoid expt.py cwd race; parallel across tasks)
phaseE_one object & PE1=$!
phaseE_one team   & PE2=$!
wait $PE1 $PE2
echo "=== ALL DONE $(date) ==="
