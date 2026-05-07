#!/bin/bash
# Fix class1 opus val for BBH benchmarks — pass dotlist as array, not single string.
set +e
ROOT="/Users/anon/Desktop/anon_research/secretagent"
set -a; source "$ROOT/.env"; set +a

run_bbh_class1_opus_val() {
  local sub="$1"; local iface="$2"; local wf="$3"; local n="$4"
  cd "$ROOT/benchmarks/bbh/$sub"
  if [ ! -f learned_opus/codedistill_config.yaml ]; then
    echo "[$sub] no learned_opus config — skip"
    return
  fi
  # Read each ENABLED ptool's overrides as separate args
  declare -a PTOOL_ARGS=()
  while IFS= read -r line; do
    PTOOL_ARGS+=("$line")
  done < <(uv run python -c "
import yaml
cfg = yaml.safe_load(open('learned_opus/codedistill_config.yaml'))
for n, kvs in (cfg.get('ptools', {}) or {}).items():
    for k, v in (kvs or {}).items():
        v = repr(v) if isinstance(v, bool) else v
        print(f'ptools.{n}.{k}={v}')
" 2>/dev/null)
  EXTRA=()
  [ "$sub" = "date_understanding" ] && EXTRA+=("ptools.answer_date_question_orchestrated.method=direct" "ptools.answer_date_question_orchestrated.fn=ptools.zeroshot_unstructured_workflow")
  echo "[$sub] launching with dotlist args: ${PTOOL_ARGS[@]}"
  nohup uv run python -m secretagent.cli.expt run \
    --interface "ptools.${iface}" \
    "ptools.${iface}.method=direct" \
    "ptools.${iface}.fn=ptools.${wf}" \
    "${PTOOL_ARGS[@]}" \
    "${EXTRA[@]}" \
    "llm.model=together_ai/deepseek-ai/DeepSeek-V3.1" \
    learn.train_dir=learned_opus \
    dataset.split=valid "dataset.n=$n" \
    "evaluate.expt_name=${sub}_val_full_class1_opus_fixed" \
    evaluate.result_dir=val_results_full > /tmp/${sub}_c1v4_fix.log 2>&1 &
  echo "  PID: $!"
}

run_bbh_class1_opus_val sports_understanding are_sports_in_sentence_consistent sports_understanding_workflow 75
run_bbh_class1_opus_val penguins_in_a_table answer_penguin_question penguins_workflow 43

echo
echo "=== launched. check status ==="
pgrep -lf "expt run" 2>&1 | head
