#!/bin/bash
# Val eval for Class 1 v5 gate compare. 6 jobs (3 tasks × 2 gates).
# Reads ENABLED ptools from learned_v5_<gate>gate/codedistill_config.yaml and runs
# the bench's pipeline on val split with those overrides applied via dotlist.
set +e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
set -a; source "$ROOT/.env"; set +a

run_natplan_val() {
  local sub="$1"; local n="$2"; local gate="$3"
  local out_dir="learned_v5_${gate}gate"
  local cfg="$ROOT/benchmarks/natural_plan/$out_dir/codedistill_config.yaml"
  if [ ! -f "$cfg" ]; then
    echo "[$sub gate=$gate] no cfg ($cfg) — skip"; return
  fi
  cd "$ROOT/benchmarks/natural_plan"
  declare -a PTOOL_ARGS=()
  while IFS= read -r line; do
    PTOOL_ARGS+=("$line")
  done < <(uv run python -c "
import yaml
cfg = yaml.safe_load(open('$out_dir/codedistill_config.yaml'))
for n, kvs in (cfg.get('ptools', {}) or {}).items():
    for k, v in (kvs or {}).items():
        v = repr(v) if isinstance(v, bool) else v
        print(f'ptools.{n}.{k}={v}')
" 2>/dev/null)
  echo "[$sub gate=$gate] PTOOL_ARGS=${PTOOL_ARGS[*]}"
  nohup uv run python expt.py run \
    --config-file "conf/${sub}.yaml" \
    "${PTOOL_ARGS[@]}" \
    "learn.train_dir=$ROOT/benchmarks/natural_plan/$out_dir" \
    dataset.partition=valid "dataset.n=$n" \
    "evaluate.expt_name=${sub}_val_full_class1v5_${gate}gate" \
    evaluate.result_dir=val_results_full > /tmp/${sub}_v5_${gate}.log 2>&1 &
  echo "  PID: $!"
}

run_finqa_val() {
  local gate="$1"
  local out_dir="learned_v5_${gate}gate"
  local cfg="$ROOT/benchmarks/finqa/finqa/$out_dir/codedistill_config.yaml"
  if [ ! -f "$cfg" ]; then
    echo "[finqa gate=$gate] no cfg — skip"; return
  fi
  cd "$ROOT/benchmarks/finqa"
  declare -a PTOOL_ARGS=()
  while IFS= read -r line; do
    PTOOL_ARGS+=("$line")
  done < <(uv run python -c "
import yaml
cfg = yaml.safe_load(open('$out_dir/codedistill_config.yaml'))
for n, kvs in (cfg.get('ptools', {}) or {}).items():
    for k, v in (kvs or {}).items():
        v = repr(v) if isinstance(v, bool) else v
        print(f'ptools.{n}.{k}={v}')
" 2>/dev/null)
  echo "[finqa gate=$gate] PTOOL_ARGS=${PTOOL_ARGS[*]}"
  nohup uv run python expt.py run \
    --config-file conf/workflow.yaml \
    "${PTOOL_ARGS[@]}" \
    "learn.train_dir=$ROOT/benchmarks/finqa/finqa/$out_dir" \
    dataset.split=valid dataset.n=100 \
    "evaluate.expt_name=finqa_val_full_class1v5_${gate}gate" \
    evaluate.result_dir=val_results_full > /tmp/finqa_v5_${gate}.log 2>&1 &
  echo "  finqa gate=$gate PID: $!"
}

echo "=== val eval — start at $(date) ==="

# Calendar
run_natplan_val calendar 100 train
run_natplan_val calendar 100 val
# Meeting
run_natplan_val meeting  100 train
run_natplan_val meeting  100 val
# Finqa
run_finqa_val train
run_finqa_val val

echo "=== launched, waiting ==="
wait
echo "=== val eval — DONE at $(date) ==="
pgrep -lf "expt run" 2>&1 | head
