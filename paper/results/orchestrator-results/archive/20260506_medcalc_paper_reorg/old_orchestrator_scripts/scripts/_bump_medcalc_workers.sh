#!/usr/bin/env bash
# Wait until both medcalc-rival lanes (musr, natural_plan) have finished
# every non-medcalc cell, then kill the in-flight 8-worker medcalc and
# restart the medcalc lane with workers=16 so it has the API to itself.

set -u
REPO=$(git rev-parse --show-toplevel)
ROOT="$REPO/benchmarks/COMMON/orchestrator-results"
DRIVER="$ROOT/scripts/run_test_eval.sh"
ORCH="$ROOT/scripts/run_parallel.sh"
RLOG="$ROOT/scripts/_logs/parallel"

NON_MEDCALC=(
  "existing_workflow:musr_object"
  "seed_from_ptools:musr_object"
  "existing_workflow:musr_team"
  "seed_from_ptools:musr_team"
  "existing_workflow:natplan_meeting"
  "seed_from_ptools:natplan_meeting"
  "existing_workflow:natplan_trip"
  "seed_from_ptools:natplan_trip"
)

cell_done_ext() {
  local cls="$1" bench="$2"
  local out_dir="$ROOT/$cls/$bench"
  [[ -d "$out_dir" ]] || return 1
  for sub in "$out_dir"/*.test_deepseek_v3_1/; do
    [[ -f "$sub/results.csv" ]] || continue
    local n exc data
    n=$(wc -l < "$sub/results.csv" 2>/dev/null || echo 0)
    (( n >= 2 )) || continue
    data=$((n - 1))
    exc=$(grep -c "exception raised" "$sub/results.csv" 2>/dev/null || echo 0)
    (( exc < data )) && return 0
  done
  return 1
}

echo "[bump] waiting for all non-medcalc cells to finish..."
while :; do
  pending=()
  for cell in "${NON_MEDCALC[@]}"; do
    IFS=":" read -r cls bench <<<"$cell"
    cell_done_ext "$cls" "$bench" || pending+=("$cell")
  done
  if (( ${#pending[@]} == 0 )); then
    break
  fi
  echo "[bump] still pending (${#pending[@]}): ${pending[*]}"
  sleep 60
done

echo "[bump] all non-medcalc cells complete at $(date -Iseconds). Switching medcalc to 16 workers."

# Kill any in-flight medcalc python (single-cell run) so the next launch
# starts fresh with 16 workers. Cache from the 8-worker run is preserved.
PYS=$(pgrep -f "expt.py.*medcalc/conf" 2>/dev/null)
if [[ -n "$PYS" ]]; then
  echo "[bump] killing in-flight medcalc python: $PYS"
  kill -TERM $PYS 2>/dev/null || true
  sleep 5
  PYS=$(pgrep -f "expt.py.*medcalc/conf" 2>/dev/null)
  [[ -n "$PYS" ]] && kill -KILL $PYS 2>/dev/null || true
fi

# Also kill any in-flight orphaned bash run_test_eval.sh for medcalc
BASHES=$(pgrep -f "run_test_eval.sh.*:medcalc" 2>/dev/null)
[[ -n "$BASHES" ]] && kill -TERM $BASHES 2>/dev/null || true
sleep 2

# Drop any partial result dir without a results.csv (the killed cell)
for d in "$ROOT"/{existing_workflow,seed_from_ptools}/medcalc/*test_deepseek_v3_1/; do
  [[ -d "$d" ]] || continue
  if [[ ! -f "$d/results.csv" ]]; then
    echo "[bump] purging partial $d"
    rm -rf "$d"
  fi
done

# Bump BENCH_WORKERS[medcalc] from 8 to 16 in the driver. Idempotent: if
# already 16, no change.
sed -i 's/\[medcalc\]=8/[medcalc]=16/' "$DRIVER"
grep "medcalc.=16\|medcalc.=8" "$DRIVER"

echo "[bump] launching medcalc lane (workers=16) in background"
LANES=medcalc bash "$ORCH" >> "$RLOG/medcalc_w16.log" 2>&1 &
echo "[bump] medcalc lane PID=$!"
wait
echo "[bump] done at $(date -Iseconds)"
