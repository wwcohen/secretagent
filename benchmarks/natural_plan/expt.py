"""NaturalPlan benchmark experiment.

Requires Together AI API key: set TOGETHER_AI_API_KEY (or TOGETHER_API_KEY).

Example CLI commands:

    # run calendar workflow (default config)
    uv run python expt.py run --config-file conf/calendar.yaml \\
      evaluate.expt_name=cal_workflow \\
      ptools.calendar_scheduling.method=direct \\
      ptools.calendar_scheduling.fn=ptools_calendar.calendar_workflow

    # run calendar zero-shot structured
    uv run python expt.py run --config-file conf/calendar.yaml \\
      evaluate.expt_name=cal_zs_struct \\
      ptools.calendar_scheduling.method=simulate

    # run meeting workflow
    uv run python expt.py run --config-file conf/meeting.yaml \\
      evaluate.expt_name=meet_workflow \\
      ptools.meeting_planning.method=direct \\
      ptools.meeting_planning.fn=ptools_meeting.meeting_workflow

    # run trip zero-shot structured
    uv run python expt.py run --config-file conf/trip.yaml \\
      evaluate.expt_name=trip_zs_struct \\
      ptools.trip_planning.method=simulate
"""

import importlib
import json
import os
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import typer

# Litellm expects TOGETHER_AI_API_KEY; support TOGETHER_API_KEY as fallback
if os.environ.get("TOGETHER_API_KEY") and not os.environ.get("TOGETHER_AI_API_KEY"):
    os.environ["TOGETHER_AI_API_KEY"] = os.environ["TOGETHER_API_KEY"]

_BENCHMARK_DIR = Path(__file__).resolve().parent
_SECRETAGENT_ROOT = _BENCHMARK_DIR.parent.parent
_DATA_DIR = _BENCHMARK_DIR / 'data'

sys.path.insert(0, str(_SECRETAGENT_ROOT / 'src'))
sys.path.insert(0, str(_BENCHMARK_DIR))

from secretagent import config
from secretagent.core import Interface, implement_via_config
from secretagent.dataset import Dataset, Case
from secretagent.evaluate import Evaluator


from eval_utils import (
    eval_calendar_single,
    eval_meeting_single,
    eval_trip_single,
)

SPLIT_TO_MODULE = {
    'calendar': 'ptools_calendar',
    'meeting': 'ptools_meeting',
    'trip': 'ptools_trip',
}

DATA_FILES = {
    'calendar': 'calendar_scheduling.json',
    'meeting': 'meeting_planning.json',
    'trip': 'trip_planning.json',
}

# Stratified sampling (same logic as AgentProject run.py, seed=42 -> 50 cal, 50 meet, 48 trip)
def _calendar_strata_key(inst: dict) -> str:
    return f"({inst['num_people']},{inst['num_days']})"

def _meeting_strata_key(inst: dict) -> str:
    return str(inst['num_people'])

def _trip_strata_key(inst: dict) -> str:
    return str(inst['num_cities'])

STRATA_KEYS: dict[str, Callable] = {
    'calendar': _calendar_strata_key,
    'meeting': _meeting_strata_key,
    'trip': _trip_strata_key,
}


def stratified_sample(
    data: dict[str, dict],
    strata_key: Callable[[dict], str],
    n: int,
    seed: int,
) -> dict[str, dict]:
    """Stratified sampling: pick n/num_strata examples from each stratum."""
    strata: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for key, instance in data.items():
        s = strata_key(instance)
        strata[s].append((key, instance))
    num_strata = len(strata)
    per_stratum = max(1, n // num_strata)
    rng = random.Random(seed)
    sampled = {}
    for s_key in sorted(strata.keys()):
        items = strata[s_key]
        rng.shuffle(items)
        for k, v in items[:per_stratum]:
            sampled[k] = v
    return sampled


class NaturalPlanEvaluator(Evaluator):
    """Evaluator for NaturalPlan tasks.

    Dispatches to task-specific eval functions from eval_utils.
    Stores the full instance dict as expected_output because
    eval_meeting_single and eval_trip_single need access to
    constraints, dist_matrix, cities, durations, etc.
    """

    def __init__(self, task: str):
        self.task = task

    def compare_predictions(
        self, predicted_output: Any, expected_output: Any
    ) -> dict[str, Any]:
        pred = str(predicted_output) if predicted_output is not None else ''
        if self.task == 'calendar':
            correct = eval_calendar_single(pred, expected_output['golden_plan'])
        elif self.task == 'meeting':
            correct = eval_meeting_single(pred, expected_output)
        elif self.task == 'trip':
            correct = eval_trip_single(pred, expected_output)
        else:
            raise ValueError(f'Unknown task: {self.task}')
        return dict(correct=correct)

    def measure(self, example: Case, interface: Interface) -> dict[str, Any]:
        try:
            return super().measure(example, interface)
        except Exception as e:
            # Cost/latency on exception paths are UNKNOWN (e.g. pydantic-ai
            # agent may have made LLM calls before Interface arg-mismatch
            # raised). Use NaN so aggregation distinguishes "actually free"
            # from "cost not captured". Downstream code should treat NaN
            # rows as partial observations.
            import math
            print(f'  [error on {example.name}: {type(e).__name__}: {e}]')
            return dict(
                predicted_output=f'**exception raised**: {type(e).__name__}: {e}',
                expected_output=example.expected_output,
                correct=False,
                input_tokens=math.nan,
                output_tokens=math.nan,
                latency=math.nan,
                cost=math.nan,
            )

    def evaluate(self, dataset: Dataset, interface: Interface) -> Path:
        """Evaluate and optionally save prompt trace for inspection."""
        from secretagent import config, savefile
        import pandas as pd
        from tqdm import tqdm

        expt_name = config.get('evaluate.expt_name')
        result_dir = config.require('evaluate.result_dir')
        prompt_trace = config.get('evaluate.prompt_trace') or False
        csv_path, jsonl_path = savefile.filename_list(
            result_dir, ['results.csv', 'results.jsonl'], file_under=expt_name)
        run_dir = csv_path.parent
        trace_path = run_dir / 'prompt_trace.jsonl' if prompt_trace else None

        results = []
        trace_file = open(trace_path, 'w') if prompt_trace and trace_path else None
        try:
            with open(jsonl_path, 'w') as fp:
                for example in tqdm(dataset.cases):
                    row = self.measure(example, interface)
                    row['case_name'] = example.name
                    row['expt_name'] = expt_name
                    prompt = example.input_args[0] if example.input_args else ''
                    if trace_file:
                        trace = {
                            'case_name': example.name,
                            'prompt': prompt,
                            'response': row.get('predicted_output', ''),
                            'correct': row.get('correct', False),
                            'golden': example.expected_output.get('golden_plan', '') if isinstance(example.expected_output, dict) else '',
                        }
                        trace_file.write(json.dumps(trace, ensure_ascii=False) + '\n')
                    try:
                        fp.write(json.dumps(row) + '\n')
                    except TypeError:
                        import warnings
                        warnings.warn(f'discarded row that cannot be serialized {row}')
                    results.append(row)
        finally:
            if trace_file:
                trace_file.close()

        df = pd.DataFrame(results).set_index('case_name')
        df.to_csv(csv_path)
        print(f'saved in {csv_path}')
        if prompt_trace and trace_path:
            print(f'prompt trace: {trace_path}')
        return csv_path


def load_dataset(
    task: str,
    prompt_mode: str = '5shot',
    stratified: bool = False,
    sample_n: int | None = None,
    sample_seed: int = 42,
    partition: str | None = None,
) -> Dataset:
    """Load NaturalPlan data.

    If partition is set (train/valid/test), load from pre-split file
    (e.g. data/calendar_valid.json) created by data/partition.py.
    Otherwise load from the monolithic JSON with optional stratified sampling.
    """
    if partition:
        split_path = _DATA_DIR / f'{task}_{partition}.json'
        if not split_path.exists():
            raise FileNotFoundError(
                f'Split file not found: {split_path}\n'
                f'Run: uv run python data/partition.py')
        return Dataset.model_validate_json(split_path.read_text())

    data_path = _DATA_DIR / DATA_FILES[task]
    if not data_path.exists():
        raise FileNotFoundError(
            f'Data file not found: {data_path}\n'
            f'Expected at: {_DATA_DIR}')
    with open(data_path) as f:
        data = json.load(f)
    if stratified and sample_n is not None and sample_n > 0:
        data = stratified_sample(data, STRATA_KEYS[task], sample_n, sample_seed)
    cases = []
    for key, inst in data.items():
        prompt = inst.get(f'prompt_{prompt_mode}', inst.get('prompt_5shot', ''))
        cases.append(Case(
            name=key,
            input_args=(prompt,),
            expected_output=inst,
        ))
    return Dataset(name=f'naturalplan_{task}', split=task, cases=cases)


app = typer.Typer()


@app.callback()
def callback():
    """NaturalPlan benchmark (calendar, meeting, trip)."""


@app.command(
    context_settings={"allow_extra_args": True, "allow_interspersed_args": False}
)
def run(
    ctx: typer.Context,
    config_file: str = typer.Option(..., help="Config YAML file"),
):
    """Run NaturalPlan evaluation. Extra args are config overrides in dot notation."""

    cfg_path = Path(config_file)
    if not cfg_path.is_absolute():
        cfg_path = _BENCHMARK_DIR / cfg_path
    config.configure(yaml_file=str(cfg_path), dotlist=ctx.args)
    config.set_root(_BENCHMARK_DIR)

    task = config.require('dataset.split')
    ptools = importlib.import_module(SPLIT_TO_MODULE[task])
    implement_via_config(ptools, config.require('ptools'))

    prompt_mode = config.get('dataset.prompt_mode') or '5shot'
    partition = config.get('dataset.partition')
    stratified = config.get('dataset.stratified') or False
    sample_n = config.get('dataset.sample_n')
    sample_seed = config.get('dataset.sample_seed') or 42
    dataset = load_dataset(
        task,
        prompt_mode,
        stratified=stratified,
        sample_n=sample_n,
        sample_seed=sample_seed,
        partition=partition,
    ).configure(
        shuffle_seed=config.get('dataset.shuffle_seed') if not stratified else None,
        n=config.get('dataset.n'),
    )
    print('dataset:', dataset.summary())

    entry_point = config.require('evaluate.entry_point')
    interface = getattr(ptools, entry_point)

    evaluator = NaturalPlanEvaluator(task)
    csv_path = evaluator.evaluate(dataset, interface)
    df = pd.read_csv(csv_path)
    print(df)
    print(f'\nAccuracy: {df["correct"].mean():.1%}')

    # Save run summary for reproducibility and quick view
    run_dir = csv_path.parent
    correct = df["correct"].astype(str).str.lower() == "true"
    acc = correct.mean()
    total_cost = df["cost"].sum() if "cost" in df.columns else 0
    total_time = df["latency"].sum() if "latency" in df.columns else 0
    reproduce_cmd = (
        "uv run python expt.py run --config-file " + config_file + " " + " ".join(ctx.args)
    )
    summary = {
        "reproduce_cmd": reproduce_cmd,
        "accuracy": acc,
        "total_cost_usd": round(total_cost, 6),
        "total_time_sec": round(total_time, 2),
        "n_samples": len(df),
    }
    summary_path = run_dir / "run_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary: {summary_path}")


if __name__ == '__main__':
    app()
