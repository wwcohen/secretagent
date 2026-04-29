from pathlib import Path
from typing import Optional

import typer

from secretagent.learn.baselines import EditedPToolLearner, RoteLearner
from secretagent.learn.codedistill import CodeDistillLearner, EndToEndDistillLearner, distill_all
from secretagent.learn.codedistill_pipeline import codedistill_induced_ptools
from secretagent.learn.examples import extract_examples
from secretagent.learn.ptool_inducer import PtoolInducer
from secretagent.learn.traces import extract_ptp_traces
from secretagent.learn.workflow_distill import WorkflowDistillLearner

app = typer.Typer()
_EXTRA_ARGS = {"allow_extra_args": True, "allow_interspersed_args": False}

@app.callback()
def main():
    """Learn implementations from recorded interface calls."""

@app.command(context_settings=_EXTRA_ARGS)
def rote(
    ctx: typer.Context,
    interface: str = typer.Option(..., help="Interface name to extract, e.g. 'consistent_sports'"),
    latest: int = typer.Option(1, help='Keep latest k dirs per tag; 0 for all'),
    check: Optional[list[str]] = typer.Option(None, help='Config constraint like key=value'),
    learned_dir: str = typer.Option('/tmp/rote_train', help='Directory to store collected data'),
):
    """Learn a rote (lookup-based) implementation from recorded calls."""
    learner = RoteLearner(interface_name=interface, train_dir=learned_dir)
    learner.learn([Path(a) for a in ctx.args], latest=latest, check=check)


@app.command(context_settings=_EXTRA_ARGS)
def codedistill(
    ctx: typer.Context,
    interface: str = typer.Option(..., help="Interface name to distill, e.g. 'sport_for'"),
    latest: int = typer.Option(1, help='Keep latest k dirs per tag; 0 for all'),
    check: Optional[list[str]] = typer.Option(None, help='Config constraint like key=value'),
    learned_dir: str = typer.Option('/tmp/codedistill_train', help='Directory to store learned code'),
    model: str = typer.Option('claude-opus-4-6', help='LLM model for code generation'),
    n_candidates: int = typer.Option(3, help='Number of candidate versions per round'),
    max_rounds: int = typer.Option(3, help='Maximum refinement rounds'),
    only_correct: bool = typer.Option(True, help='Only use rollouts that produced correct final answers'),
):
    """Learn a code-distilled implementation from recorded calls.

    Prompts an LLM to generate Python code that implements the interface,
    using multi-round refinement and ensemble selection.

    Example::

        uv run -m secretagent.cli.learn codedistill --interface sport_for recordings/*
    """
    learner = CodeDistillLearner(
        interface_name=interface,
        train_dir=learned_dir,
        model=model,
        n_candidates=n_candidates,
        max_rounds=max_rounds,
        only_correct=only_correct,
    )
    learner.learn([Path(a) for a in ctx.args], latest=latest, check=check)


@app.command(context_settings=_EXTRA_ARGS)
def edit_ptools(
    ctx: typer.Context,
    interface: str = typer.Option(..., help="Top-level interface name"),
    ptool: list[str] = typer.Option(..., help="Dotted ptool names to edit (repeatable)"),
    pattern: str = typer.Option(..., help="Pattern string to replace in ptool source"),
    replacement: str = typer.Option(..., help="Replacement string"),
    latest: int = typer.Option(1, help='Keep latest k dirs per tag; 0 for all'),
    check: Optional[list[str]] = typer.Option(None, help='Config constraint like key=value'),
    learned_dir: str = typer.Option('/tmp/edit_ptools_train', help='Directory to store collected data'),
):
    """Learn an implementation by editing ptool source code."""
    learner = EditedPToolLearner(
        interface_name=interface,
        train_dir=learned_dir,
        ptool_list=ptool,
        pattern=pattern,
        replacement=replacement,
    )
    learner.learn([Path(a) for a in ctx.args], latest=latest, check=check)


@app.command(context_settings=_EXTRA_ARGS)
def e2e_codedistill(
    ctx: typer.Context,
    interface: str = typer.Option(..., help="Top-level interface name, e.g. 'calendar_scheduling'"),
    dataset_file: str = typer.Option(..., help="Path to dataset JSON file, e.g. 'data/train.json'"),
    output_field: Optional[str] = typer.Option(None, help="Field to extract from expected_output dict, e.g. 'golden_plan'"),
    learned_dir: str = typer.Option('/tmp/e2e_codedistill', help='Directory to store learned code'),
    model: str = typer.Option('claude-opus-4-6', help='LLM model for code generation'),
    n_candidates: int = typer.Option(3, help='Number of candidate versions per round'),
    max_rounds: int = typer.Option(3, help='Maximum refinement rounds'),
):
    """Learn an end-to-end implementation directly from a dataset.

    Instead of learning intermediate interfaces from recorded rollouts,
    this generates a complete solution function from (input, output) pairs
    in a dataset JSON. The LLM is prompted to structure the code as
    parse -> solve -> format.

    Example::

        uv run -m secretagent.cli.learn e2e-codedistill \\
          --interface calendar_scheduling \\
          --dataset-file data/calendar_train.json \\
          --output-field golden_plan \\
          --learned-dir learned
    """
    learner = EndToEndDistillLearner(
        interface_name=interface,
        train_dir=learned_dir,
        dataset_file=dataset_file,
        output_field=output_field,
        model=model,
        n_candidates=n_candidates,
        max_rounds=max_rounds,
    )
    learner.learn_from_dataset()


@app.command(name='workflow-codedistill', context_settings=_EXTRA_ARGS)
def workflow_codedistill(
    ctx: typer.Context,
    interface: str = typer.Option(..., help="Top-level workflow interface name"),
    dataset_file: str = typer.Option(..., help="Path to dataset JSON file with (input, expected_output) cases"),
    tool_module: str = typer.Option(..., help="Dotted module path holding callable tools, e.g. 'ptools_meeting' or 'ptools'"),
    output_field: Optional[str] = typer.Option(None, help="Field in expected_output dict to extract (e.g. 'golden_plan')"),
    tool_filter: Optional[list[str]] = typer.Option(None, help='Restrict to these tool names (repeatable)'),
    reference_file: Optional[list[str]] = typer.Option(None, help='Reference workflow .py files for few-shot inspiration (repeatable)'),
    trace_dir: Optional[list[str]] = typer.Option(None, help='Recording dirs to sample target-benchmark workflow traces from (repeatable)'),
    react_trace_dir: Optional[list[str]] = typer.Option(None, help='ReAct recording dirs to sample tool-call sequences from (repeatable; uses step_info)'),
    cross_trace_dir: Optional[list[str]] = typer.Option(None, help='Other-benchmark recording dirs for cross-domain inspiration (repeatable)'),
    cross_dataset_file: Optional[list[str]] = typer.Option(None, help='Other-benchmark Dataset JSON files to sample cross-domain i/o examples from (repeatable)'),
    conf_file: Optional[str] = typer.Option(None, help="Benchmark conf yaml — when set, simulate ptools are bound during fit-time eval so generated code can actually call LLM tools"),
    trace_top_func: Optional[str] = typer.Option(None, help="Top-level func name in traces (defaults to --interface)"),
    learned_dir: str = typer.Option('/tmp/workflow_distill', help='Directory to store learned code'),
    model: str = typer.Option('claude-opus-4-6', help='LLM model'),
    n_candidates: int = typer.Option(3, help='Candidates per round'),
    max_rounds: int = typer.Option(3, help='Max refinement rounds'),
    holdout_fraction: float = typer.Option(0.2, help='Train/val split fraction for holdout eval'),
    backoff: bool = typer.Option(True, help='When generated fn returns None, fall back to pure-LLM call (NOT to hand-written workflow)'),
    backoff_method: str = typer.Option('simulate', help='Backoff factory method (simulate = zero-shot LLM)'),
):
    """Learn a top-level workflow that calls existing tools (Class 2).

    Generates a workflow function that orchestrates pre-existing pure-Python
    helpers and/or simulate ptools, with cross-benchmark reference workflows
    and sampled tool-call traces injected into the prompt for inspiration.

    Example::

        uv run -m secretagent.cli.learn workflow-codedistill \\
          --interface meeting_planning \\
          --dataset-file data/meeting_train.json --output-field golden_plan \\
          --tool-module ptools_meeting \\
          --reference-file ptools_calendar.py \\
          --trace-dir recordings/20260428.123456.meeting_train_record \\
          --learned-dir learned
    """
    learner = WorkflowDistillLearner(
        interface_name=interface,
        train_dir=learned_dir,
        dataset_file=dataset_file,
        tool_module=tool_module,
        output_field=output_field,
        tool_filter=tool_filter,
        reference_workflow_files=reference_file,
        trace_dirs=trace_dir,
        react_trace_dirs=react_trace_dir,
        cross_trace_dirs=cross_trace_dir,
        cross_dataset_files=cross_dataset_file,
        conf_file=conf_file,
        trace_top_func=trace_top_func,
        model=model,
        n_candidates=n_candidates,
        max_rounds=max_rounds,
        holdout_fraction=holdout_fraction,
        backoff=backoff,
        backoff_method=backoff_method,
    )
    learner.learn_from_dataset()


@app.command(context_settings=_EXTRA_ARGS)
def codedistill_all(
    ctx: typer.Context,
    latest: int = typer.Option(1, help='Keep latest k dirs per tag; 0 for all'),
    check: Optional[list[str]] = typer.Option(None, help='Config constraint like key=value'),
    learned_dir: str = typer.Option('/tmp/codedistill_train', help='Directory to store learned code'),
    model: str = typer.Option('claude-opus-4-6', help='LLM model for code generation'),
    n_candidates: int = typer.Option(3, help='Number of candidate versions per round'),
    max_rounds: int = typer.Option(3, help='Maximum refinement rounds'),
    max_wrong_rate: float = typer.Option(0.05, help='Max fraction of wrong (non-None) answers to enable'),
):
    """Auto-distill all interfaces found in recordings.

    Discovers all interfaces called in recorded rollouts, runs codedistill
    on each. Enables interfaces where the generated code rarely returns
    wrong answers (wrong_rate <= max_wrong_rate). Abstentions (returning
    None) are safe because they backoff to the LLM.

    Example::

        uv run -m secretagent.cli.learn codedistill-all --learned-dir learned recordings/*
    """
    distill_all(
        dirs=[Path(a) for a in ctx.args],
        train_dir=learned_dir,
        max_wrong_rate=max_wrong_rate,
        model=model,
        n_candidates=n_candidates,
        max_rounds=max_rounds,
        latest=latest,
        check=check,
    )


@app.command(context_settings=_EXTRA_ARGS)
def induce_ptools(
    ctx: typer.Context,
    interface: str = typer.Option(..., help="Top-level interface name"),
    task_desc: str = typer.Option(..., help="Natural-language task description"),
    trace_mode: str = typer.Option('react', help="'react' or 'cot'"),
    state_module: Optional[str] = typer.Option(None, help="Module to import state from, e.g. ptools_common"),
    state_expr: Optional[str] = typer.Option(None, help='Expression at call time, e.g. _REACT_STATE["narrative"]'),
    only_correct: bool = typer.Option(False, help='Only use correct rollouts'),
    max_ptools: int = typer.Option(5, help='Max ptools to synthesize'),
    min_count: int = typer.Option(3, help='Min category count'),
    model: Optional[str] = typer.Option(None, help='LLM model'),
    latest: int = typer.Option(1, help='Keep latest k dirs per tag'),
    check: Optional[list[str]] = typer.Option(None, help='Config filter'),
    learned_dir: str = typer.Option('learned', help='Directory to store learned ptools'),
):
    """Induce ptool specs from recorded agent thoughts.

    Pipeline: load thoughts → categorize → merge synonyms → synthesize
    ptool specs. Writes learned_ptools.py + implementation.yaml suitable
    for loading via tool_module='__learned__'.

    Example::

        uv run -m secretagent.cli.learn induce-ptools \\
          --interface react_solve \\
          --task-desc "Murder mystery reasoning" \\
          --trace-mode react --only-correct \\
          --state-module ptools_common \\
          --state-expr '_REACT_STATE["narrative"]' \\
          --learned-dir learned \\
          results/*.react_train_seed42
    """
    learner = PtoolInducer(
        interface_name=interface,
        train_dir=learned_dir,
        task_desc=task_desc,
        trace_mode=trace_mode,
        state_module=state_module,
        state_expr=state_expr,
        only_correct=only_correct,
        max_ptools=max_ptools,
        min_count=min_count,
        model=model,
    )
    learner.learn([Path(a) for a in ctx.args], latest=latest, check=check)


@app.command(context_settings=_EXTRA_ARGS, name='codedistill-induced-ptools')
def codedistill_induced_ptools_cmd(
    ctx: typer.Context,
    interface: str = typer.Option(..., help="Top-level interface name (e.g. 'answer_question')"),
    task_desc: str = typer.Option(..., help="Natural-language task description"),
    expt_cmd: str = typer.Option(..., help="Base expt.py command to re-run benchmark, e.g. 'uv run python expt.py run --config-file conf/murder.yaml dataset.split=murder_mysteries_train dataset.n=50'"),
    trace_mode: str = typer.Option('react', help="'react' or 'cot'"),
    state_module: Optional[str] = typer.Option(None, help="Module to import state from"),
    state_expr: Optional[str] = typer.Option(None, help='Expression at call time'),
    only_correct: bool = typer.Option(False, help='Only use correct rollouts for induction'),
    max_ptools: int = typer.Option(5, help='Max induced ptools'),
    min_count: int = typer.Option(3, help='Min category count to synthesize'),
    induce_model: Optional[str] = typer.Option(None, help='LLM for PtoolInducer'),
    learned_dir: str = typer.Option('learned', help='Directory for all pipeline outputs'),
    max_wrong_rate: float = typer.Option(0.10, help='Max wrong_rate to enable a ptool'),
    model: str = typer.Option('claude-opus-4-6', help='LLM for codedistill'),
    n_candidates: int = typer.Option(3, help='Codedistill candidates per round'),
    max_rounds: int = typer.Option(3, help='Codedistill max refinement rounds'),
    latest: int = typer.Option(1, help='Keep latest k source dirs per tag'),
    check: Optional[list[str]] = typer.Option(None, help='Config filter'),
    cwd: Optional[str] = typer.Option(None, help='Working directory for the Stage B subprocess (default: current)'),
    skip_stage_b: bool = typer.Option(False, help='Skip Stage B (useful if you already re-recorded)'),
):
    """Induce ptools from ReAct traces and codedistill each one.

    Four-stage pipeline:
      A) PtoolInducer on existing ReAct/CoT rollouts
      B) Re-record benchmark with induced ptools (subprocess to expt.py)
      C) codedistill-all on new recording
      D) Merge configs into induced_codedistill_config.yaml

    Example::

        uv run -m secretagent.cli.learn codedistill-induced-ptools \\
          --interface answer_question \\
          --task-desc "Solve a murder mystery from a narrative" \\
          --trace-mode react --only-correct \\
          --state-module ptools_common \\
          --state-expr '_REACT_STATE["narrative"]' \\
          --learned-dir learned_induced \\
          --expt-cmd "uv run python expt.py run --config-file conf/murder.yaml dataset.split=murder_mysteries_train dataset.n=50" \\
          --cwd benchmarks/musr \\
          benchmarks/musr/results/*murder_react_train*
    """
    codedistill_induced_ptools(
        dirs=[Path(a) for a in ctx.args],
        interface_name=interface,
        task_desc=task_desc,
        expt_cmd=expt_cmd,
        trace_mode=trace_mode,
        state_module=state_module,
        state_expr=state_expr,
        only_correct=only_correct,
        max_ptools=max_ptools,
        min_count=min_count,
        induce_model=induce_model,
        learned_dir=learned_dir,
        max_wrong_rate=max_wrong_rate,
        codedistill_model=model,
        n_candidates=n_candidates,
        max_rounds=max_rounds,
        latest=latest,
        check=check,
        cwd=cwd,
        skip_stage_b=skip_stage_b,
    )


@app.command(context_settings={"allow_extra_args": True, "allow_interspersed_args": True})
def examples(
    ctx: typer.Context,
    output: str = typer.Option('examples.json', help='Output JSON file path'),
    interface: Optional[list[str]] = typer.Option(None, help='Interface names to extract (repeatable)'),
    only_correct: bool = typer.Option(True, help='Only include examples from correct predictions'),
    max_per_interface: Optional[int] = typer.Option(None, help='Max examples per interface'),
    latest: int = typer.Option(1, help='Keep latest k dirs per tag; 0 for all'),
    check: Optional[list[str]] = typer.Option(None, help='Config constraint like key=value'),
):
    """Extract in-context examples from recorded rollouts.

    Collects successful input/output traces and saves them in the JSON
    format expected by SimulateFactory's example_file parameter.

    Example::

        uv run -m secretagent.cli.learn examples results/* --output examples.json
    """
    extract_examples(
        dirs=[Path(a) for a in ctx.args],
        output_file=output,
        interfaces=interface,
        only_correct=only_correct,
        max_per_interface=max_per_interface,
        latest=latest,
        check=check,
    )


@app.command(context_settings={"allow_extra_args": True, "allow_interspersed_args": True})
def traces(
    ctx: typer.Context,
    output: str = typer.Option('traces.txt', help='Output trace file path'),
    only_correct: bool = typer.Option(True, help='Only include traces from correct predictions'),
    max_traces: int = typer.Option(3, help='Max number of traces to include'),
    max_output_chars: int = typer.Option(200, help='Max chars per step output'),
    latest: int = typer.Option(1, help='Keep latest k dirs per tag; 0 for all'),
    check: Optional[list[str]] = typer.Option(None, help='Config constraint like key=value'),
):
    """Extract PTP (Program Trace Prompting) traces from recorded rollouts.

    Formats execution traces as doctest-style chains with abbreviated
    inputs. Use with method=ptp and trace_file=<output>.

    Example::

        uv run -m secretagent.cli.learn traces results/* --output traces.txt
        # Then use: ptools.answer_question.method=ptp ptools.answer_question.trace_file=traces.txt
    """
    extract_ptp_traces(
        dirs=[Path(a) for a in ctx.args],
        output_file=output,
        only_correct=only_correct,
        max_traces=max_traces,
        max_output_chars=max_output_chars,
        latest=latest,
        check=check,
    )


if __name__ == '__main__':
    app()
