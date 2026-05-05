#!/usr/bin/env bash
# Wait for the orphaned existing/medcalc cell to finish, then launch the
# medcalc lane to schedule seed/medcalc. By the time this fires, the
# driver's BENCH_WORKERS[medcalc] is already 16, so seed/medcalc starts
# with 16 workers — no kill of the in-flight 8-worker existing cell.

set -u
REPO=$(git rev-parse --show-toplevel)
ROOT="$REPO/benchmarks/COMMON/orchestrator-results"
ORCH="$ROOT/scripts/run_parallel.sh"
RLOG="$ROOT/scripts/_logs/parallel"
mkdir -p "$RLOG"

PATTERN="$ROOT/existing_workflow/medcalc/*test_deepseek_v3_1/results.csv"

echo "[resume-medcalc] waiting for existing/medcalc CSV ($PATTERN)"
until ls $PATTERN 2>/dev/null | grep -q .; do
  sleep 60
done
echo "[resume-medcalc] orphan complete at $(date -Iseconds), launching medcalc lane (workers=16 via driver)"

LANES=medcalc bash "$ORCH" >> "$RLOG/medcalc_resumed.log" 2>&1
echo "[resume-medcalc] medcalc lane exited at $(date -Iseconds)"
