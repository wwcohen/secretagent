#!/bin/bash
# Fill missing vals (c1_v4 / c2_v4 / c3_v4 only — NO c1_v1).
set +e
ROOT="/Users/anon/Desktop/anon_research/secretagent"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
mkdir -p "$LOG_DIR"
set -a; source "$ROOT/.env"; set +a
DS="together_ai/deepseek-ai/DeepSeek-V3.1"
DS_V3="together_ai/deepseek-ai/DeepSeek-V3"

read_pt() {
  local cfg="$1"
  uv run python -c "
import yaml
cfg = yaml.safe_load(open('$cfg')) or {}
for n, kvs in (cfg.get('ptools', {}) or {}).items():
    for k, v in (kvs or {}).items():
        v = repr(v) if isinstance(v, bool) else v
        print(f'ptools.{n}.{k}={v}')
" 2>/dev/null
}

run_class1_val() {
  local label="$1"; local cwd="$2"; local learned_dir="$3"; local exptbase="$4"; shift 4
  local cfg="$cwd/$learned_dir/codedistill_config.yaml"
  if [ ! -f "$cfg" ]; then echo "[$label $learned_dir] no config — skip"; return; fi
  local n_enabled=$(uv run python -c "import yaml; c=yaml.safe_load(open('$cfg')) or {}; print(len(c.get('ptools',{}) or {}))" 2>/dev/null | grep -v warning | tail -1)
  if [ "$n_enabled" = "0" ] || [ -z "$n_enabled" ]; then echo "[$label $learned_dir] 0 ENABLED — skip"; return; fi
  declare -a PT=()
  while IFS= read -r line; do PT+=("$line"); done < <(read_pt "$cfg")
  echo "[$(date)] $label $learned_dir val (${#PT[@]} dotlist args)"
  cd "$cwd"
  uv run python expt.py run "$@" \
    "evaluate.expt_name=${exptbase}" \
    evaluate.record_details=true evaluate.result_dir=val_results_full \
    "${PT[@]}" "learn.train_dir=$cwd/$learned_dir" \
    > "$LOG_DIR/fill_${exptbase}.log" 2>&1
  echo "[$(date)] $label $learned_dir val rc=$?"
}

run_class1_val_bbh() {
  local label="$1"; local cwd="$2"; local learned_dir="$3"; local exptbase="$4"; local iface="$5"; local wf="$6"; local n="$7"; shift 7
  local cfg="$cwd/$learned_dir/codedistill_config.yaml"
  if [ ! -f "$cfg" ]; then echo "[$label $learned_dir] no config — skip"; return; fi
  declare -a PT=()
  while IFS= read -r line; do PT+=("$line"); done < <(read_pt "$cfg")
  if [ ${#PT[@]} = 0 ]; then echo "[$label $learned_dir] 0 ENABLED — skip"; return; fi
  echo "[$(date)] $label $learned_dir val"
  cd "$cwd"
  EXTRA=()
  [ "$label" = "bbh_date" ] && EXTRA+=("ptools.answer_date_question_orchestrated.method=direct" "ptools.answer_date_question_orchestrated.fn=ptools.zeroshot_unstructured_workflow")
  uv run python -m secretagent.cli.expt run \
    --interface "ptools.${iface}" \
    "ptools.${iface}.method=direct" "ptools.${iface}.fn=ptools.${wf}" \
    "${EXTRA[@]}" \
    "llm.model=$DS" "dataset.split=valid" "dataset.n=$n" \
    "evaluate.expt_name=${exptbase}" \
    evaluate.record_details=true evaluate.result_dir=val_results_full \
    "${PT[@]}" "learn.train_dir=$cwd/$learned_dir" \
    > "$LOG_DIR/fill_${exptbase}.log" 2>&1
  echo "[$(date)] $label $learned_dir val rc=$?"
}

# ========== Class 1 opus fills ==========
echo "[$(date)] === Class 1 opus fills (no c1_v1!) ==="

( run_class1_val musr_murder "$ROOT/benchmarks/musr" learned_opus murder_val_full_class1_opus \
    --config-file conf/murder_workflow.yaml dataset.split=murder_mysteries_val dataset.n=75 ) &

( run_class1_val medcalc "$ROOT/benchmarks/medcalc" learned_opus medcalc_val_full_class1_opus \
    --config-file conf/workflow.yaml dataset.split=valid dataset.n=100 ) &

( run_class1_val_bbh bbh_geometric "$ROOT/benchmarks/bbh/geometric_shapes" learned_opus geometric_val_full_class1_opus \
    identify_shape geometric_shapes_workflow 75 ) &

( run_class1_val_bbh bbh_date "$ROOT/benchmarks/bbh/date_understanding" learned_opus date_val_full_class1_opus \
    answer_date_question zeroshot_unstructured_workflow 75 ) &

for dom in nba tax airline; do
  ( run_class1_val rulearena_${dom} "$ROOT/benchmarks/rulearena" learned_opus ${dom}_val_full_class1_opus \
      "dataset.domain=${dom}" "dataset.split=valid" "dataset.n=50" \
      "ptools.compute_rulearena_answer.method=direct" \
      "ptools.compute_rulearena_answer.fn=ptools.l1_extract_workflow" ) &
done

wait
echo "[$(date)] === Class 1 opus fills DONE ==="

# ========== Class 2 opus fills ==========
echo "[$(date)] === Class 2 opus fills ==="

run_class2_val() {
  local label="$1"; local cwd="$2"; local exptbase="$3"; local iface="$4"; shift 4
  if [ ! -d "$cwd/learned_class2_opus" ]; then echo "[$label] no learned_class2_opus — skip"; return; fi
  if [ -z "$(ls -d "$cwd/learned_class2_opus/"*"${iface}__workflow_distill" 2>/dev/null | head -1)" ]; then
    echo "[$label] no learned_class2_opus/*${iface}__workflow_distill — skip"; return
  fi
  echo "[$(date)] $label class2_opus val"
  cd "$cwd"
  uv run python expt.py run "$@" \
    "evaluate.expt_name=${exptbase}" \
    evaluate.record_details=true evaluate.result_dir=val_results_full \
    "ptools.${iface}.method=learned_code" \
    "ptools.${iface}.learner=workflow_distill" \
    "ptools.${iface}.backoff=true" \
    "learn.train_dir=$cwd/learned_class2_opus" \
    > "$LOG_DIR/fill_${exptbase}.log" 2>&1
  echo "[$(date)] $label class2_opus val rc=$?"
}

( run_class2_val musr_murder "$ROOT/benchmarks/musr" murder_val_full_class2_opus answer_question \
    --config-file conf/murder_workflow.yaml \
    "dataset.split=murder_mysteries_val" "dataset.n=75" "llm.model=$DS_V3" ) &

( run_class2_val finqa "$ROOT/benchmarks/finqa" finqa_val_full_class2_opus answer_finqa \
    --config-file conf/workflow.yaml "dataset.split=valid" "dataset.n=100" "llm.model=$DS" ) &

( run_class2_val medcalc "$ROOT/benchmarks/medcalc" medcalc_val_full_class2_opus answer_medcalc \
    --config-file conf/workflow.yaml "dataset.split=valid" "dataset.n=100" "llm.model=$DS" ) &

for dom in nba tax; do
  ( run_class2_val rulearena_${dom} "$ROOT/benchmarks/rulearena" ${dom}_val_full_class2_opus compute_rulearena_answer \
      "dataset.domain=${dom}" "dataset.split=valid" "dataset.n=50" \
      "ptools.extract_${dom}_params.method=simulate" \
      "ptools.compute_${dom}_calculator.method=direct" \
      "ptools.compute_${dom}_calculator.fn=ptools._${dom}_calc_fn" \
      "llm.model=$DS_V3" ) &
done

wait
echo "[$(date)] === Class 2 opus fills DONE ==="

# ========== Class 3 opus fills ==========
echo "[$(date)] === Class 3 opus fills ==="

run_class3_val() {
  local label="$1"; local cwd="$2"; local exptbase="$3"; local iface="$4"; shift 4
  local cfg="$cwd/learned_class3_opus/codedistill_config.yaml"
  if [ ! -d "$cwd/learned_class3_opus" ]; then echo "[$label] no class3_v4 — skip"; return; fi
  declare -a PT3=()
  if [ -f "$cfg" ]; then
    while IFS= read -r line; do PT3+=("$line"); done < <(read_pt "$cfg")
  fi
  echo "[$(date)] $label class3_opus val"
  cd "$cwd"
  uv run python expt.py run "$@" \
    "evaluate.expt_name=${exptbase}" \
    evaluate.record_details=true evaluate.result_dir=val_results_full \
    "${PT3[@]}" \
    "ptools.${iface}.method=learned_code" \
    "ptools.${iface}.learner=workflow_distill" \
    "ptools.${iface}.backoff=true" \
    "learn.train_dir=$cwd/learned_class3_opus" \
    > "$LOG_DIR/fill_${exptbase}.log" 2>&1
  echo "[$(date)] $label class3_opus val rc=$?"
}

( run_class3_val finqa "$ROOT/benchmarks/finqa" finqa_val_full_class3_opus answer_finqa \
    --config-file conf/workflow.yaml "dataset.split=valid" "dataset.n=100" "llm.model=$DS" ) &

( run_class3_val natplan_calendar "$ROOT/benchmarks/natural_plan" calendar_val_full_class3_opus calendar_scheduling \
    --config-file conf/calendar.yaml "dataset.partition=valid" "dataset.n=100" "llm.model=$DS" ) &

wait
echo "[$(date)] === Class 3 opus fills DONE ==="
echo "[$(date)] === ALL FILL_v2 DONE ==="
