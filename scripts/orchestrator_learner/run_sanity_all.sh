#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

LOG_DIR="$LOG_ROOT/sanity"
SNAPSHOT_DIR="$LOG_DIR/snapshots"
mkdir -p "$SNAPSHOT_DIR"

BEFORE_ROOTS="$SNAPSHOT_DIR/before_roots.txt"
BEFORE_ARTIFACTS="$SNAPSHOT_DIR/before_artifacts.txt"

find_artifact_roots() {
  find "$REPO_ROOT/benchmarks" -type d \
    \( -path '*/results/orchestration_learner' -o -path '*/.orchestration_learner' \) \
    -print | sort
}

snapshot_artifacts() {
  local roots_file="$1"
  local artifacts_file="$2"

  find_artifact_roots > "$roots_file"
  : > "$artifacts_file"
  while IFS= read -r root; do
    find "$root" -mindepth 1 -maxdepth 1 -print
  done < "$roots_file" | sort > "$artifacts_file"
}

cleanup_sanity_artifacts() {
  local after_roots="$SNAPSHOT_DIR/after_roots.txt"
  local after_artifacts="$SNAPSHOT_DIR/after_artifacts.txt"
  local removed="$SNAPSHOT_DIR/removed_artifacts.txt"

  snapshot_artifacts "$after_roots" "$after_artifacts"
  : > "$removed"

  while IFS= read -r path; do
    [[ -z "$path" ]] && continue
    if grep -Fxq "$path" "$BEFORE_ARTIFACTS"; then
      continue
    fi
    if [[ "$path" == *"/llm_cache"* ]]; then
      echo "Skipping llm_cache path: $path" >&2
      continue
    fi
    rm -rf -- "$path"
    echo "$path" >> "$removed"
  done < "$after_artifacts"

  while IFS= read -r root; do
    [[ -z "$root" ]] && continue
    if grep -Fxq "$root" "$BEFORE_ROOTS"; then
      continue
    fi
    rmdir "$root" 2>/dev/null || true
  done < "$after_roots"

  echo "Sanity cleanup removed $(wc -l < "$removed") new artifact(s)."
  echo "Cleanup log: $removed"
}

on_exit() {
  local status=$?
  cleanup_sanity_artifacts
  exit "$status"
}

snapshot_artifacts "$BEFORE_ROOTS" "$BEFORE_ARTIFACTS"
trap on_exit EXIT

for row in "${BENCHMARKS[@]}"; do
  IFS='|' read -r benchmark split seed _total _train _eval <<< "$row"
  run_learner existing_workflow "$benchmark" 2 1 "$split" "$seed" 1 "$LOG_DIR"
  run_learner seed_from_ptools "$benchmark" 2 1 "$split" "$seed" 1 "$LOG_DIR"
done
