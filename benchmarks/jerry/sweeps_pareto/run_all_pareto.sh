#!/usr/bin/env bash
# Run Pareto sweeps across all 5 benchmarks.
# Benchmarks run in parallel (each benchmark's domains run sequentially).
# Logs go to benchmarks/pareto_logs/<benchmark>.log
#
# Usage: bash benchmarks/run_all_pareto.sh
#   From repo root, or:  cd benchmarks && bash run_all_pareto.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/pareto_logs"
mkdir -p "$LOG_DIR"

N=30  # dataset size per eval

echo "Starting Pareto sweeps (n=$N) across 5 benchmarks..."
echo "Logs: $LOG_DIR/"
echo ""

# RuleArena: 3 domains × 24 configs = 72 evals
(
  cd "$SCRIPT_DIR/rulearena"
  echo "[rulearena] Starting airline..."
  uv run python run_pareto.py --domain airline --dataset-n $N
  echo "[rulearena] Starting nba..."
  uv run python run_pareto.py --domain nba --dataset-n $N
  echo "[rulearena] Starting tax..."
  uv run python run_pareto.py --domain tax --dataset-n $N
  echo "[rulearena] Done."
) > "$LOG_DIR/rulearena.log" 2>&1 &
PID_RULEARENA=$!

# Natural Plan: 3 domains × 25 configs = 75 evals
(
  cd "$SCRIPT_DIR/natural_plan"
  echo "[natural_plan] Starting calendar..."
  uv run python run_pareto.py --domain calendar --dataset-n $N
  echo "[natural_plan] Starting meeting..."
  uv run python run_pareto.py --domain meeting --dataset-n $N
  echo "[natural_plan] Starting trip..."
  uv run python run_pareto.py --domain trip --dataset-n $N
  echo "[natural_plan] Done."
) > "$LOG_DIR/natural_plan.log" 2>&1 &
PID_NATPLAN=$!

# TabMWP: 1 domain × 25 configs = 25 evals
(
  cd "$SCRIPT_DIR/tabmwp"
  echo "[tabmwp] Starting..."
  uv run python run_pareto.py --dataset-n $N
  echo "[tabmwp] Done."
) > "$LOG_DIR/tabmwp.log" 2>&1 &
PID_TABMWP=$!

# MuSR: 3 domains × 15 configs = 45 evals
(
  cd "$SCRIPT_DIR/musr"
  echo "[musr] Starting murder..."
  uv run python run_pareto.py --domain murder --dataset-n $N
  echo "[musr] Starting object..."
  uv run python run_pareto.py --domain object --dataset-n $N
  echo "[musr] Starting team..."
  uv run python run_pareto.py --domain team --dataset-n $N
  echo "[musr] Done."
) > "$LOG_DIR/musr.log" 2>&1 &
PID_MUSR=$!

# MedCalc: 1 domain × 30 configs = 30 evals
(
  cd "$SCRIPT_DIR/medcalc"
  echo "[medcalc] Starting..."
  uv run python run_pareto.py --dataset-n $N
  echo "[medcalc] Done."
) > "$LOG_DIR/medcalc.log" 2>&1 &
PID_MEDCALC=$!

echo "All 5 launched in parallel. PIDs:"
echo "  rulearena:    $PID_RULEARENA"
echo "  natural_plan: $PID_NATPLAN"
echo "  tabmwp:       $PID_TABMWP"
echo "  musr:         $PID_MUSR"
echo "  medcalc:      $PID_MEDCALC"
echo ""
echo "Monitor: tail -f $LOG_DIR/<benchmark>.log"
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
    echo "[FAIL] $NAME (see $LOG_DIR/$NAME.log)"
    FAILED=$((FAILED + 1))
  fi
done

echo ""
if [ $FAILED -eq 0 ]; then
  echo "All 5 benchmarks completed successfully."
else
  echo "$FAILED benchmark(s) failed. Check logs."
fi
