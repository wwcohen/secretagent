#!/bin/bash
# Class 3 gemini val launcher — runs val on val split for the 6 distilled benchmarks.
# Each launches in background, log to benchmarks/codedistill_logs_v2/class3_gemini_val_*.log
set +e
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
mkdir -p "$LOG_DIR"
set -a; source "$ROOT/.env"; set +a
DS_V31="together_ai/deepseek-ai/DeepSeek-V3.1"
DS_V3="together_ai/deepseek-ai/DeepSeek-V3"

WF_COMMON="$ROOT/paper/results/codedistill-workflow-results"

# --- musr family ---
musr_val() {
  local task=$1   # murder|object|team
  local split=$2  # murder_mysteries_val|object_placements_val|team_allocation_val
  local conf=$3
  local label="musr_${task}"
  local ldir="$WF_COMMON/musr/learned_class3_gemini_${task}"
  local d=$(ls -dt "$ldir"/*answer_question_workflow__workflow_distill 2>/dev/null | head -1)
  if [ -z "$d" ] || [ ! -f "$d/learned.py" ]; then
    echo "[$(date)] $label: no learned.py — skip val" | tee -a "$LOG_DIR/class3_gemini_val_${label}.log"
    return
  fi
  local exptbase="${label}_val_full_class3_gemini"
  local log="$LOG_DIR/class3_gemini_val_${label}.log"
  echo "[$(date)] $label class3_gemini val launching from $d" | tee -a "$log"

  cd "$ROOT/benchmarks/musr"
  nohup uv run python expt.py run --config-file "$conf" \
    "dataset.split=$split" dataset.n=75 \
    "evaluate.expt_name=$exptbase" evaluate.record_details=true \
    evaluate.result_dir=val_results_full "llm.model=$DS_V3" \
    ptools.answer_question_workflow.method=learned_code \
    ptools.answer_question_workflow.learner=workflow_distill \
    ptools.answer_question_workflow.backoff=true \
    "learn.train_dir=$ldir" \
    >> "$log" 2>&1 &
  echo "[$(date)] $label PID=$!" | tee -a "$log"
}

# --- natplan family ---
natplan_val() {
  local sub=$1   # meeting|trip
  local iface=$2
  local conf=$3
  local label="natplan_${sub}"
  local ldir="$WF_COMMON/natural_plan/learned_class3_gemini_${sub}"
  local d=$(ls -dt "$ldir"/*"${iface}__workflow_distill" 2>/dev/null | head -1)
  if [ -z "$d" ] || [ ! -f "$d/learned.py" ]; then
    echo "[$(date)] $label: no learned.py — skip val" | tee -a "$LOG_DIR/class3_gemini_val_${label}.log"
    return
  fi
  local exptbase="${label}_val_full_class3_gemini"
  local log="$LOG_DIR/class3_gemini_val_${label}.log"
  echo "[$(date)] $label class3_gemini val launching from $d" | tee -a "$log"

  cd "$ROOT/benchmarks/natural_plan"
  nohup uv run python expt.py run --config-file "conf/${sub}.yaml" \
    dataset.partition=valid dataset.n=100 \
    "evaluate.expt_name=$exptbase" evaluate.record_details=true \
    evaluate.result_dir=val_results_full "llm.model=$DS_V31" \
    "ptools.${iface}.method=learned_code" \
    "ptools.${iface}.learner=workflow_distill" \
    "ptools.${iface}.backoff=true" \
    "learn.train_dir=$ldir" \
    >> "$log" 2>&1 &
  echo "[$(date)] $label PID=$!" | tee -a "$log"
}

# --- rulearena_nba ---
nba_val() {
  local label="rulearena_nba"
  local ldir="$WF_COMMON/rulearena/learned_class3_gemini_nba"
  local d=$(ls -dt "$ldir"/*compute_nba_answer__workflow_distill 2>/dev/null | head -1)
  if [ -z "$d" ] || [ ! -f "$d/learned.py" ]; then
    echo "[$(date)] $label: no learned.py — skip val" | tee -a "$LOG_DIR/class3_gemini_val_${label}.log"
    return
  fi
  local exptbase="${label}_val_full_class3_gemini"
  local log="$LOG_DIR/class3_gemini_val_${label}.log"
  echo "[$(date)] $label class3_gemini val launching from $d" | tee -a "$log"

  cd "$ROOT/benchmarks/rulearena/nba"
  nohup uv run python -m secretagent.cli.expt run \
    --interface ptools.compute_nba_answer --evaluator evaluator.NbaEvaluator \
    dataset.split=valid dataset.n=42 \
    "evaluate.expt_name=$exptbase" evaluate.record_details=true \
    evaluate.result_dir=val_results_full "llm.model=$DS_V3" \
    ptools.compute_nba_answer.method=learned_code \
    ptools.compute_nba_answer.learner=workflow_distill \
    ptools.compute_nba_answer.backoff=true \
    "learn.train_dir=$ldir" \
    >> "$log" 2>&1 &
  echo "[$(date)] $label PID=$!" | tee -a "$log"
}

echo "=== Class 3 gemini vals — start at $(date) ==="

musr_val murder murder_mysteries_val conf/murder_workflow.yaml
musr_val object object_placements_val conf/object_workflow.yaml
musr_val team   team_allocation_val   conf/team_workflow.yaml
natplan_val meeting meeting_planning conf/meeting.yaml
natplan_val trip    trip_planning    conf/trip.yaml
nba_val

echo "=== Class 3 gemini vals — all launched at $(date) ==="
