"""MedCalc-Bench benchmark experiment.

Example CLI commands:

    # run L0 baseline
    uv run python expt.py run --config-file conf/baseline.yaml

    # run L1 simulate with 3 examples
    uv run python expt.py run --config-file conf/simulate.yaml dataset.n=3

    # quick test with echo
    uv run python expt.py quick_test --config-file conf/baseline.yaml

    # override model
    uv run python expt.py run --config-file conf/simulate.yaml llm.model=together_ai/Qwen/Qwen2.5-72B-Instruct-Turbo
"""

import json
import random
import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import typer

from secretagent import record, config
from secretagent.core import implement_via_config, Interface
from secretagent.dataset import Dataset, Case
from secretagent.evaluate import Evaluator

import ptools

from accuracy import calculate_accuracy


# =============================================================================
# Evaluator
# =============================================================================

class MedCalcEvaluator(Evaluator):
    """Evaluator with MedCalc-Bench accuracy metrics.

    Overrides measure() to pass Case metadata (category, output_type,
    lower_limit, upper_limit) to the accuracy evaluation.
    """

    def compare_predictions(self, predicted_output, expected_output) -> dict[str, Any]:
        # Not used directly — measure() handles accuracy with metadata
        return {}

    def measure(self, example: Case, interface: Interface) -> dict[str, Any]:
        meta = example.metadata or {}

        with record.recorder() as records:
            try:
                predicted_output = interface(*example.input_args)
            except Exception as ex:
                predicted_output = f'**exception raised**: {ex}'

        llm_usage_stats = self.aggregate_usage_stats(records)

        # Extract numeric prediction for numeric calculators. Date and
        # weeks/days outputs must be scored from the raw model output,
        # otherwise "08/31/2023" collapses to 2023 before accuracy sees it.
        predicted = _extract_number(predicted_output)
        output_type = meta.get('output_type', 'numeric')
        output_type_lower = str(output_type).lower()
        predicted_for_accuracy = (
            predicted_output
            if output_type_lower == 'date'
            or 'week' in output_type_lower
            or 'day' in output_type_lower
            else predicted
        )

        # Run MedCalc accuracy evaluation
        acc = calculate_accuracy(
            predicted=predicted_for_accuracy,
            ground_truth=example.expected_output,
            lower_limit=meta.get('lower_limit'),
            upper_limit=meta.get('upper_limit'),
            output_type=output_type,
            category=meta.get('category', 'formula-based'),
        )

        result = dict(
            predicted_output=predicted_output,
            predicted_numeric=predicted,
            expected_output=example.expected_output,
            correct=float(acc.is_within_tolerance),
            exact_match=float(acc.is_exact_match),
            within_limits=float(acc.is_within_limits),
            absolute_error=acc.absolute_error,
            calculator_name=meta.get('calculator_name', ''),
            category=meta.get('category', ''),
            output_type=meta.get('output_type', ''),
            **llm_usage_stats,
        )
        if config.get('evaluate.record_details'):
            result['rollout'] = records
        return result


def _extract_number(value: Any) -> Optional[float]:
    """Extract a numeric value from LLM output."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value)
    if s.startswith('**exception'):
        return None
    # Try direct float conversion
    try:
        return float(s)
    except ValueError:
        pass
    # Try to extract from <answer> tags
    match = re.search(r'<answer>\s*([\d.eE+-]+)\s*</answer>', s)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    # Try to extract from ANSWER: pattern
    match = re.search(r'ANSWER:\s*([\d.eE+-]+)', s)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    # Try to find the last number in the string
    numbers = re.findall(r'-?\d+\.?\d*', s)
    if numbers:
        try:
            return float(numbers[-1])
        except ValueError:
            pass
    return None


# =============================================================================
# Dataset loading
# =============================================================================

FORMULA_CATEGORIES = {'physical', 'lab test', 'dosage'}
RULE_CATEGORIES = {'risk', 'diagnosis', 'severity'}

# Backward-compatible alias for older configs and checked-in run artifacts.
EQUATION_CATEGORIES = FORMULA_CATEGORIES


def _category_filter_set(value: Any) -> set[str] | None:
    """Resolve dataset.category_filter into MedCalc category labels."""
    if value is None or value == '':
        return None
    if isinstance(value, str):
        key = value.strip().lower()
        if key in {'formula', 'formulas', 'formula-based'}:
            return set(FORMULA_CATEGORIES)
        if key in {'equation', 'equations', 'equation-based'}:
            return set(FORMULA_CATEGORIES)
        if key in {'rule', 'rules', 'rule-based'}:
            return set(RULE_CATEGORIES)
        if key == 'date':
            return {'date'}
        values = [part.strip().lower() for part in value.split(',')]
        return {part for part in values if part}
    if isinstance(value, (list, tuple, set)):
        return {str(part).strip().lower() for part in value if str(part).strip()}
    raise ValueError(f'Unsupported dataset.category_filter={value!r}')


def _apply_dataset_filters(cases: list[Case]) -> list[Case]:
    category_filter = _category_filter_set(config.get('dataset.category_filter'))
    if not category_filter:
        return cases
    filtered = [
        case for case in cases
        if str((case.metadata or {}).get('category', '')).lower()
        in category_filter
    ]
    print(
        f'Category filter {sorted(category_filter)}: '
        f'{len(filtered)} / {len(cases)} cases'
    )
    return filtered


def load_dataset(split: str) -> Dataset:
    """Load MedCalc-Bench from HuggingFace and convert to secretagent Dataset."""
    from datasets import load_dataset as hf_load

    print(f"Loading MedCalc-Bench {split} split from HuggingFace...")
    ds = hf_load("ncbi/MedCalc-Bench-v1.2", split=split)

    cases = []
    for idx, row in enumerate(ds):
        case = _parse_row(row, idx, split)
        if case is not None:
            cases.append(case)

    cases = _apply_dataset_filters(cases)
    print(f"Loaded {len(cases)} cases from {split} split")
    return Dataset(name='medcalc', split=split, cases=cases)


def _parse_row(row: dict, idx: int, split: str) -> Optional[Case]:
    """Parse a HuggingFace dataset row into a Case."""
    try:
        output_type = row.get("Output Type", "decimal").lower()
        gt_raw = str(row.get("Ground Truth Answer", ""))

        # Parse ground truth based on output type
        if output_type == "date":
            gt_answer = gt_raw.strip()
        elif "week" in output_type or "day" in output_type:
            gt_answer = gt_raw.strip()
        else:
            gt_val = row.get("Ground Truth Answer", 0)
            if isinstance(gt_val, str):
                match = re.search(r'-?\d+\.?\d*', gt_val)
                gt_answer = float(match.group()) if match else 0.0
            else:
                gt_answer = float(gt_val)

        # Parse limits
        lower_limit = row.get("Lower Limit")
        if lower_limit == "" or lower_limit is None:
            lower_limit = None
        else:
            try:
                lower_limit = float(lower_limit)
            except (ValueError, TypeError):
                lower_limit = None

        upper_limit = row.get("Upper Limit")
        if upper_limit == "" or upper_limit is None:
            upper_limit = None
        else:
            try:
                upper_limit = float(upper_limit)
            except (ValueError, TypeError):
                upper_limit = None

        row_number = row.get("Row Number", idx)
        try:
            row_number = int(row_number)
        except (ValueError, TypeError):
            row_number = idx
        calculator_name = row.get("Calculator Name", "unknown")

        return Case(
            name=f'{split}.{row_number:04d}',
            input_args=(row.get("Patient Note", ""), row.get("Question", "")),
            expected_output=gt_answer,
            metadata={
                'calculator_name': calculator_name,
                'category': row.get("Category", "unknown"),
                'output_type': row.get("Output Type", "decimal"),
                'lower_limit': lower_limit,
                'upper_limit': upper_limit,
                'row_number': row_number,
            },
        )
    except Exception as e:
        print(f"Warning: Failed to parse row {idx}: {e}")
        return None


# =============================================================================
# Stratified sampling
# =============================================================================

def stratified_sample(cases: list[Case], n: int, seed: int = 42) -> list[Case]:
    """Stratified sample preserving calculator_name proportions.

    Uses largest-remainder method: each calculator gets at least 1
    representative (if n >= num_calculators).
    """
    if n >= len(cases):
        result = list(cases)
        random.Random(seed).shuffle(result)
        return result

    rng = random.Random(seed)

    # Group by calculator_name
    groups: dict[str, list[Case]] = {}
    for case in cases:
        calc = (case.metadata or {}).get('calculator_name', 'unknown')
        groups.setdefault(calc, []).append(case)

    for items in groups.values():
        rng.shuffle(items)

    if n < len(groups):
        flat = list(cases)
        rng.shuffle(flat)
        return flat[:n]

    total = len(cases)
    exact = {name: len(items) * n / total for name, items in groups.items()}
    allocs = {name: max(int(e), 1) for name, e in exact.items()}

    allocated = sum(allocs.values())
    remaining = n - allocated

    if remaining > 0:
        remainders = [(name, exact[name] - allocs[name]) for name in groups]
        remainders.sort(key=lambda x: x[1], reverse=True)
        for name, _ in remainders:
            if remaining <= 0:
                break
            if allocs[name] < len(groups[name]):
                allocs[name] += 1
                remaining -= 1
    elif remaining < 0:
        trimmable = [(name, allocs[name]) for name in groups if allocs[name] > 1]
        trimmable.sort(key=lambda x: x[1], reverse=True)
        for name, _ in trimmable:
            if remaining >= 0:
                break
            allocs[name] -= 1
            remaining += 1

    selected = []
    for name, items in groups.items():
        selected.extend(items[:allocs[name]])

    rng.shuffle(selected)
    return selected


def per_calculator_sample(
    cases: list[Case],
    per_calculator_n: int,
    seed: int = 42,
    skip_per_calculator: int = 0,
) -> list[Case]:
    """Balanced sample with up to N cases per calculator.

    skip_per_calculator lets a second sample use the next cases from the same
    seeded per-calculator ordering, giving a simple disjoint eval slice.
    """
    rng = random.Random(seed)
    groups: dict[str, list[Case]] = {}
    for case in cases:
        calc = (case.metadata or {}).get('calculator_name', 'unknown')
        groups.setdefault(calc, []).append(case)

    selected: list[Case] = []
    for items in groups.values():
        rng.shuffle(items)
        start = max(0, skip_per_calculator)
        stop = start + per_calculator_n
        selected.extend(items[start:stop])

    rng.shuffle(selected)
    return selected


def stratified_split(cases: list[Case], n_train: int, n_eval: int,
                     seed: int = 42) -> tuple[list[Case], list[Case]]:
    """Split cases into disjoint train/eval sets, stratified by calculator_name.

    Each calculator gets n_train/total and n_eval/total cases respectively,
    with no overlap between the two sets.
    """
    rng = random.Random(seed)

    # Group by calculator_name and shuffle within each group
    groups: dict[str, list[Case]] = {}
    for case in cases:
        calc = (case.metadata or {}).get('calculator_name', 'unknown')
        groups.setdefault(calc, []).append(case)
    for items in groups.values():
        rng.shuffle(items)

    n_per_calc_train = max(1, n_train // len(groups))
    n_per_calc_eval = max(1, n_eval // len(groups))

    train_cases = []
    eval_cases = []
    for name, items in groups.items():
        n_t = min(n_per_calc_train, len(items))
        train_cases.extend(items[:n_t])
        remaining = items[n_t:]
        n_e = min(n_per_calc_eval, len(remaining))
        eval_cases.extend(remaining[:n_e])

    rng.shuffle(train_cases)
    rng.shuffle(eval_cases)
    return train_cases, eval_cases


# =============================================================================
# Setup
# =============================================================================

_EXTRA_ARGS = {"allow_extra_args": True, "allow_interspersed_args": False}


def setup(ctx: typer.Context, config_file: Path | None = None):
    """Load config, dataset, and configure interfaces.

    Returns (dataset, interface) ready for evaluation.
    """
    if config_file is None:
        config_file = Path(__file__).parent / 'conf' / 'baseline.yaml'
    config.configure(yaml_file=config_file, dotlist=ctx.args)
    config.set_root(Path(__file__).parent)

    # Load dataset
    split = config.require('dataset.split')
    dataset = load_dataset(split)

    # Apply stratified sampling if configured
    stratified = config.get('dataset.stratified', False)
    n = config.get('dataset.n')
    shuffle_seed = config.get('dataset.shuffle_seed', 42)

    per_calc_n = config.get('dataset.per_calculator_n')
    per_calc_skip = int(config.get('dataset.per_calculator_skip', 0) or 0)

    if per_calc_n:
        dataset.cases = per_calculator_sample(
            dataset.cases,
            int(per_calc_n),
            seed=shuffle_seed,
            skip_per_calculator=per_calc_skip,
        )
        print(
            f'Per-calculator sample: {len(dataset.cases)} cases '
            f'({per_calc_n}/calc, skip={per_calc_skip})'
        )
    elif stratified and n:
        dataset.cases = stratified_sample(dataset.cases, int(n), seed=shuffle_seed)
        print(f'Stratified sample: {len(dataset.cases)} cases')
    elif stratified and not n:
        # Default: 3 per calculator
        num_calcs = len(set(
            (c.metadata or {}).get('calculator_name', '') for c in dataset.cases
        ))
        target_n = num_calcs * 3
        dataset.cases = stratified_sample(dataset.cases, target_n, seed=shuffle_seed)
        print(f'Stratified sample (3/calc): {len(dataset.cases)} cases')
    else:
        dataset = dataset.configure(
            shuffle_seed=shuffle_seed,
            n=n or None,
        )

    print('dataset is', dataset.summary())

    # Bind interfaces from config
    implement_via_config(ptools, config.require('ptools'))

    # Get entry point interface
    entry_point_name = config.get('evaluate.entry_point', 'calculate_medical_value')
    interface = getattr(ptools, entry_point_name)

    return dataset, interface


# =============================================================================
# CLI
# =============================================================================

app = typer.Typer()


@app.callback()
def callback():
    """MedCalc-Bench benchmark."""


@app.command(context_settings=_EXTRA_ARGS)
def run(ctx: typer.Context,
        config_file: Path = typer.Option(None, help="Config YAML file")):
    """Run MedCalc-Bench evaluation.

    Extra args are parsed as config overrides in dot notation, e.g.:
        uv run python expt.py run --config-file conf/baseline.yaml dataset.n=10
    """
    dataset, interface = setup(ctx, config_file)

    evaluator = MedCalcEvaluator()
    csv_path = evaluator.evaluate(dataset, interface)

    df = pd.read_csv(csv_path)
    print()
    print(df[['predicted_numeric', 'expected_output', 'correct',
              'calculator_name', 'category']].to_string())
    print()
    print(f"Accuracy (within tolerance): {df['correct'].mean():.3f}")
    print(f"Exact match: {df['exact_match'].mean():.3f}")
    if 'cost' in df.columns:
        print(f"Total cost: ${df['cost'].sum():.4f}")


@app.command(context_settings=_EXTRA_ARGS)
def quick_test(ctx: typer.Context,
               config_file: Path = typer.Option(None, help="Config YAML file")):
    """Quick test: run one example with echo enabled."""
    dataset, interface = setup(ctx, config_file)

    import pprint
    pprint.pprint(dict(config.GLOBAL_CONFIG))

    example = dataset.cases[0]
    print(f'\nCalculator: {(example.metadata or {}).get("calculator_name")}')
    print(f'Question: {example.input_args[1]}')
    print(f'Expected: {example.expected_output}')

    with config.configuration(
            cachier={'enable_caching': False},
            echo={'service': True, 'llm_input': True, 'llm_output': True,
                  'code_eval_input': True, 'code_eval_output': True}):
        with record.recorder() as records:
            predicted = interface(*example.input_args)

    print(f'\nPredicted: {predicted}')
    predicted_num = _extract_number(predicted)
    print(f'Numeric: {predicted_num}')

    acc = calculate_accuracy(
        predicted=predicted_num,
        ground_truth=example.expected_output,
        output_type=(example.metadata or {}).get('output_type', 'numeric'),
        category=(example.metadata or {}).get('category', 'formula-based'),
    )
    print(f'Correct (tolerance): {acc.is_within_tolerance}')
    print(f'Exact match: {acc.is_exact_match}')
    pprint.pprint(records)


if __name__ == '__main__':
    app()
