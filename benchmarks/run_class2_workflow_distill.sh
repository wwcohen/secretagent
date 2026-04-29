#!/bin/bash
# Class 2: Workflow codedistill using existing tools
# - For each benchmark, generate a top-level workflow function that calls
#   pre-existing pure-Python helpers and/or simulate ptools
# - Prompt includes: dataset examples, introspected tool signatures,
#   cross-benchmark reference workflows, sampled tool-call traces
# - 80/20 train/val holdout reported per benchmark
# Usage: nohup bash run_class2_workflow_distill.sh > class2_all.log 2>&1 &

set +e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
mkdir -p "$LOG_DIR"

set -a
source "$ROOT/.env"
set +a

CD_MODEL="${CD_MODEL:-claude-opus-4-6}"

run_wf() {
  local label="$1"; shift
  echo "============================================================"
  echo "[$(date)] class2 $label: starting"
  echo "------------------------------------------------------------"
  "$@" 2>&1
  local rc=$?
  echo "[$(date)] class2 $label: rc=$rc"
}

echo "=== Class 2 workflow-codedistill — start at $(date) ==="

# Latest recordings of train splits (produced by Phase 1)
latest_rec() {
  local cwd="$1"; local pat="$2"
  ls -d "$cwd"/recordings/*."$pat" 2>/dev/null | sort | tail -1
}

# 1) NatPlan calendar: ref = meeting+trip; trace = calendar_train_record
cd "$ROOT/benchmarks/natural_plan"
TRACE_CAL=$(latest_rec "." calendar_train_record)
run_wf natplan_calendar \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface calendar_scheduling \
    --dataset-file data/calendar_train_50.json \
    --output-field golden_plan \
    --tool-module ptools_calendar \
    --reference-file ptools_meeting.py --reference-file ptools_trip.py \
    ${TRACE_CAL:+--trace-dir "$TRACE_CAL"} \
    --learned-dir learned_class2 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_natplan_calendar.log" 2>&1

# 2) NatPlan meeting: ref = calendar+trip
TRACE_MEET=$(latest_rec "." meeting_train_record)
run_wf natplan_meeting \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface meeting_planning \
    --dataset-file data/meeting_train_50.json \
    --output-field golden_plan \
    --tool-module ptools_meeting \
    --reference-file ptools_calendar.py --reference-file ptools_trip.py \
    ${TRACE_MEET:+--trace-dir "$TRACE_MEET"} \
    --learned-dir learned_class2 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_natplan_meeting.log" 2>&1

# 3) NatPlan trip
TRACE_TRIP=$(latest_rec "." trip_train_record)
run_wf natplan_trip \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface trip_planning \
    --dataset-file data/trip_train_50.json \
    --output-field golden_plan \
    --tool-module ptools_trip \
    --reference-file ptools_calendar.py --reference-file ptools_meeting.py \
    ${TRACE_TRIP:+--trace-dir "$TRACE_TRIP"} \
    --learned-dir learned_class2 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_natplan_trip.log" 2>&1

cd "$ROOT"

# 4) MuSR murder: SKIP — raw {split, examples} dataset shape (would need
#    a conversion shim that's out of scope for this run).
echo "[$(date)] class2 musr_murder: SKIPPED (raw dataset format)"

# BBH quartet: cross-reference among themselves
BBH_DIR="$ROOT/benchmarks/bbh"

# 5) BBH sports
cd "$BBH_DIR/sports_understanding"
TRACE=$(latest_rec "." sports_train_record)
run_wf bbh_sports \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface are_sports_in_sentence_consistent \
    --dataset-file data/train.json \
    --tool-module ptools \
    --reference-file ../penguins_in_a_table/ptools.py \
    --reference-file ../geometric_shapes/ptools.py \
    --reference-file ../date_understanding/ptools.py \
    ${TRACE:+--trace-dir "$TRACE"} \
    --learned-dir learned_class2 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_bbh_sports.log" 2>&1

# 6) BBH penguins
cd "$BBH_DIR/penguins_in_a_table"
TRACE=$(latest_rec "." penguins_train_record)
run_wf bbh_penguins \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface answer_penguin_question \
    --dataset-file data/train.json \
    --tool-module ptools \
    --reference-file ../sports_understanding/ptools.py \
    --reference-file ../geometric_shapes/ptools.py \
    --reference-file ../date_understanding/ptools.py \
    ${TRACE:+--trace-dir "$TRACE"} \
    --learned-dir learned_class2 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_bbh_penguins.log" 2>&1

# 7) BBH geometric
cd "$BBH_DIR/geometric_shapes"
TRACE=$(latest_rec "." geometric_train_record)
run_wf bbh_geometric \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface identify_shape \
    --dataset-file data/train.json \
    --tool-module ptools \
    --reference-file ../sports_understanding/ptools.py \
    --reference-file ../penguins_in_a_table/ptools.py \
    --reference-file ../date_understanding/ptools.py \
    ${TRACE:+--trace-dir "$TRACE"} \
    --learned-dir learned_class2 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_bbh_geometric.log" 2>&1

# 8) BBH date
cd "$BBH_DIR/date_understanding"
TRACE=$(latest_rec "." date_train_record)
run_wf bbh_date \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface answer_date_question \
    --dataset-file data/train.json \
    --tool-module ptools \
    --reference-file ../sports_understanding/ptools.py \
    --reference-file ../penguins_in_a_table/ptools.py \
    --reference-file ../geometric_shapes/ptools.py \
    ${TRACE:+--trace-dir "$TRACE"} \
    --learned-dir learned_class2 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_bbh_date.log" 2>&1

# 9) MedCalc
cd "$ROOT/benchmarks/medcalc"
TRACE=$(latest_rec "." medcalc_train_record)
run_wf medcalc \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface calculate_medical_value \
    --dataset-file data_train_100_diverse.json \
    --tool-module ptools \
    --reference-file ../natural_plan/ptools_calendar.py \
    ${TRACE:+--trace-dir "$TRACE"} \
    --learned-dir learned_class2 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_medcalc.log" 2>&1

# 10) FinQA
cd "$ROOT/benchmarks/finqa"
TRACE=$(latest_rec "." finqa_train_record)
run_wf finqa \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface answer_finqa \
    --dataset-file data/train.json \
    --tool-module ptools \
    --reference-file ../natural_plan/ptools_calendar.py \
    --reference-file ../medcalc/ptools.py \
    ${TRACE:+--trace-dir "$TRACE"} \
    --learned-dir learned_class2 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_finqa.log" 2>&1

# 11) RuleArena airline (only one with pre-built train json)
cd "$ROOT/benchmarks/rulearena"
TRACE=$(latest_rec "." airline_train_record)
run_wf rulearena_airline \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface compute_rulearena_answer \
    --dataset-file airline_train_50.json \
    --tool-module ptools \
    --reference-file ../natural_plan/ptools_calendar.py \
    --reference-file ../medcalc/ptools.py \
    ${TRACE:+--trace-dir "$TRACE"} \
    --learned-dir learned_class2 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_rulearena_airline.log" 2>&1

echo "[$(date)] class2 rulearena nba/tax: SKIPPED (no pre-built train Dataset json)"

cd "$ROOT"
echo "=== Class 2 workflow-codedistill — DONE at $(date) ==="
echo "Per-benchmark logs in $LOG_DIR/class2_*.log"
