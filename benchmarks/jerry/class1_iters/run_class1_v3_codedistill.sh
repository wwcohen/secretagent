#!/bin/bash
# Class 1 v3: re-distill with --max-wrong-rate 0.20 (looser than v2's 0.05)
# Uses existing train recordings (no re-record).
set +e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
mkdir -p "$LOG_DIR"
set -a; source "$ROOT/.env"; set +a
CD_MODEL="${CD_MODEL:-claude-opus-4-6}"
WRONG_RATE="${WRONG_RATE:-0.20}"

distill() {
  local label="$1"; local cwd="$2"; local rec_pat="$3"
  local log="$LOG_DIR/class1v3_${label}.log"
  local rec
  rec=$(ls -d "$cwd/recordings/"*."$rec_pat" 2>/dev/null | sort | tail -1)
  if [ -z "$rec" ]; then echo "[$label] no recording matching $rec_pat" | tee -a "$log"; return; fi
  echo "============================================================" | tee "$log"
  echo "[$(date)] $label v3 distill (val-gated, max_wrong_rate=$WRONG_RATE)" | tee -a "$log"
  echo "  rec: $rec" | tee -a "$log"
  echo "============================================================" | tee -a "$log"
  cd "$cwd"
  uv run -m secretagent.cli.learn codedistill-all \
    --learned-dir learned_v3 --model "$CD_MODEL" \
    --max-wrong-rate "$WRONG_RATE" "$rec" >> "$log" 2>&1
  echo "[$(date)] $label v3 done rc=$?" | tee -a "$log"
}

echo "=== Class 1 v3 (val-gated, max_wrong_rate=$WRONG_RATE) — start at $(date) ==="

fam1() {
  distill natplan_calendar "$ROOT/benchmarks/natural_plan" calendar_train_record
  distill natplan_meeting  "$ROOT/benchmarks/natural_plan" meeting_train_record
  distill natplan_trip     "$ROOT/benchmarks/natural_plan" trip_train_record
}
fam2() {
  distill musr_murder "$ROOT/benchmarks/musr" murder_train_record
  distill medcalc     "$ROOT/benchmarks/medcalc" medcalc_train_record
  distill finqa       "$ROOT/benchmarks/finqa" finqa_train_record
}
fam3() {
  distill bbh_sports     "$ROOT/benchmarks/bbh/sports_understanding" sports_train_record
  distill bbh_penguins   "$ROOT/benchmarks/bbh/penguins_in_a_table" bbh_penguins_train_record_v2
  distill bbh_geometric  "$ROOT/benchmarks/bbh/geometric_shapes" bbh_geometric_train_record_v2
  distill bbh_date       "$ROOT/benchmarks/bbh/date_understanding" date_train_record_v4
}
fam4() {
  distill rulearena_nba     "$ROOT/benchmarks/rulearena" nba_train_record
  distill rulearena_tax     "$ROOT/benchmarks/rulearena" tax_train_record
  distill rulearena_airline "$ROOT/benchmarks/rulearena" airline_train_record
}

fam1 & P1=$!
fam2 & P2=$!
fam3 & P3=$!
fam4 & P4=$!
wait $P1 $P2 $P3 $P4
echo "=== Class 1 v3 — DONE at $(date) ==="
