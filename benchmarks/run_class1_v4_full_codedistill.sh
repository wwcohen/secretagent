#!/bin/bash
# B': Class 1 opus codedistill-all on FULL-SIZE recordings (recordings_full/)
# with --max-wrong-rate 0.20. Output to learned_opus/.
set +e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
mkdir -p "$LOG_DIR"
set -a; source "$ROOT/.env"; set +a
CD_MODEL="${CD_MODEL:-claude-opus-4-6}"
WRONG_RATE="${WRONG_RATE:-0.20}"

distill() {
  local label="$1"; local cwd="$2"; local rec_pat="$3"
  local log="$LOG_DIR/class1_opus_${label}.log"
  local rec
  rec=$(ls -d "$cwd/recordings_full/"*."$rec_pat" 2>/dev/null | sort | tail -1)
  if [ -z "$rec" ]; then echo "[$label] no full-size recording matching $rec_pat — skip" | tee -a "$log"; return; fi
  echo "[$(date)] $label opus distill" | tee "$log"
  echo "  rec: $rec" | tee -a "$log"
  cd "$cwd"
  uv run -m secretagent.cli.learn codedistill-all \
    --learned-dir learned_opus --model "$CD_MODEL" \
    --max-wrong-rate "$WRONG_RATE" "$rec" >> "$log" 2>&1
  echo "[$(date)] $label opus done rc=$?" | tee -a "$log"
}

echo "=== Class 1 opus (full-size, max_wrong_rate=$WRONG_RATE) — start at $(date) ==="
fam1() {
  distill natplan_calendar "$ROOT/benchmarks/natural_plan" natplan_calendar_train_train_full
  distill natplan_meeting  "$ROOT/benchmarks/natural_plan" natplan_meeting_train_train_full
  distill natplan_trip     "$ROOT/benchmarks/natural_plan" natplan_trip_train_train_full
}
fam2() {
  distill musr_murder "$ROOT/benchmarks/musr" musr_murder_train_train_full
  distill medcalc     "$ROOT/benchmarks/medcalc" medcalc_train_train_full
  distill finqa       "$ROOT/benchmarks/finqa" finqa_train_train_full
}
fam3() {
  distill bbh_sports     "$ROOT/benchmarks/bbh/sports_understanding" bbh_sports_understanding_train_train_full
  distill bbh_penguins   "$ROOT/benchmarks/bbh/penguins_in_a_table" bbh_penguins_in_a_table_train_train_full
  distill bbh_geometric  "$ROOT/benchmarks/bbh/geometric_shapes" bbh_geometric_shapes_train_train_full
  distill bbh_date       "$ROOT/benchmarks/bbh/date_understanding" bbh_date_understanding_train_train_full
}
fam4() {
  distill rulearena_nba     "$ROOT/benchmarks/rulearena" rulearena_nba_train_train_full
  distill rulearena_tax     "$ROOT/benchmarks/rulearena" rulearena_tax_train_train_full
  distill rulearena_airline "$ROOT/benchmarks/rulearena" rulearena_airline_train_train_full
}

fam1 & P1=$!
fam2 & P2=$!
fam3 & P3=$!
fam4 & P4=$!
wait $P1 $P2 $P3 $P4
echo "=== Class 1 opus — DONE at $(date) ==="
