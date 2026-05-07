#!/bin/bash
set +e
ROOT="/Users/anon/Desktop/anon_research/secretagent"
LOG_DIR="$ROOT/benchmarks/val_eval_logs"
set -a; source "$ROOT/.env"; set +a
N=30

run_c1v2() {
  local label="$1"; local cwd="$2"; shift 2
  local log="$LOG_DIR/val_${label}_class1v2.log"
  cd "$cwd"
  if [ ! -f learned_v2/codedistill_config.yaml ]; then
    echo "[$label] no learned_v2 config — skip" > "$log"
    return
  fi
  echo "[$(date)] $label class1v2 val starting" > "$log"
  uv run python expt.py run "$@" --config-file learned_v2/codedistill_config.yaml \
    learn.train_dir=learned_v2 "dataset.n=$N" \
    "evaluate.expt_name=${label}_val_class1v2" \
    evaluate.result_dir=val_results >> "$log" 2>&1
  echo "[$(date)] $label class1v2 val rc=$?" >> "$log"
}

# natplan trio (val partition)
run_c1v2 cal  "$ROOT/benchmarks/natural_plan" \
  --config-file conf/calendar.yaml dataset.partition=valid &
P1=$!
run_c1v2 meet "$ROOT/benchmarks/natural_plan" \
  --config-file conf/meeting.yaml dataset.partition=valid &
P2=$!
run_c1v2 trip "$ROOT/benchmarks/natural_plan" \
  --config-file conf/trip.yaml dataset.partition=valid &
P3=$!

# musr murder val
run_c1v2 murder "$ROOT/benchmarks/musr" \
  --config-file conf/murder_workflow.yaml dataset.split=murder_mysteries_val &
P4=$!

# finqa val with v2 config
run_c1v2 finqa "$ROOT/benchmarks/finqa" \
  --config-file conf/workflow.yaml dataset.split=valid &
P5=$!

wait $P1 $P2 $P3 $P4 $P5
echo "all class1v2 val done at $(date)"
