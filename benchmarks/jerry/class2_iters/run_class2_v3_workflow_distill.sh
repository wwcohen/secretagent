#!/bin/bash
# Class 2 v3: re-run the 4 benchmarks where v2 still got 0%
# (sports/trip/date/finqa — generated workflow needed simulate ptools that
# weren't bound during fit-time eval). v3 passes --conf-file so the benchmark's
# default config binds simulate ptools, letting the generated code call them.
set +e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
set -a; source "$ROOT/.env"; set +a
CD_MODEL="${CD_MODEL:-claude-opus-4-6}"

# Trace pool (same as v2)
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
FINQA_REACT=$(ls -d "$ROOT/benchmarks/finqa/recordings_class3/"*.finqa_react_train 2>/dev/null | tail -1)

CAL_DS="$ROOT/benchmarks/natural_plan/data/calendar_train_50.json"
MEET_DS="$ROOT/benchmarks/natural_plan/data/meeting_train_50.json"
TRIP_DS="$ROOT/benchmarks/natural_plan/data/trip_train_50.json"
SPORTS_DS="$ROOT/benchmarks/bbh/sports_understanding/data/train.json"
GEO_DS="$ROOT/benchmarks/bbh/geometric_shapes/data/train.json"
PENG_DS="$ROOT/benchmarks/bbh/penguins_in_a_table/data/train.json"
DATE_DS="$ROOT/benchmarks/bbh/date_understanding/data/train.json"
MEDCALC_DS="$ROOT/benchmarks/medcalc/data_train_100_diverse.json"
FINQA_DS="$ROOT/benchmarks/finqa/data/train.json"

run_wf() {
  local label="$1"; shift
  echo "============================================================"
  echo "[$(date)] class2_v3 $label: starting"
  echo "------------------------------------------------------------"
  "$@" 2>&1
  local rc=$?
  echo "[$(date)] class2_v3 $label: rc=$rc"
}

echo "=== Class 2 v3 workflow-codedistill (with --conf-file binding) — start at $(date) ==="

# 1) NatPlan trip (still 0% in v2 — workflow likely needs simulate tools)
cd "$ROOT/benchmarks/natural_plan"
run_wf natplan_trip \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface trip_planning \
    --dataset-file data/trip_train_50.json --output-field golden_plan \
    --tool-module ptools_trip \
    --conf-file conf/trip.yaml \
    --reference-file ptools_calendar.py --reference-file ptools_meeting.py \
    ${TRIP_TRACE:+--trace-dir "$TRIP_TRACE"} \
    ${CAL_TRACE:+--cross-trace-dir "$CAL_TRACE"} \
    ${MEET_TRACE:+--cross-trace-dir "$MEET_TRACE"} \
    --cross-dataset-file "$CAL_DS" --cross-dataset-file "$MEET_DS" \
    --learned-dir learned_class2_v3 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_v3_natplan_trip.log" 2>&1
cd "$ROOT"

# 2) BBH sports
cd "$ROOT/benchmarks/bbh/sports_understanding"
run_wf bbh_sports \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface are_sports_in_sentence_consistent \
    --dataset-file data/train.json --tool-module ptools \
    --conf-file conf/conf.yaml \
    --reference-file ../penguins_in_a_table/ptools.py \
    --reference-file ../geometric_shapes/ptools.py \
    --reference-file ../date_understanding/ptools.py \
    ${SPORTS_TRACE:+--trace-dir "$SPORTS_TRACE"} \
    ${PENG_TRACE:+--cross-trace-dir "$PENG_TRACE"} \
    ${GEO_TRACE:+--cross-trace-dir "$GEO_TRACE"} \
    --cross-dataset-file "$PENG_DS" --cross-dataset-file "$GEO_DS" \
    --learned-dir learned_class2_v3 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_v3_bbh_sports.log" 2>&1
cd "$ROOT"

# 3) BBH date — needs the answer_date_question_orchestrated override too
cd "$ROOT/benchmarks/bbh/date_understanding"
run_wf bbh_date \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface answer_date_question \
    --dataset-file data/train.json --tool-module ptools \
    --conf-file conf/conf.yaml \
    --reference-file ../sports_understanding/ptools.py \
    --reference-file ../penguins_in_a_table/ptools.py \
    --reference-file ../geometric_shapes/ptools.py \
    ${DATE_TRACE:+--trace-dir "$DATE_TRACE"} \
    ${SPORTS_TRACE:+--cross-trace-dir "$SPORTS_TRACE"} \
    ${GEO_TRACE:+--cross-trace-dir "$GEO_TRACE"} \
    --cross-dataset-file "$SPORTS_DS" --cross-dataset-file "$GEO_DS" \
    --learned-dir learned_class2_v3 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_v3_bbh_date.log" 2>&1
cd "$ROOT"

# 4) FinQA — has React trace
cd "$ROOT/benchmarks/finqa"
run_wf finqa \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface answer_finqa \
    --dataset-file data/train.json --tool-module ptools \
    --conf-file conf/workflow.yaml \
    --reference-file ../natural_plan/ptools_calendar.py \
    --reference-file ../medcalc/ptools.py \
    ${FINQA_TRACE:+--trace-dir "$FINQA_TRACE"} \
    ${FINQA_REACT:+--react-trace-dir "$FINQA_REACT"} \
    ${MEDCALC_TRACE:+--cross-trace-dir "$MEDCALC_TRACE"} \
    --cross-dataset-file "$MEDCALC_DS" --cross-dataset-file "$CAL_DS" \
    --learned-dir learned_class2_v3 --model "$CD_MODEL" \
  > "$LOG_DIR/class2_v3_finqa.log" 2>&1
cd "$ROOT"

echo "=== Class 2 v3 — DONE at $(date) ==="
