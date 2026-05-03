#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

LOG_DIR="$LOG_ROOT/seed_from_ptools"
mkdir -p "$LOG_DIR"

for row in "${BENCHMARKS[@]}"; do
  IFS='|' read -r benchmark split seed _total train eval <<< "$row"
  run_learner seed_from_ptools "$benchmark" "$train" "$eval" "$split" "$seed" 5 "$LOG_DIR"
done
