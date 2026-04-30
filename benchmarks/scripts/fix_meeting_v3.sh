#!/bin/bash
# Re-distill meeting class 2 with golden_plan list → str conversion
set +e
ROOT="/Users/yanjiarui/Desktop/Will_research/secretagent"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
set -a; source "$ROOT/.env"; set +a
CD_MODEL="${CD_MODEL:-claude-opus-4-6}"
DS_V31="together_ai/deepseek-ai/DeepSeek-V3.1"

cd "$ROOT/benchmarks/natural_plan"

# Step 1: Convert meeting_train.json — golden_plan list → str
echo "[$(date)] === Step 1: convert meeting_train golden_plan list → str ==="
uv run python -c "
import json
src = json.load(open('data/meeting_train.json'))
cases = src['cases'] if 'cases' in src else src
for c in cases:
    eo = c.get('expected_output')
    if isinstance(eo, dict) and isinstance(eo.get('golden_plan'), list):
        eo['golden_plan'] = 'SOLUTION:\n' + '\n'.join(eo['golden_plan'])
print(f'converted {len(cases)} cases')
out = src if 'cases' in src else cases
with open('/tmp/meeting_train_v3.json', 'w') as f:
    json.dump(out, f, indent=2)
print('wrote /tmp/meeting_train_v3.json')
" 2>&1 | grep -v warning

# Step 2: Re-distill with the fixed data file
echo "[$(date)] === Step 2: meeting class 2 re-distill (golden_plan as str) ==="
CAL_TRACE=$(ls -d recordings_full/*natplan_calendar_train_full 2>/dev/null | tail -1)
MEET_TRACE=$(ls -d recordings_full/*natplan_meeting_train_full 2>/dev/null | tail -1)
TRIP_TRACE=$(ls -d recordings_full/*natplan_trip_train_full 2>/dev/null | tail -1)

uv run -m secretagent.cli.learn workflow-codedistill \
  --interface meeting_planning --dataset-file /tmp/meeting_train_v3.json --output-field golden_plan \
  --tool-module ptools_meeting --conf-file conf/meeting.yaml \
  --reference-file ptools_calendar.py --reference-file ptools_trip.py \
  ${MEET_TRACE:+--trace-dir "$MEET_TRACE"} \
  ${CAL_TRACE:+--cross-trace-dir "$CAL_TRACE"} \
  ${TRIP_TRACE:+--cross-trace-dir "$TRIP_TRACE"} \
  --learned-dir learned_class2_v4 --model "$CD_MODEL" \
  --backoff true --backoff-method simulate \
  > "$LOG_DIR/class2v4_natplan_meeting_v3.log" 2>&1
echo "[$(date)] meeting class 2 distill v3 rc=$?"

# Step 3: val
echo "[$(date)] === Step 3: meeting class 2 val (post-distill v3) ==="
uv run python expt.py run --config-file conf/meeting.yaml \
  "dataset.partition=valid" "dataset.n=100" \
  "evaluate.expt_name=meeting_val_full_class2v4_v3" \
  evaluate.record_details=true evaluate.result_dir=val_results_full \
  "llm.model=$DS_V31" \
  "ptools.meeting_planning.method=learned_code" \
  "ptools.meeting_planning.learner=workflow_distill" \
  "ptools.meeting_planning.backoff=true" \
  "learn.train_dir=$ROOT/benchmarks/natural_plan/learned_class2_v4" \
  > "$LOG_DIR/meeting_class2_val_v3.log" 2>&1
echo "[$(date)] meeting class 2 val v3 rc=$?"

uv run python -c "
import pandas as pd, glob
files = sorted(glob.glob('val_results_full/*meeting_val_full_class2v4_v3*/results.csv'))
if files:
    df = pd.read_csv(files[-1])
    print(f'meeting class2 v3 val: rows={len(df)} acc={df.correct.mean():.3f}')
" 2>&1 | grep -v warning

echo "[$(date)] === DONE ==="
