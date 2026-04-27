"""Pipeline improvement loop: chain transforms to iteratively improve a pipeline."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Sequence

from pydantic import BaseModel

from secretagent import config
from secretagent.orchestrate.catalog import PtoolCatalog
from secretagent.orchestrate.pipeline import (
    Pipeline,
)
from secretagent.orchestrate.profiler import PipelineProfile, profile_from_results

if TYPE_CHECKING:
    from secretagent.core import Interface
    from secretagent.dataset import Dataset
    from secretagent.evaluate import Evaluator
    from secretagent.orchestrate.transforms.base import PipelineTransform

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Transform registry (mirrors _FACTORIES in core.py)
# ---------------------------------------------------------------------------

_TRANSFORMS: dict[str, PipelineTransform] = {}


def register_transform(name: str, transform: PipelineTransform) -> None:
    _TRANSFORMS[name] = transform


def get_transform(name: str) -> PipelineTransform:
    if name not in _TRANSFORMS:
        raise KeyError(f'unknown transform: {name!r} (registered: {list(_TRANSFORMS)})')
    return _TRANSFORMS[name]


# ---------------------------------------------------------------------------
# Improvement report
# ---------------------------------------------------------------------------

class ImprovementReport(BaseModel):
    before_profile: PipelineProfile
    after_profile: PipelineProfile | None = None
    iterations: list[dict] = []
    improved: bool = False
    best_accuracy: float = 0.0


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def improve_pipeline(
    pipeline: Pipeline,
    result_dirs: Sequence[str | Path],
    catalog: PtoolCatalog,
    transforms: list[PipelineTransform] | None = None,
    max_iterations: int | None = None,
    run_eval_fn: Callable[[], Sequence[str | Path]] | None = None,
    target_accuracy: float | None = None,
) -> ImprovementReport:
    """Run improvement transforms on a pipeline using profiling data.

    Args:
        pipeline: the current pipeline to improve
        result_dirs: directories with results.jsonl for profiling
        catalog: ptool catalog available to the pipeline
        transforms: explicit list of transforms (default: from config or registry)
        max_iterations: how many improvement rounds (default: from config or 1)
        run_eval_fn: callback that re-runs the experiment and returns new
            result directories.  If provided, the loop re-profiles after
            each iteration and keeps improvements (rolls back regressions).
        target_accuracy: stop early when this accuracy is reached.
    """
    if transforms is None:
        transform_names = config.get('orchestrate.improve.transforms', [])
        if transform_names:
            transforms = [get_transform(n) for n in transform_names]
        else:
            transforms = list(_TRANSFORMS.values())

    if max_iterations is None:
        max_iterations = config.get('orchestrate.improve.max_iterations', 1)

    before = profile_from_results(result_dirs, pipeline_source=pipeline.source)
    iterations: list[dict] = []

    log.info('improvement loop starting: accuracy=%.1f%%, %d cases',
             before.accuracy * 100, before.n_cases)
    from secretagent.orchestrate.transforms.base import format_profiling_summary
    print('\n[improve] === Initial Profile ===')
    print(format_profiling_summary(before))

    profile = before
    best_accuracy = profile.accuracy
    current_result_dirs = list(result_dirs)

    for i in range(max_iterations):
        print(f'\n[improve] === Iteration {i + 1}/{max_iterations} ===')
        proposals = []
        results = []

        for t in transforms:
            if not t.should_apply(profile):
                log.debug('transform %s: skipped (should_apply=False)', t.name)
                continue
            try:
                proposal = t.propose(profile, catalog)
                proposals.append(proposal.model_dump())
            except NotImplementedError:
                log.debug('transform %s: propose not implemented', t.name)
                continue
            try:
                result = t.apply(proposal, pipeline, catalog)
                results.append(result.model_dump())
                if result.success:
                    print(f'[improve] {t.name}: {result.message}')
                    # Apply config overrides (e.g. model downgrades)
                    if result.new_config:
                        dotlist = [f'{k}={v}' for k, v in result.new_config.items()]
                        config.configure(dotlist=dotlist)
                        log.info('applied config overrides: %s', dotlist)
            except NotImplementedError:
                log.debug('transform %s: apply not implemented', t.name)
                continue

        iterations.append({'proposals': proposals, 'results': results})

        # Re-evaluate if we have a callback
        if run_eval_fn and any(r.get('success') for r in results):
            print('[improve] re-evaluating after transforms...')
            try:
                new_dirs = run_eval_fn()
                new_profile = profile_from_results(
                    new_dirs, pipeline_source=pipeline.source,
                )
                print(f'[improve] accuracy: {profile.accuracy:.1%} -> {new_profile.accuracy:.1%}')
                print(format_profiling_summary(new_profile))

                if new_profile.accuracy >= profile.accuracy:
                    current_result_dirs = list(new_dirs)
                    profile = new_profile
                    if new_profile.accuracy > best_accuracy:
                        best_accuracy = new_profile.accuracy
                    print(f'[improve] kept improvements (accuracy={new_profile.accuracy:.1%})')
                else:
                    print('[improve] regression detected, keeping previous state')
                    # Note: ptool state was already modified by transforms.
                    # The caller is responsible for rollback if needed.
            except Exception as e:
                log.warning('re-evaluation failed: %s', e)
                print(f'[improve] re-evaluation failed: {e}')

        # Early exit if target reached
        if target_accuracy is not None and best_accuracy >= target_accuracy:
            print(f'[improve] target accuracy {target_accuracy:.1%} reached!')
            break

    after = profile_from_results(
        current_result_dirs, pipeline_source=pipeline.source,
    ) if run_eval_fn else None

    return ImprovementReport(
        before_profile=before,
        after_profile=after,
        iterations=iterations,
        improved=best_accuracy > before.accuracy,
        best_accuracy=best_accuracy,
    )


# ---------------------------------------------------------------------------
# Supervisor-driven improvement
# ---------------------------------------------------------------------------

class IterationRecord(BaseModel):
    iteration: int
    train_accuracy: float
    train_cost: float
    train_failures: int = 0
    train_timeouts: int = 0
    eval_accuracy: float | None = None
    eval_cost: float | None = None
    eval_failures: int | None = None
    eval_timeouts: int | None = None
    supervisor_cost: float = 0.0
    reasoning: str = ''
    kept: bool = False
    code_snapshot: str = ''
    config_overrides: list[str] = []
    train_result_dir: str | None = None
    eval_result_dir: str | None = None
    config_before_path: str | None = None
    config_after_path: str | None = None


class SupervisorReport(BaseModel):
    iterations: list[IterationRecord] = []
    best_iteration: int = 0
    best_train_accuracy: float = 0.0
    final_eval_accuracy: float | None = None
    total_supervisor_cost: float = 0.0
    best_code: str = ''
    best_config_overrides: list[str] = []
    config_snapshot_path: str | None = None


def _format_failure_traces(
    result_dir: Path,
    dataset: Dataset | None = None,
    max_cases: int = 999,
    max_input_chars: int = 2000,
    max_output_chars: int = 1000,
) -> str:
    """Read results.jsonl and format failure cases with full context.

    If dataset is provided, looks up input_args (patient_note, question)
    by case_name so the supervisor can see what the LLM was asked.
    """
    jsonl_path = Path(result_dir) / 'results.jsonl'
    if not jsonl_path.exists():
        return 'No results.jsonl found.'

    # Build case lookup from dataset
    case_lookup: dict[str, Any] = {}
    if dataset is not None:
        for case in dataset.cases:
            case_lookup[case.name] = case

    failures = []
    with open(jsonl_path) as f:
        for line in f:
            record = json.loads(line)
            if not record.get('correct'):
                failures.append(record)

    if not failures:
        return 'All cases passed!'

    # Select diverse failures: group by category/calculator, pick from each
    cat_groups: dict[str, list[dict]] = {}
    for rec in failures:
        key = rec.get('calculator_name', rec.get('category', 'unknown'))
        cat_groups.setdefault(key, []).append(rec)

    selected: list[dict] = []
    # Round-robin from each category
    for _key, recs in sorted(cat_groups.items(), key=lambda kv: -len(kv[1])):
        if len(selected) >= max_cases:
            break
        selected.append(recs[0])

    # Fill remaining from largest groups
    if len(selected) < max_cases:
        used = {r.get('case_name') for r in selected}
        for _key, recs in sorted(cat_groups.items(), key=lambda kv: -len(kv[1])):
            for rec in recs[1:]:
                if rec.get('case_name') not in used and len(selected) < max_cases:
                    selected.append(rec)
                    used.add(rec.get('case_name'))

    lines = [f'Total failures: {len(failures)} / showing {len(selected)}:\n']
    # Also show failure counts by category
    lines.append('Failure counts by category:')
    for key, recs in sorted(cat_groups.items(), key=lambda kv: -len(kv[1])):
        lines.append(f'  {key}: {len(recs)} failures')
    lines.append('')

    for rec in selected:
        meta_parts = []
        for mk in ('calculator_name', 'category', 'output_type'):
            if mk in rec:
                meta_parts.append(f'{mk}={rec[mk]}')
        meta_str = f' ({", ".join(meta_parts)})' if meta_parts else ''
        lines.append(f'--- Case {rec.get("case_name", "?")}:{meta_str} ---')

        # Show REAL input data from dataset
        case_name = rec.get('case_name', '')
        case = case_lookup.get(case_name)
        if case and case.input_args:
            for i, arg in enumerate(case.input_args):
                arg_str = str(arg)[:max_input_chars]
                lines.append(f'  Input arg {i}: {arg_str}')
        else:
            lines.append('  Input: (not available)')

        # Show rollout steps (LLM call traces)
        rollout = rec.get('rollout', [])
        if rollout:
            lines.append(f'  Execution trace ({len(rollout)} LLM calls):')
            for step in rollout:
                func = step.get('func', '?')
                args_str = str(step.get('args', ''))[:200]
                output = str(step.get('output', ''))[:max_output_chars]
                cost = step.get('stats', {}).get('cost', 0)
                lines.append(f'    {func}({args_str})')
                lines.append(f'      -> {output} [${cost:.4f}]')
        else:
            lines.append('  Execution trace: (no rollout recorded)')

        pred = rec.get('predicted_output', '?')
        exp = rec.get('expected_output', '?')
        abs_err = rec.get('absolute_error', '')
        err_str = f', absolute_error={abs_err}' if abs_err else ''
        lines.append(f'  RESULT: predicted={pred}, expected={exp}{err_str}')
        lines.append('')

    return '\n'.join(lines)


def _format_iteration_history(iterations: list[IterationRecord]) -> str:
    """Full history with reasoning for all iterations.

    Every iteration shows: train/eval accuracy, kept/rolled back, and
    a concise summary of what was tried so the supervisor doesn't repeat
    failed approaches.
    """
    if not iterations:
        return ''
    lines = []
    for rec in iterations:
        status = 'KEPT' if rec.kept else 'ROLLED BACK'
        eval_str = f', eval={rec.eval_accuracy:.1%}' if rec.eval_accuracy is not None else ''
        lines.append(
            f'Iter {rec.iteration}: train={rec.train_accuracy:.1%}{eval_str} — {status}'
        )
        if rec.reasoning:
            # Show full reasoning so supervisor knows exactly what was tried
            lines.append(f'  What was tried: {rec.reasoning}')
        if not rec.kept and rec.iteration > 0:
            lines.append('  ⚠ This change HURT accuracy. Do NOT retry this approach.')
    return '\n'.join(lines)



def _count_failures(result_dir: Path) -> tuple[int, int]:
    """Count failures and timeouts from results.jsonl."""
    jsonl = result_dir / 'results.jsonl'
    if not jsonl.exists():
        return 0, 0
    failures = 0
    timeouts = 0
    with open(jsonl) as f:
        for line in f:
            rec = json.loads(line)
            if not rec.get('correct'):
                failures += 1
            if rec.get('_timeout'):
                timeouts += 1
    return failures, timeouts


def _save_running_report(output_dir, iterations, best_accuracy,
                         best_source, best_config_overrides,
                         total_supervisor_cost):
    """Save report.json after each iteration so progress survives interruption."""
    best_iter = max(
        (r for r in iterations if r.kept),
        key=lambda r: r.train_accuracy,
        default=iterations[0],
    )
    report = SupervisorReport(
        iterations=iterations,
        best_iteration=best_iter.iteration,
        best_train_accuracy=best_accuracy,
        total_supervisor_cost=total_supervisor_cost,
        best_code=f'# See ptools_evolved.py ({len(best_source)} chars)',
        best_config_overrides=best_config_overrides,
        config_snapshot_path='config.yaml',
    )
    config.save(output_dir / 'config.yaml')
    (output_dir / 'report.json').write_text(report.model_dump_json(indent=2))
    (output_dir / 'ptools_evolved.py').write_text(best_source)


def improve_with_supervisor(
    entry_interface: Interface,
    tool_interfaces: list[Interface],
    catalog: PtoolCatalog,
    evaluator: Evaluator,
    train_dataset: Dataset,
    eval_dataset: Dataset | None = None,
    supervisor_model: str = 'gemini/gemini-3.1-pro-preview',
    max_iterations: int = 10,
    target_accuracy: float | None = None,
    custom_instructions: str = '',
    model_choices: str = '',
    output_dir: Path | None = None,
    ptools_module: Any = None,
    resume_iterations: list[IterationRecord] | None = None,
    resume_best_accuracy: float | None = None,
    resume_best_eval_accuracy: float | None = None,
    resume_supervisor_cost: float = 0.0,
    on_iteration_complete: Callable[[Path], None] | None = None,
) -> SupervisorReport:
    """Iteratively improve a pipeline using a supervisor LLM.

    The supervisor sees the FULL ptools source file and can modify anything:
    workflow code, utility functions, docstrings, extraction logic, etc.
    Changes are written to ptools_evolved.py and the module is reloaded.

    Hill climbing: keep improvements, rollback regressions.

    When resume_iterations is provided, skip the initial evaluation and
    continue the improvement loop from where the previous run left off.
    """
    from secretagent.orchestrate.composer import recompose
    from secretagent.orchestrate.transforms.base import format_profiling_summary
    from secretagent.core import implement_via_config

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / 'iterations').mkdir(exist_ok=True)
        config.save(output_dir / 'config.yaml')

    # --- Setup evolved ptools file ---
    # Derive evolved path from the module's actual file, supporting any
    # module name (ptools.py, ptools_murder.py, etc.)
    evolved_path = Path(ptools_module.__file__)
    benchmark_dir = evolved_path.parent

    # If loaded from base (not evolved), create evolved copy. Timestamped
    # scratch modules are already isolated from the benchmark source tree and
    # should be edited in place.
    if '_evolved' not in evolved_path.stem and not evolved_path.stem.endswith('_scratch'):
        base_path = evolved_path
        evolved_path = benchmark_dir / f'{evolved_path.stem}_evolved.py'
        if not evolved_path.exists():
            evolved_path.write_text(base_path.read_text())
            print(f'[supervisor] created {evolved_path.name} from {base_path.name}')

    # IMPORTANT: importlib.reload() does NOT honor spec_from_file_location.
    # It re-imports using sys.path, which finds the base file instead of the
    # evolved file. We must use spec.loader.exec_module() instead.
    def _reload_evolved_module():
        """Re-execute the evolved ptools file into the existing module object."""
        import importlib.util as ilu
        spec = ilu.spec_from_file_location(ptools_module.__name__, str(evolved_path))
        spec.loader.exec_module(ptools_module)

    print(f'[supervisor] evolved ptools: {evolved_path.name}')

    current_source = evolved_path.read_text()
    entry_point_name = entry_interface.name

    iterations: list[IterationRecord] = []
    best_source = current_source
    best_config_overrides: list[str] = []
    best_eval_accuracy: float | None = None
    total_supervisor_cost = 0.0

    # --- Resume from previous run or do initial evaluation ---
    resuming = resume_iterations is not None and len(resume_iterations) > 0

    if resuming:
        # Carry forward state from the previous run
        iterations = list(resume_iterations)
        best_accuracy = resume_best_accuracy if resume_best_accuracy is not None else max(
            r.train_accuracy for r in iterations if r.kept
        )
        best_eval_accuracy = resume_best_eval_accuracy
        total_supervisor_cost = resume_supervisor_cost
        start_iter = iterations[-1].iteration + 1

        # The current source on disk IS our best source (loaded from prev run)
        best_source = current_source

        # We need a profile for the improvement loop — do a quick eval
        print(f'\n[supervisor] === Resuming from iteration {start_iter - 1} ===')
        print(f'[supervisor] previous best accuracy: {best_accuracy:.1%}')
        if best_eval_accuracy is not None:
            print(f'[supervisor] previous best eval accuracy: {best_eval_accuracy:.1%}')
        print(f'[supervisor] accumulated supervisor cost: ${total_supervisor_cost:.4f}')
        print('[supervisor] re-evaluating current code to get fresh profile...')

        with config.configuration(evaluate=dict(
            expt_name='rc_resume_baseline', record_details=True,
        )):
            csv_path = evaluator.evaluate(train_dataset, entry_interface)
        result_dir = csv_path.parent
        profile = profile_from_results([result_dir])
        best_result_dir = result_dir

        print(f'[supervisor] current accuracy: {profile.accuracy:.1%}, '
              f'avg_cost=${profile.avg_cost:.4f}')
        print(format_profiling_summary(profile))

    else:
        start_iter = 1

        # --- Initial evaluation ---
        print('\n[supervisor] === Initial Evaluation ===')
        with config.configuration(evaluate=dict(
            expt_name='rc_iter0', record_details=True,
        )):
            csv_path = evaluator.evaluate(train_dataset, entry_interface)
        result_dir = csv_path.parent
        profile = profile_from_results([result_dir])
        best_accuracy = profile.accuracy
        best_result_dir = result_dir

        # Eval baseline on held-out set
        baseline_eval_acc = None
        baseline_eval_cost = None
        if eval_dataset is not None:
            import pandas as pd
            print('[supervisor] evaluating baseline on held-out set...')
            with config.configuration(evaluate=dict(
                expt_name='rc_iter0_eval', record_details=False,
            )):
                try:
                    eval_csv = evaluator.evaluate(eval_dataset, entry_interface)
                    eval_df = pd.read_csv(eval_csv)
                    baseline_eval_acc = float(eval_df['correct'].mean())
                    baseline_eval_cost = float(eval_df.get('cost', pd.Series([0])).mean())
                    print(f'[supervisor] baseline eval accuracy: {baseline_eval_acc:.1%}')
                except Exception as e:
                    print(f'[supervisor] baseline eval failed: {e}')

        best_eval_accuracy = baseline_eval_acc

        train_fail, train_to = _count_failures(result_dir)
        eval_fail, eval_to = (None, None)
        if baseline_eval_acc is not None:
            eval_fail, eval_to = _count_failures(eval_csv.parent) if eval_csv else (None, None)

        rec0 = IterationRecord(
            iteration=0, train_accuracy=profile.accuracy,
            train_cost=profile.avg_cost, kept=True,
            train_failures=train_fail, train_timeouts=train_to,
            eval_accuracy=baseline_eval_acc, eval_cost=baseline_eval_cost,
            eval_failures=eval_fail, eval_timeouts=eval_to,
            code_snapshot=f'# ptools_evolved.py ({len(current_source)} chars)',
            train_result_dir=str(result_dir),
            eval_result_dir=str(eval_csv.parent) if baseline_eval_acc is not None else None,
        )
        iterations.append(rec0)

        print(f'[supervisor] baseline: accuracy={profile.accuracy:.1%}, '
              f'avg_cost=${profile.avg_cost:.4f}')
        if baseline_eval_acc is not None:
            print(f'[supervisor] baseline eval: {baseline_eval_acc:.1%}')
        print(format_profiling_summary(profile))

        if output_dir:
            iter_dir = output_dir / 'iterations' / 'iter_000_baseline'
            iter_dir.mkdir(exist_ok=True)
            (iter_dir / 'ptools_evolved.py').write_text(current_source)
            config.save(iter_dir / 'config.yaml')
            (iter_dir / 'result_dirs.json').write_text(json.dumps({
                'train_result_dir': str(result_dir),
                'eval_result_dir': str(eval_csv.parent) if baseline_eval_acc is not None else None,
            }, indent=2))

    # --- Improvement loop ---
    no_improve_count = 0
    end_iter = start_iter + max_iterations

    for i in range(start_iter, end_iter):
        print(f'\n[supervisor] === Iteration {i}/{end_iter - 1} ===')

        # 1. Build context
        prof_summary = format_profiling_summary(profile)
        # Add call analysis
        called = [n for n, pp in profile.ptool_profiles.items()
                  if pp.calls_per_case > 0.01]
        if called:
            prof_summary += f'\n\nPtools called via LLM: {called}'
        # Add eval accuracy so supervisor can see generalization
        if best_eval_accuracy is not None:
            prof_summary += (
                f'\n\nHeld-out eval accuracy: {best_eval_accuracy:.1%}'
                f' (train: {profile.accuracy:.1%})'
                f'\nA large train-eval gap means your changes are OVERFITTING.'
                f' Prefer changes that generalize to unseen cases.'
            )

        failure_traces = _format_failure_traces(
            best_result_dir, dataset=train_dataset,
        )
        history_text = _format_iteration_history(iterations)

        # 2. Call supervisor with FULL ptools source
        print('[supervisor] calling supervisor LLM...')
        try:
            new_source, reasoning, cfg_overrides, sup_stats = recompose(
                ptools_source=current_source,
                profiling_summary=prof_summary,
                failure_traces=failure_traces,
                iteration_history=history_text,
                custom_instructions=custom_instructions,
                model_choices=model_choices,
                model=supervisor_model,
            )
        except Exception as e:
            import traceback
            err = f'{type(e).__name__}: {e}'
            print(f'[supervisor] supervisor LLM failed: {err}')
            iterations.append(IterationRecord(
                iteration=i,
                train_accuracy=profile.accuracy,
                train_cost=profile.avg_cost,
                supervisor_cost=0.0,
                reasoning=f'Supervisor call failed: {err}',
                kept=False,
            ))
            no_improve_count += 1
            if output_dir:
                iter_dir = output_dir / 'iterations' / f'iter_{i:03d}'
                iter_dir.mkdir(exist_ok=True)
                (iter_dir / 'supervisor_error.txt').write_text(
                    traceback.format_exc()
                )
                (iter_dir / 'profiling_summary.txt').write_text(prof_summary)
                (iter_dir / 'failure_traces.txt').write_text(failure_traces)
                (iter_dir / 'iteration_history.txt').write_text(
                    history_text or 'No previous iterations.')
                _save_running_report(output_dir, iterations, best_accuracy,
                                     best_source, best_config_overrides,
                                     total_supervisor_cost)
                if on_iteration_complete:
                    on_iteration_complete(output_dir)
            if no_improve_count >= 5:
                print('[supervisor] 5 consecutive supervisor failures/no-changes, stopping')
                break
            continue
        sup_cost = sup_stats.get('cost', 0.0)
        total_supervisor_cost += sup_cost
        print(f'[supervisor] supervisor cost: ${sup_cost:.4f}')
        if reasoning:
            print(f'[supervisor] reasoning: {reasoning[:300]}')

        # Save iteration artifacts
        if output_dir:
            iter_dir = output_dir / 'iterations' / f'iter_{i:03d}'
            iter_dir.mkdir(exist_ok=True)
            (iter_dir / 'ptools_before.py').write_text(current_source)
            (iter_dir / 'ptools_after.py').write_text(new_source)
            (iter_dir / 'reasoning.txt').write_text(reasoning)
            (iter_dir / 'profiling_summary.txt').write_text(prof_summary)
            (iter_dir / 'failure_traces.txt').write_text(failure_traces)
            (iter_dir / 'iteration_history.txt').write_text(
                history_text or 'No previous iterations.')
            if sup_stats.get('_prompt'):
                (iter_dir / 'supervisor_prompt.txt').write_text(sup_stats['_prompt'])
            if sup_stats.get('_raw_output'):
                (iter_dir / 'supervisor_response.txt').write_text(sup_stats['_raw_output'])
            if cfg_overrides:
                (iter_dir / 'config_overrides.txt').write_text(
                    '\n'.join(cfg_overrides)
                )
            config.save(iter_dir / 'config_before.yaml')

        # 3. Check if anything changed
        if new_source.strip() == current_source.strip() and not cfg_overrides:
            print('[supervisor] no changes proposed, skipping')
            iterations.append(IterationRecord(
                iteration=i, train_accuracy=profile.accuracy,
                train_cost=profile.avg_cost, supervisor_cost=sup_cost,
                reasoning=reasoning, kept=False,
            ))
            no_improve_count += 1
            if no_improve_count >= 5:
                print('[supervisor] 5 consecutive no-change iterations, stopping')
                break
            continue

        # 4. Validate syntax of new source
        import ast
        try:
            ast.parse(new_source)
        except SyntaxError as e:
            print(f'[supervisor] syntax error in {evolved_path.name}: {e}')
            iterations.append(IterationRecord(
                iteration=i, train_accuracy=profile.accuracy,
                train_cost=profile.avg_cost, supervisor_cost=sup_cost,
                reasoning=reasoning, kept=False,
            ))
            continue

        # 5. Write evolved file and reload module
        saved_source = current_source
        saved_config = config.GLOBAL_CONFIG.copy() if cfg_overrides else None

        evolved_path.write_text(new_source)

        try:
            # Re-execute the evolved ptools file into the module
            _reload_evolved_module()
            # Re-bind interfaces from config
            implement_via_config(ptools_module, config.require('ptools'))
            # Get the fresh entry interface
            entry_interface = getattr(ptools_module, entry_point_name)

            if cfg_overrides:
                print(f'[supervisor] applying config: {cfg_overrides}')
                config.configure(dotlist=cfg_overrides)
            if output_dir:
                config.save(iter_dir / 'config_after.yaml')

        except Exception as e:
            print(f'[supervisor] reload failed: {e}')
            # Rollback: restore old source
            evolved_path.write_text(saved_source)
            if saved_config is not None:
                config.GLOBAL_CONFIG = saved_config
            _reload_evolved_module()
            implement_via_config(ptools_module, config.require('ptools'))
            entry_interface = getattr(ptools_module, entry_point_name)
            iterations.append(IterationRecord(
                iteration=i, train_accuracy=profile.accuracy,
                train_cost=profile.avg_cost, supervisor_cost=sup_cost,
                reasoning=reasoning, kept=False,
            ))
            continue

        # 6. Re-evaluate
        print('[supervisor] re-evaluating on train set...')
        with config.configuration(evaluate=dict(
            expt_name=f'rc_iter{i}', record_details=True,
        )):
            try:
                csv_path = evaluator.evaluate(train_dataset, entry_interface)
            except Exception as e:
                print(f'[supervisor] evaluation failed: {e}')
                # Rollback
                evolved_path.write_text(saved_source)
                if saved_config is not None:
                    config.GLOBAL_CONFIG = saved_config
                _reload_evolved_module()
                implement_via_config(ptools_module, config.require('ptools'))
                entry_interface = getattr(ptools_module, entry_point_name)
                iterations.append(IterationRecord(
                    iteration=i, train_accuracy=profile.accuracy,
                    train_cost=profile.avg_cost, supervisor_cost=sup_cost,
                    reasoning=reasoning, kept=False,
                ))
                continue

        new_result_dir = csv_path.parent
        new_profile = profile_from_results([new_result_dir])

        # 7. Count failures in train results
        iter_train_fail_early, iter_train_to_early = _count_failures(new_result_dir)
        n_train = len(train_dataset.cases)

        print(f'[supervisor] train: {new_profile.accuracy:.1%} '
              f'({n_train - iter_train_fail_early}/{n_train} correct, '
              f'{iter_train_to_early} timeouts)')
        print(f'[supervisor] cost: ${new_profile.avg_cost:.4f}/case')

        # 8. Always run eval to track generalization curve
        eval_acc = None
        eval_cost_val = None
        if eval_dataset is not None:
            print('[supervisor] evaluating on held-out set...')
            import pandas as pd
            with config.configuration(evaluate=dict(
                expt_name=f'rc_iter{i}_eval', record_details=False,
            )):
                try:
                    eval_csv = evaluator.evaluate(eval_dataset, entry_interface)
                    eval_df = pd.read_csv(eval_csv)
                    eval_acc = float(eval_df['correct'].mean())
                    eval_cost_val = float(eval_df.get('cost', pd.Series([0])).mean())
                except Exception as e:
                    print(f'[supervisor] eval failed: {e}')

        # 9. Keep or rollback
        if new_profile.accuracy > best_accuracy:
            kept = True  # strict train improvement
        elif (new_profile.accuracy >= best_accuracy
              and eval_acc is not None and best_eval_accuracy is not None):
            kept = eval_acc > best_eval_accuracy  # tiebreak on eval
        else:
            kept = False  # train regression or no improvement

        # Print eval results
        if eval_acc is not None:
            n_eval = len(eval_dataset.cases) if eval_dataset else 0
            eval_correct = int(round(eval_acc * n_eval))
            print(f'[supervisor] eval:  {eval_acc:.1%} '
                  f'({eval_correct}/{n_eval} correct)')

        # Print decision with full context
        decision = 'KEPT' if kept else 'ROLLED BACK'
        prev_train = f'{profile.accuracy:.1%}'
        prev_eval = f'{best_eval_accuracy:.1%}' if best_eval_accuracy is not None else '—'
        new_eval = f'{eval_acc:.1%}' if eval_acc is not None else '—'
        print(f'[supervisor] {decision}: '
              f'train {prev_train}→{new_profile.accuracy:.1%}, '
              f'eval {prev_eval}→{new_eval}, '
              f'best={best_accuracy:.1%}')

        if kept:
            no_improve_count = 0
            best_accuracy = new_profile.accuracy
            if eval_acc is not None:
                best_eval_accuracy = eval_acc
            best_source = new_source
            best_result_dir = new_result_dir
            current_source = new_source
            profile = new_profile
            if cfg_overrides:
                best_config_overrides = cfg_overrides
        else:
            no_improve_count += 1
            evolved_path.write_text(current_source)
            if saved_config is not None:
                config.GLOBAL_CONFIG = saved_config
            _reload_evolved_module()
            implement_via_config(ptools_module, config.require('ptools'))
            entry_interface = getattr(ptools_module, entry_point_name)
            print('[supervisor] ROLLED BACK (accuracy dropped)')

        iter_eval_fail, iter_eval_to = (None, None)
        if eval_acc is not None:
            eval_result_dirs = sorted(
                Path(config.get('evaluate.result_dir', 'results')).glob(
                    f'*rc_iter{i}_eval'))
            if eval_result_dirs:
                iter_eval_fail, iter_eval_to = _count_failures(eval_result_dirs[-1])

        iterations.append(IterationRecord(
            iteration=i, train_accuracy=new_profile.accuracy,
            train_cost=new_profile.avg_cost, supervisor_cost=sup_cost,
            train_failures=iter_train_fail_early, train_timeouts=iter_train_to_early,
            reasoning=reasoning, kept=kept,
            eval_accuracy=eval_acc, eval_cost=eval_cost_val,
            eval_failures=iter_eval_fail, eval_timeouts=iter_eval_to,
            config_overrides=cfg_overrides,
            train_result_dir=str(new_result_dir),
            eval_result_dir=str(eval_csv.parent) if eval_acc is not None else None,
            config_before_path=(
                f'iterations/iter_{i:03d}/config_before.yaml'
                if output_dir else None
            ),
            config_after_path=(
                f'iterations/iter_{i:03d}/config_after.yaml'
                if output_dir and cfg_overrides else None
            ),
        ))

        # Save outcome and running report
        if output_dir:
            outcome = 'KEPT' if kept else 'ROLLED BACK'
            (iter_dir / 'outcome.txt').write_text(
                f'{outcome}\n'
                f'accuracy: {profile.accuracy:.1%} -> {new_profile.accuracy:.1%}\n'
                f'cost: ${profile.avg_cost:.4f} -> ${new_profile.avg_cost:.4f}\n'
                f'best so far: {best_accuracy:.1%}\n'
            )
            (iter_dir / 'result_dirs.json').write_text(json.dumps({
                'train_result_dir': str(new_result_dir),
                'eval_result_dir': str(eval_csv.parent) if eval_acc is not None else None,
                'kept': kept,
            }, indent=2))
            # Save running report so progress is visible if run is interrupted
            _save_running_report(output_dir, iterations, best_accuracy,
                                 best_source, best_config_overrides,
                                 total_supervisor_cost)
            # Auto-regenerate HTML report (refresh browser to see updates)
            if on_iteration_complete:
                on_iteration_complete(output_dir)

        # 8. Check stopping criteria
        if target_accuracy is not None and best_accuracy >= target_accuracy:
            print(f'[supervisor] target accuracy {target_accuracy:.1%} reached!')
            break
        if no_improve_count >= 5:
            print('[supervisor] 5 consecutive non-improvements, stopping')
            break

    # --- Final report ---
    best_iter = max(
        (r for r in iterations if r.kept),
        key=lambda r: r.train_accuracy,
        default=iterations[0],
    )

    # Leave the live module bound to the selected best source. The learner
    # runs final eval after this function returns, so it must not see the last
    # tried candidate after a metric rollback.
    evolved_path.write_text(best_source)
    _reload_evolved_module()
    implement_via_config(ptools_module, config.require('ptools'))
    getattr(ptools_module, entry_point_name)

    report = SupervisorReport(
        iterations=iterations,
        best_iteration=best_iter.iteration,
        best_train_accuracy=best_accuracy,
        total_supervisor_cost=total_supervisor_cost,
        best_code=f'# See ptools_evolved.py ({len(best_source)} chars)',
        best_config_overrides=best_config_overrides,
        config_snapshot_path='config.yaml',
    )

    # Save report and best evolved file
    if output_dir:
        config.save(output_dir / 'config.yaml')
        (output_dir / 'ptools_evolved.py').write_text(best_source)
        (output_dir / 'report.json').write_text(
            report.model_dump_json(indent=2)
        )

    print('\n[supervisor] === Summary ===')
    print(f'Iterations: {len(iterations) - 1}')
    print(f'Best accuracy: {best_accuracy:.1%} (iteration {best_iter.iteration})')
    print(f'Total supervisor cost: ${total_supervisor_cost:.4f}')
    print(f'Evolved ptools saved to: {evolved_path}')

    return report
