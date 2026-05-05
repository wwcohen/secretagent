#!/usr/bin/env bash
# Print accuracy + cost summary tables for both workflow types to terminal.
# Implementation lives in scripts/show_summary.py — this is a convenience
# wrapper so the only top-level entry point is one obvious bash command.

set -e
HERE=$(dirname "$(realpath "$0")")
exec uv run --script "$HERE/scripts/show_summary.py" "$@"
