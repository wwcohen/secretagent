#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ORCH_RUN_TIMESTAMP="${ORCH_RUN_TIMESTAMP:-$(date +%Y%m%d.%H%M%S)}"

bash "$SCRIPT_DIR/run_existing_workflow_all.sh"
bash "$SCRIPT_DIR/run_seed_from_ptools_all.sh"
