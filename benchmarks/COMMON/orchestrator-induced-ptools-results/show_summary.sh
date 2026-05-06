#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
uv run --script scripts/show_summary.py
