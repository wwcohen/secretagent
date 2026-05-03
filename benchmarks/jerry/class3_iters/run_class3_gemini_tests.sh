#!/bin/bash
# Class 3 gemini test launcher — re-runs cached learners on test split.
# Mirrors run_class3_gemini_vals.sh but uses test split + writes to test_results_full.
set +e
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
mkdir -p "$LOG_DIR"
set -a; source "$ROOT/.env"; set +a
DS_V31="together_ai/deepseek-ai/DeepSeek-V3.1"
DS_V3="together_ai/deepseek-ai/DeepSeek-V3"

WF="$ROOT/benchmarks/COMMON/codedistill-workflow-results"

musr_test() {
  local task=$1   # murder|object|team
  local split=$2  # murder_mysteries_test|...
  local conf=$3
  local label="musr_${task}"
  local ldir="$WF/musr/learned_class3_gemini_${task}"
  local d=$(ls -dt "$ldir"/*answer_question_workflow__workflow_distill 2>/dev/null | head -1)
  [ -z "$d" ] || [ ! -f "$d/learned.py" ] && { echo "$label: no learned.py — skip" | tee -a "$LOG_DIR/class3_gemini_test_${label}.log"; return; }
  local exptbase="${label}_test_full_class3_gemini"
  local log="$LOG_DIR/class3_gemini_test_${label}.log"
  echo "[$(date)] $label test launching" | tee "$log"

  cd "$ROOT/benchmarks/musr"
  nohup uv run python expt.py run --config-file "$conf" \
    "dataset.split=$split" dataset.n=75 \
    "evaluate.expt_name=$exptbase" evaluate.record_details=true \
    evaluate.result_dir=test_results_full "llm.model=$DS_V3" \
    ptools.answer_question_workflow.method=learned_code \
    ptools.answer_question_workflow.learner=workflow_distill \
    ptools.answer_question_workflow.backoff=true \
    "learn.train_dir=$ldir" \
    >> "$log" 2>&1 &
  echo "[$(date)] $label PID=$!" | tee -a "$log"
}

natplan_test() {
  local sub=$1
  local iface=$2
  local label="natplan_${sub}"
  local ldir="$WF/natural_plan/learned_class3_gemini_${sub}"
  local d=$(ls -dt "$ldir"/*"${iface}__workflow_distill" 2>/dev/null | head -1)
  [ -z "$d" ] || [ ! -f "$d/learned.py" ] && { echo "$label: no learned.py — skip" | tee -a "$LOG_DIR/class3_gemini_test_${label}.log"; return; }
  local exptbase="${label}_test_full_class3_gemini"
  local log="$LOG_DIR/class3_gemini_test_${label}.log"
  echo "[$(date)] $label test launching" | tee "$log"

  cd "$ROOT/benchmarks/natural_plan"
  nohup uv run python expt.py run --config-file "conf/${sub}.yaml" \
    dataset.partition=test dataset.n=100 \
    "evaluate.expt_name=$exptbase" evaluate.record_details=true \
    evaluate.result_dir=test_results_full "llm.model=$DS_V31" \
    "ptools.${iface}.method=learned_code" \
    "ptools.${iface}.learner=workflow_distill" \
    "ptools.${iface}.backoff=true" \
    "learn.train_dir=$ldir" \
    >> "$log" 2>&1 &
  echo "[$(date)] $label PID=$!" | tee -a "$log"
}

nba_test() {
  local label="rulearena_nba"
  local ldir="$WF/rulearena/learned_class3_gemini_nba"
  local d=$(ls -dt "$ldir"/*compute_nba_answer__workflow_distill 2>/dev/null | head -1)
  [ -z "$d" ] || [ ! -f "$d/learned.py" ] && { echo "$label: no learned.py — skip" | tee -a "$LOG_DIR/class3_gemini_test_${label}.log"; return; }
  local exptbase="${label}_test_full_class3_gemini"
  local log="$LOG_DIR/class3_gemini_test_${label}.log"
  echo "[$(date)] $label test launching" | tee "$log"

  cd "$ROOT/benchmarks/rulearena/nba"
  nohup uv run python -m secretagent.cli.expt run \
    --interface ptools.compute_nba_answer --evaluator evaluator.NbaEvaluator \
    dataset.split=test dataset.n=46 \
    "evaluate.expt_name=$exptbase" evaluate.record_details=true \
    evaluate.result_dir=test_results_full "llm.model=$DS_V3" \
    ptools.compute_nba_answer.method=learned_code \
    ptools.compute_nba_answer.learner=workflow_distill \
    ptools.compute_nba_answer.backoff=true \
    "learn.train_dir=$ldir" \
    >> "$log" 2>&1 &
  echo "[$(date)] $label PID=$!" | tee -a "$log"
}

echo "=== Class 3 gemini tests — start at $(date) ==="

musr_test murder murder_mysteries_test conf/murder_workflow.yaml
musr_test object object_placements_test conf/object_workflow.yaml
musr_test team   team_allocation_test   conf/team_workflow.yaml
natplan_test meeting meeting_planning
natplan_test trip    trip_planning
nba_test

echo "=== Class 3 gemini tests — all launched at $(date) ==="
