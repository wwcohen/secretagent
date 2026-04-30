"""MedAgentBench benchmark experiment.

Example CLI commands:

    # run with defaults
    uv run python expt.py run

    # run first 5 examples only
    uv run python expt.py run dataset.n=5

    # override model
    uv run python expt.py run llm.model=claude-haiku-4-5-20251001

    # quick test on single case
    uv run python expt.py quick_test dataset.n=1
"""

import importlib.util
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterator

import pandas as pd
import pprint
from tqdm import tqdm
import typer

_BENCHMARK_DIR = Path(__file__).parent
_PROJECT_ROOT = _BENCHMARK_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / 'src'))
sys.path.insert(0, str(_BENCHMARK_DIR))

from secretagent import config, record
from secretagent.core import implement_via_config
import secretagent.implement  # noqa: F401 (registers all factories)
from secretagent.dataset import Dataset, Case
from secretagent.evaluate import Evaluator

import fhir_tools
import ptools


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _to_native_type(value):
    """Convert a string to int or float if it looks numeric.

    refsol graders compare with == against native types (e.g. [60] not ["60"]).
    The paper's FINISH([60, 2.3]) preserves types via JSON parsing, but
    pydantic-ai returns list[str], so we convert back.
    """
    if not isinstance(value, str):
        return value
    try:
        # Try int first (e.g. "60" → 60)
        f = float(value)
        i = int(f)
        return i if f == i else f
    except (ValueError, OverflowError):
        return value


# ---------------------------------------------------------------------------
# refsol loading
# ---------------------------------------------------------------------------

def _load_refsol():
    """Try to import refsol.py from the data directory.

    refsol.py uses `from .utils import *` to get send_get_request.
    Since we load it standalone, we inject the needed symbols before exec.
    """
    refsol_path = _BENCHMARK_DIR / 'data' / 'refsol.py'
    if not refsol_path.exists():
        return None

    # Read source and replace the relative import with nothing —
    # we'll inject the needed functions into the module namespace.
    source = refsol_path.read_text()
    source = source.replace('from .utils import *', '')

    spec = importlib.util.spec_from_file_location('refsol', refsol_path)
    module = importlib.util.module_from_spec(spec)

    # Inject send_get_request (used by task2, task4–task10 graders)
    module.send_get_request = fhir_tools._send_get_request_raw
    module.verify_fhir_server = fhir_tools.verify_fhir_server

    exec(compile(source, str(refsol_path), 'exec'), module.__dict__)
    return module


class _HistoryItem:
    """Mimics the AgentBench ChatHistoryItem for refsol compatibility."""

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content


class _TaskResult:
    """Wrapper matching TaskOutput interface that refsol graders expect.

    Attributes:
        result: JSON string of the answer list (e.g. '["S6534835"]')
        history: list of _HistoryItem reconstructed from the POST log
    """

    def __init__(self, result_str: str, post_log: list[dict]):
        self.result = result_str
        self.history = self._build_history(post_log)

    @staticmethod
    def _build_history(post_log: list[dict]) -> list[_HistoryItem]:
        """Build a fake conversation history from the POST log.

        refsol's extract_posts() looks for consecutive pairs:
          - agent message containing "POST" + url + JSON payload
          - user message containing "POST request accepted"
        """
        history: list[_HistoryItem] = []
        for entry in post_log:
            url = entry['url']
            payload_str = json.dumps(entry['payload'])
            history.append(_HistoryItem('agent', f'POST {url}\n{payload_str}'))
            history.append(_HistoryItem(
                'user',
                'POST request accepted and executed successfully.'))
        return history


# ---------------------------------------------------------------------------
# dataset loading
# ---------------------------------------------------------------------------

def load_dataset(version: str = 'v2') -> Dataset:
    """Load MedAgentBench test data and convert to secretagent Dataset."""
    data_file = _BENCHMARK_DIR / 'data' / f'test_data_{version}.json'
    with open(data_file) as fp:
        raw = json.load(fp)

    # Load FHIR functions reference to embed in context
    funcs_file = _BENCHMARK_DIR / 'data' / 'funcs_v1.json'
    funcs_json = funcs_file.read_text()

    fhir_base = config.get('fhir.api_base', 'http://localhost:8080/fhir/')

    cases = []
    for item in raw:
        # Build enriched context: FHIR API base + function definitions + per-case context
        context_parts = [
            f"FHIR API base URL: {fhir_base}",
            f"Available FHIR functions:\n{funcs_json}",
        ]
        if item.get('context'):
            context_parts.append(f"Task context: {item['context']}")
        enriched_context = '\n\n'.join(context_parts)

        cases.append(Case(
            name=item['id'],
            input_args=(item['instruction'], enriched_context),
            expected_output=item.get('sol'),
            metadata={
                'task_type': item['id'].split('_')[0],
                'eval_MRN': item.get('eval_MRN'),
                'raw': item,
            },
        ))

    return Dataset(name='medagentbench', split=version, cases=cases)


# ---------------------------------------------------------------------------
# evaluator
# ---------------------------------------------------------------------------

class MedAgentBenchEvaluator(Evaluator):
    """Evaluator that uses refsol.py graders when available."""

    def __init__(self, fhir_api_base: str):
        self.fhir_api_base = fhir_api_base
        self.refsol = _load_refsol()
        if self.refsol is None:
            print('WARNING: refsol.py not found in data/. '
                  'Only task1 (with sol field) will be graded.')

    def measure(self, example: Case, interface) -> dict[str, Any]:
        """Run a case with POST-log management."""
        fhir_tools.clear_post_log()

        with record.recorder() as records:
            try:
                predicted_output = interface(*example.input_args)
            except Exception as ex:
                predicted_output = f'**exception raised**: {ex}'

        llm_usage_stats = self.aggregate_usage_stats(records)
        post_log = fhir_tools.get_post_log()

        eval_metadata = dict(example.metadata or {})
        eval_metadata['post_log'] = post_log
        metrics = self.compare_predictions(
            predicted_output, example.expected_output, eval_metadata)

        result = dict(
            predicted_output=str(predicted_output),
            expected_output=str(example.expected_output),
            task_type=example.metadata.get('task_type', ''),
            num_posts=len(post_log),
            **metrics,
            **llm_usage_stats,
        )
        if config.get('evaluate.record_details'):
            result['rollout'] = records
            result['post_log'] = post_log
        return result

    def measurements(self, dataset, interface) -> Iterator[dict[str, Any]]:
        """Run cases, optionally in parallel via evaluate.max_workers."""
        max_workers = int(config.get('evaluate.max_workers', 1))
        if max_workers <= 1:
            yield from super().measurements(dataset, interface)
            return

        # Parallel execution — skip record.recorder() (not thread-safe)
        def run_case(example):
            fhir_tools.clear_post_log()
            try:
                predicted_output = interface(*example.input_args)
            except Exception as ex:
                predicted_output = f'**exception raised**: {ex}'
            post_log = fhir_tools.get_post_log()
            eval_metadata = dict(example.metadata or {})
            eval_metadata['post_log'] = post_log
            metrics = self.compare_predictions(
                predicted_output, example.expected_output, eval_metadata)
            row = dict(
                predicted_output=str(predicted_output),
                expected_output=str(example.expected_output),
                task_type=example.metadata.get('task_type', ''),
                num_posts=len(post_log),
                case_name=example.name,
                **metrics,
            )
            return row

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(run_case, ex): ex for ex in dataset.cases}
            for future in tqdm(as_completed(futures), total=len(futures)):
                yield future.result()

    def compare_predictions(
            self, predicted_output, expected_output,
            metadata=None) -> dict[str, Any]:
        """Grade a prediction using refsol or fallback to exact match."""
        metadata = metadata or {}
        task_type = metadata.get('task_type', '')
        raw_item = metadata.get('raw', {})

        # Try refsol grading first
        if self.refsol is not None:
            grader = getattr(self.refsol, task_type, None)
            if grader is not None:
                try:
                    # refsol expects results.result to be a JSON list string
                    # with native types (int/float, not strings of numbers).
                    # pydantic-ai returns list[str], so convert numeric strings
                    # back to numbers to match the FINISH([60, 2.3]) format.
                    # PoT may return a bare value — wrap it in a list.
                    if not isinstance(predicted_output, list):
                        predicted_output = [predicted_output]
                    result_str = json.dumps([_to_native_type(v) for v in predicted_output])
                    post_log = metadata.get('post_log', [])
                    task_result = _TaskResult(result_str, post_log)
                    correct = grader(raw_item, task_result, self.fhir_api_base) is True
                    return dict(correct=float(correct))
                except Exception as ex:
                    return dict(correct=0.0, eval_error=str(ex))

        # Fallback: exact match on sol field (only task1 has this)
        if expected_output is not None:
            if isinstance(predicted_output, list):
                correct = predicted_output == expected_output
            else:
                correct = str(predicted_output) == str(expected_output)
            return dict(correct=float(correct))

        # No grader available and no sol — can't evaluate
        return dict(correct=float('nan'))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

app = typer.Typer()

_EXTRA_ARGS = {"allow_extra_args": True, "allow_interspersed_args": False}


def setup(dotlist: list[str], config_file: Path | None = None) -> tuple[Dataset, Any]:
    """Load config, verify FHIR server, load dataset, bind implementations."""
    if config_file is None:
        config_file = _BENCHMARK_DIR / 'conf' / 'unstructured_baseline.yaml'
    config.configure(yaml_file=config_file, dotlist=dotlist)
    config.set_root(_BENCHMARK_DIR)

    if not 'baseline' in str(config_file):
        # Verify FHIR server for tool-using
        fhir_base = config.get('fhir.api_base', 'http://localhost:8080/fhir/')
        fhir_tools.set_api_base(fhir_base)
        if not fhir_tools.verify_fhir_server():
            print(f'ERROR: FHIR server not reachable at {fhir_base}')
            print('Start it with: docker run -d -p 8080:8080 jyxsu6/medagentbench:latest')
            raise SystemExit(1)
        print(f'FHIR server OK at {fhir_base}')

    # Load dataset
    version = config.get('dataset.version', 'v2')
    dataset = load_dataset(version)
    dataset.configure(
        shuffle_seed=config.get('dataset.shuffle_seed'),
        n=config.get('dataset.n') or None,
    )
    print(f'Dataset: {dataset.summary()}')

    # Bind implementations
    implement_via_config(ptools, config.require('ptools'))

    return dataset, ptools.solve_medical_task


@app.command(context_settings=_EXTRA_ARGS)
def run(ctx: typer.Context,
        config_file: Path = typer.Option(None, help="Config YAML file")):
    """Run MedAgentBench evaluation.

    Extra args are parsed as config overrides in dot notation, e.g.:
        uv run python expt.py run --config-file conf/pot.yaml dataset.n=10
    """
    dataset, interface = setup(ctx.args, config_file)

    fhir_base = config.get('fhir.api_base', 'http://localhost:8080/fhir/')
    evaluator = MedAgentBenchEvaluator(fhir_base)
    csv_path = evaluator.evaluate(dataset, interface)

    # Print summary
    df = pd.read_csv(csv_path)
    print(df)
    print()

    # Per-task-type breakdown
    if 'task_type' in df.columns and 'correct' in df.columns:
        numeric_df = df[df['correct'].notna()]
        if not numeric_df.empty:
            print(f"\nOverall success rate: {numeric_df['correct'].mean():.3f}")
            for task_type in sorted(numeric_df['task_type'].unique()):
                mask = numeric_df['task_type'] == task_type
                n = mask.sum()
                rate = numeric_df.loc[mask, 'correct'].mean()
                print(f'  {task_type}: {rate:.3f} ({n} cases)')


@app.command(context_settings=_EXTRA_ARGS)
def quick_test(ctx: typer.Context,
               config_file: Path = typer.Option(None, help="Config YAML file")):
    """Quick test on a single case with full echo enabled."""
    dataset, interface = setup(ctx.args, config_file)
    pprint.pprint(config.GLOBAL_CONFIG)

    example = dataset.cases[0]
    print(f'\nCase: {example.name}')
    print(f'Instruction: {example.metadata["raw"]["instruction"][:200]}')

    with config.configuration(
            cachier={'enable_caching': False},
            echo={'llm_input': True, 'llm_output': True}):
        fhir_tools.clear_post_log()
        with record.recorder() as records:
            predicted = interface(*example.input_args)

    print(f'\nPredicted: {predicted}')
    print(f'Expected: {example.expected_output}')
    print(f'POST log: {fhir_tools.get_post_log()}')
    print(f'\nRecords:')
    pprint.pprint(records)


@app.command(context_settings=_EXTRA_ARGS)
def orchestrate_evolve_run(ctx: typer.Context,
                           config_file: Path = typer.Option(None, help="Config YAML file")):
    """Orchestrate a workflow, improve a random ptool, then evaluate.

    1. Orchestrate generates workflow (bind-time)
    2. Pick a random simulate ptool and improve it via evolutionary refinement
    3. Run improved workflow on full dataset
    """
    from collections import defaultdict
    from secretagent.experimental.improve import improve_ptool_within_workflow
    from secretagent.core import all_interfaces, Interface

    dataset, interface = setup(ctx.args, config_file)

    # Build train set: 2 cases per task type
    train_per_task = int(config.get('improve.train_per_task', 2))
    by_type = defaultdict(list)
    for case in dataset.cases:
        by_type[case.name.split('_')[0]].append(case)
    train_cases = []
    for task_type in sorted(by_type):
        train_cases.extend(by_type[task_type][:train_per_task])
    print(f'[evolve] train set: {len(train_cases)} cases')

    # Find improvable ptools (simulate-bound interfaces)
    improvable = [i for i in all_interfaces()
                  if isinstance(i, Interface)
                  and i.implementation is not None
                  and i.name not in ('solve_medical_task',)
                  and i.name in config.get('ptools', {})]

    if improvable:
        import random
        target_name = config.get('improve.target')
        if target_name:
            target = next((i for i in improvable if i.name == target_name), None)
            if not target:
                print(f'[evolve] target {target_name} not found, picking random')
                target = random.choice(improvable)
        else:
            target = random.choice(improvable)
        print(f'[evolve] improving: {target.name}')

        pop_size = int(config.get('improve.population_size', 5))
        n_gen = int(config.get('improve.n_generations', 2))

        result = improve_ptool_within_workflow(
            ptool_name=target.name,
            workflow_interface=interface,
            train_cases=train_cases,
            population_size=pop_size,
            n_generations=n_gen,
        )

        from secretagent.experimental.improve import _apply_variant, _get_ptool_info

        if result['improved'] and result['code']:
            print(f'[evolve] improvement found! fitness: {result["fitness"].get("fitness", 0):.3f}')
            _apply_variant(target, result['code'], _get_ptool_info(target))
        else:
            print(f'[evolve] no improvement over baseline')

        # Save improvement log
        import json as json_mod
        improvements_path = Path(config.require('evaluate.result_dir'))
        improvements_path.mkdir(parents=True, exist_ok=True)
        improvement_log = {
            'ptool_name': target.name,
            'method': result['method'],
            'improved': result['improved'],
            'baseline_fitness': result['all_scores'][-1] if result['all_scores'] else {},
            'best_fitness': result['fitness'],
            'original_code': _get_ptool_info(target).get('impl_source', target.doc)[:2000],
            'improved_code': result['code'][:2000] if result['code'] else None,
            'all_scores': result['all_scores'],
            'generations': result['generations'],
        }
        log_file = _BENCHMARK_DIR / 'improvements.jsonl'
        with open(log_file, 'a') as f:
            f.write(json_mod.dumps(improvement_log, default=str) + '\n')
        print(f'[evolve] improvement log saved to {log_file}')
    else:
        print(f'[evolve] no improvable ptools found')

    # Run evaluation with (possibly improved) workflow
    fhir_base = config.get('fhir.api_base', 'http://localhost:8080/fhir/')
    evaluator = MedAgentBenchEvaluator(fhir_base)
    csv_path = evaluator.evaluate(dataset, interface)

    df = pd.read_csv(csv_path)
    print(df)
    if 'task_type' in df.columns and 'correct' in df.columns:
        numeric_df = df[df['correct'].notna()]
        if not numeric_df.empty:
            print(f"\nOverall success rate: {numeric_df['correct'].mean():.3f}")
            for task_type in sorted(numeric_df['task_type'].unique()):
                mask = numeric_df['task_type'] == task_type
                n = mask.sum()
                rate = numeric_df.loc[mask, 'correct'].mean()
                print(f'  {task_type}: {rate:.3f} ({n} cases)')


@app.command(context_settings=_EXTRA_ARGS)
def orchestrate_improve_prompt(ctx: typer.Context,
                               config_file: Path = typer.Option(None, help="Config YAML file")):
    """Improve the orchestrate task description, re-generate workflow, evaluate.

    Uses the improve module to evolve the task description that orchestrate
    uses to generate the workflow. Each variant = different description →
    different generated workflow → different accuracy.
    """
    from collections import defaultdict
    from secretagent.experimental.improve import _FitnessTracker, _llm_call, _extract_code
    from secretagent.orchestrate.catalog import PtoolCatalog
    from secretagent.orchestrate.composer import compose
    from secretagent.orchestrate.pipeline import build_pipeline, _entry_signature_from_interface
    from secretagent.core import all_interfaces, Interface
    import json as json_mod
    import random

    # Load config and dataset but DON'T bind solve_medical_task yet
    if config_file is None:
        config_file = _BENCHMARK_DIR / 'conf' / 'orchestrate.yaml'
    config.configure(yaml_file=config_file, dotlist=ctx.args)
    config.set_root(_BENCHMARK_DIR)

    fhir_base = config.get('fhir.api_base', 'http://localhost:8080/fhir/')
    fhir_tools.set_api_base(fhir_base)
    if not fhir_tools.verify_fhir_server():
        print(f'ERROR: FHIR server not reachable at {fhir_base}')
        raise SystemExit(1)

    version = config.get('dataset.version', 'v2')
    dataset = load_dataset(version)
    dataset.configure(
        shuffle_seed=config.get('dataset.shuffle_seed'),
        n=config.get('dataset.n') or None)

    # Bind all ptools EXCEPT solve_medical_task
    ptools_cfg = dict(config.require('ptools'))
    smt_cfg = ptools_cfg.pop('solve_medical_task')
    implement_via_config(ptools, ptools_cfg)

    # Build train set
    train_per_task = int(config.get('improve.train_per_task', 2))
    by_type = defaultdict(list)
    for case in dataset.cases:
        by_type[case.name.split('_')[0]].append(case)
    train_cases = []
    for task_type in sorted(by_type):
        train_cases.extend(by_type[task_type][:train_per_task])
    print(f'[improve-prompt] train set: {len(train_cases)} cases')

    # Get orchestrate setup
    tool_ifaces = [i for i in all_interfaces()
                   if i.implementation is not None and i.name != 'solve_medical_task']
    catalog = PtoolCatalog.from_interfaces(tool_ifaces)
    entry_sig = _entry_signature_from_interface(ptools.solve_medical_task)
    model = config.get('orchestrate.model', config.require('llm.model'))

    # Get original task description
    original_desc = smt_cfg.get('task_description', '')
    print(f'[improve-prompt] original description: {original_desc[:100]}...')

    pop_size = int(config.get('improve.population_size', 5))
    n_gen = int(config.get('improve.n_generations', 2))
    tracker = _FitnessTracker()

    def evaluate_description(desc):
        """Generate workflow from description, evaluate on train set."""
        try:
            code = compose(desc, catalog, entry_sig, model=model)
            pipeline = build_pipeline(code, ptools.solve_medical_task, tool_ifaces)
            import json
            pipeline._fn.__globals__['json'] = json
            # Bind the pipeline to the interface so __call__ works
            from secretagent.core import Implementation
            ptools.solve_medical_task.implementation = Implementation(
                implementing_fn=pipeline,
                factory_method='orchestrate',
                factory_kwargs={})
        except Exception as ex:
            print(f'[improve-prompt]   compose failed: {ex}')
            return 0.0, 999.0, 999.0, None

        # Use the full evaluator with refsol grading
        evaluator = MedAgentBenchEvaluator(fhir_base)
        correct = 0
        total_latency = 0.0
        total_cost = 0.0
        n = len(train_cases)

        for case in train_cases:
            try:
                row = evaluator.measure(case, ptools.solve_medical_task)
                correct += row.get('correct', 0.0)
                total_latency += row.get('latency', 0.0)
                total_cost += row.get('cost', 0.0)
            except Exception:
                pass

        # Unbind so next variant can rebind
        ptools.solve_medical_task.implementation = None
        return correct / n, total_latency / n, total_cost / n, code

    # Baseline
    ptools.solve_medical_task.implement_via('orchestrate', **{k: v for k, v in smt_cfg.items() if k != 'method'})
    acc, lat, cost, baseline_code = evaluate_description(original_desc)
    baseline_entry = tracker.add(acc, lat, cost)
    print(f'[improve-prompt] baseline: accuracy={acc:.2f} latency={lat:.1f}s cost=${cost:.4f}')

    # Generate variants — seed population with baseline so it participates in selection
    population = [(original_desc, baseline_code, baseline_entry)]
    previous = []

    for gen in range(n_gen + 1):
        if gen == 0:
            print(f'\n[improve-prompt] === Initial Population ===')
            target_count = pop_size
        else:
            print(f'\n[improve-prompt] === Generation {gen}/{n_gen} ===')
            population.sort(key=lambda x: tracker.get_fitness(x[2]), reverse=True)
            survivors = population[:3]
            for i, (d, c, e) in enumerate(survivors):
                print(f'[improve-prompt] survivor {i}: fitness={tracker.get_fitness(e):.3f} accuracy={e["accuracy"]:.2f}')
            population = list(survivors)
            target_count = pop_size - len(population)

        for i in range(target_count):
            if gen == 0:
                # Mutate: ask LLM to improve the task description
                prev_text = '\n---\n'.join(previous[-3:]) if previous else 'None'
                prompt = f"""Improve this task description used to generate a medical EHR workflow.
The workflow is auto-generated by an LLM from this description. It currently fails on
conditional ordering tasks (task5,9), referral tasks (task8), and stale-check tasks (task10).

Current description:
{original_desc}

Previous attempts (don't repeat):
{prev_text}

Write an improved task description that will help the LLM generate correct workflow branches
for ALL 10 task types. Be very specific about the conditional logic, thresholds, dosing
calculations, SNOMED vs LOINC codes, and return formats.

Return ONLY the improved description text (no code blocks, no markdown)."""
            else:
                # Crossover: merge two survivors' descriptions
                p1, p2 = random.sample(population[:3], 2)
                prompt = f"""Merge the best aspects of these two task descriptions into one.

Description A:
{p1[0]}

Description B:
{p2[0]}

Create a merged description that combines the strengths of both.
Return ONLY the merged description text."""

            raw = _llm_call(prompt)
            desc = raw.strip()
            if desc.startswith('```'):
                desc = '\n'.join(desc.split('\n')[1:-1])

            ptools.solve_medical_task.implementation = None
            acc, lat, cost, code = evaluate_description(desc)
            if code:
                entry = tracker.add(acc, lat, cost)
                population.append((desc, code, entry))
                previous.append(desc[:300])
                print(f'[improve-prompt] variant: accuracy={acc:.2f} latency={lat:.1f}s fitness={tracker.get_fitness(entry):.3f}')
            else:
                print(f'[improve-prompt] variant failed to compile')

    # Select best
    tracker._renormalize()
    all_candidates = [(original_desc, baseline_code, baseline_entry)] + population
    all_candidates.sort(key=lambda x: tracker.get_fitness(x[2]), reverse=True)
    best_desc, best_code, best_entry = all_candidates[0]

    print(f'\n[improve-prompt] === Result ===')
    print(f'[improve-prompt] best: accuracy={best_entry["accuracy"]:.2f} fitness={tracker.get_fitness(best_entry):.3f}')
    if best_desc != original_desc:
        print(f'[improve-prompt] improved description found!')
        print(f'[improve-prompt] description: {best_desc[:200]}...')
    else:
        print(f'[improve-prompt] baseline was best')

    # Apply best and run full evaluation
    if best_code:
        pipeline = build_pipeline(best_code, ptools.solve_medical_task, tool_ifaces)
        import json
        pipeline._fn.__globals__['json'] = json
        from secretagent.core import Implementation
        ptools.solve_medical_task.implementation = Implementation(
            implementing_fn=pipeline,
            factory_method='orchestrate',
            factory_kwargs={})

    evaluator = MedAgentBenchEvaluator(fhir_base)
    csv_path = evaluator.evaluate(dataset, ptools.solve_medical_task)

    df = pd.read_csv(csv_path)
    if 'task_type' in df.columns and 'correct' in df.columns:
        numeric_df = df[df['correct'].notna()]
        if not numeric_df.empty:
            print(f"\nOverall success rate: {numeric_df['correct'].mean():.3f}")
            for task_type in sorted(numeric_df['task_type'].unique()):
                mask = numeric_df['task_type'] == task_type
                print(f'  {task_type}: {numeric_df.loc[mask, "correct"].mean():.3f} ({mask.sum()} cases)')

    # Save log
    log_file = _BENCHMARK_DIR / 'improvements.jsonl'
    with open(log_file, 'a') as f:
        f.write(json_mod.dumps({
            'type': 'orchestrate_prompt',
            'original_desc': original_desc[:1000],
            'best_desc': best_desc[:1000],
            'best_accuracy': best_entry['accuracy'],
            'baseline_accuracy': baseline_entry['accuracy'],
            'all_scores': [{'fitness': tracker.get_fitness(e), **e} for _, _, e in all_candidates],
        }, default=str) + '\n')


if __name__ == '__main__':
    app()
