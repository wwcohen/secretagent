#!/bin/bash
# Parallel val evals — n=30, run benchmark families in parallel.
set +e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/benchmarks/val_eval_logs"
mkdir -p "$LOG_DIR"
set -a; source "$ROOT/.env"; set +a
N=30

class2_dir() {
  local cwd="$1"; local iface="$2"
  for d in learned_class2_v3 learned_class2_v2 learned_class2; do
    full=$(ls -td "$cwd/$d/"*"${iface}__workflow_distill" 2>/dev/null | head -1)
    [ -n "$full" ] && { echo "$full"; return; }
  done
}

# Each family runs sequentially internally but families run in parallel
natplan_family() {
  cd "$ROOT/benchmarks/natural_plan"
  for sub in calendar meeting trip; do
    case $sub in
      calendar) iface=calendar_scheduling; wf=ptools_calendar.calendar_workflow ;;
      meeting)  iface=meeting_planning;    wf=ptools_meeting.meeting_workflow  ;;
      trip)     iface=trip_planning;        wf=ptools_trip.trip_workflow ;;
    esac
    LOG="$LOG_DIR/val_natplan_${sub}.log"
    {
      echo "[$(date)] BASELINE $sub"
      uv run python expt.py run --config-file conf/${sub}.yaml \
        ptools.${iface}.method=direct ptools.${iface}.fn=${wf} \
        dataset.partition=valid dataset.n=$N \
        evaluate.expt_name=${sub}_val_baseline evaluate.result_dir=val_results 2>&1 | tail -10
      if [ -f learned/codedistill_config.yaml ]; then
        echo "[$(date)] CLASS1 $sub"
        uv run python expt.py run --config-file conf/${sub}.yaml \
          --config-file learned/codedistill_config.yaml \
          ptools.${iface}.method=direct ptools.${iface}.fn=${wf} \
          dataset.partition=valid dataset.n=$N learn.train_dir=learned \
          evaluate.expt_name=${sub}_val_class1 evaluate.result_dir=val_results 2>&1 | tail -10
      fi
      C2DIR=$(class2_dir "$PWD" "$iface")
      if [ -n "$C2DIR" ]; then
        echo "[$(date)] CLASS2 $sub"
        uv run python expt.py run --config-file conf/${sub}.yaml \
          ptools.${iface}.method=learned_code \
          ptools.${iface}.learner=workflow_distill \
          ptools.${iface}.backoff=false \
          learn.train_dir="$(dirname $C2DIR)" \
          dataset.partition=valid dataset.n=$N \
          evaluate.expt_name=${sub}_val_class2 evaluate.result_dir=val_results 2>&1 | tail -10
      fi
      echo "[$(date)] $sub DONE"
    } > "$LOG" 2>&1
  done
}

musr_family() {
  cd "$ROOT/benchmarks/musr"
  LOG="$LOG_DIR/val_musr_murder.log"
  {
    echo "[$(date)] BASELINE murder"
    uv run python expt.py run --config-file conf/murder_workflow.yaml \
      dataset.split=murder_mysteries_val dataset.n=$N \
      evaluate.expt_name=murder_val_baseline evaluate.result_dir=val_results 2>&1 | tail -10
    if [ -f learned/codedistill_config.yaml ]; then
      echo "[$(date)] CLASS1 murder"
      uv run python expt.py run --config-file conf/murder_workflow.yaml \
        --config-file learned/codedistill_config.yaml \
        dataset.split=murder_mysteries_val dataset.n=$N learn.train_dir=learned \
        evaluate.expt_name=murder_val_class1 evaluate.result_dir=val_results 2>&1 | tail -10
    fi
    if [ -f learned_class3/induced_codedistill_config.yaml ]; then
      echo "[$(date)] CLASS3 murder"
      uv run python expt.py run --config-file conf/murder.yaml \
        --config-file learned_class3/induced_codedistill_config.yaml \
        dataset.split=murder_mysteries_val dataset.n=$N learn.train_dir=learned_class3 \
        evaluate.expt_name=murder_val_class3 evaluate.result_dir=val_results 2>&1 | tail -10
    fi
  } > "$LOG"
}

bbh_family() {
  for s_iw in "sports_understanding:are_sports_in_sentence_consistent:sports_understanding_workflow" \
              "penguins_in_a_table:answer_penguin_question:penguins_workflow" \
              "geometric_shapes:identify_shape:geometric_shapes_workflow" \
              "date_understanding:answer_date_question:zeroshot_unstructured_workflow"; do
    IFS=":" read sub iface wf <<< "$s_iw"
    cd "$ROOT/benchmarks/bbh/$sub"
    LOG="$LOG_DIR/val_bbh_${sub}.log"
    EXTRA=""
    [ "$sub" = "date_understanding" ] && EXTRA="ptools.answer_date_question_orchestrated.method=direct ptools.answer_date_question_orchestrated.fn=ptools.zeroshot_unstructured_workflow"
    {
      echo "[$(date)] BASELINE $sub"
      uv run python -m secretagent.cli.expt run --interface ptools.${iface} \
        ptools.${iface}.method=direct ptools.${iface}.fn=ptools.${wf} \
        $EXTRA llm.model=together_ai/deepseek-ai/DeepSeek-V3.1 \
        dataset.split=valid dataset.n=$N \
        evaluate.expt_name=${sub}_val_baseline evaluate.result_dir=val_results 2>&1 | tail -10
      if [ -f learned/codedistill_config.yaml ]; then
        echo "[$(date)] CLASS1 $sub"
        uv run python -m secretagent.cli.expt run --interface ptools.${iface} \
          --config-file learned/codedistill_config.yaml \
          ptools.${iface}.method=direct ptools.${iface}.fn=ptools.${wf} \
          $EXTRA llm.model=together_ai/deepseek-ai/DeepSeek-V3.1 \
          learn.train_dir=learned dataset.split=valid dataset.n=$N \
          evaluate.expt_name=${sub}_val_class1 evaluate.result_dir=val_results 2>&1 | tail -10
      fi
      C2DIR=$(class2_dir "$PWD" "$iface")
      if [ -n "$C2DIR" ]; then
        echo "[$(date)] CLASS2 $sub"
        uv run python -m secretagent.cli.expt run --interface ptools.${iface} \
          ptools.${iface}.method=learned_code ptools.${iface}.learner=workflow_distill \
          ptools.${iface}.backoff=false $EXTRA \
          llm.model=together_ai/deepseek-ai/DeepSeek-V3.1 \
          learn.train_dir="$(dirname $C2DIR)" \
          dataset.split=valid dataset.n=$N \
          evaluate.expt_name=${sub}_val_class2 evaluate.result_dir=val_results 2>&1 | tail -10
      fi
    } > "$LOG"
  done
}

other_family() {
  cd "$ROOT/benchmarks/medcalc"
  {
    echo "[$(date)] BASELINE medcalc"
    uv run python expt.py run --config-file conf/workflow.yaml \
      dataset.split=valid dataset.n=$N \
      evaluate.expt_name=medcalc_val_baseline evaluate.result_dir=val_results 2>&1 | tail -10
    if [ -f learned/codedistill_config.yaml ]; then
      echo "[$(date)] CLASS1 medcalc"
      uv run python expt.py run --config-file conf/workflow.yaml \
        --config-file learned/codedistill_config.yaml \
        dataset.split=valid dataset.n=$N learn.train_dir=learned \
        evaluate.expt_name=medcalc_val_class1 evaluate.result_dir=val_results 2>&1 | tail -10
    fi
  } > "$LOG_DIR/val_medcalc.log"

  cd "$ROOT/benchmarks/finqa"
  {
    echo "[$(date)] BASELINE finqa"
    uv run python expt.py run --config-file conf/workflow.yaml \
      dataset.split=valid dataset.n=$N \
      evaluate.expt_name=finqa_val_baseline evaluate.result_dir=val_results 2>&1 | tail -10
    if [ -f learned/codedistill_config.yaml ]; then
      echo "[$(date)] CLASS1 finqa"
      uv run python expt.py run --config-file conf/workflow.yaml \
        --config-file learned/codedistill_config.yaml \
        dataset.split=valid dataset.n=$N learn.train_dir=learned \
        evaluate.expt_name=finqa_val_class1 evaluate.result_dir=val_results 2>&1 | tail -10
    fi
  } > "$LOG_DIR/val_finqa.log"

  cd "$ROOT/benchmarks/rulearena"
  for dom in nba tax airline; do
    {
      echo "[$(date)] BASELINE $dom"
      uv run python expt.py run dataset.domain=${dom} \
        ptools.compute_rulearena_answer.method=direct \
        ptools.compute_rulearena_answer.fn=ptools.l1_extract_workflow \
        dataset.split=valid dataset.n=$N \
        evaluate.expt_name=${dom}_val_baseline evaluate.result_dir=val_results 2>&1 | tail -10
      C2DIR=$(class2_dir "$PWD" "compute_rulearena_answer")
      if [ -n "$C2DIR" ] && [ "$dom" = "airline" ]; then
        echo "[$(date)] CLASS2 $dom"
        uv run python expt.py run dataset.domain=${dom} \
          ptools.compute_rulearena_answer.method=learned_code \
          ptools.compute_rulearena_answer.learner=workflow_distill \
          ptools.compute_rulearena_answer.backoff=false \
          learn.train_dir="$(dirname $C2DIR)" \
          dataset.split=valid dataset.n=$N \
          evaluate.expt_name=${dom}_val_class2 evaluate.result_dir=val_results 2>&1 | tail -10
      fi
    } > "$LOG_DIR/val_rulearena_${dom}.log"
  done
}

echo "=== Parallel val evals (n=$N) start at $(date) ==="
natplan_family &
P1=$!
musr_family &
P2=$!
bbh_family &
P3=$!
other_family &
P4=$!
echo "PIDs: natplan=$P1 musr=$P2 bbh=$P3 other=$P4"
wait $P1 $P2 $P3 $P4
echo "=== Parallel val evals DONE at $(date) ==="
