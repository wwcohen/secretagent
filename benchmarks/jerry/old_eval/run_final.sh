#!/bin/bash
# Final comparison: baseline vs fewshot baseline vs ptool codedistill vs e2e codedistill
set -x
cd "$(dirname "$0")/.."
export $(grep -v '^#' .env | xargs)

MODEL=claude-opus-4-6

# ============================================================
# MEETING
# ============================================================
cd benchmarks/natural_plan

# Meeting baseline with fewshot examples
echo "[$(date)] meet workflow fewshot val..."
uv run python expt.py run --config-file conf/meeting.yaml \
  evaluate.expt_name=meet_workflow_fewshot \
  ptools.meeting_planning.method=direct \
  ptools.meeting_planning.fn=ptools_meeting.meeting_workflow \
  ptools.parse_meeting_info.example_file=examples_meet.json \
  ptools.plan_visit_order.example_file=examples_meet.json \
  ptools.build_meeting_plan.example_file=examples_meet.json \
  dataset.partition=valid dataset.n=50

# Meeting e2e codedistill (already trained, eval with sandbox)
echo "[$(date)] meet e2e val (sandbox)..."
uv run python expt.py run --config-file conf/meeting.yaml \
  evaluate.expt_name=meet_e2e_codedistill \
  learn.train_dir=learned \
  ptools.meeting_planning.method=learned_code \
  ptools.meeting_planning.learner=e2e_codedistill \
  ptools.meeting_planning.backoff=False \
  dataset.partition=valid dataset.n=50

cd ../..

# ============================================================
# SPORTS
# ============================================================
cd benchmarks/bbh/sports_understanding

# Sports workflow with fewshot examples
echo "[$(date)] sports workflow fewshot val..."
uv run python -m secretagent.cli.expt run \
  --interface ptools.are_sports_in_sentence_consistent \
  evaluate.expt_name=workflow_fewshot \
  ptools.are_sports_in_sentence_consistent.method=direct \
  ptools.are_sports_in_sentence_consistent.fn=ptools.sports_understanding_workflow \
  ptools.analyze_sentence.example_file=examples.json \
  ptools.sport_for.example_file=examples.json \
  ptools.consistent_sports.example_file=examples.json \
  dataset.split=valid

# Sports e2e codedistill (train + eval)
echo "[$(date)] sports e2e codedistill train..."
uv run python -u -m secretagent.cli.learn e2e-codedistill \
  --interface are_sports_in_sentence_consistent \
  --dataset-file data/train.json \
  --learned-dir learned \
  --model $MODEL \
  --n-candidates 1 --max-rounds 3

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
# CALENDAR with fewshot baseline
# ============================================================
cd benchmarks/natural_plan

echo "[$(date)] cal workflow fewshot val..."
uv run python expt.py run --config-file conf/calendar.yaml \
  evaluate.expt_name=cal_workflow_fewshot \
  ptools.calendar_scheduling.method=direct \
  ptools.calendar_scheduling.fn=ptools_calendar.calendar_workflow \
  ptools.parse_schedules.example_file=examples_cal.json \
  ptools.find_available_slots.example_file=examples_cal.json \
  ptools.select_and_format.example_file=examples_cal.json \
  dataset.partition=valid dataset.n=50

cd ../..

# ============================================================
# SUMMARY
# ============================================================
echo ""
echo "=== ALL DONE at $(date) ==="

python3 -c "
import json, pathlib

def show(title, rdir, keys, min_rows=10):
    print(f'\n{title}')
    print(f'  {\"Method\":<50s} {\"Acc\":>10s} {\"Cost\":>10s}')
    print(f'  {\"-\"*50} {\"-\"*10} {\"-\"*10}')
    for k in keys:
        best = None
        for d in sorted(pathlib.Path(rdir).glob('*')):
            jl = d / 'results.jsonl'
            if not jl.exists(): continue
            parts = d.name.split('.', 2)
            name = parts[2] if len(parts) >= 3 else d.name
            if k != name: continue
            with open(jl) as f:
                rows = [json.loads(l) for l in f]
            if len(rows) < min_rows: continue
            c = sum(1 for r in rows if r.get('correct'))
            cost = sum(r.get('cost',0) for r in rows)
            best = (c, len(rows), cost)
        if best:
            c, n, cost = best
            print(f'  {k:<50s} {c:3d}/{n:3d}={c/n:4.0%}  \${cost:.4f}')
        else:
            print(f'  {k:<50s} (no data)')

show('CALENDAR', 'benchmarks/natural_plan/results',
    ['cal_workflow', 'cal_workflow_fewshot', 'cal_codedistill_opus', 'cal_e2e_codedistill_sandbox'])
show('MEETING', 'benchmarks/natural_plan/results',
    ['meet_workflow', 'meet_workflow_fewshot', 'meet_e2e_codedistill'])
show('SPORTS', 'benchmarks/bbh/sports_understanding/results',
    ['workflow', 'workflow_fewshot', 'workflow_with_learning', 'workflow_codedistill', 'e2e_codedistill'])
"
