#!/bin/bash
# Class 1: Ptool codedistill on 13 benchmarks
# - Records train split with each benchmark's hand-written workflow
# - Runs codedistill-all per benchmark, auto-enabling ptools with wrong_rate <= 5%
# - Single benchmark failure does NOT halt others (set +e)
# Usage: nohup bash run_class1_codedistill.sh > class1_all.log 2>&1 &

set +e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
mkdir -p "$LOG_DIR"

# Load API keys
set -a
source "$ROOT/.env"
set +a

CD_MODEL="${CD_MODEL:-claude-opus-4-6}"
N_CASES="${N_CASES:-50}"

run_step() {
  local label="$1"; shift
  echo "[$(date)] $label: starting"
  "$@" 2>&1
  local rc=$?
  echo "[$(date)] $label: rc=$rc"
  return $rc
}

# Helper: record + distill one benchmark
# args: name, cwd, expt_name, "record_args..."
do_bench() {
  local name="$1"; local cwd="$2"; local expt="$3"; shift 3
  local log="$LOG_DIR/class1_${name}.log"
  echo "============================================================" | tee "$log"
  echo "[$(date)] benchmark: $name" | tee -a "$log"
  echo "  cwd: $cwd" | tee -a "$log"
  echo "  expt_name: $expt" | tee -a "$log"
  echo "============================================================" | tee -a "$log"

  cd "$cwd" || { echo "  cwd missing, skipping" | tee -a "$log"; return; }

  # 1) record train split
  run_step "record" "$@" \
    "evaluate.expt_name=$expt" \
    "evaluate.record_details=true" \
    "evaluate.result_dir=recordings" \
    >> "$log" 2>&1

  # 2) codedistill-all (only if recording dir exists)
  local rec_dirs
  rec_dirs=$(ls -d recordings/*."$expt" 2>/dev/null | sort | tail -1)
  if [ -z "$rec_dirs" ]; then
    echo "  no recording produced; skipping distill" | tee -a "$log"
    return
  fi
  echo "  using recording: $rec_dirs" | tee -a "$log"

  run_step "codedistill-all" \
    uv run -m secretagent.cli.learn codedistill-all \
      --learned-dir learned \
      --model "$CD_MODEL" \
      --max-wrong-rate 0.05 \
      "$rec_dirs" \
    >> "$log" 2>&1

  echo "[$(date)] benchmark: $name DONE" | tee -a "$log"
  cd "$ROOT"
}

echo "=== Class 1 codedistill — start at $(date) ==="

# 1) NatPlan calendar
do_bench natplan_calendar "$ROOT/benchmarks/natural_plan" calendar_train_record \
  uv run python expt.py run --config-file conf/calendar.yaml \
    ptools.calendar_scheduling.method=direct \
    ptools.calendar_scheduling.fn=ptools_calendar.calendar_workflow \
    dataset.partition=train "dataset.n=$N_CASES"

# 2) NatPlan meeting
do_bench natplan_meeting "$ROOT/benchmarks/natural_plan" meeting_train_record \
  uv run python expt.py run --config-file conf/meeting.yaml \
    ptools.meeting_planning.method=direct \
    ptools.meeting_planning.fn=ptools_meeting.meeting_workflow \
    dataset.partition=train "dataset.n=$N_CASES"

# 3) NatPlan trip
do_bench natplan_trip "$ROOT/benchmarks/natural_plan" trip_train_record \
  uv run python expt.py run --config-file conf/trip.yaml \
    ptools.trip_planning.method=direct \
    ptools.trip_planning.fn=ptools_trip.trip_workflow \
    dataset.partition=train "dataset.n=$N_CASES"

# 4) MuSR murder
do_bench musr_murder "$ROOT/benchmarks/musr" murder_train_record \
  uv run python expt.py run --config-file conf/murder_workflow.yaml \
    dataset.split=murder_mysteries_train "dataset.n=$N_CASES"

# 5) BBH sports
do_bench bbh_sports "$ROOT/benchmarks/bbh/sports_understanding" sports_train_record \
  uv run python -m secretagent.cli.expt run \
    --interface ptools.are_sports_in_sentence_consistent \
    ptools.are_sports_in_sentence_consistent.method=direct \
    ptools.are_sports_in_sentence_consistent.fn=ptools.sports_understanding_workflow \
    dataset.split=train "dataset.n=$N_CASES"

# 6) BBH penguins
do_bench bbh_penguins "$ROOT/benchmarks/bbh/penguins_in_a_table" penguins_train_record \
  uv run python -m secretagent.cli.expt run \
    --interface ptools.answer_penguin_question \
    ptools.answer_penguin_question.method=direct \
    ptools.answer_penguin_question.fn=ptools.penguins_workflow \
    dataset.split=train "dataset.n=$N_CASES"

# 7) BBH geometric
do_bench bbh_geometric "$ROOT/benchmarks/bbh/geometric_shapes" geometric_train_record \
  uv run python -m secretagent.cli.expt run \
    --interface ptools.identify_shape \
    ptools.identify_shape.method=direct \
    ptools.identify_shape.fn=ptools.geometric_shapes_workflow \
    dataset.split=train "dataset.n=$N_CASES"

# 8) BBH date_understanding (uses zeroshot_unstructured_workflow as workflow)
do_bench bbh_date "$ROOT/benchmarks/bbh/date_understanding" date_train_record \
  uv run python -m secretagent.cli.expt run \
    --interface ptools.answer_date_question \
    ptools.answer_date_question.method=direct \
    ptools.answer_date_question.fn=ptools.zeroshot_unstructured_workflow \
    dataset.split=train "dataset.n=$N_CASES"

# 9) MedCalc
do_bench medcalc "$ROOT/benchmarks/medcalc" medcalc_train_record \
  uv run python expt.py run --config-file conf/workflow.yaml \
    dataset.split=train "dataset.n=$N_CASES"

# 10) FinQA
do_bench finqa "$ROOT/benchmarks/finqa" finqa_train_record \
  uv run python expt.py run --config-file conf/workflow.yaml \
    dataset.split=train "dataset.n=$N_CASES"

# 11/12/13) RuleArena nba, tax, airline
for dom in nba tax airline; do
  do_bench "rulearena_${dom}" "$ROOT/benchmarks/rulearena" "${dom}_train_record" \
    uv run python expt.py run \
      "dataset.domain=${dom}" \
      ptools.compute_rulearena_answer.method=direct \
      ptools.compute_rulearena_answer.fn=ptools.l1_extract_workflow \
      dataset.split=train "dataset.n=$N_CASES"
done

echo "=== Class 1 codedistill — DONE at $(date) ==="
echo "Per-benchmark logs in $LOG_DIR/class1_*.log"
