#!/usr/bin/env bash

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
COMMON=$(cd "$HERE/.." && pwd)
exec uv run --script "$COMMON/scripts/show_orchestrator_summary.py" "$HERE" "$@"
