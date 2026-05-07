#!/bin/bash
# E: Full-size val eval for all classes.
# Runs baseline + Class1 opus + Class2 opus + Class3 opus on val splits with proper sizes.
set +e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/benchmarks/full_size_val_logs"
mkdir -p "$LOG_DIR"
set -a; source "$ROOT/.env"; set +a
DS="together_ai/deepseek-ai/DeepSeek-V3.1"

run_eval() {
  local label="$1"; shift
  echo "============================================================" | tee -a "$LOG_DIR/$label.log"
  echo "[$(date)] $label start" | tee -a "$LOG_DIR/$label.log"
  "$@" >> "$LOG_DIR/$label.log" 2>&1
  echo "[$(date)] $label rc=$?" | tee -a "$LOG_DIR/$label.log"
}

# natplan trio
natplan_eval() {
  cd "$ROOT/benchmarks/natural_plan"
  for sub_iface_wf in "calendar:calendar_scheduling:ptools_calendar.calendar_workflow:100" \
                      "meeting:meeting_planning:ptools_meeting.meeting_workflow:100" \
                      "trip:trip_planning:ptools_trip.trip_workflow:100"; do
    IFS=":" read sub iface wf n <<< "$sub_iface_wf"
    # baseline
    run_eval "natplan_${sub}_baseline_full" \
      uv run python expt.py run --config-file conf/${sub}.yaml \
        ptools.${iface}.method=direct ptools.${iface}.fn=${wf} \
        dataset.partition=valid "dataset.n=$n" \
        evaluate.expt_name=${sub}_val_full_baseline evaluate.result_dir=val_results_full
    # class1 opus if config exists
    if [ -f learned_opus/codedistill_config.yaml ]; then
      run_eval "natplan_${sub}_class1_opus_full" \
        uv run python expt.py run --config-file learned_opus/codedistill_config.yaml \
          --config-file conf/${sub}.yaml \
          ptools.${iface}.method=direct ptools.${iface}.fn=${wf} \
          learn.train_dir=learned_opus dataset.partition=valid "dataset.n=$n" \
          evaluate.expt_name=${sub}_val_full_class1_opus evaluate.result_dir=val_results_full
    fi
    # class2 opus if exists
    C2DIR=$(ls -td "$PWD/learned_class2_opus"/*${iface}__workflow_distill 2>/dev/null | head -1)
    if [ -n "$C2DIR" ]; then
      run_eval "natplan_${sub}_class2_opus_full" \
        uv run python expt.py run --config-file conf/${sub}.yaml \
          ptools.${iface}.method=learned_code ptools.${iface}.learner=workflow_distill \
          ptools.${iface}.backoff=true \
          learn.train_dir="$(dirname $C2DIR)" \
          dataset.partition=valid "dataset.n=$n" \
          evaluate.expt_name=${sub}_val_full_class2_opus evaluate.result_dir=val_results_full
    fi
  done
}

musr_eval() {
  cd "$ROOT/benchmarks/musr"
  run_eval "musr_baseline_full" \
    uv run python expt.py run --config-file conf/murder_workflow.yaml \
      dataset.split=murder_mysteries_val dataset.n=75 \
      evaluate.expt_name=murder_val_full_baseline evaluate.result_dir=val_results_full
  if [ -f learned_opus/codedistill_config.yaml ]; then
    run_eval "musr_class1_opus_full" \
      uv run python expt.py run --config-file learned_opus/codedistill_config.yaml \
        --config-file conf/murder_workflow.yaml \
        dataset.split=murder_mysteries_val dataset.n=75 \
        learn.train_dir=learned_opus \
        evaluate.expt_name=murder_val_full_class1_opus evaluate.result_dir=val_results_full
  fi
  # Class 3 v3 induced existed for murder
  if [ -f learned_class3_v3/induced_codedistill_config.yaml ]; then
    run_eval "musr_class3v3_full" \
      uv run python expt.py run --config-file learned_class3_v3/induced_codedistill_config.yaml \
        --config-file conf/murder.yaml \
        learn.train_dir=learned_class3_v3 \
        dataset.split=murder_mysteries_val dataset.n=75 \
        evaluate.expt_name=murder_val_full_class3v3 evaluate.result_dir=val_results_full
  fi
}

bbh_eval() {
  for sub_iface_wf in "sports_understanding:are_sports_in_sentence_consistent:sports_understanding_workflow:75" \
                      "penguins_in_a_table:answer_penguin_question:penguins_workflow:43" \
                      "geometric_shapes:identify_shape:geometric_shapes_workflow:75" \
                      "date_understanding:answer_date_question:zeroshot_unstructured_workflow:75"; do
    IFS=":" read sub iface wf n <<< "$sub_iface_wf"
    cd "$ROOT/benchmarks/bbh/$sub"
    EXTRA=""
    [ "$sub" = "date_understanding" ] && EXTRA="ptools.answer_date_question_orchestrated.method=direct ptools.answer_date_question_orchestrated.fn=ptools.zeroshot_unstructured_workflow"
    run_eval "bbh_${sub}_baseline_full" \
      uv run python -m secretagent.cli.expt run --interface ptools.${iface} \
        ptools.${iface}.method=direct ptools.${iface}.fn=ptools.${wf} \
        $EXTRA "llm.model=$DS" dataset.split=valid "dataset.n=$n" \
        evaluate.expt_name=${sub}_val_full_baseline evaluate.result_dir=val_results_full
    if [ -f learned_opus/codedistill_config.yaml ]; then
      PTOOL_DOTS=$(uv run python -c "
import yaml
cfg = yaml.safe_load(open('learned_opus/codedistill_config.yaml'))
for n, kvs in (cfg.get('ptools', {}) or {}).items():
    for k, v in (kvs or {}).items():
        v = repr(v) if isinstance(v, bool) else v
        print(f'ptools.{n}.{k}={v}')
" 2>/dev/null)
      run_eval "bbh_${sub}_class1_opus_full" \
        uv run python -m secretagent.cli.expt run --interface ptools.${iface} \
          ptools.${iface}.method=direct ptools.${iface}.fn=ptools.${wf} \
          $PTOOL_DOTS $EXTRA "llm.model=$DS" \
          learn.train_dir=learned_opus dataset.split=valid "dataset.n=$n" \
          evaluate.expt_name=${sub}_val_full_class1_opus evaluate.result_dir=val_results_full
    fi
    C2DIR=$(ls -td "$PWD/learned_class2_opus"/*${iface}__workflow_distill 2>/dev/null | head -1)
    if [ -n "$C2DIR" ]; then
      run_eval "bbh_${sub}_class2_opus_full" \
        uv run python -m secretagent.cli.expt run --interface ptools.${iface} \
          ptools.${iface}.method=learned_code ptools.${iface}.learner=workflow_distill \
          ptools.${iface}.backoff=true $EXTRA "llm.model=$DS" \
          learn.train_dir="$(dirname $C2DIR)" \
          dataset.split=valid "dataset.n=$n" \
          evaluate.expt_name=${sub}_val_full_class2_opus evaluate.result_dir=val_results_full
    fi
  done
}

other_eval() {
  cd "$ROOT/benchmarks/medcalc"
  run_eval "medcalc_baseline_full" \
    uv run python expt.py run --config-file conf/workflow.yaml \
      dataset.split=valid dataset.n=100 \
      evaluate.expt_name=medcalc_val_full_baseline evaluate.result_dir=val_results_full
  cd "$ROOT/benchmarks/finqa"
  run_eval "finqa_baseline_full" \
    uv run python expt.py run --config-file conf/workflow.yaml \
      dataset.split=valid dataset.n=100 \
      evaluate.expt_name=finqa_val_full_baseline evaluate.result_dir=val_results_full
  cd "$ROOT/benchmarks/rulearena"
  for dom in nba tax airline; do
    run_eval "rulearena_${dom}_baseline_full" \
      uv run python expt.py run "dataset.domain=${dom}" \
        ptools.compute_rulearena_answer.method=direct \
        ptools.compute_rulearena_answer.fn=ptools.l1_extract_workflow \
        dataset.split=valid dataset.n=50 \
        evaluate.expt_name=${dom}_val_full_baseline evaluate.result_dir=val_results_full
  done
}

echo "=== E: Full-size val eval — start at $(date) ==="
natplan_eval & P1=$!
musr_eval & P2=$!
bbh_eval & P3=$!
other_eval & P4=$!
wait $P1 $P2 $P3 $P4
echo "=== E val DONE at $(date) ==="
