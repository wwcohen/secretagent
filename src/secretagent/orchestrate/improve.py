"""Pipeline improvement loop: chain transforms to iteratively improve a pipeline.

Supports two modes:
- Single-trajectory (population_size=1): existing transform loop
- Population-based (population_size>1): evolutionary loop with meta-optimizer
"""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Sequence

from pydantic import BaseModel

from secretagent import config
from secretagent.orchestrate.catalog import PtoolCatalog
from secretagent.orchestrate.pipeline import Pipeline
from secretagent.orchestrate.profiler import PipelineProfile, profile_from_results

if TYPE_CHECKING:
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
    # --- Population mode parameters ---
    population_size: int = 1,
    seed_strategy: str = 'compose_then_mutate',
    meta_model: str | None = None,
    budget: float | None = None,
    budget_mode: str = 'soft_stop',
    minibatch_size: int = 50,
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
        population_size: number of candidates (1 = single-trajectory, >1 = population mode).
        seed_strategy: 'compose_then_mutate' or 'compose_n'.
        meta_model: LLM model for meta-optimizer (None = use heuristics).
        budget: optimization budget in dollars (None = no budget tracking).
        budget_mode: 'hard_stop', 'soft_stop', or 'pareto'.
        minibatch_size: examples per evaluation minibatch in population mode.
    """
    # Read defaults from config where not explicitly provided
    population_size = config.get('improve.population_size', population_size)
    seed_strategy = config.get('improve.seed_strategy', seed_strategy)
    meta_model = meta_model or config.get('improve.meta_model')
    budget = budget if budget is not None else config.get('improve.budget')
    budget_mode = config.get('improve.budget_mode', budget_mode)
    minibatch_size = config.get('improve.minibatch_size', minibatch_size)

    if transforms is None:
        transform_names = config.get('orchestrate.improve.transforms', [])
        if transform_names:
            transforms = [get_transform(n) for n in transform_names]
        else:
            transforms = list(_TRANSFORMS.values())

    if max_iterations is None:
        max_iterations = config.get('orchestrate.improve.max_iterations', 1)

    # --- Population mode dispatch ---
    if population_size > 1:
        return _improve_population(
            pipeline=pipeline,
            result_dirs=result_dirs,
            catalog=catalog,
            transforms=transforms,
            max_iterations=max_iterations,
            run_eval_fn=run_eval_fn,
            target_accuracy=target_accuracy,
            population_size=population_size,
            seed_strategy=seed_strategy,
            meta_model=meta_model,
            budget=budget,
            budget_mode=budget_mode,
            minibatch_size=minibatch_size,
        )

    # --- Single-trajectory mode (existing behavior) ---
    return _improve_single(
        pipeline=pipeline,
        result_dirs=result_dirs,
        catalog=catalog,
        transforms=transforms,
        max_iterations=max_iterations,
        run_eval_fn=run_eval_fn,
        target_accuracy=target_accuracy,
    )


# ---------------------------------------------------------------------------
# Single-trajectory mode (original behavior)
# ---------------------------------------------------------------------------

def _improve_single(
    pipeline: Pipeline,
    result_dirs: Sequence[str | Path],
    catalog: PtoolCatalog,
    transforms: list[PipelineTransform],
    max_iterations: int,
    run_eval_fn: Callable[[], Sequence[str | Path]] | None,
    target_accuracy: float | None,
) -> ImprovementReport:
    """Original single-trajectory improvement loop."""
    before = profile_from_results(result_dirs, pipeline_source=pipeline.source)
    iterations: list[dict] = []

    log.info('improvement loop starting: accuracy=%.1f%%, %d cases',
             before.accuracy * 100, before.n_cases)
    from secretagent.orchestrate.transforms.base import format_profiling_summary
    print(f'\n[improve] === Initial Profile ===')
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
                    print(f'[improve] regression detected, keeping previous state')
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
# Population-based mode
# ---------------------------------------------------------------------------

def _improve_population(
    pipeline: Pipeline,
    result_dirs: Sequence[str | Path],
    catalog: PtoolCatalog,
    transforms: list[PipelineTransform],
    max_iterations: int,
    run_eval_fn: Callable[[], Sequence[str | Path]] | None,
    target_accuracy: float | None,
    population_size: int,
    seed_strategy: str,
    meta_model: str | None,
    budget: float | None,
    budget_mode: str,
    minibatch_size: int,
) -> ImprovementReport:
    """Population-based improvement with evolutionary search.

    Loop: SEED → EVALUATE → SELECT → GUIDE → MUTATE → ACCEPT → BUDGET
    """
    from secretagent.orchestrate.budget import BudgetTracker
    from secretagent.orchestrate.meta_optimizer import MetaOptimizer
    from secretagent.orchestrate.population import PipelineCandidate, Population
    from secretagent.orchestrate.transforms.base import format_profiling_summary

    # --- Setup ---
    budget_tracker = BudgetTracker(
        budget_limit=budget or float('inf'),
        mode=budget_mode,
    )
    population = Population(
        population_size=population_size,
        seed_strategy=seed_strategy,
    )

    transform_map = {t.name: t for t in transforms}

    meta_optimizer = None
    if meta_model:
        meta_optimizer = MetaOptimizer(
            model=meta_model,
            operators=transform_map,
        )

    # --- STEP 1: SEED ---
    print(f'\n[population] === Seeding {population_size} candidates ===')
    before = profile_from_results(result_dirs, pipeline_source=pipeline.source)

    # Candidate 0: the given pipeline
    seed_candidate = PipelineCandidate(
        pipeline=pipeline,
        profile=before,
        generation=0,
    )
    population.add(seed_candidate)

    if seed_strategy == 'compose_then_mutate':
        # Generate variants by applying transforms to the seed
        _seed_via_mutation(
            population, pipeline, before, catalog, transforms,
            target_count=population_size,
        )
    elif seed_strategy == 'compose_n':
        # Generate independent compositions
        _seed_via_composition(
            population, catalog, pipeline,
            target_count=population_size,
        )

    print(f'[population] seeded {len(population.candidates)} candidates')

    # --- STEP 2: Initial EVALUATE ---
    # The seed pipeline already has a profile from result_dirs.
    # Other candidates don't yet — they'll be evaluated in the loop.
    best_accuracy = before.accuracy
    iterations: list[dict] = []

    # --- STEP 3-7: Main loop ---
    for i in range(max_iterations):
        print(f'\n[population] === Generation {i + 1}/{max_iterations} ===')
        print(population.summary())
        population.advance_generation()

        # SELECT: Compute Pareto front
        front = population.pareto_front()
        print(f'[population] Pareto front: {front}')

        # GUIDE: Choose mutations
        proposals_for_iter: list[dict] = []
        results_for_iter: list[dict] = []

        if meta_optimizer and front:
            # Build profiling details for all front candidates
            profiling_parts = []
            for idx in front:
                c = population.candidates[idx]
                if c.profile:
                    profiling_parts.append(
                        f'--- Candidate #{idx} ---\n'
                        + format_profiling_summary(c.profile)
                    )

            # Build operator descriptions
            op_lines = []
            for name, t in transform_map.items():
                op_lines.append(
                    f'- {name}: {t.__doc__.strip().split(chr(10))[0] if t.__doc__ else "no description"}'
                    f' (requires_llm={t.requires_llm})'
                )

            budget_info = budget_tracker.summary()
            budget_info['n_candidates'] = len(population.candidates)
            budget_info['generation'] = population.generation

            mutation_proposals, guide_cost = meta_optimizer.guide(
                population_summary=population.summary(),
                profiling_details='\n\n'.join(profiling_parts),
                operator_descriptions='\n'.join(op_lines),
                budget_summary=budget_info,
            )
            budget_tracker.record(guide_cost, 'meta-optimizer guide')

            for mp in mutation_proposals:
                print(
                    f'[population] meta-optimizer: {mp.operator} on '
                    f'candidate #{mp.candidate_index} — {mp.reasoning}'
                )
                proposals_for_iter.append(mp.model_dump())

                new_cand = _apply_mutation(
                    mp.operator, mp.candidate_index, population,
                    transform_map, catalog, before, front,
                )
                if new_cand:
                    results_for_iter.append({'success': True, 'operator': mp.operator})
        else:
            # Heuristic mode: try all transforms on Pareto front candidates
            for idx in front:
                for t in transforms:
                    new_cand = _apply_mutation(
                        t.name, idx, population,
                        transform_map, catalog, before, front,
                    )
                    if new_cand:
                        results_for_iter.append({'success': True, 'operator': t.name})

        iterations.append({
            'generation': population.generation,
            'proposals': proposals_for_iter,
            'results': results_for_iter,
            'population_size': len(population.candidates),
            'pareto_front': front,
        })

        # ACCEPT: Evaluate each new candidate with its config applied
        if run_eval_fn and any(r.get('success') for r in results_for_iter):
            print('[population] evaluating new candidates...')
            for c in population.candidates:
                if c.profile is not None or c.generation != population.generation:
                    continue
                # Apply this candidate's config overrides to global config
                if c.config:
                    dotlist = [f'{k}={v}' for k, v in c.config.items()]
                    config.configure(dotlist=dotlist)
                    log.info('applied candidate config: %s', dotlist)
                    print(f'[population] evaluating candidate with config: {c.config}')
                try:
                    new_dirs = run_eval_fn()
                    c.profile = profile_from_results(
                        new_dirs, pipeline_source=c.pipeline.source,
                    )
                    print(f'[population] candidate accuracy: {c.accuracy:.1%}')
                except Exception as e:
                    log.warning('candidate evaluation failed: %s', e)
                    print(f'[population] candidate eval failed: {e}')
            # Update best accuracy
            best_cand = population.best()
            if best_cand and best_cand.accuracy > best_accuracy:
                best_accuracy = best_cand.accuracy
            print(f'[population] best accuracy: {best_accuracy:.1%}')

        # BUDGET CHECK
        print(f'[population] {budget_tracker.format_summary()}')
        if budget_tracker.should_stop():
            print('[population] budget exhausted, stopping.')
            break

        # Early exit if target reached
        if target_accuracy is not None and best_accuracy >= target_accuracy:
            print(f'[population] target accuracy {target_accuracy:.1%} reached!')
            break

    # --- Final report ---
    best_cand = population.best()
    after = best_cand.profile if best_cand else None

    print(f'\n[population] === Optimization Summary ===')
    print(budget_tracker.format_summary())
    print(f'Generations: {population.generation}')
    print(f'Candidates evaluated: {len(population.candidates)}')
    print(f'Best accuracy: {best_accuracy:.1%}')
    print(population.summary())

    return ImprovementReport(
        before_profile=before,
        after_profile=after,
        iterations=iterations,
        improved=best_accuracy > before.accuracy,
        best_accuracy=best_accuracy,
    )


def _apply_mutation(
    operator_name: str,
    candidate_index: int,
    population: Any,
    transform_map: dict[str, Any],
    catalog: PtoolCatalog,
    fallback_profile: PipelineProfile,
    pareto_front: list[int],
) -> Any | None:
    """Apply a single mutation to a candidate, return new PipelineCandidate or None."""
    from secretagent.orchestrate.population import PipelineCandidate
    from secretagent.orchestrate.transforms.crossover import CrossoverTransform

    if operator_name not in transform_map:
        log.warning('unknown operator: %s', operator_name)
        return None
    if candidate_index >= len(population.candidates):
        log.warning('candidate index out of range: %d', candidate_index)
        return None

    t = transform_map[operator_name]
    candidate = population.candidates[candidate_index]
    profile = candidate.profile or fallback_profile

    # Wire crossover: set the other parent from a different Pareto-front candidate
    if isinstance(t, CrossoverTransform) and len(pareto_front) >= 2:
        other_idx = [idx for idx in pareto_front if idx != candidate_index]
        if other_idx:
            other = population.candidates[other_idx[0]]
            t.set_other(other.pipeline, other.profile)

    try:
        if not t.should_apply(profile):
            log.debug('transform %s: skipped (should_apply=False)', t.name)
            return None
        proposal = t.propose(profile, catalog)
        result = t.apply(proposal, candidate.pipeline, catalog)

        if result.success:
            print(f'[population] {t.name} on #{candidate_index}: {result.message}')
            new_pipeline = candidate.pipeline
            if result.new_pipeline_code:
                new_pipeline = Pipeline(
                    result.new_pipeline_code,
                    candidate.pipeline.entry_signature,
                    candidate.pipeline._fn.__globals__,
                )
            new_candidate = PipelineCandidate(
                pipeline=new_pipeline,
                config=dict(candidate.config),
                generation=population.generation,
                parent_index=candidate_index,
                mutation_history=list(candidate.mutation_history) + [t.name],
            )
            if result.new_config:
                new_candidate.config.update(result.new_config)
            population.add(new_candidate)
            return new_candidate
    except NotImplementedError:
        log.debug('transform %s: not implemented', operator_name)
    except Exception as e:
        log.warning('transform %s failed on #%d: %s', operator_name, candidate_index, e)
    return None


def _seed_via_mutation(
    population: Any,
    pipeline: Pipeline,
    profile: PipelineProfile,
    catalog: PtoolCatalog,
    transforms: list[PipelineTransform],
    target_count: int,
) -> None:
    """Seed population by applying transforms to the base pipeline."""
    for t in transforms:
        if len(population.candidates) >= target_count:
            break
        try:
            if not t.should_apply(profile):
                continue
            proposal = t.propose(profile, catalog)
            result = t.apply(proposal, pipeline, catalog)
            if result.success and result.new_pipeline_code:
                from secretagent.orchestrate.population import PipelineCandidate
                new_pipeline = Pipeline(
                    result.new_pipeline_code,
                    pipeline.entry_signature,
                    pipeline._fn.__globals__,
                )
                candidate = PipelineCandidate(
                    pipeline=new_pipeline,
                    generation=0,
                    parent_index=0,
                    mutation_history=[t.name],
                )
                if result.new_config:
                    candidate.config = dict(result.new_config)
                population.add(candidate)
                log.info('seeded candidate via %s', t.name)
        except (NotImplementedError, Exception) as e:
            log.debug('seed transform %s failed: %s', t.name, e)
            continue


def _seed_via_composition(
    population: Any,
    catalog: PtoolCatalog,
    seed_pipeline: Pipeline,
    target_count: int,
) -> None:
    """Seed population by composing N independent pipelines."""
    from secretagent.orchestrate.composer import compose
    from secretagent.orchestrate.population import PipelineCandidate

    entry_signature = seed_pipeline.entry_signature
    namespace = seed_pipeline._fn.__globals__

    for attempt in range(target_count - 1):
        if len(population.candidates) >= target_count:
            break
        try:
            task_desc = config.get('orchestrate.task_description', '')
            code = compose(
                task_description=task_desc,
                catalog=catalog,
                entry_signature=entry_signature,
            )
            new_pipeline = Pipeline(code, entry_signature, namespace)
            candidate = PipelineCandidate(
                pipeline=new_pipeline,
                generation=0,
                mutation_history=['compose'],
            )
            population.add(candidate)
            log.info('seeded candidate via composition (attempt %d)', attempt)
        except Exception as e:
            log.warning('composition seed failed (attempt %d): %s', attempt, e)
            continue
