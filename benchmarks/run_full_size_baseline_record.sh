#!/bin/bash
# A: Re-record all benchmark train + val rollouts at proper benchmark sizes
# (no n=50 truncation). Sequential per family, families in parallel.
#
# Sizes (per benchmark):
#   natplan_calendar/meeting/trip:  train=100, valid=100   (data has 100 each)
#   musr_murder:                    train=75, val=75       (real splits)
#   bbh_sports/penguins/geometric/date:  train+valid=75    (43 for penguins)
#   medcalc:                        train=100              (data_train_100_diverse.json)
#   finqa:                          train=100, valid=100   (cap finqa val at 100, real has 883)
#   rulearena_airline:              train=50, valid=50     (only 50 train json exists)
#
# Output goes to recordings_full/ to keep separate from old recordings/.
set +e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/benchmarks/full_size_logs"
mkdir -p "$LOG_DIR"
set -a; source "$ROOT/.env"; set +a
DS="together_ai/deepseek-ai/DeepSeek-V3.1"

run_pair() {
  local label="$1"; local cwd="$2"; local n="$3"; shift 3
  local log="$LOG_DIR/baseline_${label}.log"
  echo "============================================================" | tee "$log"
  echo "[$(date)] $label baseline n=$n" | tee -a "$log"
  echo "============================================================" | tee -a "$log"
  cd "$cwd"
  # train
  echo "[$(date)] $label TRAIN n=$n" | tee -a "$log"
  "$@" "dataset.n=$n" "evaluate.expt_name=${label}_train_full" \
    evaluate.record_details=true evaluate.result_dir=recordings_full >> "$log" 2>&1
  echo "[$(date)] $label TRAIN rc=$?" | tee -a "$log"
}

natplan_family() {
  for sub_iface_wf in "calendar:calendar_scheduling:ptools_calendar.calendar_workflow" \
                      "meeting:meeting_planning:ptools_meeting.meeting_workflow" \
                      "trip:trip_planning:ptools_trip.trip_workflow"; do
    IFS=":" read sub iface wf <<< "$sub_iface_wf"
    for partition in train valid; do
      label="natplan_${sub}_${partition}"
      run_pair "$label" "$ROOT/benchmarks/natural_plan" 100 \
        uv run python expt.py run --config-file conf/${sub}.yaml \
          "ptools.${iface}.method=direct" "ptools.${iface}.fn=${wf}" \
          "dataset.partition=${partition}"
    done
  done
}

musr_family() {
  for partition in murder_mysteries_train murder_mysteries_val; do
    label="musr_murder_${partition##*_}"
    run_pair "$label" "$ROOT/benchmarks/musr" 75 \
      uv run python expt.py run --config-file conf/murder_workflow.yaml \
        "dataset.split=${partition}"
  done
}

bbh_family() {
  for sub_iface_wf in "sports_understanding:are_sports_in_sentence_consistent:sports_understanding_workflow:75" \
                      "penguins_in_a_table:answer_penguin_question:penguins_workflow:43" \
                      "geometric_shapes:identify_shape:geometric_shapes_workflow:75" \
                      "date_understanding:answer_date_question:zeroshot_unstructured_workflow:75"; do
    IFS=":" read sub iface wf n <<< "$sub_iface_wf"
    EXTRA=""
    [ "$sub" = "date_understanding" ] && EXTRA="ptools.answer_date_question_orchestrated.method=direct ptools.answer_date_question_orchestrated.fn=ptools.zeroshot_unstructured_workflow"
    for split in train valid; do
      label="bbh_${sub}_${split}"
      run_pair "$label" "$ROOT/benchmarks/bbh/$sub" $n \
        uv run python -m secretagent.cli.expt run --interface "ptools.${iface}" \
          "ptools.${iface}.method=direct" "ptools.${iface}.fn=ptools.${wf}" \
          $EXTRA "llm.model=${DS}" "dataset.split=${split}"
    done
  done
}

other_family() {
  for split in train valid; do
    label="medcalc_${split}"
    run_pair "$label" "$ROOT/benchmarks/medcalc" 100 \
      uv run python expt.py run --config-file conf/workflow.yaml "dataset.split=${split}"
  done
  for split in train valid; do
    label="finqa_${split}"
    run_pair "$label" "$ROOT/benchmarks/finqa" 100 \
      uv run python expt.py run --config-file conf/workflow.yaml "dataset.split=${split}"
  done
  for dom in nba tax airline; do
    for split in train valid; do
      label="rulearena_${dom}_${split}"
      run_pair "$label" "$ROOT/benchmarks/rulearena" 50 \
        uv run python expt.py run "dataset.domain=${dom}" \
          "ptools.compute_rulearena_answer.method=direct" \
          "ptools.compute_rulearena_answer.fn=ptools.l1_extract_workflow" \
          "dataset.split=${split}"
    done
  done
}

echo "=== A: Full-size baseline re-record — start at $(date) ==="
natplan_family & P1=$!
musr_family & P2=$!
bbh_family & P3=$!
other_family & P4=$!
echo "PIDs: natplan=$P1 musr=$P2 bbh=$P3 other=$P4"
wait $P1 $P2 $P3 $P4
echo "=== A baseline re-record DONE at $(date) ==="
