#!/bin/bash
# gemini val watcher — bash 3.2 compatible (no associative arrays).
# Polls every 60s. Launches val for any benchmark whose distill is done.
# Skips already-done vals. Exits when all distills done + all vals launched.
set +e
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
LOG_DIR="$ROOT/benchmarks/codedistill_logs_v2"
mkdir -p "$LOG_DIR"
set -a; source "$ROOT/.env"; set +a
DS_V31="together_ai/deepseek-ai/DeepSeek-V3.1"
DS_V3="together_ai/deepseek-ai/DeepSeek-V3"

# track-launched flag files (instead of associative array)
TRACK_DIR="/tmp/gemini_vals_launched"
mkdir -p "$TRACK_DIR"

# (label cwd_suffix c2_iface c2_dir model split n)
# fields semicolon-delimited so we can iterate
BENCHES="
natplan_calendar;benchmarks/natural_plan;calendar_scheduling;learned_class2_gemini;$DS_V31;valid;100
natplan_meeting;benchmarks/natural_plan;meeting_planning;learned_class2_gemini;$DS_V31;valid;100
natplan_trip;benchmarks/natural_plan;trip_planning;learned_class2_gemini;$DS_V31;valid;100
musr_murder;benchmarks/musr;answer_question_workflow;learned_class2_gemini_murder;$DS_V3;murder_mysteries_val;75
musr_object;benchmarks/musr;answer_question_workflow;learned_class2_gemini_object;$DS_V3;object_placements_val;75
musr_team;benchmarks/musr;answer_question_workflow;learned_class2_gemini_team;$DS_V3;team_allocation_val;75
bbh_sports;benchmarks/bbh/sports_understanding;are_sports_in_sentence_consistent;learned_class2_gemini;$DS_V31;valid;75
bbh_penguins;benchmarks/bbh/penguins_in_a_table;answer_penguin_question;learned_class2_gemini;$DS_V31;valid;43
bbh_geometric;benchmarks/bbh/geometric_shapes;identify_shape;learned_class2_gemini;$DS_V31;valid;75
bbh_date;benchmarks/bbh/date_understanding;answer_date_question;learned_class2_gemini;$DS_V31;valid;75
medcalc;benchmarks/medcalc;calculate_medical_value;learned_class2_gemini;$DS_V31;test;100
finqa;benchmarks/finqa;answer_finqa;learned_class2_gemini;$DS_V31;valid;100
rulearena_nba;benchmarks/rulearena;;;$DS_V3;valid;42
rulearena_tax;benchmarks/rulearena;;;$DS_V3;valid;50
rulearena_airline;benchmarks/rulearena;compute_rulearena_answer;learned_class2_gemini;$DS_V3;valid;50
tabmwp;benchmarks/tabmwp;tabmwp_solve;learned_class2_gemini;$DS_V31;dev1k;100
"

# returns 0 if val for $1=label $2=class is already done OR launched
val_already_handled() {
  local label="$1"; local cls="$2"  # cls=class1 or class2
  local cwd="$3"
  local exptbase="${label}_val_full_${cls}gemini"
  ls -d "$cwd/val_results_full/"*."$exptbase" 2>/dev/null | head -1 | grep -q . && return 0
  [ -f "$TRACK_DIR/${cls}_${label}" ] && return 0
  return 1
}
mark_launched() {
  touch "$TRACK_DIR/$1_$2"
}

# === class 1 val per benchmark ===
launch_c1() {
  local label="$1"; local cwd="$2"; local model="$3"; local split="$4"; local n="$5"
  local cfg="$cwd/learned_gemini/codedistill_config.yaml"
  [ ! -f "$cfg" ] && return 1
  val_already_handled "$label" "class1" "$cwd" && return 0
  mark_launched class1 "$label"

  local exptbase="${label}_val_full_class1_gemini"
  local log="$LOG_DIR/gemini_val_class1_${label}.log"
  echo "[$(date)] launching c1_gemini val: $label" | tee -a "$log"

  # extract dotlist from cfg
  local PT_FILE="/tmp/gemini_pt_${label}_class1.txt"
  uv run python -c "
import yaml
c = yaml.safe_load(open('$cfg')) or {}
for n, kvs in (c.get('ptools', {}) or {}).items():
    for k, v in (kvs or {}).items():
        v = repr(v) if isinstance(v, bool) else v
        print(f'ptools.{n}.{k}={v}')
" 2>/dev/null > "$PT_FILE"

  cd "$cwd"
  case "$label" in
    natplan_calendar|natplan_meeting|natplan_trip)
      local sub="${label#natplan_}"
      local extra=""
      [ "$label" = natplan_meeting ] && extra="ptools.meeting_planning.method=direct ptools.meeting_planning.fn=ptools_meeting.meeting_workflow"
      nohup uv run python expt.py run --config-file "conf/${sub}.yaml" \
        dataset.partition=valid "dataset.n=$n" \
        "evaluate.expt_name=$exptbase" evaluate.record_details=true \
        evaluate.result_dir=val_results_full "llm.model=$model" \
        $(cat "$PT_FILE") $extra "learn.train_dir=$cwd/learned_gemini" \
        > "$log" 2>&1 &
      ;;
    musr_murder)
      nohup uv run python expt.py run --config-file conf/murder_workflow.yaml \
        "dataset.split=$split" "dataset.n=$n" \
        "evaluate.expt_name=$exptbase" evaluate.record_details=true \
        evaluate.result_dir=val_results_full "llm.model=$model" \
        $(cat "$PT_FILE") "learn.train_dir=$cwd/learned_gemini" \
        > "$log" 2>&1 &
      ;;
    musr_object)
      nohup uv run python expt.py run --config-file conf/object_workflow.yaml \
        "dataset.split=$split" "dataset.n=$n" \
        "evaluate.expt_name=$exptbase" evaluate.record_details=true \
        evaluate.result_dir=val_results_full "llm.model=$model" \
        $(cat "$PT_FILE") "learn.train_dir=$cwd/learned_gemini" \
        > "$log" 2>&1 &
      ;;
    musr_team)
      nohup uv run python expt.py run --config-file conf/team_workflow.yaml \
        "dataset.split=$split" "dataset.n=$n" \
        "evaluate.expt_name=$exptbase" evaluate.record_details=true \
        evaluate.result_dir=val_results_full "llm.model=$model" \
        $(cat "$PT_FILE") "learn.train_dir=$cwd/learned_gemini" \
        > "$log" 2>&1 &
      ;;
    bbh_sports|bbh_penguins|bbh_geometric|bbh_date)
      local iface wf
      case "$label" in
        bbh_sports) iface=are_sports_in_sentence_consistent; wf=sports_understanding_workflow ;;
        bbh_penguins) iface=answer_penguin_question; wf=penguins_workflow ;;
        bbh_geometric) iface=identify_shape; wf=geometric_shapes_workflow ;;
        bbh_date) iface=answer_date_question; wf=zeroshot_unstructured_workflow ;;
      esac
      local extra=""
      [ "$label" = bbh_date ] && extra="ptools.answer_date_question_orchestrated.method=direct ptools.answer_date_question_orchestrated.fn=ptools.zeroshot_unstructured_workflow"
      nohup uv run python -m secretagent.cli.expt run \
        --interface "ptools.$iface" \
        "ptools.$iface.method=direct" "ptools.$iface.fn=ptools.$wf" $extra \
        "llm.model=$model" "dataset.split=$split" "dataset.n=$n" \
        "evaluate.expt_name=$exptbase" evaluate.record_details=true \
        evaluate.result_dir=val_results_full \
        $(cat "$PT_FILE") "learn.train_dir=$cwd/learned_gemini" \
        > "$log" 2>&1 &
      ;;
    medcalc)
      nohup uv run python expt.py run --config-file conf/workflow.yaml \
        "dataset.split=$split" "dataset.n=$n" \
        "evaluate.expt_name=$exptbase" evaluate.record_details=true \
        evaluate.result_dir=val_results_full "llm.model=$model" \
        $(cat "$PT_FILE") "learn.train_dir=$cwd/learned_gemini" \
        > "$log" 2>&1 &
      ;;
    finqa)
      nohup uv run python expt.py run --config-file conf/workflow.yaml \
        "dataset.split=$split" "dataset.n=$n" \
        "evaluate.expt_name=$exptbase" evaluate.record_details=true \
        evaluate.result_dir=val_results_full "llm.model=$model" \
        $(cat "$PT_FILE") "learn.train_dir=$cwd/learned_gemini" \
        > "$log" 2>&1 &
      ;;
    rulearena_nba|rulearena_tax|rulearena_airline)
      local dom="${label#rulearena_}"
      nohup uv run python expt.py run \
        "dataset.domain=$dom" "dataset.split=$split" "dataset.n=$n" \
        ptools.compute_rulearena_answer.method=direct \
        ptools.compute_rulearena_answer.fn=ptools.l1_extract_workflow \
        "llm.model=$model" \
        "evaluate.expt_name=$exptbase" evaluate.record_details=true \
        evaluate.result_dir=val_results_full \
        $(cat "$PT_FILE") "learn.train_dir=$cwd/learned_gemini" \
        > "$log" 2>&1 &
      ;;
    tabmwp)
      nohup uv run python expt.py run --config-file conf/workflow_incontext.yaml \
        "dataset.split=$split" "dataset.n=$n" \
        "evaluate.expt_name=$exptbase" evaluate.record_details=true \
        evaluate.result_dir=val_results_full "llm.model=$model" \
        $(cat "$PT_FILE") "learn.train_dir=$cwd/learned_gemini" \
        > "$log" 2>&1 &
      ;;
  esac
  echo "[$(date)] $label c1_gemini val PID=$!" | tee -a "$log"
}

# === class 2 val per benchmark ===
launch_c2() {
  local label="$1"; local cwd="$2"; local iface="$3"; local ldir="$4"
  local model="$5"; local split="$6"; local n="$7"
  [ -z "$iface" ] && return 1  # nba/tax don't have c2 distill (no per-domain)
  local d=$(ls -dt "$cwd/$ldir"/*"${iface}__workflow_distill" 2>/dev/null | head -1)
  [ -z "$d" ] || [ ! -f "$d/learned.py" ] && return 1
  val_already_handled "$label" "class2" "$cwd" && return 0
  mark_launched class2 "$label"

  local exptbase="${label}_val_full_class2_gemini"
  local log="$LOG_DIR/gemini_val_class2_${label}.log"
  echo "[$(date)] launching c2_gemini val: $label" | tee -a "$log"

  cd "$cwd"
  case "$label" in
    natplan_calendar|natplan_meeting|natplan_trip)
      local sub="${label#natplan_}"
      nohup uv run python expt.py run --config-file "conf/${sub}.yaml" \
        dataset.partition=valid "dataset.n=$n" \
        "evaluate.expt_name=$exptbase" evaluate.record_details=true \
        evaluate.result_dir=val_results_full "llm.model=$model" \
        "ptools.${iface}.method=learned_code" \
        "ptools.${iface}.learner=workflow_distill" \
        "ptools.${iface}.backoff=true" \
        "learn.train_dir=$cwd/$ldir" > "$log" 2>&1 &
      ;;
    musr_murder|musr_object|musr_team)
      local conf
      case "$label" in
        musr_murder) conf=conf/murder_workflow.yaml ;;
        musr_object) conf=conf/object_workflow.yaml ;;
        musr_team) conf=conf/team_workflow.yaml ;;
      esac
      nohup uv run python expt.py run --config-file "$conf" \
        "dataset.split=$split" "dataset.n=$n" \
        "evaluate.expt_name=$exptbase" evaluate.record_details=true \
        evaluate.result_dir=val_results_full "llm.model=$model" \
        "ptools.${iface}.method=learned_code" \
        "ptools.${iface}.learner=workflow_distill" \
        "ptools.${iface}.backoff=true" \
        "learn.train_dir=$cwd/$ldir" > "$log" 2>&1 &
      ;;
    bbh_sports|bbh_penguins|bbh_geometric|bbh_date)
      local extra=""
      [ "$label" = bbh_date ] && extra="ptools.answer_date_question_orchestrated.method=direct ptools.answer_date_question_orchestrated.fn=ptools.zeroshot_unstructured_workflow"
      nohup uv run python -m secretagent.cli.expt run \
        --interface "ptools.$iface" $extra \
        "llm.model=$model" "dataset.split=$split" "dataset.n=$n" \
        "evaluate.expt_name=$exptbase" evaluate.record_details=true \
        evaluate.result_dir=val_results_full \
        "ptools.${iface}.method=learned_code" \
        "ptools.${iface}.learner=workflow_distill" \
        "ptools.${iface}.backoff=true" \
        "learn.train_dir=$cwd/$ldir" > "$log" 2>&1 &
      ;;
    medcalc)
      nohup uv run python expt.py run --config-file conf/workflow.yaml \
        "dataset.split=$split" "dataset.n=$n" \
        "evaluate.expt_name=$exptbase" evaluate.record_details=true \
        evaluate.result_dir=val_results_full "llm.model=$model" \
        "ptools.${iface}.method=learned_code" \
        "ptools.${iface}.learner=workflow_distill" \
        "ptools.${iface}.backoff=true" \
        "learn.train_dir=$cwd/$ldir" > "$log" 2>&1 &
      ;;
    finqa)
      nohup uv run python expt.py run --config-file conf/workflow.yaml \
        "dataset.split=$split" "dataset.n=$n" \
        "evaluate.expt_name=$exptbase" evaluate.record_details=true \
        evaluate.result_dir=val_results_full "llm.model=$model" \
        "ptools.${iface}.method=learned_code" \
        "ptools.${iface}.learner=workflow_distill" \
        "ptools.${iface}.backoff=true" \
        "learn.train_dir=$cwd/$ldir" > "$log" 2>&1 &
      ;;
    rulearena_airline)
      nohup uv run python expt.py run \
        dataset.domain=airline "dataset.split=$split" "dataset.n=$n" \
        ptools.extract_airline_params.method=simulate \
        ptools.compute_airline_calculator.method=direct \
        ptools.compute_airline_calculator.fn=ptools._airline_calc_fn \
        "ptools.${iface}.method=learned_code" \
        "ptools.${iface}.learner=workflow_distill" \
        "ptools.${iface}.backoff=true" \
        "llm.model=$model" \
        "evaluate.expt_name=$exptbase" evaluate.record_details=true \
        evaluate.result_dir=val_results_full \
        "learn.train_dir=$cwd/$ldir" > "$log" 2>&1 &
      ;;
    tabmwp)
      nohup uv run python expt.py run --config-file conf/workflow_incontext.yaml \
        "dataset.split=$split" "dataset.n=$n" \
        "evaluate.expt_name=$exptbase" evaluate.record_details=true \
        evaluate.result_dir=val_results_full "llm.model=$model" \
        "ptools.${iface}.method=learned_code" \
        "ptools.${iface}.learner=workflow_distill" \
        "ptools.${iface}.backoff=true" \
        "learn.train_dir=$cwd/$ldir" > "$log" 2>&1 &
      ;;
  esac
  echo "[$(date)] $label c2_gemini val PID=$!" | tee -a "$log"
}

echo "[$(date)] === gemini vals watcher START ==="
ITER=0
while [ $ITER -lt 200 ]; do
  PENDING_C1=0; PENDING_C2=0; LAUNCHED_THIS_ITER=0
  while IFS=";" read -r label sub iface ldir model split n; do
    [ -z "$label" ] && continue
    cwd="$ROOT/$sub"
    if launch_c1 "$label" "$cwd" "$model" "$split" "$n"; then LAUNCHED_THIS_ITER=$((LAUNCHED_THIS_ITER+1)); fi
    [ ! -f "$cwd/learned_gemini/codedistill_config.yaml" ] && PENDING_C1=$((PENDING_C1+1))
    if [ -n "$iface" ]; then
      if launch_c2 "$label" "$cwd" "$iface" "$ldir" "$model" "$split" "$n"; then LAUNCHED_THIS_ITER=$((LAUNCHED_THIS_ITER+1)); fi
      d=$(ls -dt "$cwd/$ldir"/*"${iface}__workflow_distill" 2>/dev/null | head -1)
      [ -z "$d" ] || [ ! -f "$d/learned.py" ] && PENDING_C2=$((PENDING_C2+1))
    fi
  done <<< "$BENCHES"

  C1_ALIVE=0; C2_ALIVE=0
  pgrep -f "run_class1_gemini_gemini.sh" >/dev/null && C1_ALIVE=1
  pgrep -f "run_class2_gemini_gemini.sh" >/dev/null && C2_ALIVE=1

  if [ "$PENDING_C1" -eq 0 ] && [ "$PENDING_C2" -eq 0 ] && [ "$C1_ALIVE" -eq 0 ] && [ "$C2_ALIVE" -eq 0 ]; then
    echo "[$(date)] all distills done, all vals queued. exiting watcher loop."
    break
  fi
  echo "[$(date)] iter $ITER: launched=$LAUNCHED_THIS_ITER pending_c1=$PENDING_C1 pending_c2=$PENDING_C2 c1master=$C1_ALIVE c2master=$C2_ALIVE"
  sleep 60
  ITER=$((ITER+1))
done

echo "[$(date)] waiting for any in-flight val children"
wait
echo "[$(date)] === gemini vals watcher DONE ==="
