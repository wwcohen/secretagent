#!/usr/bin/env bash
# Replay all musr cells that had transient exception rows. With cache hot,
# previously successful sub-tool calls are reused; only the failed cases
# re-issue LLM calls. Each cell writes to a NEW timestamped dir;
# show_results.py picks the latest, so the new clean run becomes the
# reference automatically.

set -u
REPO=$(git rev-parse --show-toplevel)
ROOT="$REPO/benchmarks/COMMON/orchestrator-results"
DRIVER="$ROOT/scripts/run_test_eval.sh"

# All affected cells share musr/llm_cache, so run them serially to avoid
# file-lock contention on the cache directory.
CELLS=(
  "existing_workflow:musr_murder"
  "existing_workflow:musr_object"
  "existing_workflow:musr_team"
  "seed_from_ptools:musr_object"
  "seed_from_ptools:musr_team"
)

for cell in "${CELLS[@]}"; do
  echo "[replay] $(date -Iseconds) starting $cell"
  bash "$DRIVER" "$cell"
  echo "[replay] $(date -Iseconds) done $cell"
done
echo "[replay] all cells done at $(date -Iseconds)"
