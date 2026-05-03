#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ -f "$REPO_ROOT/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$REPO_ROOT/.env"
  set +a
else
  echo "Missing $REPO_ROOT/.env" >&2
  exit 1
fi

if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  echo "GEMINI_API_KEY must be set in $REPO_ROOT/.env or the environment" >&2
  exit 1
fi

AGENT_MODEL="gemini/gemini-3.1-flash-lite-preview"
SUPERVISOR_MODEL="gemini/gemini-3.1-pro-preview"
MAX_WORKERS=1
RUN_TIMESTAMP="${ORCH_RUN_TIMESTAMP:-$(date +%Y%m%d.%H%M%S)}"
LOG_ROOT="$REPO_ROOT/logs/orchestration_runs/$RUN_TIMESTAMP"

# benchmark|pool_split|seed|total|train|eval
BENCHMARKS=(
  "finqa|valid|42|300|210|90"
  "medcalc|train|42|275|193|82"
  "musr_murder|murder_mysteries_test|42|100|70|30"
  "musr_object|object_placements_test|42|106|74|32"
  "musr_team|team_allocation_test|42|100|70|30"
  "natural_plan_calendar|calendar|42|100|70|30"
  "natural_plan_meeting|meeting|42|100|70|30"
  "natural_plan_trip|trip|42|100|70|30"
  "rulearena_airline|valid|137|60|42|18"
  "rulearena_nba|valid|137|42|29|13"
  "rulearena_tax|valid|137|60|42|18"
  "tabmwp|dev1k|42|100|70|30"
  "sports_understanding|valid|137|75|53|22"
  "geometric_shapes|valid|137|75|53|22"
  "penguins_in_a_table|valid|137|43|30|13"
)

run_learner() {
  local class="$1"
  local benchmark="$2"
  local n_train="$3"
  local n_eval="$4"
  local split="$5"
  local seed="$6"
  local max_iter="$7"
  local log_dir="$8"

  mkdir -p "$log_dir"
  local log_file="$log_dir/${class}_${benchmark}.log"
  local seed_args=()

  case "$class" in
    existing_workflow)
      ;;
    seed_from_ptools)
      seed_args=(--seed-orchestrate)
      ;;
    *)
      echo "Unknown orchestration learner class: $class" >&2
      return 2
      ;;
  esac

  echo
  echo "=== $class :: $benchmark split=$split train=$n_train eval=$n_eval iter=$max_iter ==="
  echo "Log: $log_file"

  (
    cd "$REPO_ROOT"
    uv run python -m secretagent.cli.orchestration_learner run \
      --benchmark "$benchmark" \
      --train-split "$split" \
      --eval-split "$split" \
      --n-train "$n_train" \
      --n-eval "$n_eval" \
      --max-iterations "$max_iter" \
      --supervisor-model "$SUPERVISOR_MODEL" \
      --scratch-evolved \
      "${seed_args[@]}" \
      llm.model="$AGENT_MODEL" \
      orchestrate.model="$SUPERVISOR_MODEL" \
      cachier.enable_caching=true \
      dataset.shuffle_seed="$seed" \
      evaluate.max_workers="$MAX_WORKERS"
  ) 2>&1 | tee "$log_file"
  return "${PIPESTATUS[0]}"
}
