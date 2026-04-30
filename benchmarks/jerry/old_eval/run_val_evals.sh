#!/bin/bash
# Eval each benchmark on its val split:
#  - baseline (workflow, DeepSeek-V3.1)
#  - Class 1 distilled (codedistill_config.yaml from learned/)
#  - Class 2 distilled (workflow_distill from learned_class2_v2/v3)
#  - Class 3 distilled (induced_codedistill_config.yaml from learned_class3/) — musr only
# All eval n=50 cases.
set +e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/benchmarks/val_evals.log"
set -a; source "$ROOT/.env"; set +a

run() {
  local label="$1"; shift
  echo "============================================================" | tee -a "$LOG"
  echo "[$(date)] VAL EVAL: $label" | tee -a "$LOG"
  echo "------------------------------------------------------------" | tee -a "$LOG"
  "$@" >> "$LOG" 2>&1
  echo "[$(date)] $label rc=$?" | tee -a "$LOG"
}

echo "=== val evals start at $(date) ===" > "$LOG"

# Helper: latest learned class2_v3 > _v2 > _v1 dir for a given iface
class2_dir() {
  local cwd="$1"; local iface="$2"
  for d in learned_class2_v3 learned_class2_v2 learned_class2; do
    full=$(ls -td "$cwd/$d/"*"${iface}__workflow_distill" 2>/dev/null | head -1)
    [ -n "$full" ] && { echo "$full"; return; }
  done
}

# ===== NatPlan calendar =====
cd "$ROOT/benchmarks/natural_plan"
# baseline val
run "natplan_calendar BASELINE val" \
  uv run python expt.py run --config-file conf/calendar.yaml \
    ptools.calendar_scheduling.method=direct \
    ptools.calendar_scheduling.fn=ptools_calendar.calendar_workflow \
    dataset.partition=valid dataset.n=50 \
    evaluate.expt_name=cal_val_baseline evaluate.result_dir=val_results
# Class 1 distilled
[ -f learned/codedistill_config.yaml ] && run "natplan_calendar CLASS1 val" \
  uv run python expt.py run --config-file conf/calendar.yaml \
    --config-file learned/codedistill_config.yaml \
    ptools.calendar_scheduling.method=direct \
    ptools.calendar_scheduling.fn=ptools_calendar.calendar_workflow \
    dataset.partition=valid dataset.n=50 \
    learn.train_dir=learned \
    evaluate.expt_name=cal_val_class1 evaluate.result_dir=val_results
# Class 2 — calendar v2 success (92.5%/100%)
C2DIR=$(class2_dir "$PWD" "calendar_scheduling")
if [ -n "$C2DIR" ]; then
  C2DIR_PARENT=$(dirname "$C2DIR")
  run "natplan_calendar CLASS2 val" \
    uv run python expt.py run --config-file conf/calendar.yaml \
      "ptools.calendar_scheduling.method=learned_code" \
      "ptools.calendar_scheduling.learner=workflow_distill" \
      "ptools.calendar_scheduling.backoff=false" \
      learn.train_dir="$C2DIR_PARENT" \
      dataset.partition=valid dataset.n=50 \
      evaluate.expt_name=cal_val_class2 evaluate.result_dir=val_results
fi

# ===== NatPlan meeting =====
run "natplan_meeting BASELINE val" \
  uv run python expt.py run --config-file conf/meeting.yaml \
    ptools.meeting_planning.method=direct \
    ptools.meeting_planning.fn=ptools_meeting.meeting_workflow \
    dataset.partition=valid dataset.n=50 \
    evaluate.expt_name=meet_val_baseline evaluate.result_dir=val_results
[ -f learned/codedistill_config.yaml ] && run "natplan_meeting CLASS1 val" \
  uv run python expt.py run --config-file conf/meeting.yaml \
    --config-file learned/codedistill_config.yaml \
    ptools.meeting_planning.method=direct \
    ptools.meeting_planning.fn=ptools_meeting.meeting_workflow \
    dataset.partition=valid dataset.n=50 \
    learn.train_dir=learned \
    evaluate.expt_name=meet_val_class1 evaluate.result_dir=val_results
C2DIR=$(class2_dir "$PWD" "meeting_planning")
if [ -n "$C2DIR" ]; then
  C2DIR_PARENT=$(dirname "$C2DIR")
  run "natplan_meeting CLASS2 val" \
    uv run python expt.py run --config-file conf/meeting.yaml \
      "ptools.meeting_planning.method=learned_code" \
      "ptools.meeting_planning.learner=workflow_distill" \
      "ptools.meeting_planning.backoff=false" \
      learn.train_dir="$C2DIR_PARENT" \
      dataset.partition=valid dataset.n=50 \
      evaluate.expt_name=meet_val_class2 evaluate.result_dir=val_results
fi

# ===== NatPlan trip =====
run "natplan_trip BASELINE val" \
  uv run python expt.py run --config-file conf/trip.yaml \
    ptools.trip_planning.method=direct \
    ptools.trip_planning.fn=ptools_trip.trip_workflow \
    dataset.partition=valid dataset.n=50 \
    evaluate.expt_name=trip_val_baseline evaluate.result_dir=val_results
[ -f learned/codedistill_config.yaml ] && run "natplan_trip CLASS1 val" \
  uv run python expt.py run --config-file conf/trip.yaml \
    --config-file learned/codedistill_config.yaml \
    ptools.trip_planning.method=direct \
    ptools.trip_planning.fn=ptools_trip.trip_workflow \
    dataset.partition=valid dataset.n=50 \
    learn.train_dir=learned \
    evaluate.expt_name=trip_val_class1 evaluate.result_dir=val_results

# ===== MuSR murder =====
cd "$ROOT/benchmarks/musr"
run "musr_murder BASELINE val" \
  uv run python expt.py run --config-file conf/murder_workflow.yaml \
    dataset.split=murder_mysteries_val dataset.n=50 \
    evaluate.expt_name=murder_val_baseline evaluate.result_dir=val_results
[ -f learned/codedistill_config.yaml ] && run "musr_murder CLASS1 val" \
  uv run python expt.py run --config-file conf/murder_workflow.yaml \
    --config-file learned/codedistill_config.yaml \
    dataset.split=murder_mysteries_val dataset.n=50 \
    learn.train_dir=learned \
    evaluate.expt_name=murder_val_class1 evaluate.result_dir=val_results
[ -f learned_class3/induced_codedistill_config.yaml ] && run "musr_murder CLASS3 val" \
  uv run python expt.py run --config-file conf/murder.yaml \
    --config-file learned_class3/induced_codedistill_config.yaml \
    dataset.split=murder_mysteries_val dataset.n=50 \
    learn.train_dir=learned_class3 \
    evaluate.expt_name=murder_val_class3 evaluate.result_dir=val_results

# ===== BBH (per-subdir) =====
for sub_iface_wf in "sports_understanding:are_sports_in_sentence_consistent:sports_understanding_workflow" \
                    "penguins_in_a_table:answer_penguin_question:penguins_workflow" \
                    "geometric_shapes:identify_shape:geometric_shapes_workflow" \
                    "date_understanding:answer_date_question:zeroshot_unstructured_workflow"; do
  IFS=":" read sub iface wf <<< "$sub_iface_wf"
  cd "$ROOT/benchmarks/bbh/$sub" || continue
  EXTRA=()
  if [ "$sub" = "date_understanding" ]; then
    EXTRA+=("ptools.answer_date_question_orchestrated.method=direct"
            "ptools.answer_date_question_orchestrated.fn=ptools.zeroshot_unstructured_workflow")
  fi
  run "bbh_${sub} BASELINE val" \
    uv run python -m secretagent.cli.expt run \
      --interface "ptools.${iface}" \
      "ptools.${iface}.method=direct" \
      "ptools.${iface}.fn=ptools.${wf}" \
      "${EXTRA[@]}" \
      "llm.model=together_ai/deepseek-ai/DeepSeek-V3.1" \
      dataset.split=valid dataset.n=50 \
      "evaluate.expt_name=${sub}_val_baseline" evaluate.result_dir=val_results
  if [ -f learned/codedistill_config.yaml ]; then
    run "bbh_${sub} CLASS1 val" \
      uv run python -m secretagent.cli.expt run \
        --interface "ptools.${iface}" \
        --config-file learned/codedistill_config.yaml \
        "ptools.${iface}.method=direct" \
        "ptools.${iface}.fn=ptools.${wf}" \
        "${EXTRA[@]}" \
        "llm.model=together_ai/deepseek-ai/DeepSeek-V3.1" \
        learn.train_dir=learned \
        dataset.split=valid dataset.n=50 \
        "evaluate.expt_name=${sub}_val_class1" evaluate.result_dir=val_results
  fi
  C2DIR=$(class2_dir "$PWD" "$iface")
  if [ -n "$C2DIR" ]; then
    C2DIR_PARENT=$(dirname "$C2DIR")
    run "bbh_${sub} CLASS2 val" \
      uv run python -m secretagent.cli.expt run \
        --interface "ptools.${iface}" \
        "ptools.${iface}.method=learned_code" \
        "ptools.${iface}.learner=workflow_distill" \
        "ptools.${iface}.backoff=false" \
        "${EXTRA[@]}" \
        "llm.model=together_ai/deepseek-ai/DeepSeek-V3.1" \
        learn.train_dir="$C2DIR_PARENT" \
        dataset.split=valid dataset.n=50 \
        "evaluate.expt_name=${sub}_val_class2" evaluate.result_dir=val_results
  fi
done

# ===== MedCalc =====
cd "$ROOT/benchmarks/medcalc"
run "medcalc BASELINE val" \
  uv run python expt.py run --config-file conf/workflow.yaml \
    dataset.split=valid dataset.n=50 \
    evaluate.expt_name=medcalc_val_baseline evaluate.result_dir=val_results
[ -f learned/codedistill_config.yaml ] && run "medcalc CLASS1 val" \
  uv run python expt.py run --config-file conf/workflow.yaml \
    --config-file learned/codedistill_config.yaml \
    dataset.split=valid dataset.n=50 \
    learn.train_dir=learned \
    evaluate.expt_name=medcalc_val_class1 evaluate.result_dir=val_results

# ===== FinQA =====
cd "$ROOT/benchmarks/finqa"
run "finqa BASELINE val" \
  uv run python expt.py run --config-file conf/workflow.yaml \
    dataset.split=valid dataset.n=50 \
    evaluate.expt_name=finqa_val_baseline evaluate.result_dir=val_results
[ -f learned/codedistill_config.yaml ] && run "finqa CLASS1 val" \
  uv run python expt.py run --config-file conf/workflow.yaml \
    --config-file learned/codedistill_config.yaml \
    dataset.split=valid dataset.n=50 \
    learn.train_dir=learned \
    evaluate.expt_name=finqa_val_class1 evaluate.result_dir=val_results

# ===== RuleArena =====
cd "$ROOT/benchmarks/rulearena"
for dom in nba tax airline; do
  run "rulearena_${dom} BASELINE val" \
    uv run python expt.py run \
      "dataset.domain=${dom}" \
      ptools.compute_rulearena_answer.method=direct \
      ptools.compute_rulearena_answer.fn=ptools.l1_extract_workflow \
      dataset.split=valid dataset.n=50 \
      "evaluate.expt_name=${dom}_val_baseline" evaluate.result_dir=val_results
  C2DIR=$(class2_dir "$PWD" "compute_rulearena_answer")
  if [ -n "$C2DIR" ] && [ "$dom" = "airline" ]; then
    C2DIR_PARENT=$(dirname "$C2DIR")
    run "rulearena_${dom} CLASS2 val" \
      uv run python expt.py run \
        "dataset.domain=${dom}" \
        ptools.compute_rulearena_answer.method=learned_code \
        ptools.compute_rulearena_answer.learner=workflow_distill \
        ptools.compute_rulearena_answer.backoff=false \
        learn.train_dir="$C2DIR_PARENT" \
        dataset.split=valid dataset.n=50 \
        "evaluate.expt_name=${dom}_val_class2" evaluate.result_dir=val_results
  fi
done

cd "$ROOT"
echo "=== val evals DONE at $(date) ===" | tee -a "$LOG"
