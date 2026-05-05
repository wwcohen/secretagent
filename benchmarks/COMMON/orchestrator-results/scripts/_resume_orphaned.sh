#!/usr/bin/env bash
# Watcher: when each orphaned in-flight cell finishes (its results.csv lands),
# launch the lane it belongs to so the lane's remaining cells get scheduled.
# The lane's cell_done check will SKIP the just-completed orphan and the other
# already-done cells.

set -u
REPO=$(git rev-parse --show-toplevel)
ROOT="$REPO/benchmarks/COMMON/orchestrator-results"
ORCH="$ROOT/scripts/run_parallel.sh"
RLOG="$ROOT/scripts/_logs/parallel"
mkdir -p "$RLOG"

wait_for_csv() {
  local pattern="$1" label="$2"
  echo "[resume] waiting for $label ($pattern)"
  until ls $pattern 2>/dev/null | grep -q .; do
    sleep 60
  done
  echo "[resume] $label complete at $(date -Iseconds)"
}

# medcalc lane — orphan cell: existing/medcalc
(
  wait_for_csv "$ROOT/existing_workflow/medcalc/*test_deepseek_v3_1/results.csv" "existing/medcalc"
  echo "[resume] launching medcalc lane (will SKIP done cell, run seed/medcalc)"
  LANES=medcalc bash "$ORCH" >> "$RLOG/medcalc_resumed.log" 2>&1
) &

# natural_plan lane — orphan cell: seed/natplan_calendar
(
  wait_for_csv "$ROOT/seed_from_ptools/natplan_calendar/*test_deepseek_v3_1/results.csv" "seed/natplan_calendar"
  echo "[resume] launching natural_plan lane (will SKIP done cells, run meeting+trip)"
  LANES=natural_plan bash "$ORCH" >> "$RLOG/natural_plan_resumed.log" 2>&1
) &

wait
echo "[resume] all watchers exited at $(date -Iseconds)"
