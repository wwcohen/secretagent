#!/bin/bash
# Class 3 gemini — workflow-codedistill on prof's induced ptools, using Gemini Pro as learner.
# Uses 6 induced ptool modules from src/secretagent/learn/inducer_results/ (seed=42).
# Each induced .py imports `from ptools.ptools_common import _REACT_STATE` (prof's repo
# convention); we patch the import to match this repo (`from ptools_common import` for
# musr; equivalent paths for natural_plan / rulearena).
set +e
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
PT_STAGE="/tmp/induced_ptools_gemini"
mkdir -p "$LOG_DIR" "$PT_STAGE"
set -a; source "$ROOT/.env"; set +a
CD_MODEL="${CD_MODEL:-gemini/gemini-3.1-pro-preview}"
DS_V3="together_ai/deepseek-ai/DeepSeek-V3"
DS_V31="together_ai/deepseek-ai/DeepSeek-V3.1"

INDUCED_ROOT="$ROOT/src/secretagent/learn/inducer_results"

# Step 1: stage patched induced ptool modules (rewrite the prof's import path)
patch_induced() {
  local src="$1"; local dst="$2"; local repo_import="$3"
  sed "s|from ptools\\.ptools_common|from $repo_import|g" "$src" > "$dst"
  echo "$dst"
}

# Step 2: prepare datasets (musr needs Dataset-format conversion; natplan_meeting needs list→str)
prep_musr_dataset() {
  local task=$1
  local split_train=object_placements_train
  [ "$task" = team ]   && split_train=team_allocation_train
  [ "$task" = murder ] && split_train=murder_mysteries_train
  local out="/tmp/musr_${task}_train_dataset.json"
  if [ ! -f "$out" ]; then
    uv run python -c "
import sys; sys.path.insert(0, '$ROOT/benchmarks/musr')
import expt
ds = expt.load_dataset('$split_train')
print(ds.model_dump_json(indent=2), file=open('$out', 'w'))
" 2>/dev/null
  fi
  echo "$out"
}
prep_meeting_dataset() {
  local out="/tmp/meeting_train_gemini_class3.json"
  if [ ! -f "$out" ]; then
    uv run python -c "
import json
src = json.load(open('$ROOT/benchmarks/natural_plan/data/meeting_train.json'))
cases = src['cases'] if 'cases' in src else src
for c in cases:
    eo = c.get('expected_output')
    if isinstance(eo, dict) and isinstance(eo.get('golden_plan'), list):
        eo['golden_plan'] = 'SOLUTION:\n' + '\n'.join(eo['golden_plan'])
out = src if 'cases' in src else cases
json.dump(out, open('$out', 'w'), indent=2)
"
  fi
  echo "$out"
}

# Common output dir helper (writes to COMMON/codedistill-workflow-results/<bench>/learned_class3_gemini/)
WF_COMMON="$ROOT/benchmarks/COMMON/codedistill-workflow-results"

# === musr 3 tasks ===
musr_one() {
  local task=$1   # murder|object|team
  local split=$2
  local conf=$3
  local label="musr_${task}"
  local log="$LOG_DIR/class3_gemini_${label}.log"
  echo "[$(date)] $label class3 gemini distill" | tee "$log"

  local induced_src="$INDUCED_ROOT/musr/induced_ptools_seed42_correct_${task}.py"
  if [ ! -f "$induced_src" ]; then echo "  no induced module — skip" | tee -a "$log"; return; fi
  local induced_patched="$PT_STAGE/musr_${task}_induced.py"
  patch_induced "$induced_src" "$induced_patched" "ptools_common"

  local ds=$(prep_musr_dataset "$task")
  local trace=$(ls -d "$ROOT/benchmarks/musr/recordings_full/"*"musr_${task}_react_train_full" 2>/dev/null | tail -1)
  [ -z "$trace" ] && trace=$(ls -d "$ROOT/benchmarks/musr/recordings_full/"*"musr_${task}_train"* 2>/dev/null | tail -1)

  cd "$ROOT/benchmarks/musr"
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface answer_question_workflow \
    --dataset-file "$ds" --output-field answer_index \
    --tool-module "$induced_patched" \
    --conf-file "$conf" \
    --max-rounds 2 --n-candidates 5 \
    ${trace:+--trace-dir "$trace"} \
    --learned-dir "$WF_COMMON/musr/learned_class3_gemini_${task}" \
    --model "$CD_MODEL" --backoff true --backoff-method simulate \
    >> "$log" 2>&1
  echo "[$(date)] $label class3 gemini distill rc=$?" | tee -a "$log"
}

# === natplan meeting + trip ===
natplan_one() {
  local sub=$1   # meeting|trip
  local iface=$2
  local conf=$3
  local label="natplan_${sub}"
  local log="$LOG_DIR/class3_gemini_${label}.log"
  echo "[$(date)] $label class3 gemini distill" | tee "$log"

  local induced_src="$INDUCED_ROOT/natural_plan/induced_ptools_seed42_correct_llm_${sub}.py"
  if [ ! -f "$induced_src" ]; then echo "  no induced module — skip" | tee -a "$log"; return; fi
  local induced_patched="$PT_STAGE/natplan_${sub}_induced.py"
  # natplan: the `_REACT_STATE` references — none of natplan ptools have it as a module-level dict.
  # Just copy as-is (no patch needed if module doesn't import _REACT_STATE) but fix import.
  patch_induced "$induced_src" "$induced_patched" "ptools_common"

  local ds
  if [ "$sub" = "meeting" ]; then
    ds=$(prep_meeting_dataset)
  else
    ds="$ROOT/benchmarks/natural_plan/data/${sub}_train.json"
  fi
  local trace=$(ls -d "$ROOT/benchmarks/natural_plan/recordings_full/"*"natplan_${sub}_train_full" 2>/dev/null | tail -1)

  cd "$ROOT/benchmarks/natural_plan"
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface "$iface" \
    --dataset-file "$ds" --output-field golden_plan \
    --tool-module "$induced_patched" \
    --conf-file "$conf" \
    --max-rounds 2 --n-candidates 5 \
    ${trace:+--trace-dir "$trace"} \
    --learned-dir "$WF_COMMON/natural_plan/learned_class3_gemini_${sub}" \
    --model "$CD_MODEL" --backoff true --backoff-method simulate \
    >> "$log" 2>&1
  echo "[$(date)] $label class3 gemini distill rc=$?" | tee -a "$log"
}

# === rulearena nba ===
rulearena_nba_one() {
  local label="rulearena_nba"
  local log="$LOG_DIR/class3_gemini_${label}.log"
  echo "[$(date)] $label class3 gemini distill" | tee "$log"

  local induced_src="$INDUCED_ROOT/rulearena/induced_ptools_seed42_correct_enh_nba.py"
  if [ ! -f "$induced_src" ]; then echo "  no induced module — skip" | tee -a "$log"; return; fi
  local induced_patched="$PT_STAGE/rulearena_nba_induced.py"
  patch_induced "$induced_src" "$induced_patched" "ptools_common"

  cd "$ROOT/benchmarks/rulearena/nba"
  uv run -m secretagent.cli.learn workflow-codedistill \
    --interface compute_nba_answer \
    --dataset-file data/train.json --output-field answer \
    --tool-module "$induced_patched" \
    --conf-file conf/conf.yaml \
    --max-rounds 2 --n-candidates 5 \
    --learned-dir "$WF_COMMON/rulearena/learned_class3_gemini_nba" \
    --model "$CD_MODEL" --backoff true --backoff-method simulate \
    >> "$log" 2>&1
  echo "[$(date)] $label class3 gemini distill rc=$?" | tee -a "$log"
}

echo "=== Class 3 gemini (Gemini Pro on prof's induced ptools) — start at $(date) ==="

# Run in 3 parallel families — different cwd, no collision
(
  musr_one murder murder_mysteries_train conf/murder_workflow.yaml
  musr_one object object_placements_train conf/object_workflow.yaml
  musr_one team   team_allocation_train   conf/team_workflow.yaml
) &
P1=$!

(
  natplan_one meeting meeting_planning conf/meeting.yaml
  natplan_one trip    trip_planning    conf/trip.yaml
) &
P2=$!

rulearena_nba_one &
P3=$!

wait $P1 $P2 $P3
echo "=== Class 3 gemini — DONE at $(date) ==="
