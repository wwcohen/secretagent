#!/bin/bash
# Run all strategy variants per benchmark with consistent minibatch configs.
# Model: gemini/gemini-3.1-flash-lite-preview
# Each benchmark uses the same seed, same n, same split across all strategies.

set -e
cd /mnt/d/Aditya/CMU/Research/William_Cohen_Group/Codebase/secretagent
source .env

MODEL="gemini/gemini-3.1-flash-lite-preview"
COMMON="llm.model=$MODEL evaluate.max_workers=1"

run_bbh() {
    local dir=$1 iface=$2 workflow_fn=$3 unstructured_fn=$4 n=$5
    local base="benchmarks/bbh/$dir"
    local ds="dataset.split=valid dataset.shuffle_seed=137 dataset.n=$n"

    echo "===== $dir: simulate (n=$n) ====="
    uv run python -m secretagent.cli.expt run --interface ptools.$iface \
        $ds ptools.$iface.method=simulate \
        evaluate.expt_name=simulate $COMMON \
        2>&1 | tail -3
    echo ""

    echo "===== $dir: unstructured (n=$n) ====="
    uv run python -m secretagent.cli.expt run --interface ptools.$iface \
        $ds ptools.$iface.method=direct ptools.$iface.fn=ptools.$unstructured_fn \
        evaluate.expt_name=unstructured $COMMON \
        2>&1 | tail -3
    echo ""

    echo "===== $dir: workflow (n=$n) ====="
    uv run python -m secretagent.cli.expt run --interface ptools.$iface \
        $ds ptools.$iface.method=direct ptools.$iface.fn=ptools.$workflow_fn \
        evaluate.expt_name=workflow $COMMON \
        2>&1 | tail -3
    echo ""
}

run_musr() {
    local domain=$1 split=$2 n=$3
    local ds="dataset.split=${split}_val dataset.shuffle_seed=42 dataset.n=$n"

    echo "===== musr_$domain: simulate (n=$n) ====="
    (cd benchmarks/musr && uv run python expt.py run \
        --config-file conf/${domain}_unstructured_baseline.yaml \
        $ds evaluate.expt_name=simulate $COMMON) 2>&1 | tail -3
    echo ""

    echo "===== musr_$domain: workflow (n=$n) ====="
    (cd benchmarks/musr && uv run python expt.py run \
        --config-file conf/${domain}_workflow.yaml \
        $ds evaluate.expt_name=workflow $COMMON) 2>&1 | tail -3
    echo ""

    echo "===== musr_$domain: pot (n=$n) ====="
    (cd benchmarks/musr && uv run python expt.py run \
        --config-file conf/${domain}_pot.yaml \
        $ds evaluate.expt_name=pot $COMMON) 2>&1 | tail -3
    echo ""
}

run_natural_plan() {
    local task=$1 iface=$2 workflow_fn=$3 mod=$4 n=$5
    local ds="dataset.partition=valid dataset.shuffle_seed=42 dataset.n=$n"

    echo "===== natural_plan_$task: simulate (n=$n) ====="
    (cd benchmarks/natural_plan && uv run python expt.py run \
        --config-file conf/${task}.yaml \
        $ds ptools.$iface.method=simulate \
        evaluate.expt_name=simulate $COMMON) 2>&1 | tail -3
    echo ""

    echo "===== natural_plan_$task: workflow (n=$n) ====="
    (cd benchmarks/natural_plan && uv run python expt.py run \
        --config-file conf/${task}.yaml \
        $ds ptools.$iface.method=direct ptools.$iface.fn=${mod}.${workflow_fn} \
        evaluate.expt_name=workflow $COMMON) 2>&1 | tail -3
    echo ""
}

run_rulearena() {
    local domain=$1 n=$2
    local ds="dataset.split=valid dataset.domain=$domain dataset.shuffle_seed=137 dataset.n=$n"

    echo "===== rulearena_$domain: simulate (n=$n) ====="
    (cd benchmarks/rulearena && uv run python expt.py run \
        $ds ptools.compute_rulearena_answer.method=simulate \
        evaluate.expt_name=simulate $COMMON) 2>&1 | tail -3
    echo ""

    echo "===== rulearena_$domain: workflow (n=$n) ====="
    (cd benchmarks/rulearena && uv run python expt.py run \
        $ds ptools.compute_rulearena_answer.method=direct \
        ptools.compute_rulearena_answer.fn=ptools.l1_extract_workflow \
        evaluate.expt_name=workflow $COMMON) 2>&1 | tail -3
    echo ""
}

echo "########################################"
echo "# BBH BENCHMARKS"
echo "########################################"

(cd benchmarks/bbh/sports_understanding && \
    run_bbh sports_understanding are_sports_in_sentence_consistent \
    sports_understanding_workflow zeroshot_unstructured_workflow 20)

(cd benchmarks/bbh/geometric_shapes && \
    run_bbh geometric_shapes identify_shape \
    geometric_shapes_workflow zeroshot_unstructured_workflow 20)

(cd benchmarks/bbh/penguins_in_a_table && \
    run_bbh penguins_in_a_table answer_penguin_question \
    penguins_workflow zeroshot_unstructured_workflow 20)

echo "########################################"
echo "# MUSR BENCHMARKS"
echo "########################################"

run_musr murder murder_mysteries 10
run_musr object object_placements 10
run_musr team team_allocation 10

echo "########################################"
echo "# NATURAL PLAN BENCHMARKS"
echo "########################################"

run_natural_plan calendar calendar_scheduling calendar_workflow ptools_calendar 10
run_natural_plan meeting meeting_planning meeting_workflow ptools_meeting 10
run_natural_plan trip trip_planning trip_workflow ptools_trip 10

echo "########################################"
echo "# RULEARENA BENCHMARKS"
echo "########################################"

run_rulearena airline 10
run_rulearena nba 10
run_rulearena tax 10

echo "########################################"
echo "# MEDCALC"
echo "########################################"

echo "===== medcalc: baseline (n=110, stratified 2/calc) ====="
(cd benchmarks/medcalc && uv run python expt.py run \
    --config-file conf/baseline.yaml \
    dataset.n=110 evaluate.expt_name=baseline $COMMON) 2>&1 | tail -5
echo ""

echo "===== medcalc: simulate (n=110, stratified 2/calc) ====="
(cd benchmarks/medcalc && uv run python expt.py run \
    --config-file conf/simulate.yaml \
    dataset.n=110 evaluate.expt_name=simulate $COMMON) 2>&1 | tail -5
echo ""

echo "===== medcalc: pot (n=110, stratified 2/calc) ====="
(cd benchmarks/medcalc && uv run python expt.py run \
    --config-file conf/pot.yaml \
    dataset.n=110 evaluate.expt_name=pot $COMMON) 2>&1 | tail -5
echo ""

echo "===== medcalc: workflow (n=110, stratified 2/calc) ====="
(cd benchmarks/medcalc && uv run python expt.py run \
    --config-file conf/workflow.yaml \
    dataset.n=110 evaluate.expt_name=workflow $COMMON) 2>&1 | tail -5
echo ""

echo "########################################"
echo "# TABMWP"
echo "########################################"

echo "===== tabmwp: simulate (n=20) ====="
(cd benchmarks/tabmwp && uv run python expt.py run \
    --config-file conf/conf.yaml \
    dataset.split=dev1k dataset.shuffle_seed=42 dataset.n=20 \
    ptools.tabmwp_solve.method=simulate \
    evaluate.expt_name=simulate $COMMON) 2>&1 | tail -3
echo ""

echo "===== tabmwp: workflow_incontext (n=20) ====="
(cd benchmarks/tabmwp && uv run python expt.py run \
    --config-file conf/workflow_incontext.yaml \
    dataset.split=dev1k dataset.shuffle_seed=42 dataset.n=20 \
    evaluate.expt_name=workflow $COMMON) 2>&1 | tail -3
echo ""

echo "===== tabmwp: pot (n=20) ====="
(cd benchmarks/tabmwp && uv run python expt.py run \
    --config-file conf/pot.yaml \
    dataset.split=dev1k dataset.shuffle_seed=42 dataset.n=20 \
    evaluate.expt_name=pot $COMMON) 2>&1 | tail -3
echo ""

echo "########################################"
echo "# DONE"
echo "########################################"
