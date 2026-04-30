#!/usr/bin/env bash
# Run all 5 strategies on the full valid set, sequentially. Cases run one at a
# time inside each strategy (matches the team's sequential default; see
# benchmarks/results/, where 185/190 runs use max_workers=1). Continues on
# per-strategy failures so one bad run doesn't abort the others.
#
# Usage:    bash run_all_valid.sh
# Logs:     logs/run_all_<timestamp>.log

set -u

DOTPAIRS="evaluate.record_details=true"

mkdir -p logs
LOG="logs/run_all_$(date +%Y%m%d_%H%M%S).log"
echo "Logging to $LOG"

for s in unstructured_baseline structured_baseline workflow pot react; do
  {
    echo "=== $s start: $(date) ==="
    make "$s" DOTPAIRS="$DOTPAIRS"
    echo "=== $s end:   $(date) (exit=$?) ==="
    echo
  } 2>&1 | tee -a "$LOG"
done

echo "=== ALL DONE: $(date) ===" | tee -a "$LOG"
