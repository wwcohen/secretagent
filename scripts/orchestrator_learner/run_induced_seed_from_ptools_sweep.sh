#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ -f "$REPO_ROOT/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$REPO_ROOT/.env"
  set +a
fi

if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  echo "GEMINI_API_KEY must be set in $REPO_ROOT/.env or the environment" >&2
  exit 1
fi

AGENT_MODEL="${AGENT_MODEL:-gemini/gemini-3.1-flash-lite-preview}"
SUPERVISOR_MODEL="${SUPERVISOR_MODEL:-gemini/gemini-3.1-pro-preview}"
MAX_WORKERS="${MAX_WORKERS:-1}"
MAX_ITERATIONS="${MAX_ITERATIONS:-5}"
RUN_TIMESTAMP="${ORCH_RUN_TIMESTAMP:-$(date +%Y%m%d.%H%M%S)}"
LOG_DIR="$REPO_ROOT/logs/orchestration_runs/$RUN_TIMESTAMP/induced_seed_from_ptools"
LINK_ROOT="$REPO_ROOT/paper/results/orchestrator-results/_train_dirs/induced_seed_from_ptools"
export PYDANTIC_DISABLE_PLUGINS="${PYDANTIC_DISABLE_PLUGINS:-1}"
mkdir -p "$LOG_DIR" "$LINK_ROOT"

# label|benchmark|bench_dir|config_rel|ptools_module|split|seed|n_train|n_eval
ROWS=(
  "musr_murder|musr_murder|musr|conf/murder_induced_seed_from_ptools.yaml|ptools_murder_induced_seed|murder_mysteries_test|42|70|30"
  "musr_object|musr_object|musr|conf/object_induced_seed_from_ptools.yaml|ptools_object_induced_seed|object_placements_test|42|74|32"
  "musr_team|musr_team|musr|conf/team_induced_seed_from_ptools.yaml|ptools_team_induced_seed|team_allocation_test|42|70|30"
  "natplan_meeting|natural_plan_meeting|natural_plan|conf/meeting_induced_seed_from_ptools.yaml|ptools_meeting_induced_seed|meeting|42|70|30"
  "natplan_trip|natural_plan_trip|natural_plan|conf/trip_induced_seed_from_ptools.yaml|ptools_trip_induced_seed|trip|42|70|30"
  "rulearena_nba|rulearena_nba|rulearena|conf/nba_induced_seed_from_ptools.yaml|ptools_nba_induced_seed|valid|137|29|13"
)

if (( $# > 0 )); then
  FILTERS=("$@")
else
  FILTERS=()
fi

selected() {
  local label="$1"
  if (( ${#FILTERS[@]} == 0 )); then
    return 0
  fi
  local filter
  for filter in "${FILTERS[@]}"; do
    [[ "$label" == "$filter" ]] && return 0
  done
  return 1
}

latest_matching_run() {
  local bench_dir="$1" ptools_module="$2" split="$3" n_train="$4" n_eval="$5" max_iterations="$6"
  python3 - "$bench_dir/results/orchestration_learner" "$ptools_module" "$split" "$n_train" "$n_eval" "$max_iterations" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
ptools_module, split = sys.argv[2], sys.argv[3]
n_train, n_eval = int(sys.argv[4]), int(sys.argv[5])
max_iterations = int(sys.argv[6])
matches = []
for meta in root.glob("*.orch_learner/run_metadata.json"):
    try:
        data = json.loads(meta.read_text())
    except Exception:
        continue
    if (
        data.get("ptools_module") == ptools_module
        and data.get("seed_orchestrate") is True
        and data.get("scratch_evolved") is True
        and data.get("train_split") == split
        and data.get("eval_split") == split
        and data.get("n_train") == n_train
        and data.get("n_eval") == n_eval
        and data.get("max_iterations") == max_iterations
        and data.get("supervisor_model") == "gemini/gemini-3.1-pro-preview"
    ):
        matches.append(meta.parent)
if not matches:
    raise SystemExit(1)
print(sorted(matches)[-1])
PY
}

link_run() {
  local label="$1" run_dir="$2"
  local dest="$LINK_ROOT/$label"
  local pointer="$dest/$(basename "$run_dir")"
  local rel_run_dir
  mkdir -p "$dest"
  find "$dest" -maxdepth 1 \( -type l -o -type f \) -name '*.orch_learner' -delete
  if [[ -d "$pointer" && ! -L "$pointer" ]]; then
    pointer="$dest/$(basename "$run_dir").pointer.orch_learner"
  fi
  if [[ -e "$pointer" ]]; then
    echo "ERROR: cannot write pointer; path already exists: $pointer" >&2
    return 1
  fi
  rel_run_dir=$(python3 - "$REPO_ROOT" "$run_dir" <<'PY'
import os
import sys

print(os.path.relpath(sys.argv[2], sys.argv[1]))
PY
)
  printf '%s\n' "$rel_run_dir" > "$pointer"
}

for row in "${ROWS[@]}"; do
  IFS='|' read -r label benchmark bench_rel config_rel ptools_module split seed n_train n_eval <<< "$row"
  selected "$label" || continue

  bench_dir="$REPO_ROOT/benchmarks/$bench_rel"
  config_file="$bench_dir/$config_rel"
  log_file="$LOG_DIR/$label.log"

  echo
  echo "=== induced_seed_from_ptools :: $label split=$split train=$n_train eval=$n_eval iter=$MAX_ITERATIONS ==="
  echo "Config: $config_file"
  echo "Ptools: $ptools_module"
  echo "Log: $log_file"

  (
    cd "$REPO_ROOT"
    uv run python -m secretagent.cli.orchestration_learner run \
      --benchmark "$benchmark" \
      --config-file "$config_file" \
      --ptools-module "$ptools_module" \
      --train-split "$split" \
      --eval-split "$split" \
      --n-train "$n_train" \
      --n-eval "$n_eval" \
      --max-iterations "$MAX_ITERATIONS" \
      --supervisor-model "$SUPERVISOR_MODEL" \
      --seed-orchestrate \
      --scratch-evolved \
      llm.model="$AGENT_MODEL" \
      orchestrate.model="$SUPERVISOR_MODEL" \
      cachier.enable_caching=true \
      dataset.shuffle_seed="$seed" \
      evaluate.max_workers="$MAX_WORKERS"
  ) 2>&1 | tee "$log_file"
  rc=${PIPESTATUS[0]}
  if (( rc != 0 )); then
    exit "$rc"
  fi

  run_dir=$(latest_matching_run "$bench_dir" "$ptools_module" "$split" "$n_train" "$n_eval" "$MAX_ITERATIONS")
  link_run "$label" "$run_dir"
  echo "Linked $label -> $run_dir"
done
