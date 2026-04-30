#!/bin/bash
# Run remaining val evaluations for benchmarks with codedistill results
set -x
cd "$(dirname "$0")/.."
export $(grep -v '^#' .env | xargs)

# ============================================================
# SPORTS: e2e codedistill (train from dataset, then eval)
# ============================================================
cd benchmarks/bbh/sports_understanding
echo "[$(date)] sports e2e codedistill train..."
uv run python -u -m secretagent.cli.learn e2e-codedistill \
  --interface are_sports_in_sentence_consistent \
  --dataset-file data/train.json \
  --learned-dir learned \
  --model claude-opus-4-6 \
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
# PENGUINS: codedistill val (use low wrong-rate interfaces)
# table_operation: 100% wrong=0%, choose_response: 98% wrong=0%
# ============================================================
cd benchmarks/bbh/penguins_in_a_table
echo "[$(date)] penguins codedistill val..."
uv run python -m secretagent.cli.expt run \
  --interface ptools.answer_penguin_question \
  evaluate.expt_name=workflow_codedistill \
  learn.train_dir=learned \
  ptools.table_operation.method=learned_code \
  ptools.table_operation.learner=codedistill \
  ptools.table_operation.backoff=True \
  ptools.choose_response.method=learned_code \
  ptools.choose_response.learner=codedistill \
  ptools.choose_response.backoff=True \
  ptools.answer_penguin_question.method=direct \
  ptools.answer_penguin_question.fn=ptools.penguins_workflow \
  dataset.split=valid

cd ../../..

# ============================================================
# GEOMETRIC: codedistill val (use low wrong-rate interfaces)
# decompose_path: 100% wrong=0%, extract_path_and_options: 100% wrong=0%
# describe_command: 96% wrong=0.78%, select_option: 99% wrong=1.33%
# ============================================================
cd benchmarks/bbh/geometric_shapes
echo "[$(date)] geometric codedistill val..."
uv run python -m secretagent.cli.expt run \
  --interface ptools.identify_shape \
  evaluate.expt_name=workflow_codedistill \
  learn.train_dir=learned \
  ptools.decompose_path.method=learned_code \
  ptools.decompose_path.learner=codedistill \
  ptools.decompose_path.backoff=True \
  ptools.extract_path_and_options.method=learned_code \
  ptools.extract_path_and_options.learner=codedistill \
  ptools.extract_path_and_options.backoff=True \
  ptools.describe_command.method=learned_code \
  ptools.describe_command.learner=codedistill \
  ptools.describe_command.backoff=True \
  ptools.select_option.method=learned_code \
  ptools.select_option.learner=codedistill \
  ptools.select_option.backoff=True \
  ptools.identify_shape.method=direct \
  ptools.identify_shape.fn=ptools.geometric_shapes_workflow \
  dataset.split=valid

cd ../../..

# ============================================================
# SUMMARY
# ============================================================
echo ""
echo "=== ALL EVALS DONE at $(date) ==="

python3 -c "
import json, pathlib

def show(title, results_dir, name_filter=None, min_rows=10):
    print(f'\n{title}')
    print('-'*70)
    for d in sorted(pathlib.Path(results_dir).glob('*')):
        jl = d / 'results.jsonl'
        if not jl.exists(): continue
        with open(jl) as f:
            rows = [json.loads(l) for l in f]
        if len(rows) < min_rows: continue
        parts = d.name.split('.', 2)
        name = parts[2] if len(parts) >= 3 else d.name
        if name_filter and not any(n in name for n in name_filter): continue
        correct = sum(1 for r in rows if r.get('correct'))
        cost = sum(r.get('cost',0) for r in rows)
        print(f'  {name:<45s} {correct:3d}/{len(rows):3d} = {correct/len(rows):4.0%}  \${cost:.4f}')

show('SPORTS', 'benchmarks/bbh/sports_understanding/results',
     ['workflow', 'codedistill', 'e2e', 'structured', 'unstructured', 'learning'])
show('PENGUINS', 'benchmarks/bbh/penguins_in_a_table/results',
     ['workflow', 'codedistill'])
show('GEOMETRIC', 'benchmarks/bbh/geometric_shapes/results',
     ['workflow', 'codedistill'])
show('CALENDAR', 'benchmarks/natural_plan/results',
     ['cal_'])
show('MUSR', 'benchmarks/musr/results',
     ['murder_workflow', 'murder_codedistill'])
"
