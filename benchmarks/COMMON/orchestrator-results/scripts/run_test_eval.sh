#!/usr/bin/env bash
# Test-set re-evaluation of orchestration-learner final workflows.
# Loops 16 (class, bench) cells, invoking each benchmark's local expt.py
# with __learned__.<fn> bound to the workflow this run produced.
#
# The runner reads each cell's bench / entry_point / fn / config_file from
# its source run's run_metadata.json + implementation.yaml, so swapping a
# symlink under _train_dirs/<class>/<bench>/ is enough to pick a different
# orch_learner run.

set -uo pipefail

REPO=$(git rev-parse --show-toplevel)
ROOT="$REPO/benchmarks/COMMON/orchestrator-results"
LOG_ROOT="$ROOT/scripts/_logs"
mkdir -p "$LOG_ROOT"

MODEL="${MODEL:-together_ai/deepseek-ai/DeepSeek-V3.1}"
EXPT_TAG="${EXPT_TAG:-test_deepseek_v3_1}"
MAX_WORKERS="${MAX_WORKERS:-4}"

# Per-bench overrides for max_workers. Heavier benchmarks (medcalc, ~5 sub-tool
# LLM calls per case across 1100 cases) get more parallelism. Stay <~10 to
# avoid Together AI rate-limit 429s.
declare -A BENCH_WORKERS=(
  [medcalc]=16
)

# bench → bench_dir on disk
declare -A BENCH_DIR=(
  [medcalc]=medcalc
  [musr_murder]=musr
  [musr_object]=musr
  [musr_team]=musr
  [natplan_calendar]=natural_plan
  [natplan_meeting]=natural_plan
  [natplan_trip]=natural_plan
  [rulearena_nba]=rulearena
)

# bench → test-split dotlist (passed as positional config overrides)
# medcalc: stratified=false forces the FULL test split (conf has stratified=true
# which would otherwise sub-sample). We want the complete held-out set.
declare -A SPLIT_DOTLIST=(
  [medcalc]="dataset.split=test dataset.stratified=false"
  [musr_murder]="dataset.split=murder_mysteries_test"
  [musr_object]="dataset.split=object_placements_test"
  [musr_team]="dataset.split=team_allocation_test"
  [natplan_calendar]="dataset.partition=test"
  [natplan_meeting]="dataset.partition=test"
  [natplan_trip]="dataset.partition=test"
  [rulearena_nba]="dataset.split=test dataset.domain=nba dataset.complexity=all"
)

ROWS=(
  "existing_workflow:medcalc"
  "seed_from_ptools:medcalc"
  "existing_workflow:musr_murder"
  "seed_from_ptools:musr_murder"
  "existing_workflow:musr_object"
  "seed_from_ptools:musr_object"
  "existing_workflow:musr_team"
  "seed_from_ptools:musr_team"
  "existing_workflow:natplan_calendar"
  "seed_from_ptools:natplan_calendar"
  "existing_workflow:natplan_meeting"
  "seed_from_ptools:natplan_meeting"
  "existing_workflow:natplan_trip"
  "seed_from_ptools:natplan_trip"
  "existing_workflow:rulearena_nba"
  "seed_from_ptools:rulearena_nba"
)

ONLY="${ONLY:-}"  # optional substring filter, e.g. ONLY=rulearena_nba

# Optional CLI args:  ./run_test_eval.sh existing_workflow:rulearena_nba
if (( $# > 0 )); then
  ROWS=("$@")
fi

run_one() {
  local cls="$1" bench="$2"
  local bench_dir="${BENCH_DIR[$bench]:-}"
  if [[ -z "$bench_dir" ]]; then
    echo "ERROR: unknown bench '$bench'" >&2
    return 1
  fi

  local td="$ROOT/scripts/_train_dirs/$cls/$bench"
  local src
  src=$(readlink -f "$td"/*.orch_learner)
  if [[ ! -d "$src" ]]; then
    echo "ERROR: no symlink target under $td" >&2
    return 1
  fi

  # Pull entry point, fn binding, conf path from the source run's metadata.
  local meta="$src/run_metadata.json"
  local impl="$src/implementation.yaml"
  local entry fn conf_basename
  entry=$(python3 -c "import yaml; d=yaml.safe_load(open('$impl')); print(list(d)[0])")
  fn=$(python3 -c "import yaml; d=yaml.safe_load(open('$impl')); print(d[list(d)[0]]['fn'])")
  conf_basename=$(python3 -c "import json,os; print(os.path.basename(json.load(open('$meta'))['config_file']))")

  local conf_path="$REPO/benchmarks/$bench_dir/conf/$conf_basename"
  if [[ ! -f "$conf_path" ]]; then
    echo "ERROR: conf file not found: $conf_path" >&2
    return 1
  fi

  local out_dir="$ROOT/$cls/$bench"
  mkdir -p "$out_dir"

  local log_dir="$LOG_ROOT/$cls"
  mkdir -p "$log_dir"
  local log_path="$log_dir/$bench.log"

  local split_dotlist="${SPLIT_DOTLIST[$bench]}"
  local workers="${BENCH_WORKERS[$bench]:-$MAX_WORKERS}"

  # Auto-bind any @interface stubs in ptools_evolved.py that the conf
  # doesn't already configure. Without this, evolved workflows that call
  # *new* sub-tool stubs (e.g. extract_movements added by the evolver)
  # crash on first use with NotImplementedError. Default method is
  # simulate; works for str/int/float returns. Any sub-tool already in
  # the conf is left alone (its conf binding wins).
  local extra_bindings
  extra_bindings=$(python3 - "$conf_path" "$src/ptools_evolved.py" "$entry" <<'PY'
import re, sys, yaml
conf_path, evolved_path, entry = sys.argv[1:4]
cfg = yaml.safe_load(open(conf_path).read()) or {}
bound = set((cfg.get('ptools') or {}).keys())
src = open(evolved_path).read()
pat = re.compile(r"^@interface\b[^\n]*\n(?:^@\w[\w.]*[^\n]*\n)*^def\s+(\w+)\s*\(", re.MULTILINE)
out = []
for m in pat.finditer(src):
    name = m.group(1)
    if name == entry or name in bound:
        continue
    out.append(f"ptools.{name}.method=simulate")
print(' '.join(out))
PY
)

  echo "==============================================================" | tee -a "$log_path"
  echo "[$(date -Iseconds)] $cls / $bench" | tee -a "$log_path"
  echo "  src           = $src" | tee -a "$log_path"
  echo "  entry         = $entry" | tee -a "$log_path"
  echo "  fn            = $fn" | tee -a "$log_path"
  echo "  conf          = $conf_path" | tee -a "$log_path"
  echo "  split dotlist = $split_dotlist" | tee -a "$log_path"
  echo "  extra binds   = $extra_bindings" | tee -a "$log_path"
  echo "  workers       = $workers" | tee -a "$log_path"
  echo "  out_dir       = $out_dir" | tee -a "$log_path"
  echo "==============================================================" | tee -a "$log_path"

  ( cd "$REPO/benchmarks/$bench_dir" && \
    uv run python expt.py run \
      --config-file "$conf_path" \
      llm.model="$MODEL" \
      cachier.enable_caching=true \
      learn.train_dir="$td" \
      ptools."$entry".method=direct \
      ptools."$entry".fn="$fn" \
      ptools."$entry".learner=orch_learner \
      evaluate.entry_point="$entry" \
      evaluate.result_dir="$out_dir" \
      evaluate.expt_name="$EXPT_TAG" \
      evaluate.record_details=true \
      evaluate.max_workers="$workers" \
      dataset.n=null \
      $split_dotlist \
      $extra_bindings \
  ) 2>&1 | tee -a "$log_path"
  local rc=${PIPESTATUS[0]}
  echo "[$(date -Iseconds)] $cls / $bench exit=$rc" | tee -a "$log_path"
  return $rc
}

failed=()
for row in "${ROWS[@]}"; do
  IFS=":" read -r cls bench <<<"$row"
  if [[ -n "$ONLY" && "$row" != *"$ONLY"* ]]; then
    continue
  fi
  if ! run_one "$cls" "$bench"; then
    failed+=("$row")
  fi
done

echo
if (( ${#failed[@]} > 0 )); then
  echo "FAILED rows:"
  printf '  %s\n' "${failed[@]}"
  exit 1
fi
echo "All requested rows completed."
