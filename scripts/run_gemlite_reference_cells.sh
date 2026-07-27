#!/usr/bin/env bash
# Gemini flash-lite reference cells matched to the AFlow rebuttal runs.
#
# Sports: valid n=50 (seed-137 subset, = AFlow validation set) + test n=100.
# FinQA:  valid n=50 (head-50, = AFlow validation set)        + test n=300.
# Methods: engineered workflow, react, structured (simulate), unstructured.
#
# Usage: bash scripts/run_gemlite_reference_cells.sh [sports|finqa|all] [smoke]
#        smoke => n=2 everywhere, expt names get _smoke suffix.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODEL="llm.model=gemini/gemini-2.5-flash-lite"
TARGET="${1:-all}"
SMOKE="${2:-}"
SUF=""
if [ "$SMOKE" = "smoke" ]; then SUF="_smoke"; fi

n() { # n <requested> -> 2 in smoke mode
  if [ "$SMOKE" = "smoke" ]; then echo 2; else echo "$1"; fi
}

run_sports() {
  cd "$ROOT/benchmarks/bbh/sports_understanding" || exit 1
  local BASE="uv run python -m secretagent.cli.expt run --interface ptools.are_sports_in_sentence_consistent"
  local IFACE="ptools.are_sports_in_sentence_consistent"
  for split_n in "valid $(n 50)" "test $(n 100)"; do
    set -- $split_n; local SPLIT=$1 N=$2
    local DS="dataset.split=$SPLIT dataset.n=$N"
    $BASE $MODEL $DS $IFACE.method=direct $IFACE.fn=ptools.sports_understanding_workflow \
      evaluate.expt_name=gemlite_workflow_${SPLIT}${N}${SUF}
    $BASE $MODEL $DS $IFACE.method=simulate_pydantic \
      "$IFACE.tools=[ptools.analyze_sentence,ptools.sport_for,ptools.consistent_sports]" \
      evaluate.expt_name=gemlite_react_${SPLIT}${N}${SUF}
    $BASE $MODEL $DS $IFACE.method=simulate \
      evaluate.expt_name=gemlite_structured_${SPLIT}${N}${SUF}
    $BASE $MODEL $DS $IFACE.method=direct $IFACE.fn=ptools.zeroshot_unstructured_workflow \
      evaluate.expt_name=gemlite_unstructured_${SPLIT}${N}${SUF}
  done
}

run_finqa() {
  cd "$ROOT/benchmarks/finqa" || exit 1
  for split_n in "valid $(n 50)" "test $(n 300)"; do
    set -- $split_n; local SPLIT=$1 N=$2
    local DS="dataset.split=$SPLIT dataset.n=$N"
    for conf in workflow react; do
      uv run python expt.py run --config-file conf/$conf.yaml $MODEL $DS \
        evaluate.expt_name=gemlite_${conf}_${SPLIT}${N}${SUF}
    done
    # zeroshot via CLI overrides on the base conf (paper's EXPERIMENT_CMDS form);
    # conf/zeroshot_prompt.yaml is stale: it lacks the zeroshot_answer_finqa binding.
    uv run python expt.py run --config-file conf/conf.yaml $MODEL $DS \
      ptools.answer_finqa.method=direct ptools.answer_finqa.fn=ptools.unstructured_baseline_workflow \
      evaluate.expt_name=gemlite_zeroshot_${SPLIT}${N}${SUF}
    # structured baseline = plain simulate on the top-level interface (base conf)
    uv run python expt.py run --config-file conf/conf.yaml $MODEL $DS \
      evaluate.expt_name=gemlite_structured_${SPLIT}${N}${SUF}
  done
}

case "$TARGET" in
  sports) run_sports ;;
  finqa)  run_finqa ;;
  all)    run_sports; run_finqa ;;
  *) echo "unknown target: $TARGET"; exit 1 ;;
esac
