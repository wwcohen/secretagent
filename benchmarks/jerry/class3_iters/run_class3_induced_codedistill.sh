#!/bin/bash
# Class 3: Workflow distill with induced ptool (4-stage pipeline)
# - Step 1: record train split with ReAct conf → ReAct rollout traces
# - Step 2: codedistill-induced-ptools (Stage A: induce ptools from ReAct;
#   Stage B: re-record with induced ptools; Stage C: codedistill-all on new
#   recording; Stage D: merge configs)
# Only benchmarks with a ReAct conf qualify; others are skipped.
# Usage: nohup bash run_class3_induced_codedistill.sh > class3_all.log 2>&1 &

set +e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
mkdir -p "$LOG_DIR"

set -a
source "$ROOT/.env"
set +a

CD_MODEL="${CD_MODEL:-claude-opus-4-6}"
N_CASES="${N_CASES:-50}"

run_step() {
  local label="$1"; shift
  echo "[$(date)] $label: starting"
  "$@" 2>&1
  local rc=$?
  echo "[$(date)] $label: rc=$rc"
}

echo "=== Class 3 induced-codedistill — start at $(date) ==="

# ────────────────────────────────────────────────────────────────────
# 1) MuSR murder — has conf/murder_react_train.yaml + ptools_common state
# ────────────────────────────────────────────────────────────────────
echo "============================================================"
echo "[$(date)] class3 musr_murder: starting"
LOG="$LOG_DIR/class3_musr_murder.log"
cd "$ROOT/benchmarks/musr"

# Step 1: record ReAct train rollouts
run_step "musr_murder_react_record" \
  uv run python expt.py run --config-file conf/murder_react_train.yaml \
    "dataset.n=$N_CASES" \
    evaluate.expt_name=murder_react_train \
    evaluate.record_details=true \
    evaluate.result_dir=recordings_class3 \
  > "$LOG" 2>&1

REC=$(ls -d recordings_class3/*.murder_react_train 2>/dev/null | sort | tail -1)
if [ -z "$REC" ]; then
  echo "  no ReAct recording produced; skipping pipeline" >> "$LOG"
else
  echo "  using ReAct recording: $REC" >> "$LOG"

  # Step 2: 4-stage pipeline (induction → re-record → codedistill → merge)
  run_step "musr_murder_pipeline" \
    uv run -m secretagent.cli.learn codedistill-induced-ptools \
      --interface answer_question \
      --task-desc "Solve a murder mystery from a narrative; identify which suspect committed the murder." \
      --trace-mode react --only-correct \
      --state-module ptools_common \
      --state-expr '_REACT_STATE["narrative"]' \
      --learned-dir learned_class3 \
      --max-wrong-rate 0.10 \
      --model "$CD_MODEL" \
      --expt-cmd "uv run python expt.py run --config-file conf/murder.yaml dataset.split=murder_mysteries_train dataset.n=$N_CASES" \
      "$REC" \
    >> "$LOG" 2>&1
fi

cd "$ROOT"

# ────────────────────────────────────────────────────────────────────
# 2) FinQA — has conf/react.yaml (no react_train variant; use react.yaml + override split)
# ────────────────────────────────────────────────────────────────────
echo "============================================================"
echo "[$(date)] class3 finqa: starting"
LOG="$LOG_DIR/class3_finqa.log"
cd "$ROOT/benchmarks/finqa"

run_step "finqa_react_record" \
  uv run python expt.py run --config-file conf/react.yaml \
    "dataset.n=$N_CASES" dataset.split=train \
    evaluate.expt_name=finqa_react_train \
    evaluate.record_details=true \
    evaluate.result_dir=recordings_class3 \
  > "$LOG" 2>&1

REC=$(ls -d recordings_class3/*.finqa_react_train 2>/dev/null | sort | tail -1)
if [ -z "$REC" ]; then
  echo "  no ReAct recording produced; skipping pipeline" >> "$LOG"
else
  echo "  using ReAct recording: $REC" >> "$LOG"

  run_step "finqa_pipeline" \
    uv run -m secretagent.cli.learn codedistill-induced-ptools \
      --interface answer_finqa \
      --task-desc "Answer a financial QA problem requiring numerical reasoning over a table and surrounding text." \
      --trace-mode react --only-correct \
      --learned-dir learned_class3 \
      --max-wrong-rate 0.10 \
      --model "$CD_MODEL" \
      --expt-cmd "uv run python expt.py run --config-file conf/workflow.yaml dataset.split=train dataset.n=$N_CASES" \
      "$REC" \
    >> "$LOG" 2>&1
fi

cd "$ROOT"

# Skipped — no ReAct conf
for s in natplan_calendar natplan_meeting natplan_trip bbh_sports bbh_penguins \
         bbh_geometric bbh_date medcalc rulearena_airline rulearena_nba rulearena_tax; do
  echo "[$(date)] class3 $s: SKIPPED (no ReAct conf available in this benchmark)"
done

echo "=== Class 3 induced-codedistill — DONE at $(date) ==="
echo "Per-benchmark logs in $LOG_DIR/class3_*.log"
