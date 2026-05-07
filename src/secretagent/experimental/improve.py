"""Improve a single ptool within a frozen workflow via evolutionary LLM refinement.

Usage:
    from secretagent.experimental.improve import improve_ptool_within_workflow

    best = improve_ptool_within_workflow(
        ptool_name='parse_task',
        workflow_interface=ptools.solve_medical_task,
        train_cases=dataset.cases[:20],
        population_size=5,
        n_generations=3,
    )

The function:
1. Runs the workflow with the current ptool on the train set → baseline fitness
2. Generates population_size variants via LLM (improve code if direct, prompt if simulate)
3. Evaluates each variant, selects best 3, crossover to replenish
4. Repeats for n_generations, returns the best ptool implementation

Fitness is multi-objective (accuracy, latency, cost) with global min-max
normalization so no single metric dominates.
"""

import ast
import inspect
import json
import random
import time

from litellm import completion

from secretagent import config, record
from secretagent.cache_util import cached, clear_all_caches  # noqa: F401
from secretagent.core import Interface, all_interfaces
from secretagent.dataset import Case


# ──────────────────────────────────────────────────────────────────────
# Fitness tracking with global min-max normalization
# ──────────────────────────────────────────────────────────────────────

class _FitnessTracker:
    """Track and normalize fitness scores across all candidates.

    Bi-objective: accuracy (maximize) + cost (minimize).
    Latency excluded — too noisy (crashed workflows get 0.0s which
    looks like "fast" instead of "broken").

    Supports two modes:
    - Linear: (accuracy_norm + cost_norm) / 2 — default
    - Pareto: non-dominated sorting, prefer accuracy then cost
    """

    def __init__(self, pareto: bool = False):
        self.history: list[dict] = []
        self.pareto = pareto

    def add(self, accuracy: float, latency: float, cost: float) -> dict:
        entry = {'accuracy': accuracy, 'latency': latency, 'cost': cost}
        self.history.append(entry)
        self._renormalize()
        return entry

    def _renormalize(self):
        """Re-compute normalized scores for ALL entries using global min-max."""
        if not self.history:
            return

        for key in ['accuracy', 'cost']:
            values = [e[key] for e in self.history]
            lo = 0.0  # fixed floor at 0, not observed min
            hi = max(values)
            for e in self.history:
                if hi == lo:
                    e[f'{key}_norm'] = 0.5
                else:
                    norm = (e[key] - lo) / (hi - lo)
                    if key == 'cost':
                        norm = 1.0 - norm  # lower cost = higher score
                    e[f'{key}_norm'] = norm

        if self.pareto:
            self._assign_pareto_fitness()
        else:
            for e in self.history:
                e['fitness'] = (e['accuracy_norm'] + e['cost_norm']) / 2.0

    def _assign_pareto_fitness(self):
        """Assign fitness based on Pareto rank + crowding distance.

        Rank 0 = non-dominated front (best). Within same rank, prefer
        solutions that are more spread out (higher crowding distance).
        """
        n = len(self.history)
        # Compute domination: a dominates b if a >= b on all objectives and a > b on at least one
        # Objectives: accuracy (max), -cost (min cost = max -cost)
        ranks = [0] * n
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                ai, aj = self.history[i], self.history[j]
                # j dominates i?
                if (aj['accuracy'] >= ai['accuracy'] and aj['cost'] <= ai['cost']
                        and (aj['accuracy'] > ai['accuracy'] or aj['cost'] < ai['cost'])):
                    ranks[i] += 1

        # Fitness = 1 / (1 + rank), so rank 0 = fitness 1.0
        # Within same rank, break ties by accuracy (prefer higher)
        for i, e in enumerate(self.history):
            e['pareto_rank'] = ranks[i]
            e['fitness'] = 1.0 / (1.0 + ranks[i]) + e['accuracy'] * 0.001

    def get_fitness(self, entry: dict) -> float:
        return entry.get('fitness', 0.0)

    def pareto_frontier(self) -> list[dict]:
        """Return non-dominated solutions (rank 0)."""
        return [e for e in self.history if e.get('pareto_rank', 0) == 0]


# ──────────────────────────────────────────────────────────────────────
# Evaluation
# ──────────────────────────────────────────────────────────────────────

def _evaluate_workflow(
    interface: Interface,
    cases: list[Case],
    cache_tag: str = '',
) -> tuple[float, float, float]:
    """Run workflow on cases, return (accuracy, avg_latency, avg_cost)."""
    correct = 0
    total_latency = 0.0
    total_cost = 0.0
    n = len(cases)

    for case in cases:
        with record.recorder() as records:
            try:
                start = time.time()
                predicted = interface(*case.input_args)
                latency = time.time() - start
                total_latency += latency

                if case.expected_output is not None and predicted == case.expected_output:
                    correct += 1

                # Extract cost from records
                for rec in records:
                    stats = rec.get('stats', {})
                    total_cost += stats.get('cost', 0.0)
            except Exception:
                pass

    return (correct / n if n else 0.0,
            total_latency / n if n else 0.0,
            total_cost / n if n else 0.0)


# ──────────────────────────────────────────────────────────────────────
# LLM-based ptool improvement
# ──────────────────────────────────────────────────────────────────────

def _get_ptool_info(ptool: Interface) -> dict:
    """Extract current implementation details of a ptool."""
    info = {
        'name': ptool.name,
        'src': ptool.src,
        'doc': ptool.doc,
        'annotations': {k: str(v) for k, v in ptool.annotations.items()},
    }

    if ptool.implementation:
        method = ptool.implementation.factory_method
        info['method'] = method

        # Get the actual function source for direct implementations
        fn = ptool.implementation.implementing_fn
        try:
            # The implementing_fn is a wrapper — get the inner function
            inner = fn.__wrapped__ if hasattr(fn, '__wrapped__') else fn
            info['impl_source'] = inspect.getsource(inner)
        except (TypeError, OSError):
            info['impl_source'] = ''

    return info


def _build_workflow_graph(interface: Interface, cases: list[Case], max_cases: int = 3) -> str:
    """Extract a compact call graph from execution traces.

    Shows how ptools connect: which calls which, with what data flows.
    Example output:
        Case task1_1: "What's the MRN of Peter Stafford..."
          parse_task(instruction, context) → '{"task_type":"lookup","family":"Stafford",...}'
          find_patient("http://...", "Stafford", "Peter", "1932-12-29") → "S6534835"
          → WORKFLOW RETURNED: ["S6534835"] (expected: ["S6534835"]) ✓

        Case task5_1: "Check patient S6315806's magnesium..."
          parse_task(instruction, context) → '{"task_type":"conditional_order",...}'
          get_observations("http://...", "S6315806", "MG", 24) → '[{"value":2.3,...}]'
          → WORKFLOW RETURNED: [-1] (expected: [2.3]) ✗
    """
    graphs = []
    for case in cases[:max_cases]:
        with record.recorder() as records:
            try:
                result = interface(*case.input_args)
            except Exception as ex:
                result = f'**exception: {ex}**'

        lines = [f'Case {case.name}: "{str(case.input_args[0])[:80]}..."']
        for rec in records:
            func = rec.get('func', '?')
            args = rec.get('args', ())
            kw = rec.get('kw', {})
            output = rec.get('output', '')
            # Compact arg display
            arg_strs = [str(a)[:80] for a in args]
            kw_strs = [f'{k}={str(v)[:40]}' for k, v in kw.items()]
            all_args = ', '.join(arg_strs + kw_strs)
            if len(all_args) > 150:
                all_args = all_args[:150] + '...'
            out_str = str(output)[:150]
            lines.append(f'  {func}({all_args}) → {out_str}')

        correct = case.expected_output is not None and result == case.expected_output
        mark = '✓' if correct else '✗'
        lines.append(f'  → RETURNED: {str(result)[:100]} (expected: {str(case.expected_output)[:100]}) {mark}')
        graphs.append('\n'.join(lines))

    return '\n\n'.join(graphs)


def _collect_traces(interface: Interface, cases: list[Case], ptool_name: str, max_cases: int = 5) -> tuple[list[dict], str]:
    """Run workflow on cases and collect traces + workflow graph.

    Returns (traces_for_target_ptool, workflow_graph_string).
    """
    traces = []
    all_records = []

    for case in cases[:max_cases]:
        with record.recorder() as records:
            try:
                result = interface(*case.input_args)
            except Exception:
                result = '**exception**'

        all_records.append((case, records, result))

        # Find records for our ptool
        for rec in records:
            if rec.get('func') == ptool_name:
                traces.append({
                    'input_args': str(rec.get('args', ''))[:500],
                    'input_kw': str(rec.get('kw', ''))[:200],
                    'output': str(rec.get('output', ''))[:500],
                    'case_name': case.name,
                    'workflow_output': str(result)[:200],
                    'expected': str(case.expected_output)[:200],
                })
        if not any(t.get('case_name') == case.name for t in traces):
            traces.append({
                'input_args': str(case.input_args)[:500],
                'output': str(result)[:200],
                'expected': str(case.expected_output)[:200],
                'case_name': case.name,
            })

    # Build workflow graph from ALL records (not just target ptool)
    graph = _build_workflow_graph(interface, cases[:max_cases])

    return traces, graph


def _llm_call(prompt: str, max_tokens: int = 4096) -> str:
    model = config.get('improve.model', config.get('llm.model', 'together_ai/deepseek-ai/DeepSeek-V3.1'))
    for attempt in range(3):
        try:
            response = completion(model=model, messages=[{"role": "user", "content": prompt}], max_tokens=max_tokens)
            return response.choices[0].message.content or ''
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def _generate_variant(
    ptool_info: dict,
    traces: list[dict],
    fitness_entry: dict,
    previous_variants: list[str],
    is_direct: bool,
    workflow_graph: str = '',
    profiling_summary: str = '',
) -> str:
    """Ask LLM to generate an improved version of the ptool."""
    traces_text = json.dumps(traces[:5], indent=2, default=str)
    prev_text = '\n---\n'.join(previous_variants[-3:]) if previous_variants else 'None'

    graph_section = f"""
Workflow call graph (shows how this ptool connects to others):
{workflow_graph}
""" if workflow_graph else ''

    profile_section = f"""
Pipeline profiling data (FREE analysis of execution — use this to understand failure patterns):
{profiling_summary}
""" if profiling_summary else ''

    if is_direct:
        prompt = f"""Improve this Python function implementation. The function is used in a workflow.

Current implementation:
```python
{ptool_info.get('impl_source', 'Not available')}
```

Interface definition:
```python
{ptool_info['src']}
```
{graph_section}{profile_section}
Execution traces (input → output for recent cases):
{traces_text}

Current fitness: accuracy={fitness_entry.get('accuracy', 0):.2f}, latency={fitness_entry.get('latency', 0):.1f}s, cost={fitness_entry.get('cost', 0):.4f}

Previous improvement attempts (don't repeat these):
{prev_text}

Generate an improved implementation. Fix bugs, handle edge cases, improve accuracy.
The function signature and return type MUST stay the same.
Return ONLY a ```python``` code block with the complete function."""
    else:
        prompt = f"""Improve this function's docstring/prompt. It's used with an LLM that reads the docstring to predict the output.

Current interface:
```python
{ptool_info['src']}
```
{graph_section}{profile_section}
Execution traces (what the LLM produced vs what was expected):
{traces_text}

Current fitness: accuracy={fitness_entry.get('accuracy', 0):.2f}

Previous improvement attempts (don't repeat these):
{prev_text}

Generate an improved version of the interface with a better docstring that will help the LLM produce more accurate outputs.
Keep the same function name, parameters, and return type.
Return ONLY a ```python``` code block with the complete @interface decorated function."""

    return _llm_call(prompt)


def _extract_code(response: str) -> str | None:
    """Extract Python code from LLM response."""
    import re
    match = re.search(r'```python\n(.*?)```', response, re.DOTALL)
    return match.group(1).strip() if match else None


def _lint_check(code: str, ptool_info: dict) -> str | None:
    """Check that code parses and has matching signature. Returns error or None."""
    try:
        ast.parse(code)
    except SyntaxError as e:
        return f"SyntaxError: {e}"

    # Check function name exists
    name = ptool_info['name']
    if is_direct_impl(ptool_info):
        expected = f"{name}_impl" if f"{name}_impl" in code else name
        if f"def {expected}" not in code and f"def {name}" not in code:
            return f"Missing function definition for {name}"
    else:
        if f"def {name}" not in code:
            return f"Missing function definition for {name}"

    return None


def is_direct_impl(ptool_info: dict) -> bool:
    return ptool_info.get('method', '') == 'DirectFactory'


def _apply_variant(ptool: Interface, code: str, ptool_info: dict):
    """Apply a variant to the ptool (modifies in place)."""
    if is_direct_impl(ptool_info):
        # Execute the code to get the function, then rebind
        namespace = {}
        exec(code, namespace)
        # Find the function (try name_impl first, then name)
        fn = namespace.get(f"{ptool.name}_impl") or namespace.get(ptool.name)
        if fn:
            ptool.implement_via('direct', fn=fn)
    else:
        # For simulate: re-create the interface with new docstring
        namespace = {'interface': lambda f: f}  # mock decorator
        exec(code, namespace)
        fn = namespace.get(ptool.name)
        if fn and fn.__doc__:
            ptool.doc = fn.__doc__
            ptool.src = code


# ──────────────────────────────────────────────────────────────────────
# Main API
# ──────────────────────────────────────────────────────────────────────

def improve_ptool_within_workflow(
    ptool_name: str,
    workflow_interface: Interface,
    train_cases: list[Case],
    population_size: int = 5,
    n_generations: int = 3,
    verbose: bool = True,
    profiling_summary: str = '',
    pareto: bool = False,
) -> dict:
    """Improve a single ptool within a frozen workflow via evolutionary LLM refinement.

    Args:
        ptool_name: name of the @interface to improve
        workflow_interface: the top-level workflow Interface to evaluate
        train_cases: list of Case objects for evaluation
        population_size: number of parallel solutions per generation (default 5)
        n_generations: number of evolutionary generations (default 3)
        verbose: print progress
        profiling_summary: optional profiling data string to include in LLM
            prompts (FREE — computed from results files, no API cost)
        pareto: if True, use Pareto non-dominated sorting instead of
            linear fitness. Returns the highest-accuracy Pareto-optimal
            solution instead of the best linear combination.

    Returns:
        dict with keys: 'code' (best implementation), 'fitness' (score dict),
        'method' (direct or simulate), 'generations' (history),
        'pareto_frontier' (list of scores, only if pareto=True)
    """
    # Find the ptool
    ptool = None
    for iface in all_interfaces():
        if iface.name == ptool_name:
            ptool = iface
            break
    if ptool is None:
        raise ValueError(f"Interface '{ptool_name}' not found")

    ptool_info = _get_ptool_info(ptool)
    is_direct = is_direct_impl(ptool_info)
    tracker = _FitnessTracker(pareto=pareto)

    if verbose:
        print(f"[improve] target: {ptool_name} (method: {'direct' if is_direct else 'simulate'})")
        print(f"[improve] train set: {len(train_cases)} cases, pop: {population_size}, gen: {n_generations}")

    # Save original state to restore between variants
    original_impl = ptool.implementation
    original_doc = ptool.doc
    original_src = ptool.src

    # Step 1: Baseline evaluation (with cachier warm-up)
    if verbose:
        print("\n[improve] === Baseline ===")
    acc, lat, cost = _evaluate_workflow(workflow_interface, train_cases)
    baseline_entry = tracker.add(acc, lat, cost)
    if verbose:
        print(f"[improve] baseline: accuracy={acc:.2f} latency={lat:.1f}s cost={cost:.4f}")

    # Collect traces + workflow graph for LLM context
    traces, workflow_graph = _collect_traces(workflow_interface, train_cases, ptool_name)
    if verbose and workflow_graph:
        print(f"[improve] workflow graph:\n{workflow_graph[:500]}")

    # Step 2: Generate initial population of variants
    if verbose:
        print("\n[improve] === Generation 0: Initial Population ===")

    population = []  # list of (code_str, fitness_entry)
    previous_variants = []

    for i in range(population_size):
        if verbose:
            print(f"[improve] generating variant {i+1}/{population_size}...")

        response = _generate_variant(ptool_info, traces, baseline_entry, previous_variants, is_direct, workflow_graph, profiling_summary)
        code = _extract_code(response)
        if not code:
            if verbose:
                print("[improve]   no code extracted, skipping")
            continue

        # Lint check
        error = _lint_check(code, ptool_info)
        if error:
            if verbose:
                print(f"[improve]   lint failed: {error}, retrying...")
            # Retry with error context
            response = _llm_call(f"Fix this code. Error: {error}\n\nOriginal code:\n```python\n{code}\n```\n\nReturn ONLY a ```python``` code block.")
            code = _extract_code(response)
            if not code:
                continue
            error = _lint_check(code, ptool_info)
            if error:
                if verbose:
                    print(f"[improve]   retry failed: {error}, skipping")
                continue

        # Evaluate variant
        try:
            _apply_variant(ptool, code, ptool_info)
            acc, lat, cost = _evaluate_workflow(workflow_interface, train_cases)
            entry = tracker.add(acc, lat, cost)
            population.append((code, entry))
            previous_variants.append(code[:500])
            if verbose:
                print(f"[improve]   accuracy={acc:.2f} latency={lat:.1f}s cost={cost:.4f} fitness={tracker.get_fitness(entry):.3f}")
        except Exception as ex:
            if verbose:
                print(f"[improve]   evaluation failed: {ex}")
        finally:
            # Restore original for next variant
            ptool.implementation = original_impl
            ptool.doc = original_doc
            ptool.src = original_src

    # Step 3: Evolutionary loop
    generation_history = [{'gen': 0, 'population': len(population)}]

    for gen in range(1, n_generations + 1):
        if verbose:
            print(f"\n[improve] === Generation {gen}/{n_generations} ===")

        if len(population) < 2:
            if verbose:
                print(f"[improve] population too small ({len(population)}), skipping generation")
            continue

        # Select best 3 (by fitness after renormalization)
        population.sort(key=lambda x: tracker.get_fitness(x[1]), reverse=True)
        survivors = population[:3]

        if verbose:
            for i, (_, entry) in enumerate(survivors):
                print(f"[improve] survivor {i}: fitness={tracker.get_fitness(entry):.3f} accuracy={entry['accuracy']:.2f} latency={entry['latency']:.1f}s cost={entry['cost']:.4f}")

        # Crossover: pair survivors randomly, merge via LLM
        offspring = []
        while len(survivors) + len(offspring) < population_size:
            p1, p2 = random.sample(survivors, 2)

            merge_prompt = f"""Combine the best aspects of these two implementations into one improved version.

Version A:
```python
{p1[0]}
```

Version B:
```python
{p2[0]}
```

Create a merged version that takes the strengths of both.
Return ONLY a ```python``` code block."""

            response = _llm_call(merge_prompt)
            code = _extract_code(response)
            if not code:
                continue

            error = _lint_check(code, ptool_info)
            if error:
                response = _llm_call(f"Fix this code. Error: {error}\n\n```python\n{code}\n```\n\nReturn ONLY a ```python``` code block.")
                code = _extract_code(response)
                if not code or _lint_check(code, ptool_info):
                    continue

            try:
                _apply_variant(ptool, code, ptool_info)
                acc, lat, cost = _evaluate_workflow(workflow_interface, train_cases)
                entry = tracker.add(acc, lat, cost)
                offspring.append((code, entry))
                if verbose:
                    print(f"[improve] crossover: accuracy={acc:.2f} latency={lat:.1f}s cost={cost:.4f} fitness={tracker.get_fitness(entry):.3f}")
            except Exception:
                pass
            finally:
                ptool.implementation = original_impl

        population = survivors + offspring
        generation_history.append({'gen': gen, 'population': len(population)})

    # Step 4: Select and return best
    # Final renormalization
    tracker._renormalize()

    all_candidates = [(None, baseline_entry)] + population
    all_candidates.sort(key=lambda x: tracker.get_fitness(x[1]), reverse=True)
    best_code, best_entry = all_candidates[0]

    if verbose:
        print("\n[improve] === Result ===")
        mode_str = 'pareto' if pareto else 'linear'
        print(f"[improve] selection mode: {mode_str}")
        print(f"[improve] best fitness: {tracker.get_fitness(best_entry):.3f}")
        print(f"[improve] best accuracy: {best_entry['accuracy']:.2f} "
              f"latency: {best_entry['latency']:.1f}s cost: {best_entry['cost']:.4f}")
        if pareto:
            frontier = tracker.pareto_frontier()
            print(f"[improve] pareto frontier: {len(frontier)} solutions")
            for i, e in enumerate(sorted(frontier, key=lambda x: -x['accuracy'])):
                print(f"[improve]   #{i}: accuracy={e['accuracy']:.2f} cost={e['cost']:.4f}")
        if best_code is None:
            print("[improve] baseline was best — no improvement found")
        else:
            print(f"[improve] improved implementation found ({len(best_code)} chars)")

    # Restore original state
    ptool.implementation = original_impl
    ptool.doc = original_doc
    ptool.src = original_src

    result = {
        'code': best_code,
        'fitness': best_entry,
        'method': 'direct' if is_direct else 'simulate',
        'improved': best_code is not None,
        'generations': generation_history,
        'all_scores': [{'fitness': tracker.get_fitness(e), **e} for _, e in all_candidates],
    }
    if pareto:
        result['pareto_frontier'] = [
            {'accuracy': e['accuracy'], 'cost': e['cost'], 'pareto_rank': e.get('pareto_rank', 0)}
            for e in tracker.pareto_frontier()
        ]
    return result
