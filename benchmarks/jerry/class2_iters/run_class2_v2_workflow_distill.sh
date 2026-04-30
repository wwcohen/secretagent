#!/bin/bash
# Class 2 v2: re-run failed benchmarks with richer prompt
# - Adds cross-benchmark i/o + cross-benchmark traces (workflow + react)
# - Bug fixes: save code even at 0%, abstained cases now feed error feedback,
#   no round-1 early-stop for workflow distill
# Usage: nohup bash run_class2_v2_workflow_distill.sh > class2_v2_all.log 2>&1 &

set +e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
mkdir -p "$LOG_DIR"

set -a
source "$ROOT/.env"
set +a

CD_MODEL="${CD_MODEL:-claude-opus-4-6}"

# Cross-benchmark trace pool (latest train_record dirs for each)
CAL_TRACE=$(ls -d "$ROOT/benchmarks/natural_plan/recordings/"*.calendar_train_record 2>/dev/null | tail -1)
MEET_TRACE=$(ls -d "$ROOT/benchmarks/natural_plan/recordings/"*.meeting_train_record 2>/dev/null | tail -1)
TRIP_TRACE=$(ls -d "$ROOT/benchmarks/natural_plan/recordings/"*.trip_train_record 2>/dev/null | tail -1)
MUSR_TRACE=$(ls -d "$ROOT/benchmarks/musr/recordings/"*.murder_train_record 2>/dev/null | tail -1)
SPORTS_TRACE=$(ls -d "$ROOT/benchmarks/bbh/sports_understanding/recordings/"*.sports_train_record 2>/dev/null | tail -1)
GEO_TRACE=$(ls -d "$ROOT/benchmarks/bbh/geometric_shapes/recordings/"*.bbh_geometric_train_record_v2 2>/dev/null | tail -1)
PENG_TRACE=$(ls -d "$ROOT/benchmarks/bbh/penguins_in_a_table/recordings/"*.bbh_penguins_train_record_v2 2>/dev/null | tail -1)
DATE_TRACE=$(ls -d "$ROOT/benchmarks/bbh/date_understanding/recordings/"*.date_train_record_v4 2>/dev/null | tail -1)
MEDCALC_TRACE=$(ls -d "$ROOT/benchmarks/medcalc/recordings/"*.medcalc_train_record 2>/dev/null | tail -1)
FINQA_TRACE=$(ls -d "$ROOT/benchmarks/finqa/recordings/"*.finqa_train_record 2>/dev/null | tail -1)
AIRLINE_TRACE=$(ls -d "$ROOT/benchmarks/rulearena/recordings/"*.airline_train_record 2>/dev/null | tail -1)

# ReAct traces (only musr/finqa have them)
MUSR_REACT=$(ls -d "$ROOT/benchmarks/musr/recordings_class3/"*.murder_react_train 2>/dev/null | tail -1)
FINQA_REACT=$(ls -d "$ROOT/benchmarks/finqa/recordings_class3/"*.finqa_react_train 2>/dev/null | tail -1)

# Cross-benchmark dataset files
CAL_DS="$ROOT/benchmarks/natural_plan/data/calendar_train_50.json"
MEET_DS="$ROOT/benchmarks/natural_plan/data/meeting_train_50.json"
TRIP_DS="$ROOT/benchmarks/natural_plan/data/trip_train_50.json"
SPORTS_DS="$ROOT/benchmarks/bbh/sports_understanding/data/train.json"
GEO_DS="$ROOT/benchmarks/bbh/geometric_shapes/data/train.json"
PENG_DS="$ROOT/benchmarks/bbh/penguins_in_a_table/data/train.json"
DATE_DS="$ROOT/benchmarks/bbh/date_understanding/data/train.json"
MEDCALC_DS="$ROOT/benchmarks/medcalc/data_train_100_diverse.json"
FINQA_DS="$ROOT/benchmarks/finqa/data/train.json"
AIRLINE_DS="$ROOT/benchmarks/rulearena/airline_train_50.json"

run_wf() {
  local label="$1"; shift
  echo "============================================================"
  echo "[$(date)] class2_v2 $label: starting"
  echo "------------------------------------------------------------"
  "$@" 2>&1
  local rc=$?
  echo "[$(date)] class2_v2 $label: rc=$rc"
}

echo "=== Class 2 v2 workflow-codedistill — start at $(date) ==="

# 1) NatPlan calendar (FAILED v1) — cross: meeting+trip+airline+sports
cd "$ROOT/benchmarks/natural_plan"
run_wf natplan_calendar \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface calendar_scheduling \
    --dataset-file data/calendar_train_50.json --output-field golden_plan \
    --tool-module ptools_calendar \
    --reference-file ptools_meeting.py --reference-file ptools_trip.py \
    ${CAL_TRACE:+--trace-dir "$CAL_TRACE"} \
    ${MEET_TRACE:+--cross-trace-dir "$MEET_TRACE"} \
    ${TRIP_TRACE:+--cross-trace-dir "$TRIP_TRACE"} \
    ${AIRLINE_TRACE:+--cross-trace-dir "$AIRLINE_TRACE"} \
    --cross-dataset-file "$MEET_DS" --cross-dataset-file "$TRIP_DS" \
    --cross-dataset-file "$AIRLINE_DS" \
    --learned-dir learned_class2_v2 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_v2_natplan_calendar.log" 2>&1

# 2) NatPlan trip (FAILED v1)
run_wf natplan_trip \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface trip_planning \
    --dataset-file data/trip_train_50.json --output-field golden_plan \
    --tool-module ptools_trip \
    --reference-file ptools_calendar.py --reference-file ptools_meeting.py \
    ${TRIP_TRACE:+--trace-dir "$TRIP_TRACE"} \
    ${CAL_TRACE:+--cross-trace-dir "$CAL_TRACE"} \
    ${MEET_TRACE:+--cross-trace-dir "$MEET_TRACE"} \
    ${MUSR_TRACE:+--cross-trace-dir "$MUSR_TRACE"} \
    --cross-dataset-file "$CAL_DS" --cross-dataset-file "$MEET_DS" \
    --cross-dataset-file "$MEDCALC_DS" \
    --learned-dir learned_class2_v2 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_v2_natplan_trip.log" 2>&1

cd "$ROOT"

# 3) BBH sports (FAILED v1)
cd "$ROOT/benchmarks/bbh/sports_understanding"
run_wf bbh_sports \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface are_sports_in_sentence_consistent \
    --dataset-file data/train.json --tool-module ptools \
    --reference-file ../penguins_in_a_table/ptools.py \
    --reference-file ../geometric_shapes/ptools.py \
    --reference-file ../date_understanding/ptools.py \
    ${SPORTS_TRACE:+--trace-dir "$SPORTS_TRACE"} \
    ${PENG_TRACE:+--cross-trace-dir "$PENG_TRACE"} \
    ${GEO_TRACE:+--cross-trace-dir "$GEO_TRACE"} \
    ${DATE_TRACE:+--cross-trace-dir "$DATE_TRACE"} \
    --cross-dataset-file "$PENG_DS" --cross-dataset-file "$GEO_DS" \
    --cross-dataset-file "$DATE_DS" \
    --learned-dir learned_class2_v2 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_v2_bbh_sports.log" 2>&1

# 4) BBH penguins (FAILED v1)
cd "$ROOT/benchmarks/bbh/penguins_in_a_table"
run_wf bbh_penguins \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface answer_penguin_question \
    --dataset-file data/train.json --tool-module ptools \
    --reference-file ../sports_understanding/ptools.py \
    --reference-file ../geometric_shapes/ptools.py \
    --reference-file ../date_understanding/ptools.py \
    ${PENG_TRACE:+--trace-dir "$PENG_TRACE"} \
    ${SPORTS_TRACE:+--cross-trace-dir "$SPORTS_TRACE"} \
    ${GEO_TRACE:+--cross-trace-dir "$GEO_TRACE"} \
    ${DATE_TRACE:+--cross-trace-dir "$DATE_TRACE"} \
    --cross-dataset-file "$SPORTS_DS" --cross-dataset-file "$GEO_DS" \
    --cross-dataset-file "$DATE_DS" \
    --learned-dir learned_class2_v2 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_v2_bbh_penguins.log" 2>&1

# 5) BBH date (FAILED v1)
cd "$ROOT/benchmarks/bbh/date_understanding"
run_wf bbh_date \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface answer_date_question \
    --dataset-file data/train.json --tool-module ptools \
    --reference-file ../sports_understanding/ptools.py \
    --reference-file ../penguins_in_a_table/ptools.py \
    --reference-file ../geometric_shapes/ptools.py \
    ${DATE_TRACE:+--trace-dir "$DATE_TRACE"} \
    ${SPORTS_TRACE:+--cross-trace-dir "$SPORTS_TRACE"} \
    ${PENG_TRACE:+--cross-trace-dir "$PENG_TRACE"} \
    ${GEO_TRACE:+--cross-trace-dir "$GEO_TRACE"} \
    --cross-dataset-file "$SPORTS_DS" --cross-dataset-file "$PENG_DS" \
    --cross-dataset-file "$GEO_DS" \
    --learned-dir learned_class2_v2 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_v2_bbh_date.log" 2>&1

cd "$ROOT"

# 6) FinQA (FAILED v1) — has React trace!
cd "$ROOT/benchmarks/finqa"
run_wf finqa \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface answer_finqa \
    --dataset-file data/train.json --tool-module ptools \
    --reference-file ../natural_plan/ptools_calendar.py \
    --reference-file ../medcalc/ptools.py \
    ${FINQA_TRACE:+--trace-dir "$FINQA_TRACE"} \
    ${FINQA_REACT:+--react-trace-dir "$FINQA_REACT"} \
    ${MEDCALC_TRACE:+--cross-trace-dir "$MEDCALC_TRACE"} \
    ${CAL_TRACE:+--cross-trace-dir "$CAL_TRACE"} \
    --cross-dataset-file "$MEDCALC_DS" --cross-dataset-file "$CAL_DS" \
    --learned-dir learned_class2_v2 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_v2_finqa.log" 2>&1

cd "$ROOT"
echo "=== Class 2 v2 workflow-codedistill — DONE at $(date) ==="
