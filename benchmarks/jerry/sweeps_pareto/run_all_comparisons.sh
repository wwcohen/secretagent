#!/bin/bash
# Run all codedistill comparison experiments across benchmarks.
# Two modes: per-ptool codedistill vs e2e codedistill vs baseline.
# Usage: nohup bash run_all_comparisons.sh > comparisons.log 2>&1 &

set -x
cd "$(dirname "$0")/.."
export $(grep -v '^#' .env | xargs)

MODEL=claude-opus-4-6
E2E_OPTS="--model $MODEL --n-candidates 1 --max-rounds 3"

echo "=== Starting all comparisons at $(date) ==="

# ============================================================
# NATPLAN: E2E codedistill for all 3 tasks
# ============================================================
cd benchmarks/natural_plan

# Calendar e2e already done (90% train). Run val with sandbox.
echo "[$(date)] cal e2e val..."
uv run python expt.py run --config-file conf/calendar.yaml \
  evaluate.expt_name=cal_e2e_codedistill \
  learn.train_dir=learned \
  ptools.calendar_scheduling.method=learned_code \
  ptools.calendar_scheduling.learner=e2e_codedistill \
  ptools.calendar_scheduling.backoff=False \
  dataset.partition=valid dataset.n=50

# Meeting e2e - already done (56% train). Run val with sandbox.
echo "[$(date)] meet e2e val..."
uv run python expt.py run --config-file conf/meeting.yaml \
  evaluate.expt_name=meet_e2e_codedistill \
  learn.train_dir=learned \
  ptools.meeting_planning.method=learned_code \
  ptools.meeting_planning.learner=e2e_codedistill \
  ptools.meeting_planning.backoff=False \
  dataset.partition=valid dataset.n=50

# Trip e2e - need to rerun with fixed sandbox
echo "[$(date)] trip e2e codedistill..."
uv run python -u -m secretagent.cli.learn e2e-codedistill \
  --interface trip_planning \
  --dataset-file data/trip_train.json \
  --output-field golden_plan \
  --learned-dir learned $E2E_OPTS
echo "[$(date)] trip e2e val..."
uv run python expt.py run --config-file conf/trip.yaml \
  evaluate.expt_name=trip_e2e_codedistill \
  learn.train_dir=learned \
  ptools.trip_planning.method=learned_code \
  ptools.trip_planning.learner=e2e_codedistill \
  ptools.trip_planning.backoff=False \
  dataset.partition=valid dataset.n=50

# Baselines on val (if not already run)
echo "[$(date)] cal baseline val..."
uv run python expt.py run --config-file conf/calendar.yaml \
  evaluate.expt_name=cal_workflow \
  ptools.calendar_scheduling.method=direct \
  ptools.calendar_scheduling.fn=ptools_calendar.calendar_workflow \
  dataset.partition=valid dataset.n=50
echo "[$(date)] meet baseline val..."
uv run python expt.py run --config-file conf/meeting.yaml \
  evaluate.expt_name=meet_workflow \
  ptools.meeting_planning.method=direct \
  ptools.meeting_planning.fn=ptools_meeting.meeting_workflow \
  dataset.partition=valid dataset.n=50
echo "[$(date)] trip baseline val..."
uv run python expt.py run --config-file conf/trip.yaml \
  evaluate.expt_name=trip_workflow \
  ptools.trip_planning.method=direct \
  ptools.trip_planning.fn=ptools_trip.trip_workflow \
  dataset.partition=valid dataset.n=50

cd ../..

# ============================================================
# SPORTS: E2E codedistill
# ============================================================
cd benchmarks/bbh/sports_understanding

echo "[$(date)] sports e2e codedistill..."
uv run python -u -m secretagent.cli.learn e2e-codedistill \
  --interface are_sports_in_sentence_consistent \
  --dataset-file data/train.json \
  --learned-dir learned $E2E_OPTS
echo "[$(date)] sports e2e val..."
uv run python -m secretagent.cli.expt run \
  --interface ptools.are_sports_in_sentence_consistent \
  evaluate.expt_name=e2e_codedistill \
  learn.train_dir=learned \
  ptools.are_sports_in_sentence_consistent.method=learned_code \
  ptools.are_sports_in_sentence_consistent.learner=e2e_codedistill \
  ptools.are_sports_in_sentence_consistent.backoff=False \
  dataset.split=valid

cd ../../..

# ============================================================
# MUSR: per-ptool codedistill val (extract_index already 100%)
# ============================================================
cd benchmarks/musr

echo "[$(date)] musr codedistill val..."
uv run python expt.py run --config-file conf/murder.yaml \
  evaluate.expt_name=murder_codedistill \
  learn.train_dir=learned \
  ptools.extract_index.method=learned_code \
  ptools.extract_index.learner=codedistill \
  ptools.extract_index.backoff=True \
  evaluate.entry_point=answer_question_workflow dataset.n=50

cd ../..

# ============================================================
# SUMMARY
# ============================================================
echo ""
echo "=== ALL COMPARISONS DONE at $(date) ==="
echo ""
echo "=== NATPLAN RESULTS ==="
cd benchmarks/natural_plan
python3 -c "
import json, pathlib
for d in sorted(pathlib.Path('results').glob('*')):
    jl = d / 'results.jsonl'
    if not jl.exists(): continue
    with open(jl) as f:
        rows = [json.loads(l) for l in f]
    if len(rows) < 10: continue
    correct = sum(1 for r in rows if r.get('correct'))
    total_cost = sum(r.get('cost',0) for r in rows)
    print(f'  {d.name:50s} {correct}/{len(rows):3d} = {correct/len(rows):5.0%}  cost=\${total_cost:.4f}')
"
cd ../..

echo ""
echo "=== SPORTS RESULTS ==="
cd benchmarks/bbh/sports_understanding
python3 -c "
import json, pathlib
for d in sorted(pathlib.Path('results').glob('*')):
    jl = d / 'results.jsonl'
    if not jl.exists(): continue
    with open(jl) as f:
        rows = [json.loads(l) for l in f]
    if len(rows) < 10: continue
    correct = sum(1 for r in rows if r.get('correct'))
    total_cost = sum(r.get('cost',0) for r in rows)
    print(f'  {d.name:50s} {correct}/{len(rows):3d} = {correct/len(rows):5.0%}  cost=\${total_cost:.4f}')
"
cd ../../..

echo ""
echo "=== MUSR RESULTS ==="
cd benchmarks/musr
python3 -c "
import json, pathlib
for d in sorted(pathlib.Path('results').glob('*murder*')):
    jl = d / 'results.jsonl'
    if not jl.exists(): continue
    with open(jl) as f:
        rows = [json.loads(l) for l in f]
    if len(rows) < 10: continue
    correct = sum(1 for r in rows if r.get('correct'))
    total_cost = sum(r.get('cost',0) for r in rows)
    print(f'  {d.name:50s} {correct}/{len(rows):3d} = {correct/len(rows):5.0%}  cost=\${total_cost:.4f}')
"
cd ../..
