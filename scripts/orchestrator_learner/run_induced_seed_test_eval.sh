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

if [[ -z "${TOGETHERAI_API_KEY:-}${TOGETHER_API_KEY:-}" ]]; then
  echo "Together AI credentials must be set in $REPO_ROOT/.env or the environment" >&2
  exit 1
fi

MODEL="${MODEL:-together_ai/deepseek-ai/DeepSeek-V3.1}"
MAX_WORKERS="${MAX_WORKERS:-1}"
CACHING="${CACHING:-false}"
LINK_ROOT="$REPO_ROOT/paper/results/orchestrator-results/_train_dirs/induced_seed_from_ptools"
RESOLVE_RUN="$REPO_ROOT/paper/results/orchestrator-results/scripts/resolve_learner_run.py"
LOG_DIR="$REPO_ROOT/logs/orchestration_runs/$(date +%Y%m%d.%H%M%S)/induced_seed_test_eval"
export PYDANTIC_DISABLE_PLUGINS="${PYDANTIC_DISABLE_PLUGINS:-1}"
mkdir -p "$LOG_DIR"

# label|bench_dir|config_rel|entry|expected_rows|expt_name|dataset_dotlist
ROWS=(
  "musr_murder|musr|conf/murder.yaml|answer_question_workflow|100|musr_murder_induced_seed_ptools_deepseek_v3_1|dataset.n=null dataset.split=murder_mysteries_test"
  "musr_object|musr|conf/object.yaml|answer_question_workflow|106|musr_object_induced_seed_ptools_deepseek_v3_1|dataset.n=null dataset.split=object_placements_test"
  "musr_team|musr|conf/team.yaml|answer_question|100|musr_team_induced_seed_ptools_deepseek_v3_1|dataset.n=null dataset.split=team_allocation_test"
  "natplan_meeting|natural_plan|conf/meeting.yaml|meeting_planning|100|natplan_meeting_induced_seed_ptools_deepseek_v3_1|dataset.n=100 dataset.split=meeting"
  "natplan_trip|natural_plan|conf/trip.yaml|trip_planning|100|natplan_trip_induced_seed_ptools_deepseek_v3_1|dataset.n=100 dataset.split=trip"
  "rulearena_nba|rulearena|conf/conf.yaml|compute_rulearena_answer|46|rulearena_nba_induced_seed_ptools_deepseek_v3_1|dataset.n=null dataset.split=test dataset.domain=nba dataset.complexity=all"
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

for row in "${ROWS[@]}"; do
  IFS='|' read -r label bench_rel config_rel entry expected_rows expt_name dataset_dotlist <<< "$row"
  selected "$label" || continue

  train_dir="$LINK_ROOT/$label"
  run_dir=$(python3 "$RESOLVE_RUN" "$train_dir" --repo-root "$REPO_ROOT")
  if [[ ! -d "$run_dir" ]]; then
    echo "ERROR: no induced learner run found under $train_dir" >&2
    exit 1
  fi

  impl="$run_dir/implementation.yaml"
  fn=$(python3 - "$impl" <<'PY'
import sys
import yaml

data = yaml.safe_load(open(sys.argv[1]).read())
entry = next(iter(data))
print(data[entry]["fn"])
PY
)

  bench_dir="$REPO_ROOT/benchmarks/$bench_rel"
  config_file="$bench_dir/$config_rel"
  out_dir="$bench_dir/test_results_full"
  mkdir -p "$out_dir"
  log_file="$LOG_DIR/$label.log"

  echo
  echo "=== test_eval :: $label rows=$expected_rows model=$MODEL ==="
  echo "Run: $run_dir"
  echo "Output: $out_dir"
  echo "Log: $log_file"

  (
    cd "$bench_dir"
    uv run python expt.py run \
      --config-file "$config_file" \
      llm.model="$MODEL" \
      cachier.enable_caching="$CACHING" \
      learn.train_dir="$train_dir" \
      ptools."$entry".method=direct \
      ptools."$entry".fn="$fn" \
      ptools."$entry".learner=orch_learner \
      evaluate.entry_point="$entry" \
      evaluate.result_dir="$out_dir" \
      evaluate.expt_name="$expt_name" \
      evaluate.record_details=true \
      evaluate.max_workers="$MAX_WORKERS" \
      $dataset_dotlist
  ) 2>&1 | tee "$log_file"

  csv_path=$(python3 - "$out_dir" "$expt_name" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
tag = sys.argv[2]
matches = sorted(root.glob(f"*.{tag}/results.csv"))
if not matches:
    raise SystemExit(1)
print(matches[-1])
PY
)
  actual_rows=$(python3 - "$csv_path" <<'PY'
import csv
import sys

with open(sys.argv[1], newline="") as f:
    print(sum(1 for _ in csv.DictReader(f)))
PY
)
  if [[ "$actual_rows" != "$expected_rows" ]]; then
    echo "ERROR: $label expected $expected_rows rows, got $actual_rows in $csv_path" >&2
    exit 1
  fi
  echo "Verified $label rows=$actual_rows ($csv_path)"
done
