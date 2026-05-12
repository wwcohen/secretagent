#!/bin/bash
# gemini: Class 2 workflow-codedistill on FULL-SIZE datasets using GEMINI 3.1 PRO PREVIEW
# as learner. Output: learned_class2_gemini/ (and _gemini_object/_gemini_team/_gemini_murder for musr).
# Includes meeting golden_plan list→str fix at start (else meeting → 0% from list bug).
set +e
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
mkdir -p "$LOG_DIR"
set -a; source "$ROOT/.env"; set +a
CD_MODEL="${CD_MODEL:-gemini/gemini-3.1-pro-preview}"

# ===== Step 0: convert meeting golden_plan list → str (one-shot, idempotent) =====
MEET_DS_FIXED="/tmp/meeting_train_gemini.json"
if [ ! -f "$MEET_DS_FIXED" ]; then
  uv run python -c "
import json
src = json.load(open('$ROOT/benchmarks/natural_plan/data/meeting_train.json'))
cases = src['cases'] if 'cases' in src else src
for c in cases:
    eo = c.get('expected_output')
    if isinstance(eo, dict) and isinstance(eo.get('golden_plan'), list):
        eo['golden_plan'] = 'SOLUTION:\n' + '\n'.join(eo['golden_plan'])
out = src if 'cases' in src else cases
json.dump(out, open('$MEET_DS_FIXED', 'w'), indent=2)
print(f'wrote $MEET_DS_FIXED')
" 2>&1 | grep -v warning
fi

# ===== Step 0b: prepare musr/tabmwp Dataset-format JSON (if needed) =====
prep_musr() {
  local task=$1
  local split_train=object_placements_train
  [ "$task" = team ] && split_train=team_allocation_train
  [ "$task" = murder ] && split_train=murder_mysteries_train
  local out="/tmp/musr_${task}_train_dataset.json"
  if [ ! -f "$out" ]; then
    uv run python -c "
import sys; sys.path.insert(0, '$ROOT/benchmarks/musr')
import expt
ds = expt.load_dataset('$split_train')
print(ds.model_dump_json(indent=2), file=open('$out', 'w'))
" 2>/dev/null
  fi
  echo "$out"
}
prep_tabmwp() {
  local out="/tmp/tabmwp_train_dataset.json"
  if [ ! -f "$out" ]; then
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
  fi
  echo "$out"
}
DS_OBJ=$(prep_musr object | tail -1)
DS_TEAM=$(prep_musr team | tail -1)
DS_MURDER=$(prep_musr murder | tail -1)
DS_TABMWP=$(prep_tabmwp | tail -1)

# ===== Trace dirs (reuse opus recordings) =====
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
TRACE_OBJ=$(ls -d "$ROOT/benchmarks/musr/recordings_full"/*musr_object_train_full 2>/dev/null | tail -1)
TRACE_TEAM=$(ls -d "$ROOT/benchmarks/musr/recordings_full"/*musr_team_train_full 2>/dev/null | tail -1)
TRACE_MURDER=$(ls -d "$ROOT/benchmarks/musr/recordings_full"/*musr_murder_train_train_full 2>/dev/null | tail -1)
TRACE_TABMWP=$(ls -d "$ROOT/benchmarks/tabmwp/tabmwp/recordings_full"/*tabmwp_train_full 2>/dev/null | tail -1)

# Cross-dataset files
CAL_DS="$ROOT/benchmarks/natural_plan/data/calendar_train.json"
TRIP_DS="$ROOT/benchmarks/natural_plan/data/trip_train.json"

run_wf() {
  local label="$1"; shift
  echo "[$(date)] class2_gemini $label START — model=$CD_MODEL"
  "$@"
  echo "[$(date)] class2_gemini $label END rc=$?"
}

echo "=== Class 2 gemini (Gemini Pro Preview, full-size) — start at $(date) ==="

# === Family A: NatPlan (sequential within family — share recordings_full dir) ===
famA() {
  cd "$ROOT/benchmarks/natural_plan"
  run_wf natplan_calendar \
    uv run -m secretagent.cli.learn workflow-codedistill \
      --interface calendar_scheduling --dataset-file data/calendar_train.json --output-field golden_plan \
      --tool-module ptools_calendar --conf-file conf/calendar.yaml \
      --reference-file ptools_meeting.py --reference-file ptools_trip.py \
      ${CAL_TRACE:+--trace-dir "$CAL_TRACE"} \
      ${MEET_TRACE:+--cross-trace-dir "$MEET_TRACE"} \
      ${TRIP_TRACE:+--cross-trace-dir "$TRIP_TRACE"} \
      --learned-dir learned_class2_gemini --model "$CD_MODEL" \
      --backoff true --backoff-method simulate \
      > "$LOG_DIR/class2_gemini_natplan_calendar.log" 2>&1

  run_wf natplan_meeting \
    uv run -m secretagent.cli.learn workflow-codedistill \
      --interface meeting_planning --dataset-file "$MEET_DS_FIXED" --output-field golden_plan \
      --tool-module ptools_meeting --conf-file conf/meeting.yaml \
      --reference-file ptools_calendar.py --reference-file ptools_trip.py \
      ${MEET_TRACE:+--trace-dir "$MEET_TRACE"} \
      ${CAL_TRACE:+--cross-trace-dir "$CAL_TRACE"} \
      ${TRIP_TRACE:+--cross-trace-dir "$TRIP_TRACE"} \
      --learned-dir learned_class2_gemini --model "$CD_MODEL" \
      --backoff true --backoff-method simulate \
      > "$LOG_DIR/class2_gemini_natplan_meeting.log" 2>&1

  run_wf natplan_trip \
    uv run -m secretagent.cli.learn workflow-codedistill \
      --interface trip_planning --dataset-file data/trip_train.json --output-field golden_plan \
      --tool-module ptools_trip --conf-file conf/trip.yaml \
      --reference-file ptools_calendar.py --reference-file ptools_meeting.py \
      ${TRIP_TRACE:+--trace-dir "$TRIP_TRACE"} \
      ${CAL_TRACE:+--cross-trace-dir "$CAL_TRACE"} \
      ${MEET_TRACE:+--cross-trace-dir "$MEET_TRACE"} \
      --learned-dir learned_class2_gemini --model "$CD_MODEL" \
      --backoff true --backoff-method simulate \
      > "$LOG_DIR/class2_gemini_natplan_trip.log" 2>&1
}

# === Family B: BBH 4 ===
famB() {
  for sub_iface in "sports_understanding:are_sports_in_sentence_consistent" \
                   "penguins_in_a_table:answer_penguin_question" \
                   "geometric_shapes:identify_shape" \
                   "date_understanding:answer_date_question"; do
    IFS=":" read sub iface <<< "$sub_iface"
    cd "$ROOT/benchmarks/bbh/$sub"
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
        --learned-dir learned_class2_gemini --model "$CD_MODEL" --backoff true --backoff-method simulate \
        > "$LOG_DIR/class2_gemini_bbh_${sub}.log" 2>&1
  done
}

# === Family C: medcalc + finqa + rulearena_airline ===
famC() {
  cd "$ROOT/benchmarks/medcalc"
  run_wf medcalc \
    uv run -m secretagent.cli.learn workflow-codedistill \
      --interface calculate_medical_value --dataset-file data_train_100_diverse.json \
      --tool-module ptools --conf-file conf/workflow.yaml \
      ${MEDCALC_TRACE:+--trace-dir "$MEDCALC_TRACE"} \
      --learned-dir learned_class2_gemini --model "$CD_MODEL" --backoff true --backoff-method simulate \
      > "$LOG_DIR/class2_gemini_medcalc.log" 2>&1

  cd "$ROOT/benchmarks/finqa"
  run_wf finqa \
    uv run -m secretagent.cli.learn workflow-codedistill \
      --interface answer_finqa --dataset-file data/train.json \
      --tool-module ptools --conf-file conf/workflow.yaml \
      ${FINQA_TRACE:+--trace-dir "$FINQA_TRACE"} \
      --learned-dir learned_class2_gemini --model "$CD_MODEL" --backoff true --backoff-method simulate \
      > "$LOG_DIR/class2_gemini_finqa.log" 2>&1

  cd "$ROOT/benchmarks/rulearena"
  run_wf rulearena_airline \
    uv run -m secretagent.cli.learn workflow-codedistill \
      --interface compute_rulearena_answer --dataset-file airline_train_50.json \
      --tool-module ptools \
      ${AIRLINE_TRACE:+--trace-dir "$AIRLINE_TRACE"} \
      --learned-dir learned_class2_gemini --model "$CD_MODEL" --backoff true --backoff-method simulate \
      > "$LOG_DIR/class2_gemini_rulearena_airline.log" 2>&1
}

# === Family D: musr (sequential — same iface name across object/team/murder) ===
# Use SEPARATE output dirs to avoid same-iface collision.
famD() {
  cd "$ROOT/benchmarks/musr"
  run_wf musr_object \
    uv run -m secretagent.cli.learn workflow-codedistill \
      --interface answer_question_workflow --dataset-file "$DS_OBJ" --output-field answer_index \
      --tool-module ptools_object --conf-file conf/object_workflow.yaml \
      --reference-file ptools_team.py --reference-file ptools_murder.py \
      ${TRACE_OBJ:+--trace-dir "$TRACE_OBJ"} \
      ${TRACE_MURDER:+--cross-trace-dir "$TRACE_MURDER"} \
      --learned-dir learned_class2_gemini_object --model "$CD_MODEL" \
      --backoff true --backoff-method simulate \
      > "$LOG_DIR/class2_gemini_musr_object.log" 2>&1

  run_wf musr_team \
    uv run -m secretagent.cli.learn workflow-codedistill \
      --interface answer_question_workflow --dataset-file "$DS_TEAM" --output-field answer_index \
      --tool-module ptools_team --conf-file conf/team_workflow.yaml \
      --reference-file ptools_object.py --reference-file ptools_murder.py \
      ${TRACE_TEAM:+--trace-dir "$TRACE_TEAM"} \
      ${TRACE_MURDER:+--cross-trace-dir "$TRACE_MURDER"} \
      --learned-dir learned_class2_gemini_team --model "$CD_MODEL" \
      --backoff true --backoff-method simulate \
      > "$LOG_DIR/class2_gemini_musr_team.log" 2>&1

  run_wf musr_murder \
    uv run -m secretagent.cli.learn workflow-codedistill \
      --interface answer_question_workflow --dataset-file "$DS_MURDER" --output-field answer_index \
      --tool-module ptools_murder --conf-file conf/murder_workflow.yaml \
      --reference-file ptools_object.py --reference-file ptools_team.py \
      ${TRACE_MURDER:+--trace-dir "$TRACE_MURDER"} \
      ${TRACE_OBJ:+--cross-trace-dir "$TRACE_OBJ"} \
      --learned-dir learned_class2_gemini_murder --model "$CD_MODEL" \
      --backoff true --backoff-method simulate \
      > "$LOG_DIR/class2_gemini_musr_murder.log" 2>&1
}

# === Family E: tabmwp ===
famE() {
  cd "$ROOT/benchmarks/tabmwp"
  run_wf tabmwp \
    uv run -m secretagent.cli.learn workflow-codedistill \
      --interface tabmwp_solve --dataset-file "$DS_TABMWP" --output-field answer \
      --tool-module ptools --conf-file conf/workflow_incontext.yaml \
      ${TRACE_TABMWP:+--trace-dir "$TRACE_TABMWP"} \
      --learned-dir learned_class2_gemini --model "$CD_MODEL" --backoff true --backoff-method simulate \
      > "$LOG_DIR/class2_gemini_tabmwp.log" 2>&1
}

famA & PA=$!
famB & PB=$!
famC & PC=$!
famD & PD=$!
famE & PE=$!
wait $PA $PB $PC $PD $PE
echo "=== Class 2 gemini — DONE at $(date) ==="
