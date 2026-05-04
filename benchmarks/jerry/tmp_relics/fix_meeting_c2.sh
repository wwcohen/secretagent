#!/bin/bash
# Re-distill meeting class 2 with the patched prompt (emphasizes return type).
set +e
ROOT="/Users/yanjiarui/Desktop/Will_research/secretagent"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
set -a; source "$ROOT/.env"; set +a
CD_MODEL="${CD_MODEL:-claude-opus-4-6}"
DS_V31="together_ai/deepseek-ai/DeepSeek-V3.1"

cd "$ROOT/benchmarks/natural_plan"

CAL_TRACE=$(ls -d recordings_full/*natplan_calendar_train_full 2>/dev/null | tail -1)
MEET_TRACE=$(ls -d recordings_full/*natplan_meeting_train_full 2>/dev/null | tail -1)
TRIP_TRACE=$(ls -d recordings_full/*natplan_trip_train_full 2>/dev/null | tail -1)

echo "[$(date)] === meeting class 2 re-distill (patched prompt) ==="
uv run -m secretagent.cli.learn workflow-codedistill \
  --interface meeting_planning --dataset-file data/meeting_train.json --output-field golden_plan \
  --tool-module ptools_meeting --conf-file conf/meeting.yaml \
  --reference-file ptools_calendar.py --reference-file ptools_trip.py \
  ${MEET_TRACE:+--trace-dir "$MEET_TRACE"} \
  ${CAL_TRACE:+--cross-trace-dir "$CAL_TRACE"} \
  ${TRIP_TRACE:+--cross-trace-dir "$TRIP_TRACE"} \
  --learned-dir learned_class2_opus --model "$CD_MODEL" \
  --backoff true --backoff-method simulate \
  > "$LOG_DIR/class2_opus_natplan_meeting_v2.log" 2>&1
echo "[$(date)] meeting class 2 distill rc=$?"

# Now val (uses LATEST learned_class2_opus dir for meeting_planning)
echo "[$(date)] === meeting class 2 val (post-redistill) ==="
uv run python expt.py run --config-file conf/meeting.yaml \
  "dataset.partition=valid" "dataset.n=100" \
  "evaluate.expt_name=meeting_val_full_class2_opus_v2" \
  evaluate.record_details=true evaluate.result_dir=val_results_full \
  "llm.model=$DS_V31" \
  "ptools.meeting_planning.method=learned_code" \
  "ptools.meeting_planning.learner=workflow_distill" \
  "ptools.meeting_planning.backoff=true" \
  "learn.train_dir=$ROOT/benchmarks/natural_plan/learned_class2_opus" \
  > "$LOG_DIR/meeting_class2_val_v2.log" 2>&1
echo "[$(date)] meeting class 2 val rc=$?"

# Show acc
uv run python -c "
import pandas as pd, glob
files = sorted(glob.glob('val_results_full/*meeting_val_full_class2_opus_v2*/results.csv'))
if files:
    df = pd.read_csv(files[-1])
    print(f'meeting class2 v4_v2 val: rows={len(df)} acc={df.correct.mean():.3f}')
else:
    print('no meeting_class2_opus_v2 val results')
" 2>&1 | grep -v warning

echo "[$(date)] === DONE ==="
