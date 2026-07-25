#!/bin/bash
# Rerun Table 1 core conditions (workflow / ReAct / zero-shot) on a non-DeepSeek
# model over a benchmark subset (MuSR x3, NaturalPlan meeting/trip, RuleArena
# airline/nba), matched to the paper cells: same splits, N, seeds, ptool bindings.
#
# Usage:
#   MODEL=gemini/gemini-3.1-flash-lite-preview SMOKE=1 bash scripts/run_table1_nondeepseek.sh  # 2-example smoke
#   MODEL=gemini/gemini-3.1-flash-lite-preview bash scripts/run_table1_nondeepseek.sh          # full test-split run
#
# Requires the matching provider API key in .env (e.g. GEMINI_API_KEY for gemini/ models).
# The model must be in litellm's price map, or llm_util's completion_cost call raises.
# Status: musr workflow+react cells validated end-to-end (claude-haiku-4-5, 2026-07-24);
# natplan/rulearena react cells launch from the archived result-dir config snapshots and
# have not been smoke-tested yet — run SMOKE=1 first.

set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
set -a; source .env; set +a

MODEL="${MODEL:-gemini/gemini-3.1-flash-lite-preview}"
TAG=$(echo "$MODEL" | tr '/.' '__')
SMOKE="${SMOKE:-0}"
LOG_DIR="$ROOT/benchmarks/xmodel_sweep_logs"
CACHE="$ROOT/benchmarks/xmodel_llm_cache_$TAG"
mkdir -p "$LOG_DIR"
COMMON_ARGS="llm.model=$MODEL evaluate.max_workers=4 cachier.cache_dir=$CACHE"

n_or_smoke() { if [ "$SMOKE" = "1" ]; then echo 2; else echo "$1"; fi; }

run_one() { # label, workdir, then full command...
  local label=$1 wd=$2; shift 2
  echo "===== $label ====="
  (cd "$wd" && "$@" ) > "$LOG_DIR/$label.$TAG.log" 2>&1
  echo "rc=$? (log: $LOG_DIR/$label.$TAG.log)"
  tail -2 "$LOG_DIR/$label.$TAG.log"
}

# ---------------- MuSR ----------------
for domain_split_n in "murder:murder_mysteries:100" "object:object_placements:106" "team:team_allocation:100"; do
  IFS=":" read domain split n <<< "$domain_split_n"
  N=$(n_or_smoke "$n")
  DS="dataset.split=${split}_test dataset.shuffle_seed=42 dataset.n=$N"
  run_one "musr_${domain}_workflow" benchmarks/musr \
    uv run python expt.py run --config-file conf/${domain}_workflow.yaml \
      $DS evaluate.expt_name=${domain}_workflow_xmodel evaluate.result_dir=xmodel_results $COMMON_ARGS
  run_one "musr_${domain}_react" benchmarks/musr \
    uv run python expt.py run --config-file conf/${domain}_react_engineered.yaml \
      $DS evaluate.expt_name=${domain}_react_xmodel evaluate.result_dir=xmodel_results $COMMON_ARGS
  run_one "musr_${domain}_zeroshot" benchmarks/musr \
    uv run python expt.py run --config-file conf/${domain}_unstructured_baseline.yaml \
      $DS evaluate.expt_name=${domain}_zeroshot_xmodel evaluate.result_dir=xmodel_results $COMMON_ARGS
done

# ---------------- NaturalPlan ----------------
for task_iface_wf in "meeting:meeting_planning:ptools_meeting.meeting_workflow" "trip:trip_planning:ptools_trip.trip_workflow"; do
  IFS=":" read task iface wf <<< "$task_iface_wf"
  N=$(n_or_smoke 100)
  DS="dataset.partition=test dataset.shuffle_seed=42 dataset.n=$N"
  run_one "natplan_${task}_workflow" benchmarks/natural_plan \
    uv run python expt.py run --config-file conf/${task}.yaml \
      $DS ptools.${iface}.method=direct ptools.${iface}.fn=${wf} \
      evaluate.expt_name=${task}_workflow_xmodel evaluate.result_dir=xmodel_results $COMMON_ARGS
  run_one "natplan_${task}_zeroshot" benchmarks/natural_plan \
    uv run python expt.py run --config-file conf/${task}.yaml \
      $DS ptools.${iface}.method=simulate \
      evaluate.expt_name=${task}_zeroshot_xmodel evaluate.result_dir=xmodel_results $COMMON_ARGS
  SNAP=$(ls -td benchmarks/COMMON/results/natural_plan/${task}/*react_engineered*/config.yaml 2>/dev/null | head -1)
  if [ -n "${SNAP:-}" ]; then
    run_one "natplan_${task}_react" benchmarks/natural_plan \
      uv run python expt.py run --config-file "$ROOT/$SNAP" \
        $DS evaluate.expt_name=${task}_react_xmodel evaluate.result_dir=xmodel_results $COMMON_ARGS
  else
    echo "!! no react snapshot for natplan/$task — resolve manually"
  fi
done

# ---------------- RuleArena ----------------
for domain_n in "airline:50" "nba:46"; do
  IFS=":" read domain n <<< "$domain_n"
  N=$(n_or_smoke "$n")
  DS="dataset.split=test dataset.domain=$domain dataset.shuffle_seed=137 dataset.n=$N"
  run_one "rulearena_${domain}_workflow" benchmarks/rulearena \
    uv run python expt.py run $DS \
      ptools.compute_rulearena_answer.method=direct ptools.compute_rulearena_answer.fn=ptools.l1_extract_workflow \
      evaluate.expt_name=${domain}_workflow_xmodel evaluate.result_dir=xmodel_results $COMMON_ARGS
  run_one "rulearena_${domain}_zeroshot" benchmarks/rulearena \
    uv run python expt.py run $DS \
      ptools.compute_rulearena_answer.method=simulate \
      evaluate.expt_name=${domain}_zeroshot_xmodel evaluate.result_dir=xmodel_results $COMMON_ARGS
  SNAP=$(ls -td benchmarks/COMMON/results/rulearena/${domain}/*react*/config.yaml 2>/dev/null | grep -v learned | head -1)
  if [ -n "${SNAP:-}" ]; then
    run_one "rulearena_${domain}_react" benchmarks/rulearena \
      uv run python expt.py run --config-file "$ROOT/$SNAP" \
        $DS evaluate.expt_name=${domain}_react_xmodel evaluate.result_dir=xmodel_results $COMMON_ARGS
  else
    echo "!! no react snapshot for rulearena/$domain — resolve manually"
  fi
done

echo "===== SWEEP DONE ($MODEL, SMOKE=$SMOKE) ====="
echo "Summarize: uv run -m secretagent.cli.results average --metric correct --metric cost- benchmarks/*/xmodel_results/*"
