#!/bin/bash
# Re-run BBH val evals using dotlist (cli.expt has no --config-file)
set +e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/benchmarks/val_eval_logs"
set -a; source "$ROOT/.env"; set +a
N=30

run_b() {
  local sub="$1"; local iface="$2"; local wf="$3"
  cd "$ROOT/benchmarks/bbh/$sub"
  EXTRA=""
  [ "$sub" = "date_understanding" ] && EXTRA="ptools.answer_date_question_orchestrated.method=direct ptools.answer_date_question_orchestrated.fn=ptools.zeroshot_unstructured_workflow"

  # Read codedistill_config.yaml and turn ptool overrides into dotlist
  CFG="learned_v2/codedistill_config.yaml"
  if [ ! -f "$CFG" ]; then
    echo "[$sub] no class1v2 config — skipping"
    return
  fi
  PTOOL_DOTS=$(uv run python -c "
import yaml
cfg = yaml.safe_load(open('$CFG'))
for name, kvs in (cfg.get('ptools', {}) or {}).items():
    for k, v in (kvs or {}).items():
        v = repr(v) if isinstance(v, bool) else v
        print(f'ptools.{name}.{k}={v}')
" 2>/dev/null)
  echo "[$sub] class1 dotlist:"; echo "$PTOOL_DOTS" | sed 's/^/    /'

  uv run python -m secretagent.cli.expt run --interface "ptools.${iface}" \
    "ptools.${iface}.method=direct" "ptools.${iface}.fn=ptools.${wf}" \
    $PTOOL_DOTS $EXTRA \
    "llm.model=together_ai/deepseek-ai/DeepSeek-V3.1" \
    learn.train_dir=learned_v2 dataset.split=valid "dataset.n=$N" \
    "evaluate.expt_name=${sub}_val_class1v2" evaluate.result_dir=val_results 2>&1 | tail -10
}

echo "=== BBH Class 1 v2 val evals ==="
for triple in "sports_understanding:are_sports_in_sentence_consistent:sports_understanding_workflow" \
              "penguins_in_a_table:answer_penguin_question:penguins_workflow" \
              "geometric_shapes:identify_shape:geometric_shapes_workflow" \
              "date_understanding:answer_date_question:zeroshot_unstructured_workflow"; do
  IFS=":" read sub iface wf <<< "$triple"
  echo "--- $sub ---"
  run_b "$sub" "$iface" "$wf" > "$LOG_DIR/val_${sub}_class1v2.log" 2>&1
done
echo "=== done at $(date) ==="
