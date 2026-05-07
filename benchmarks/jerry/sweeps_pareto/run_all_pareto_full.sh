#!/usr/bin/env bash
# Run Pareto sweeps across all 5 benchmarks — full validation splits.
#
# Budget: ~$80 estimated (RuleArena/MuSR full val, others capped at N=200).
# Caching: examples already evaluated at N=30 are cached and won't re-call the API.
# Benchmarks run in parallel; each benchmark's domains run sequentially.
# Logs go to benchmarks/pareto_logs/<benchmark>_full.log
#
# Usage: bash benchmarks/run_all_pareto_full.sh
#   From repo root, or:  cd benchmarks && bash run_all_pareto_full.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/pareto_logs"
mkdir -p "$LOG_DIR"

# --- Dataset sizes ---
# RuleArena val: airline=60, nba=42, tax=60 → use 9999 to get full split
# MuSR val: 75 per domain → use 75
# Natural Plan: 1000/1000/1600 (no split) → cap at 200
# TabMWP test1k: 1000 → cap at 200
# MedCalc test: 1100 → cap at 200

N_RULEARENA=9999   # full validation split (42-60 examples)
N_MUSR=75          # full validation split
N_NATPLAN=200      # capped (full=1000-1600)
N_TABMWP=200       # capped (full=1000)
N_MEDCALC=200      # capped (full=1100)

TIMEOUT=1200  # 20 min per config (larger N needs more time)

echo "Starting FULL Pareto sweeps across 5 benchmarks..."
echo "  RuleArena:    N=$N_RULEARENA (full val)"
echo "  MuSR:         N=$N_MUSR (full val)"
echo "  Natural Plan: N=$N_NATPLAN (capped)"
echo "  TabMWP:       N=$N_TABMWP (capped)"
echo "  MedCalc:      N=$N_MEDCALC (capped)"
echo "Logs: $LOG_DIR/"
echo ""

# RuleArena: 3 domains × 24 configs
(
  cd "$SCRIPT_DIR/rulearena"
  echo "[rulearena] Starting airline (N=$N_RULEARENA)..."
  uv run python run_pareto.py --domain airline --dataset-n $N_RULEARENA --timeout $TIMEOUT
  echo "[rulearena] Starting nba (N=$N_RULEARENA)..."
  uv run python run_pareto.py --domain nba --dataset-n $N_RULEARENA --timeout $TIMEOUT
  echo "[rulearena] Starting tax (N=$N_RULEARENA)..."
  uv run python run_pareto.py --domain tax --dataset-n $N_RULEARENA --timeout $TIMEOUT
  echo "[rulearena] Done."
) > "$LOG_DIR/rulearena_full.log" 2>&1 &
PID_RULEARENA=$!

# Natural Plan: 3 domains × 25 configs
(
  cd "$SCRIPT_DIR/natural_plan"
  echo "[natural_plan] Starting calendar (N=$N_NATPLAN)..."
  uv run python run_pareto.py --domain calendar --dataset-n $N_NATPLAN --timeout $TIMEOUT
  echo "[natural_plan] Starting meeting (N=$N_NATPLAN)..."
  uv run python run_pareto.py --domain meeting --dataset-n $N_NATPLAN --timeout $TIMEOUT
  echo "[natural_plan] Starting trip (N=$N_NATPLAN)..."
  uv run python run_pareto.py --domain trip --dataset-n $N_NATPLAN --timeout $TIMEOUT
  echo "[natural_plan] Done."
) > "$LOG_DIR/natural_plan_full.log" 2>&1 &
PID_NATPLAN=$!

# TabMWP: 1 domain × 25 configs
(
  cd "$SCRIPT_DIR/tabmwp"
  echo "[tabmwp] Starting (N=$N_TABMWP)..."
  uv run python run_pareto.py --dataset-n $N_TABMWP --timeout $TIMEOUT
  echo "[tabmwp] Done."
) > "$LOG_DIR/tabmwp_full.log" 2>&1 &
PID_TABMWP=$!

# MuSR: 3 domains × 15 configs
(
  cd "$SCRIPT_DIR/musr"
  echo "[musr] Starting murder (N=$N_MUSR)..."
  uv run python run_pareto.py --domain murder --dataset-n $N_MUSR --timeout $TIMEOUT
  echo "[musr] Starting object (N=$N_MUSR)..."
  uv run python run_pareto.py --domain object --dataset-n $N_MUSR --timeout $TIMEOUT
  echo "[musr] Starting team (N=$N_MUSR)..."
  uv run python run_pareto.py --domain team --dataset-n $N_MUSR --timeout $TIMEOUT
  echo "[musr] Done."
) > "$LOG_DIR/musr_full.log" 2>&1 &
PID_MUSR=$!

# MedCalc: 1 domain × 30 configs
(
  cd "$SCRIPT_DIR/medcalc"
  echo "[medcalc] Starting (N=$N_MEDCALC)..."
  uv run python run_pareto.py --dataset-n $N_MEDCALC --timeout $TIMEOUT
  echo "[medcalc] Done."
) > "$LOG_DIR/medcalc_full.log" 2>&1 &
PID_MEDCALC=$!

echo "All 5 launched in parallel. PIDs:"
echo "  rulearena:    $PID_RULEARENA"
echo "  natural_plan: $PID_NATPLAN"
echo "  tabmwp:       $PID_TABMWP"
echo "  musr:         $PID_MUSR"
echo "  medcalc:      $PID_MEDCALC"
echo ""
echo "Monitor: tail -f $LOG_DIR/<benchmark>_full.log"
echo "Wait all: wait"
echo ""

# Wait for all and report
FAILED=0
for NAME_PID in "rulearena:$PID_RULEARENA" "natural_plan:$PID_NATPLAN" \
                "tabmwp:$PID_TABMWP" "musr:$PID_MUSR" "medcalc:$PID_MEDCALC"; do
  NAME="${NAME_PID%%:*}"
  PID="${NAME_PID##*:}"
  if wait "$PID"; then
    echo "[DONE] $NAME"
  else
    echo "[FAIL] $NAME (see $LOG_DIR/${NAME}_full.log)"
    FAILED=$((FAILED + 1))
  fi
done

echo ""
if [ $FAILED -eq 0 ]; then
  echo "All 5 benchmarks completed successfully."
else
  echo "$FAILED benchmark(s) failed. Check logs."
fi
