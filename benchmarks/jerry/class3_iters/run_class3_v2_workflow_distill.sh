#!/bin/bash
# Class 3 v2: workflow_distill on top of induced ptools (NOT tool-by-tool
# distill). The induced ptool module from PtoolInducer (Stage A from v1)
# is reused as the tool_module for workflow-codedistill.
set +e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
set -a; source "$ROOT/.env"; set +a
CD_MODEL="${CD_MODEL:-claude-opus-4-6}"

# Synthesize a conf that binds the induced simulate ptools so the
# workflow_distill fit-time eval can actually call them.
synth_induced_conf() {
  local outpath="$1"; local model="$2"; shift 2
  local ptools_yaml=""
  for p in "$@"; do
    ptools_yaml="${ptools_yaml}  ${p}:\n    method: simulate\n"
  done
  cat > "$outpath" <<EOF
llm:
  model: ${model}
cachier:
  cache_dir: llm_cache
evaluate:
  result_dir: results
  expt_name: synth_induced
ptools:
$(printf "%b" "$ptools_yaml")
EOF
}

run_wf() {
  local label="$1"; shift
  echo "============================================================"
  echo "[$(date)] $label START"
  echo "------------------------------------------------------------"
  "$@" 2>&1
  echo "[$(date)] $label END rc=$?"
}

echo "=== Class 3 v2 (workflow_distill on induced) — start at $(date) ==="

# ===== MuSR murder =====
cd "$ROOT/benchmarks/musr"
INDUCED=$(ls "$ROOT/benchmarks/musr/learned_class3"/*answer_question__ptool_inducer/learned_ptools.py 2>/dev/null | tail -1)
STAGE_B=$(ls -d "$ROOT/benchmarks/musr/learned_class3/induced_recordings"/*.answer_question_induced_record 2>/dev/null | tail -1)
WORKFLOW_TRACE=$(ls -d "$ROOT/benchmarks/musr/recordings"/*.murder_train_record 2>/dev/null | tail -1)

if [ -z "$INDUCED" ]; then
  echo "musr: no induced ptools found — skip"
else
  # Synth conf binding the _impl simulate functions
  SYNTH="$LOG_DIR/musr_class3v2_synth.yaml"
  synth_induced_conf "$SYNTH" "together_ai/deepseek-ai/DeepSeek-V3.1" \
    _gather_evidence_impl _search_suspect_attributes_impl \
    _analyze_and_synthesize_evidence_impl _form_conclusion_impl \
    _plan_investigation_approach_impl
  echo "synth conf: $SYNTH"

  run_wf "musr_murder class3_v2" \
    uv run -m secretagent.cli.learn workflow-codedistill \
      --interface answer_question \
      --dataset-file data_train_50.json \
      --tool-module "$INDUCED" \
      --conf-file "$SYNTH" \
      ${STAGE_B:+--trace-dir "$STAGE_B"} \
      ${WORKFLOW_TRACE:+--cross-trace-dir "$WORKFLOW_TRACE"} \
      --learned-dir learned_class3_v2 --model "$CD_MODEL" \
      --backoff false \
    > "$LOG_DIR/class3v2_musr_murder.log" 2>&1
fi

cd "$ROOT"
echo "=== Class 3 v2 — DONE at $(date) ==="
