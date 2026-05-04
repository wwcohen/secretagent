#!/bin/bash
# D': Class 3 opus — workflow_distill on induced ptools, full-size data.
# Only benchmarks with usable React/CoT recordings (musr, finqa, calendar).
set +e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
set -a; source "$ROOT/.env"; set +a
CD_MODEL="${CD_MODEL:-claude-opus-4-6}"

# Reuse v3 outputs that worked (Stage A induce + Stage B re-record)
# Then stack workflow_distill on the induced ptools.

run_v4() {
  local label="$1"; shift
  echo "============================================================"
  echo "[$(date)] class3_v4 $label START"
  "$@" 2>&1
  echo "[$(date)] class3_v4 $label END rc=$?"
}

echo "=== Class 3 opus (workflow_distill on induced, full-size) — start at $(date) ==="

# musr_murder
cd "$ROOT/benchmarks/musr"
INDUCED=$(ls "$ROOT/benchmarks/musr/learned_class3_v3"/*answer_question__ptool_inducer/learned_ptools.py 2>/dev/null | tail -1)
[ -z "$INDUCED" ] && INDUCED=$(ls "$ROOT/benchmarks/musr/learned_class3"/*answer_question__ptool_inducer/learned_ptools.py 2>/dev/null | tail -1)
STAGE_B=$(ls -d "$ROOT/benchmarks/musr/learned_class3_v3/induced_recordings"/*answer_question_induced_record 2>/dev/null | tail -1)
[ -z "$STAGE_B" ] && STAGE_B=$(ls -d "$ROOT/benchmarks/musr/learned_class3/induced_recordings"/*answer_question_induced_record 2>/dev/null | tail -1)
if [ -n "$INDUCED" ]; then
  SYNTH="$LOG_DIR/musr_class3_opus_synth.yaml"
  cat > "$SYNTH" <<EOF
llm:
  model: together_ai/deepseek-ai/DeepSeek-V3.1
cachier:
  cache_dir: llm_cache
evaluate:
  result_dir: results
  expt_name: synth
ptools:
  _gather_evidence_impl: {method: simulate}
  _search_suspect_attributes_impl: {method: simulate}
  _analyze_and_synthesize_evidence_impl: {method: simulate}
  _form_conclusion_impl: {method: simulate}
  _plan_investigation_approach_impl: {method: simulate}
EOF
  run_v4 musr_murder \
    uv run -m secretagent.cli.learn workflow-codedistill \
      --interface answer_question --dataset-file data_train_50.json \
      --tool-module "$INDUCED" --conf-file "$SYNTH" \
      ${STAGE_B:+--trace-dir "$STAGE_B"} \
      --learned-dir learned_class3_opus --model "$CD_MODEL" \
      --backoff true \
    > "$LOG_DIR/class3_opus_musr_murder.log" 2>&1
fi

# finqa
cd "$ROOT/benchmarks/finqa"
INDUCED=$(ls "$ROOT/benchmarks/finqa/learned_class3_v3"/*answer_finqa__ptool_inducer/learned_ptools.py 2>/dev/null | tail -1)
STAGE_B=$(ls -d "$ROOT/benchmarks/finqa/learned_class3_v3/induced_recordings"/*induced_record 2>/dev/null | tail -1)
if [ -n "$INDUCED" ]; then
  run_v4 finqa \
    uv run -m secretagent.cli.learn workflow-codedistill \
      --interface answer_finqa --dataset-file data/train.json \
      --tool-module "$INDUCED" --conf-file conf/workflow.yaml \
      ${STAGE_B:+--trace-dir "$STAGE_B"} \
      --learned-dir learned_class3_opus --model "$CD_MODEL" \
      --backoff true \
    > "$LOG_DIR/class3_opus_finqa.log" 2>&1
fi

# natplan_calendar
cd "$ROOT/benchmarks/natural_plan"
INDUCED=$(ls "$ROOT/benchmarks/natural_plan/learned_class3_v3"/*calendar_scheduling__ptool_inducer/learned_ptools.py 2>/dev/null | tail -1)
STAGE_B=$(ls -d "$ROOT/benchmarks/natural_plan/learned_class3_v3/induced_recordings"/*induced_record 2>/dev/null | tail -1)
if [ -n "$INDUCED" ]; then
  run_v4 natplan_calendar \
    uv run -m secretagent.cli.learn workflow-codedistill \
      --interface calendar_scheduling --dataset-file data/calendar_train.json --output-field golden_plan \
      --tool-module "$INDUCED" --conf-file conf/calendar.yaml \
      ${STAGE_B:+--trace-dir "$STAGE_B"} \
      --learned-dir learned_class3_opus --model "$CD_MODEL" \
      --backoff true \
    > "$LOG_DIR/class3_opus_natplan_calendar.log" 2>&1
fi

cd "$ROOT"
echo "=== Class 3 opus — DONE at $(date) ==="
