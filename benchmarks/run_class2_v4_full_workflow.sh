#!/bin/bash
# C': Class 2 opus workflow-codedistill on FULL-SIZE datasets, with backoff=True
# (LLM-only fallback when generated returns None). Output: learned_class2_opus/.
set +e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
set -a; source "$ROOT/.env"; set +a
CD_MODEL="${CD_MODEL:-claude-opus-4-6}"

# Trace dirs from full-size recordings
NF="$ROOT/benchmarks/natural_plan/recordings_full"
CAL_TRACE=$(ls -d "$NF"/*natplan_calendar_train_full 2>/dev/null | tail -1)
MEET_TRACE=$(ls -d "$NF"/*natplan_meeting_train_full 2>/dev/null | tail -1)
TRIP_TRACE=$(ls -d "$NF"/*natplan_trip_train_full 2>/dev/null | tail -1)
SPORTS_TRACE=$(ls -d "$ROOT/benchmarks/bbh/sports_understanding/recordings_full"/*train_full 2>/dev/null | tail -1)
PENG_TRACE=$(ls -d "$ROOT/benchmarks/bbh/penguins_in_a_table/recordings_full"/*train_full 2>/dev/null | tail -1)
GEO_TRACE=$(ls -d "$ROOT/benchmarks/bbh/geometric_shapes/recordings_full"/*train_full 2>/dev/null | tail -1)
DATE_TRACE=$(ls -d "$ROOT/benchmarks/bbh/date_understanding/recordings_full"/*train_full 2>/dev/null | tail -1)
MEDCALC_TRACE=$(ls -d "$ROOT/benchmarks/medcalc/recordings_full"/*train_full 2>/dev/null | tail -1)
FINQA_TRACE=$(ls -d "$ROOT/benchmarks/finqa/finqa/recordings_full"/*train_full 2>/dev/null | tail -1)
AIRLINE_TRACE=$(ls -d "$ROOT/benchmarks/rulearena/recordings_full"/*airline_train_full 2>/dev/null | tail -1)

# Datasets — use the ones available (some have _50 suffix only)
CAL_DS="$ROOT/benchmarks/natural_plan/data/calendar_train.json"
MEET_DS="$ROOT/benchmarks/natural_plan/data/meeting_train.json"
TRIP_DS="$ROOT/benchmarks/natural_plan/data/trip_train.json"
SPORTS_DS="$ROOT/benchmarks/bbh/sports_understanding/data/train.json"
GEO_DS="$ROOT/benchmarks/bbh/geometric_shapes/data/train.json"
PENG_DS="$ROOT/benchmarks/bbh/penguins_in_a_table/data/train.json"
DATE_DS="$ROOT/benchmarks/bbh/date_understanding/data/train.json"
MEDCALC_DS="$ROOT/benchmarks/medcalc/data_train_100_diverse.json"
FINQA_DS="$ROOT/benchmarks/finqa/finqa/data/train.json"
AIRLINE_DS="$ROOT/benchmarks/rulearena/airline_train_50.json"

run_wf() {
  local label="$1"; shift
  echo "============================================================"
  echo "[$(date)] class2_v4 $label START"
  "$@" 2>&1
  echo "[$(date)] class2_v4 $label END rc=$?"
}

echo "=== Class 2 opus (full-size, backoff=True) — start at $(date) ==="

# 1) NatPlan calendar
cd "$ROOT/benchmarks/natural_plan"
run_wf natplan_calendar \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface calendar_scheduling --dataset-file data/calendar_train.json --output-field golden_plan \
    --tool-module ptools_calendar --conf-file conf/calendar.yaml \
    --reference-file ptools_meeting.py --reference-file ptools_trip.py \
    ${CAL_TRACE:+--trace-dir "$CAL_TRACE"} \
    ${MEET_TRACE:+--cross-trace-dir "$MEET_TRACE"} \
    ${TRIP_TRACE:+--cross-trace-dir "$TRIP_TRACE"} \
    --cross-dataset-file "$MEET_DS" --cross-dataset-file "$TRIP_DS" \
    --learned-dir learned_class2_opus --model "$CD_MODEL" \
    --backoff true --backoff-method simulate \
  > "$LOG_DIR/class2_opus_natplan_calendar.log" 2>&1

run_wf natplan_meeting \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface meeting_planning --dataset-file data/meeting_train.json --output-field golden_plan \
    --tool-module ptools_meeting --conf-file conf/meeting.yaml \
    --reference-file ptools_calendar.py --reference-file ptools_trip.py \
    ${MEET_TRACE:+--trace-dir "$MEET_TRACE"} \
    ${CAL_TRACE:+--cross-trace-dir "$CAL_TRACE"} \
    ${TRIP_TRACE:+--cross-trace-dir "$TRIP_TRACE"} \
    --cross-dataset-file "$CAL_DS" --cross-dataset-file "$TRIP_DS" \
    --learned-dir learned_class2_opus --model "$CD_MODEL" \
    --backoff true \
  > "$LOG_DIR/class2_opus_natplan_meeting.log" 2>&1

run_wf natplan_trip \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface trip_planning --dataset-file data/trip_train.json --output-field golden_plan \
    --tool-module ptools_trip --conf-file conf/trip.yaml \
    --reference-file ptools_calendar.py --reference-file ptools_meeting.py \
    ${TRIP_TRACE:+--trace-dir "$TRIP_TRACE"} \
    ${CAL_TRACE:+--cross-trace-dir "$CAL_TRACE"} \
    ${MEET_TRACE:+--cross-trace-dir "$MEET_TRACE"} \
    --cross-dataset-file "$CAL_DS" --cross-dataset-file "$MEET_DS" \
    --learned-dir learned_class2_opus --model "$CD_MODEL" \
    --backoff true \
  > "$LOG_DIR/class2_opus_natplan_trip.log" 2>&1

# 2) BBH quartet
for sub_iface_wf in "sports_understanding:are_sports_in_sentence_consistent" \
                    "penguins_in_a_table:answer_penguin_question" \
                    "geometric_shapes:identify_shape" \
                    "date_understanding:answer_date_question"; do
  IFS=":" read sub iface <<< "$sub_iface_wf"
  cd "$ROOT/benchmarks/bbh/$sub"
  TRACE_VAR=$(echo "$sub" | tr a-z A-Z | sed 's/_/_/g')
  trace=""
  case $sub in
    sports_understanding) trace="$SPORTS_TRACE" ;;
    penguins_in_a_table) trace="$PENG_TRACE" ;;
    geometric_shapes) trace="$GEO_TRACE" ;;
    date_understanding) trace="$DATE_TRACE" ;;
  esac
  run_wf "bbh_$sub" \
    uv run -m secretagent.cli.learn workflow-codedistill \
      --interface "$iface" --dataset-file data/train.json --tool-module ptools \
      --conf-file conf/conf.yaml \
      --reference-file ../sports_understanding/ptools.py --reference-file ../penguins_in_a_table/ptools.py \
      --reference-file ../geometric_shapes/ptools.py --reference-file ../date_understanding/ptools.py \
      ${trace:+--trace-dir "$trace"} \
      --learned-dir learned_class2_opus --model "$CD_MODEL" --backoff true \
    > "$LOG_DIR/class2_opus_bbh_${sub}.log" 2>&1
done

# 3) MedCalc
cd "$ROOT/benchmarks/medcalc"
run_wf medcalc \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface calculate_medical_value --dataset-file data_train_100_diverse.json \
    --tool-module ptools --conf-file conf/workflow.yaml \
    ${MEDCALC_TRACE:+--trace-dir "$MEDCALC_TRACE"} \
    --learned-dir learned_class2_opus --model "$CD_MODEL" --backoff true \
  > "$LOG_DIR/class2_opus_medcalc.log" 2>&1

# 4) FinQA
cd "$ROOT/benchmarks/finqa"
run_wf finqa \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface answer_finqa --dataset-file data/train.json \
    --tool-module ptools --conf-file conf/workflow.yaml \
    ${FINQA_TRACE:+--trace-dir "$FINQA_TRACE"} \
    --learned-dir learned_class2_opus --model "$CD_MODEL" --backoff true \
  > "$LOG_DIR/class2_opus_finqa.log" 2>&1

# 5) RuleArena airline only (other domains lack train Dataset json)
cd "$ROOT/benchmarks/rulearena"
run_wf rulearena_airline \
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface compute_rulearena_answer --dataset-file airline_train_50.json \
    --tool-module ptools \
    ${AIRLINE_TRACE:+--trace-dir "$AIRLINE_TRACE"} \
    --learned-dir learned_class2_opus --model "$CD_MODEL" --backoff true \
  > "$LOG_DIR/class2_opus_rulearena_airline.log" 2>&1

cd "$ROOT"
echo "=== Class 2 opus — DONE at $(date) ==="
