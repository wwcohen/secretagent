#!/bin/bash
# Master chain: runs the full pipeline at proper benchmark sizes.
# Steps:
#   X — wait for current bg tasks (class 3 v3 + B class1 v3 on n=50)
#   A — full-size baseline re-record (recordings_full/)
#   B' — re-distill C1 with max_wrong_rate=0.20 on full-size recordings
#   C' — re-distill C2 with backoff=True on full-size datasets
#   D' — re-distill C3 opus on full-size data (only musr/finqa/calendar)
#   E — full-size val eval for all classes
# Each phase output goes into a clearly named dir; logs in benchmarks/*_logs/.

set +e
ROOT="/Users/yanjiarui/Desktop/Will_research/secretagent"
LOG="$ROOT/benchmarks/master_chain.log"
exec >> "$LOG" 2>&1
echo "============================================================"
echo "[$(date)] master chain start"
echo "============================================================"

# ── Phase X: wait for current bg tasks ──
echo "[$(date)] X: waiting for class3 v3 + B (class1 v3) to finish"
for pidfile in /tmp/c3v3_finqa_pid.txt /tmp/c3v3_cal_pid.txt /tmp/class1_v3_pid.txt; do
  if [ -f "$pidfile" ]; then
    pid=$(cat "$pidfile")
    while kill -0 $pid 2>/dev/null; do sleep 60; done
    echo "[$(date)]  $(basename $pidfile) ended"
  fi
done

# ── Phase A: full-size baseline re-record ──
echo "[$(date)] A: full-size baseline re-record"
bash "$ROOT/benchmarks/run_full_size_baseline_record.sh"
echo "[$(date)] A done"

# ── Phase B': re-distill C1 on full-size recordings ──
echo "[$(date)] B': class1 opus codedistill-all on full-size recordings"
bash "$ROOT/benchmarks/run_class1_opus_full_codedistill.sh"
echo "[$(date)] B' done"

# ── Phase C': re-distill C2 on full-size data ──
echo "[$(date)] C': class2 opus workflow-codedistill on full-size datasets"
bash "$ROOT/benchmarks/run_class2_opus_full_workflow.sh"
echo "[$(date)] C' done"

# ── Phase D': re-distill C3 on full-size data ──
echo "[$(date)] D': class3 opus induced+workflow_distill on full-size"
bash "$ROOT/benchmarks/run_class3_opus_full.sh"
echo "[$(date)] D' done"

# ── Phase E: full-size val eval for all classes ──
echo "[$(date)] E: full-size val eval"
bash "$ROOT/benchmarks/run_full_size_val_eval.sh"
echo "[$(date)] E done"

echo "============================================================"
echo "[$(date)] master chain DONE"
echo "============================================================"
