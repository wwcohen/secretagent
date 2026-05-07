#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

LOG_DIR="$LOG_ROOT/existing_workflow"
mkdir -p "$LOG_DIR"

for row in "${BENCHMARKS[@]}"; do
  IFS='|' read -r benchmark split seed _total train eval <<< "$row"
  run_learner existing_workflow "$benchmark" "$train" "$eval" "$split" "$seed" 5 "$LOG_DIR"
done
