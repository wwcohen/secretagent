#!/bin/bash
# Re-run all 4 cached distills (c1_v4, c1_v4g, c2_v4, c2_v4g) on TEST split.
# No re-training: uses existing learned_v4/ + learned_v4g/ + learned_class2_v4*/ dirs.
# At inference: backoff is to baseline simulate model = DeepSeek (V3.1 / V3).
set +e
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
mkdir -p "$LOG_DIR"
set -a; source "$ROOT/.env"; set +a
DS_V31="together_ai/deepseek-ai/DeepSeek-V3.1"
DS_V3="together_ai/deepseek-ai/DeepSeek-V3"
N=${N:-100}; N75=${N75:-75}; N43=${N43:-43}; N50=${N50:-50}

# launches an expt.py val and disowns; checks if a result for this expt_name already exists
launch() {
  local cwd="$1"; local exptbase="$2"; shift 2
  if ls -d "$cwd/test_results_full/"*."$exptbase" 2>/dev/null | head -1 | grep -q .; then
    echo "[skip] $exptbase already done"; return 0
  fi
  local log="$LOG_DIR/test_${exptbase}.log"
  echo "[$(date)] launching $exptbase" | tee -a "$log"
  cd "$cwd"
  nohup "$@" > "$log" 2>&1 &
  disown $!
}

# ===== natplan test (partition=test) =====
NATPLAN="$ROOT/benchmarks/natural_plan"
read_pt() {
  local cfg="$1"
  uv run python -c "
import yaml
c = yaml.safe_load(open('$cfg')) or {}
for n, kvs in (c.get('ptools', {}) or {}).items():
    for k, v in (kvs or {}).items():
        v = repr(v) if isinstance(v, bool) else v
        print(f'ptools.{n}.{k}={v}')
" 2>/dev/null | grep -v warning | tr '\n' ' '
}

# Helper: run natplan c1 test for sub (only if applicable ENABLED ptool exists in that sub's ptool_module)
launch_natplan_c1() {
  local sub="$1"; local learned="$2"; local tag="$3"
  local cfg="$NATPLAN/$learned/codedistill_config.yaml"
  [ ! -f "$cfg" ] && return
  # filter ptools to those in this sub's module
  local pt_filter
  pt_filter=$(uv run python -c "
import sys, yaml; sys.path.insert(0, '$NATPLAN')
import importlib
m = importlib.import_module('ptools_$sub')
c = yaml.safe_load(open('$cfg')) or {}
for n, kvs in (c.get('ptools', {}) or {}).items():
    if hasattr(m, n):
        for k, v in (kvs or {}).items():
            v = repr(v) if isinstance(v, bool) else v
            print(f'ptools.{n}.{k}={v}')
" 2>/dev/null | grep -v warning | tr '\n' ' ')
  [ -z "$pt_filter" ] && return  # no applicable ptools
  local iface workflow_fn
  case "$sub" in
    calendar) iface=calendar_scheduling; workflow_fn=ptools_calendar.calendar_workflow ;;
    meeting)  iface=meeting_planning;    workflow_fn=ptools_meeting.meeting_workflow ;;
    trip)     iface=trip_planning;       workflow_fn=ptools_trip.trip_workflow ;;
  esac
  launch "$NATPLAN" "natplan_${sub}_test_full_class1${tag}" \
    uv run python expt.py run --config-file "conf/${sub}.yaml" \
      dataset.partition=test "dataset.n=$N" \
      "evaluate.expt_name=natplan_${sub}_test_full_class1${tag}" \
      evaluate.record_details=true evaluate.result_dir=test_results_full \
      "llm.model=$DS_V31" \
      "ptools.${iface}.method=direct" "ptools.${iface}.fn=${workflow_fn}" \
      $pt_filter "learn.train_dir=$NATPLAN/$learned"
}

launch_natplan_c2() {
  local sub="$1"; local ldir="$2"; local tag="$3"
  local iface
  case "$sub" in
    calendar) iface=calendar_scheduling ;;
    meeting)  iface=meeting_planning ;;
    trip)     iface=trip_planning ;;
  esac
  local d=$(ls -dt "$NATPLAN/$ldir"/*"${iface}__workflow_distill" 2>/dev/null | head -1)
  [ -z "$d" ] || [ ! -f "$d/learned.py" ] && return
  launch "$NATPLAN" "natplan_${sub}_test_full_class2${tag}" \
    uv run python expt.py run --config-file "conf/${sub}.yaml" \
      dataset.partition=test "dataset.n=$N" \
      "evaluate.expt_name=natplan_${sub}_test_full_class2${tag}" \
      evaluate.record_details=true evaluate.result_dir=test_results_full \
      "llm.model=$DS_V31" \
      "ptools.${iface}.method=learned_code" \
      "ptools.${iface}.learner=workflow_distill" \
      "ptools.${iface}.backoff=true" \
      "learn.train_dir=$NATPLAN/$ldir"
}

# ===== Run all =====
echo "=== test split vals — START $(date) ==="

# Family A: natplan baseline + 4 distill conditions per sub
famA() {
  for sub in calendar meeting trip; do
    local iface workflow_fn
    case "$sub" in
      calendar) iface=calendar_scheduling; workflow_fn=ptools_calendar.calendar_workflow ;;
      meeting)  iface=meeting_planning;    workflow_fn=ptools_meeting.meeting_workflow ;;
      trip)     iface=trip_planning;       workflow_fn=ptools_trip.trip_workflow ;;
    esac
    # baseline
    launch "$NATPLAN" "natplan_${sub}_test_full_baseline" \
      uv run python expt.py run --config-file "conf/${sub}.yaml" \
        dataset.partition=test "dataset.n=$N" \
        "evaluate.expt_name=natplan_${sub}_test_full_baseline" \
        evaluate.record_details=true evaluate.result_dir=test_results_full \
        "llm.model=$DS_V31" \
        "ptools.${iface}.method=direct" "ptools.${iface}.fn=${workflow_fn}"
    launch_natplan_c1 "$sub" learned_v4 v4
    launch_natplan_c1 "$sub" learned_v4g v4g
    launch_natplan_c2 "$sub" learned_class2_v4 v4
    launch_natplan_c2 "$sub" learned_class2_v4g v4g
  done
}

# Family B: musr — split=<task>_test
famB() {
  local MUSR="$ROOT/benchmarks/musr"
  for task in murder object team; do
    local conf split
    case "$task" in
      murder) conf=conf/murder_workflow.yaml; split=murder_mysteries_test ;;
      object) conf=conf/object_workflow.yaml; split=object_placements_test ;;
      team)   conf=conf/team_workflow.yaml;   split=team_allocation_test ;;
    esac
    # baseline
    launch "$MUSR" "musr_${task}_test_full_baseline" \
      uv run python expt.py run --config-file "$conf" \
        "dataset.split=$split" "dataset.n=$N75" \
        "evaluate.expt_name=musr_${task}_test_full_baseline" \
        evaluate.record_details=true evaluate.result_dir=test_results_full \
        "llm.model=$DS_V3"
    # c1 v4 / v4g
    for tag in v4 v4g; do
      local cfg="$MUSR/learned_${tag}/codedistill_config.yaml"
      [ ! -f "$cfg" ] && continue
      local pt_args=$(read_pt "$cfg")
      launch "$MUSR" "musr_${task}_test_full_class1${tag}" \
        uv run python expt.py run --config-file "$conf" \
          "dataset.split=$split" "dataset.n=$N75" \
          "evaluate.expt_name=musr_${task}_test_full_class1${tag}" \
          evaluate.record_details=true evaluate.result_dir=test_results_full \
          "llm.model=$DS_V3" \
          $pt_args "learn.train_dir=$MUSR/learned_${tag}"
    done
    # c2 v4 / v4g — separate dirs per task
    for tag in v4 v4g; do
      local ldir
      if [ "$tag" = "v4" ]; then
        # v4: shared learned_class2_v4, per-task answer_question_workflow distill
        ldir="learned_class2_v4_${task}"
        [ ! -d "$MUSR/$ldir" ] && ldir="learned_class2_v4"
      else
        ldir="learned_class2_v4g_${task}"
        [ ! -d "$MUSR/$ldir" ] && ldir="learned_class2_v4g"
      fi
      local d=$(ls -dt "$MUSR/$ldir"/*answer_question_workflow__workflow_distill 2>/dev/null | head -1)
      [ -z "$d" ] || [ ! -f "$d/learned.py" ] && continue
      launch "$MUSR" "musr_${task}_test_full_class2${tag}" \
        uv run python expt.py run --config-file "$conf" \
          "dataset.split=$split" "dataset.n=$N75" \
          "evaluate.expt_name=musr_${task}_test_full_class2${tag}" \
          evaluate.record_details=true evaluate.result_dir=test_results_full \
          "llm.model=$DS_V3" \
          "ptools.answer_question_workflow.method=learned_code" \
          "ptools.answer_question_workflow.learner=workflow_distill" \
          "ptools.answer_question_workflow.backoff=true" \
          "learn.train_dir=$MUSR/$ldir"
    done
  done
}

# Family C: bbh ×4
famC() {
  for sub_iface_wf_n in "sports_understanding:are_sports_in_sentence_consistent:sports_understanding_workflow:75" \
                       "penguins_in_a_table:answer_penguin_question:penguins_workflow:43" \
                       "geometric_shapes:identify_shape:geometric_shapes_workflow:75" \
                       "date_understanding:answer_date_question:zeroshot_unstructured_workflow:75"; do
    IFS=":" read sub iface wf n <<< "$sub_iface_wf_n"
    local CWD="$ROOT/benchmarks/bbh/$sub"
    local extra=""
    [ "$sub" = date_understanding ] && extra="ptools.answer_date_question_orchestrated.method=direct ptools.answer_date_question_orchestrated.fn=ptools.zeroshot_unstructured_workflow"
    local label="bbh_${sub%_*}"  # not great, but unique enough
    case "$sub" in
      sports_understanding) label=bbh_sports ;;
      penguins_in_a_table)  label=bbh_penguins ;;
      geometric_shapes)     label=bbh_geometric ;;
      date_understanding)   label=bbh_date ;;
    esac
    # baseline
    launch "$CWD" "${label}_test_full_baseline" \
      uv run python -m secretagent.cli.expt run \
        --interface "ptools.$iface" \
        "ptools.$iface.method=direct" "ptools.$iface.fn=ptools.$wf" $extra \
        "llm.model=$DS_V31" dataset.split=test "dataset.n=$n" \
        "evaluate.expt_name=${label}_test_full_baseline" \
        evaluate.record_details=true evaluate.result_dir=test_results_full
    # c1 v4 / v4g
    for tag in v4 v4g; do
      local cfg="$CWD/learned_${tag}/codedistill_config.yaml"
      [ ! -f "$cfg" ] && continue
      local pt_args=$(read_pt "$cfg")
      launch "$CWD" "${label}_test_full_class1${tag}" \
        uv run python -m secretagent.cli.expt run \
          --interface "ptools.$iface" \
          "ptools.$iface.method=direct" "ptools.$iface.fn=ptools.$wf" $extra \
          "llm.model=$DS_V31" dataset.split=test "dataset.n=$n" \
          "evaluate.expt_name=${label}_test_full_class1${tag}" \
          evaluate.record_details=true evaluate.result_dir=test_results_full \
          $pt_args "learn.train_dir=$CWD/learned_${tag}"
    done
    # c2 v4 / v4g
    for tag in v4 v4g; do
      local ldir="learned_class2_${tag}"
      local d=$(ls -dt "$CWD/$ldir"/*"${iface}__workflow_distill" 2>/dev/null | head -1)
      [ -z "$d" ] || [ ! -f "$d/learned.py" ] && continue
      launch "$CWD" "${label}_test_full_class2${tag}" \
        uv run python -m secretagent.cli.expt run \
          --interface "ptools.$iface" $extra \
          "llm.model=$DS_V31" dataset.split=test "dataset.n=$n" \
          "evaluate.expt_name=${label}_test_full_class2${tag}" \
          evaluate.record_details=true evaluate.result_dir=test_results_full \
          "ptools.$iface.method=learned_code" \
          "ptools.$iface.learner=workflow_distill" \
          "ptools.$iface.backoff=true" \
          "learn.train_dir=$CWD/$ldir"
    done
  done
}

# Family D: medcalc + tabmwp + rulearena_airline
famD() {
  # medcalc (already test; uses HF dataset)
  local MED="$ROOT/benchmarks/medcalc"
  launch "$MED" "medcalc_test_full_baseline" \
    uv run python expt.py run --config-file conf/workflow.yaml \
      "dataset.split=test" "dataset.n=$N" \
      "evaluate.expt_name=medcalc_test_full_baseline" \
      evaluate.record_details=true evaluate.result_dir=test_results_full \
      "llm.model=$DS_V31"
  for tag in v4 v4g; do
    local cfg="$MED/learned_${tag}/codedistill_config.yaml"
    if [ -f "$cfg" ]; then
      local pt_args=$(read_pt "$cfg")
      [ -n "$pt_args" ] && launch "$MED" "medcalc_test_full_class1${tag}" \
        uv run python expt.py run --config-file conf/workflow.yaml \
          "dataset.split=test" "dataset.n=$N" \
          "evaluate.expt_name=medcalc_test_full_class1${tag}" \
          evaluate.record_details=true evaluate.result_dir=test_results_full \
          "llm.model=$DS_V31" \
          $pt_args "learn.train_dir=$MED/learned_${tag}"
    fi
    local ldir="learned_class2_${tag}"
    local d=$(ls -dt "$MED/$ldir"/*calculate_medical_value__workflow_distill 2>/dev/null | head -1)
    [ -n "$d" ] && [ -f "$d/learned.py" ] && launch "$MED" "medcalc_test_full_class2${tag}" \
      uv run python expt.py run --config-file conf/workflow.yaml \
        "dataset.split=test" "dataset.n=$N" \
        "evaluate.expt_name=medcalc_test_full_class2${tag}" \
        evaluate.record_details=true evaluate.result_dir=test_results_full \
        "llm.model=$DS_V31" \
        "ptools.calculate_medical_value.method=learned_code" \
        "ptools.calculate_medical_value.learner=workflow_distill" \
        "ptools.calculate_medical_value.backoff=true" \
        "learn.train_dir=$MED/$ldir"
  done

  # tabmwp (split=test1k)
  local TM="$ROOT/benchmarks/tabmwp"
  launch "$TM" "tabmwp_test_full_baseline" \
    uv run python expt.py run --config-file conf/workflow_incontext.yaml \
      "dataset.split=test1k" "dataset.n=$N" \
      "evaluate.expt_name=tabmwp_test_full_baseline" \
      evaluate.record_details=true evaluate.result_dir=test_results_full \
      "llm.model=$DS_V31"
  for tag in v4 v4g; do
    local cfg="$TM/learned_${tag}/codedistill_config.yaml"
    if [ -f "$cfg" ]; then
      local pt_args=$(read_pt "$cfg")
      [ -n "$pt_args" ] && launch "$TM" "tabmwp_test_full_class1${tag}" \
        uv run python expt.py run --config-file conf/workflow_incontext.yaml \
          "dataset.split=test1k" "dataset.n=$N" \
          "evaluate.expt_name=tabmwp_test_full_class1${tag}" \
          evaluate.record_details=true evaluate.result_dir=test_results_full \
          "llm.model=$DS_V31" \
          $pt_args "learn.train_dir=$TM/learned_${tag}"
    fi
    local ldir="learned_class2_${tag}"
    local d=$(ls -dt "$TM/$ldir"/*tabmwp_solve__workflow_distill 2>/dev/null | head -1)
    [ -n "$d" ] && [ -f "$d/learned.py" ] && launch "$TM" "tabmwp_test_full_class2${tag}" \
      uv run python expt.py run --config-file conf/workflow_incontext.yaml \
        "dataset.split=test1k" "dataset.n=$N" \
        "evaluate.expt_name=tabmwp_test_full_class2${tag}" \
        evaluate.record_details=true evaluate.result_dir=test_results_full \
        "llm.model=$DS_V31" \
        "ptools.tabmwp_solve.method=learned_code" \
        "ptools.tabmwp_solve.learner=workflow_distill" \
        "ptools.tabmwp_solve.backoff=true" \
        "learn.train_dir=$TM/$ldir"
  done

  # rulearena (top-level, just airline since that's what was distilled at top level)
  local RA="$ROOT/benchmarks/rulearena"
  for dom in nba tax airline; do
    local n_d=$N50; [ "$dom" = nba ] && n_d=$N50
    launch "$RA" "rulearena_${dom}_test_full_baseline" \
      uv run python expt.py run \
        "dataset.domain=${dom}" "dataset.split=test" "dataset.n=$n_d" \
        "ptools.compute_rulearena_answer.method=direct" \
        "ptools.compute_rulearena_answer.fn=ptools.l1_extract_workflow" \
        "llm.model=$DS_V3" \
        "evaluate.expt_name=rulearena_${dom}_test_full_baseline" \
        evaluate.record_details=true evaluate.result_dir=test_results_full
  done
  # Only airline has a c2 distill at top-level; nba/tax don't
  for tag in v4 v4g; do
    local ldir="learned_class2_${tag}"
    local d=$(ls -dt "$RA/$ldir"/*compute_rulearena_answer__workflow_distill 2>/dev/null | head -1)
    [ -n "$d" ] && [ -f "$d/learned.py" ] && launch "$RA" "rulearena_airline_test_full_class2${tag}" \
      uv run python expt.py run \
        "dataset.domain=airline" "dataset.split=test" "dataset.n=$N50" \
        "ptools.extract_airline_params.method=simulate" \
        "ptools.compute_airline_calculator.method=direct" \
        "ptools.compute_airline_calculator.fn=ptools._airline_calc_fn" \
        "ptools.compute_rulearena_answer.method=learned_code" \
        "ptools.compute_rulearena_answer.learner=workflow_distill" \
        "ptools.compute_rulearena_answer.backoff=true" \
        "llm.model=$DS_V3" \
        "evaluate.expt_name=rulearena_airline_test_full_class2${tag}" \
        evaluate.record_details=true evaluate.result_dir=test_results_full \
        "learn.train_dir=$RA/$ldir"
  done
}

# Family E: finqa — only has train+valid, no real test. Skip with note.
famE() {
  echo "[$(date)] finqa: no test split, skipping"
}

famA & PA=$!
famB & PB=$!
famC & PC=$!
famD & PD=$!
famE & PE=$!
wait $PA $PB $PC $PD $PE

echo "[$(date)] all test val launches done. waiting for in-flight children..."
wait
echo "=== test split vals — DONE $(date) ==="
