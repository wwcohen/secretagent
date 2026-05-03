#!/bin/bash
# Run all codedistill experiments across benchmarks
# Usage: nohup bash run_all_codedistill.sh > codedistill_all.log 2>&1 &

set -e
cd "$(dirname "$0")/.."
export $(grep -v '^#' .env | xargs)

MODEL=claude-opus-4-6
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT_DIR/benchmarks/codedistill_logs"
mkdir -p "$LOG_DIR"

echo "=== Starting all codedistill experiments at $(date) ==="

# ── Natplan: meeting (plan_visit_order) ──
echo "[$(date)] natplan meeting: recording..."
cd benchmarks/natural_plan
# Recording already exists, skip if present
if [ ! -d recordings/20260410.011553.meet_workflow ]; then
  uv run python expt.py run --config-file conf/meeting.yaml \
    evaluate.expt_name=meet_workflow \
    ptools.meeting_planning.method=direct \
    ptools.meeting_planning.fn=ptools_meeting.meeting_workflow \
    dataset.partition=train dataset.n=50 \
    evaluate.record_details=true evaluate.result_dir=recordings
fi
echo "[$(date)] natplan meeting: codedistill plan_visit_order..."
uv run -m secretagent.cli.learn codedistill \
  --interface plan_visit_order --learned-dir learned --model $MODEL \
  recordings/20260410.011553.meet_workflow 2>&1 | tee "$LOG_DIR/meet_plan_visit_order.log" | tail -10
echo "[$(date)] natplan meeting: codedistill build_meeting_plan..."
uv run -m secretagent.cli.learn codedistill \
  --interface build_meeting_plan --learned-dir learned --model $MODEL \
  recordings/20260410.011553.meet_workflow 2>&1 | tee "$LOG_DIR/meet_build_meeting_plan.log" | tail -10

# ── Natplan: trip (find_valid_route) ──
echo "[$(date)] natplan trip: codedistill find_valid_route..."
uv run -m secretagent.cli.learn codedistill \
  --interface find_valid_route --learned-dir learned --model $MODEL \
  recordings/20260410.012552.trip_workflow 2>&1 | tee "$LOG_DIR/trip_find_valid_route.log" | tail -10
echo "[$(date)] natplan trip: codedistill build_trip_plan..."
uv run -m secretagent.cli.learn codedistill \
  --interface build_trip_plan --learned-dir learned --model $MODEL \
  recordings/20260410.012552.trip_workflow 2>&1 | tee "$LOG_DIR/trip_build_trip_plan.log" | tail -10
cd ../..

# ── Musr: murder (other interfaces) ──
echo "[$(date)] musr murder: codedistill deduce_murderer..."
cd benchmarks/musr
uv run -m secretagent.cli.learn codedistill \
  --interface deduce_murderer --learned-dir learned --model $MODEL \
  recordings/* 2>&1 | tee "$LOG_DIR/musr_deduce_murderer.log" | tail -10
cd ../..

# ── Rulearena: nba and tax ──
echo "[$(date)] rulearena: recording nba..."
cd benchmarks/rulearena
uv run expt.py run evaluate.expt_name=structured_baseline_nba dataset.domain=nba \
  ptools.compute_rulearena_answer.method=direct \
  ptools.compute_rulearena_answer.fn=ptools.l1_extract_workflow \
  dataset.split=train evaluate.record_details=true evaluate.result_dir=recordings 2>&1 | tail -5
echo "[$(date)] rulearena: recording tax..."
uv run expt.py run evaluate.expt_name=structured_baseline_tax dataset.domain=tax \
  ptools.compute_rulearena_answer.method=direct \
  ptools.compute_rulearena_answer.fn=ptools.l1_extract_workflow \
  dataset.split=train evaluate.record_details=true evaluate.result_dir=recordings 2>&1 | tail -5
# Find interface names from recordings
echo "[$(date)] rulearena nba: checking interface names..."
python3 -c "
import json, glob
for jl in sorted(glob.glob('recordings/*/results.jsonl')):
    with open(jl) as f:
        rec = json.loads(f.readline())
    funcs = set(s['func'] for s in rec.get('rollout', []))
    print(f'{jl}: {funcs}')
"
cd ../..

# ── Penguins ──
echo "[$(date)] penguins: recording workflow..."
cd benchmarks/bbh/penguins_in_a_table
uv run python -m secretagent.cli.expt run --interface ptools.answer_penguin_question \
  evaluate.expt_name=workflow \
  ptools.answer_penguin_question.method=direct \
  ptools.answer_penguin_question.fn=ptools.penguins_workflow \
  dataset.split=train evaluate.record_details=true evaluate.result_dir=recordings 2>&1 | tail -5
echo "[$(date)] penguins: checking interface names..."
python3 -c "
import json, glob
for jl in sorted(glob.glob('recordings/*/results.jsonl')):
    with open(jl) as f:
        rec = json.loads(f.readline())
    funcs = set(s['func'] for s in rec.get('rollout', []))
    print(f'{jl}: {funcs}')
"
# Codedistill table_operation
for iface in $(python3 -c "
import json, glob
funcs = set()
for jl in glob.glob('recordings/*/results.jsonl'):
    with open(jl) as f:
        for line in f:
            rec = json.loads(line)
            for s in rec.get('rollout', []):
                funcs.add(s['func'])
for f in sorted(funcs):
    print(f)
"); do
  echo "[$(date)] penguins: codedistill $iface..."
  uv run -m secretagent.cli.learn codedistill \
    --interface "$iface" --learned-dir learned --model $MODEL \
    recordings/* 2>&1 | tee "$LOG_DIR/penguins_${iface}.log" | tail -10
done
cd ../../..

# ── Geometric shapes ──
echo "[$(date)] geometric: recording workflow..."
cd benchmarks/bbh/geometric_shapes
uv run python -m secretagent.cli.expt run --interface ptools.identify_shape \
  evaluate.expt_name=workflow \
  ptools.identify_shape.method=direct \
  ptools.identify_shape.fn=ptools.geometric_shapes_workflow \
  dataset.split=train evaluate.record_details=true evaluate.result_dir=recordings 2>&1 | tail -5
echo "[$(date)] geometric: checking interface names..."
python3 -c "
import json, glob
for jl in sorted(glob.glob('recordings/*/results.jsonl')):
    with open(jl) as f:
        rec = json.loads(f.readline())
    funcs = set(s['func'] for s in rec.get('rollout', []))
    print(f'{jl}: {funcs}')
"
for iface in $(python3 -c "
import json, glob
funcs = set()
for jl in glob.glob('recordings/*/results.jsonl'):
    with open(jl) as f:
        for line in f:
            rec = json.loads(line)
            for s in rec.get('rollout', []):
                funcs.add(s['func'])
for f in sorted(funcs):
    print(f)
"); do
  echo "[$(date)] geometric: codedistill $iface..."
  uv run -m secretagent.cli.learn codedistill \
    --interface "$iface" --learned-dir learned --model $MODEL \
    recordings/* 2>&1 | tee "$LOG_DIR/geometric_${iface}.log" | tail -10
done
cd ../../..

echo "=== All codedistill experiments done at $(date) ==="
echo "Check logs in $LOG_DIR/"
