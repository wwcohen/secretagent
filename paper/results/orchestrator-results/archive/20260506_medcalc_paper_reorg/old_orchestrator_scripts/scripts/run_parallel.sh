#!/usr/bin/env bash
# Parallel orchestrator for run_test_eval.sh.
#
# Splits the 16 cells into 4 lanes by bench-dir (one lane per llm_cache dir
# to avoid file-lock contention). Lanes run concurrently; cells within a
# lane run serially. Each cell is retried up to MAX_RETRIES on non-zero exit.
#
# Usage:
#   bash run_parallel.sh                      # all 4 lanes
#   LANES="medcalc,rulearena" bash run_parallel.sh
#   MAX_RETRIES=3 bash run_parallel.sh
#
# Each lane writes to _logs/parallel/<lane>.log; per-cell logs still go to
# _logs/<class>/<bench>.log via run_test_eval.sh.

set -u

REPO=$(git rev-parse --show-toplevel)
ROOT="$REPO/benchmarks/COMMON/orchestrator-results"
PARALLEL_LOG_DIR="$ROOT/scripts/_logs/parallel"
mkdir -p "$PARALLEL_LOG_DIR"

DRIVER="$ROOT/scripts/run_test_eval.sh"
MAX_RETRIES="${MAX_RETRIES:-2}"
LANES_FILTER="${LANES:-}"

# Lane definitions. Cells within a lane run serially (shared bench-dir +
# shared llm_cache means file-lock contention if run in parallel).
declare -A LANE_CELLS=(
  [medcalc]="existing_workflow:medcalc seed_from_ptools:medcalc"
  [musr]="existing_workflow:musr_murder seed_from_ptools:musr_murder existing_workflow:musr_object seed_from_ptools:musr_object existing_workflow:musr_team seed_from_ptools:musr_team"
  [natural_plan]="existing_workflow:natplan_calendar seed_from_ptools:natplan_calendar existing_workflow:natplan_meeting seed_from_ptools:natplan_meeting existing_workflow:natplan_trip seed_from_ptools:natplan_trip"
  [rulearena]="existing_workflow:rulearena_nba seed_from_ptools:rulearena_nba"
)

LANE_ORDER=(medcalc musr natural_plan rulearena)

if [[ -n "$LANES_FILTER" ]]; then
  IFS=',' read -ra ORDERED <<<"$LANES_FILTER"
  LANE_ORDER=("${ORDERED[@]}")
fi

# A "cell already done" check: result_dir contains at least one timestamped
# subdir whose results.csv has at least 1 data row. Lets us re-run safely
# without redoing already-completed cells.
cell_done() {
  local cls="$1" bench="$2"
  local out_dir="$ROOT/$cls/$bench"
  [[ -d "$out_dir" ]] || return 1
  # savefile dirnames are {YYYYMMDD}.{HHMMSS}.{tag}; tag is the last `.`-segment
  for sub in "$out_dir"/*.test_deepseek_v3_1/; do
    [[ -f "$sub/results.csv" ]] || continue
    local n
    n=$(wc -l < "$sub/results.csv" 2>/dev/null || echo 0)
    (( n >= 2 )) || continue
    # Reject all-exception runs: if every data row has "exception raised",
    # treat as not-done so the cell will be retried (e.g. after a config fix).
    local data_rows=$((n - 1))
    local exc_rows
    exc_rows=$(grep -c "exception raised" "$sub/results.csv" 2>/dev/null || echo 0)
    if (( exc_rows >= data_rows )); then
      continue
    fi
    return 0
  done
  return 1
}

run_lane() {
  local lane="$1"
  local cells_str="${LANE_CELLS[$lane]:-}"
  local lane_log="$PARALLEL_LOG_DIR/$lane.log"

  if [[ -z "$cells_str" ]]; then
    echo "[lane $lane] no cells defined" >> "$lane_log"
    return 0
  fi

  read -ra cells <<<"$cells_str"
  echo "[lane $lane] starting $(date -Iseconds), cells=${#cells[@]}" > "$lane_log"

  local failures=()
  for cell in "${cells[@]}"; do
    IFS=":" read -r cls bench <<<"$cell"

    if cell_done "$cls" "$bench"; then
      echo "[lane $lane] $cell SKIP (already complete)" >> "$lane_log"
      continue
    fi

    local attempt=0 rc=1
    while (( attempt <= MAX_RETRIES )); do
      attempt=$((attempt+1))
      echo "[lane $lane] $cell attempt $attempt/$((MAX_RETRIES+1)) start $(date -Iseconds)" >> "$lane_log"
      bash "$DRIVER" "$cell" >> "$lane_log" 2>&1
      rc=$?
      echo "[lane $lane] $cell attempt $attempt exit=$rc" >> "$lane_log"
      if (( rc == 0 )) && cell_done "$cls" "$bench"; then
        break
      fi
      # Short backoff before retry; let any transient API issue settle.
      sleep 5
    done

    if (( rc != 0 )) || ! cell_done "$cls" "$bench"; then
      failures+=("$cell")
      echo "[lane $lane] $cell FAILED after $attempt attempts" >> "$lane_log"
    fi
  done

  if (( ${#failures[@]} > 0 )); then
    echo "[lane $lane] DONE WITH FAILURES at $(date -Iseconds): ${failures[*]}" >> "$lane_log"
    return 1
  fi
  echo "[lane $lane] DONE at $(date -Iseconds)" >> "$lane_log"
  return 0
}

# Launch lanes in parallel
declare -A LANE_PID=()
for lane in "${LANE_ORDER[@]}"; do
  run_lane "$lane" &
  LANE_PID[$lane]=$!
  echo "[orchestrator] launched lane=$lane pid=${LANE_PID[$lane]}"
done

# Wait, collect statuses
overall_failures=()
for lane in "${LANE_ORDER[@]}"; do
  pid=${LANE_PID[$lane]}
  wait "$pid"
  rc=$?
  echo "[orchestrator] lane=$lane pid=$pid exit=$rc"
  if (( rc != 0 )); then
    overall_failures+=("$lane")
  fi
done

if (( ${#overall_failures[@]} > 0 )); then
  echo "[orchestrator] LANES WITH FAILURES: ${overall_failures[*]}"
  exit 1
fi

echo "[orchestrator] ALL LANES COMPLETED CLEANLY at $(date -Iseconds)"
