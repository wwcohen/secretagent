#!/bin/bash
# Class 1 v5 gate comparison: 3 tasks × 2 gate metrics = 6 experiments.
# Common settings:
#   - only_correct=False (with CORRECT/INCORRECT annotation in trace prompt)
#   - no early stop (all 3 rounds run regardless of acc)
#   - --max-wrong-rate 0.20
#   - model claude-opus-4-6
# Differs only in --gate-metric: 'train' (v1 style) vs 'val' (holdout, v4 style).
# Both versions still compute holdout val_acc/val_wrong_rate (just don't gate on it
# when gate=train).
set +e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
mkdir -p "$LOG_DIR"
set -a; source "$ROOT/.env"; set +a
CD_MODEL="${CD_MODEL:-claude-opus-4-6}"
WRONG_RATE="${WRONG_RATE:-0.20}"

CAL_REC="$ROOT/benchmarks/natural_plan/recordings_full/20260429.005822.natplan_calendar_train_train_full"
MEET_REC="$ROOT/benchmarks/natural_plan/recordings_full/20260429.030705.natplan_meeting_train_train_full"
FINQA_REC="$ROOT/benchmarks/finqa/recordings_full/20260429.011245.finqa_train_train_full"

distill() {
  local label="$1"; local cwd="$2"; local rec="$3"; local gate="$4"
  local out_dir="learned_v5_${gate}gate"
  local log="$LOG_DIR/class1v5_${gate}gate_${label}.log"
  echo "[$(date)] $label v5 gate=$gate distill" | tee "$log"
  echo "  rec: $rec" | tee -a "$log"
  echo "  out: $cwd/$out_dir" | tee -a "$log"
  cd "$cwd"
  uv run -m secretagent.cli.learn codedistill-all \
    --learned-dir "$out_dir" --model "$CD_MODEL" \
    --max-wrong-rate "$WRONG_RATE" \
    --gate-metric "$gate" \
    --no-only-correct \
    "$rec" >> "$log" 2>&1
  echo "[$(date)] $label v5 gate=$gate done rc=$?" | tee -a "$log"
}

echo "=== Class 1 v5 distill (max_wr=$WRONG_RATE, only_correct=False) — start at $(date) ==="

distill calendar "$ROOT/benchmarks/natural_plan" "$CAL_REC"  train  & P1=$!
distill calendar "$ROOT/benchmarks/natural_plan" "$CAL_REC"  val    & P2=$!
distill meeting  "$ROOT/benchmarks/natural_plan" "$MEET_REC" train  & P3=$!
distill meeting  "$ROOT/benchmarks/natural_plan" "$MEET_REC" val    & P4=$!
distill finqa    "$ROOT/benchmarks/finqa"        "$FINQA_REC" train & P5=$!
distill finqa    "$ROOT/benchmarks/finqa"        "$FINQA_REC" val   & P6=$!

wait $P1 $P2 $P3 $P4 $P5 $P6
echo "=== distill — DONE at $(date) ==="
echo
echo "Now run benchmarks/run_class1_v5_val_eval.sh to evaluate."
