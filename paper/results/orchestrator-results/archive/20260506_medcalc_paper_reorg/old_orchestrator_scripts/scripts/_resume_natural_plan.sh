#!/usr/bin/env bash
# Wait for the orphaned seed/natplan_calendar cell to finish, then launch
# the natural_plan lane to schedule existing+seed natplan_meeting and
# natplan_trip cells. cell_done will SKIP the two already-done calendar
# cells.

set -u
REPO=$(git rev-parse --show-toplevel)
ROOT="$REPO/benchmarks/COMMON/orchestrator-results"
ORCH="$ROOT/scripts/run_parallel.sh"
RLOG="$ROOT/scripts/_logs/parallel"
mkdir -p "$RLOG"

PATTERN="$ROOT/seed_from_ptools/natplan_calendar/*test_deepseek_v3_1/results.csv"

echo "[resume-natplan] waiting for seed/natplan_calendar CSV ($PATTERN)"
until ls $PATTERN 2>/dev/null | grep -q .; do
  sleep 60
done
echo "[resume-natplan] orphan complete at $(date -Iseconds), launching natural_plan lane"

LANES=natural_plan bash "$ORCH" >> "$RLOG/natural_plan_resumed.log" 2>&1
echo "[resume-natplan] natural_plan lane exited at $(date -Iseconds)"
