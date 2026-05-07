"""RuleArena benchmark experiment.

Example CLI commands:

    # run L1 on airline domain (30 instances, validation split)
    uv run python expt.py run evaluate.expt_name=l1_airline dataset.domain=airline \
        ptools.compute_rulearena_answer.method=direct \
        ptools.compute_rulearena_answer.fn=ptools.l1_extract_workflow

    # run L0 oracle on tax
    uv run python expt.py run evaluate.expt_name=l0_tax dataset.domain=tax \
        ptools.compute_rulearena_answer.method=direct \
        ptools.compute_rulearena_answer.fn=ptools.l0_oracle_workflow

    # run L3 ReAct on airline
    uv run python expt.py run evaluate.expt_name=l3_airline dataset.domain=airline \
        ptools.compute_rulearena_answer.method=simulate_pydantic \
        "ptools.compute_rulearena_answer.tools=[ptools.extract_airline_params,ptools.compute_airline_calculator]"

    # override model and number of instances
    uv run python expt.py run llm.model=claude-haiku-4-5-20251001 dataset.n=10

    # quick trace of first instance
    uv run python expt.py quick_test dataset.domain=airline \
        ptools.compute_rulearena_answer.method=direct \
        ptools.compute_rulearena_answer.fn=ptools.l1_extract_workflow
"""

import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
import pprint
import typer

from secretagent import config, record
from secretagent.core import implement_via_config
from secretagent.dataset import Dataset, Case
from secretagent.evaluate import Evaluator

import ptools

DATA_DIR = Path(__file__).parent / "data"


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

def _within_tolerance(predicted: Any, expected: Any, tol: float = 0.01) -> bool:
    try:
        p = float(predicted)
        e = float(expected)
    except (TypeError, ValueError):
        return False
    if abs(e) < 1e-9:
        return abs(p - e) < 0.01
    return abs(p - e) / abs(e) <= tol


def _isclose_match(predicted: Any, expected: Any) -> bool:
    """Tight tolerance match using np.isclose (rtol=1e-5, atol=1e-8)."""
    try:
        p = float(predicted)
        e = float(expected)
    except (TypeError, ValueError):
        return False
    return bool(np.isclose(p, e))


class RuleArenaEvaluator(Evaluator):
    def compare_predictions(self, predicted_output, expected_output) -> dict[str, Any]:
        if isinstance(expected_output, bool):
            correct = float(bool(predicted_output) == expected_output)
            correct_tolerance = correct
        else:
            correct = float(_within_tolerance(predicted_output, expected_output))
            correct_tolerance = float(_isclose_match(predicted_output, expected_output))
        if isinstance(predicted_output, str) and predicted_output.startswith("**exception"):
            failure_mode = "extraction_failure"
        elif predicted_output is None:
            failure_mode = "extraction_failure"
        elif correct:
            failure_mode = "none"
        else:
            failure_mode = "calculation_error"
        return dict(correct=correct, correct_tolerance=correct_tolerance, failure_mode=failure_mode)


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

def _load_rules(domain: str) -> str:
    if domain == "airline":
        rules_file = DATA_DIR / "airline" / "reference_rules_textual.txt"
    elif domain == "nba":
        rules_file = DATA_DIR / "nba" / "reference_rules.txt"
    elif domain == "tax":
        return ""
    else:
        raise ValueError(f"Unknown domain: {domain!r}")
    if rules_file.exists():
        return rules_file.read_text(encoding="utf-8")
    return f"Rules for {domain} domain"


def _compute_ground_truth(domain: str, problem_data: dict, metadata: dict) -> Any:
    if domain == "nba":
        return problem_data.get("answer")
    try:
        if domain == "airline":
            from calculators.airline import compute_airline_fee
            return compute_airline_fee(metadata)
        if domain == "tax":
            from calculators.tax import compute_tax_fee
            return compute_tax_fee(metadata)
    except Exception:
        pass
    return None


def _iter_domain(domain: str, split: str, complexity: str = "all"):
    """Yield (orig_idx, level, problem_data, metadata) from a local split file."""
    split_file = DATA_DIR / domain / f"{split}.jsonl"
    with open(split_file, encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            level = record["level"]
            orig_idx = record["orig_idx"]
            if complexity != "all" and level != int(complexity):
                continue
            problem_data = {k: v for k, v in record.items() if k not in ("level", "orig_idx")}
            metadata = problem_data.get("info", {}) if domain == "airline" else problem_data
            yield orig_idx, level, problem_data, metadata


def load_dataset(domain: str, split: str, complexity: str = "all") -> Dataset:
    rules_text = _load_rules(domain)
    cases = []

    for idx, level, problem_data, metadata in _iter_domain(domain, split, complexity):
        instance_id = f"{domain}_{level}_{idx}"
        problem_text = problem_data.get("prompt", "")

        # Pre-build tax forms query so the prompt_llm template can use $forms_text
        if domain == "tax":
            try:
                forms_text = ptools.build_tax_forms_query(metadata)
                # Sanitize non-ASCII for portability
                forms_text = forms_text.encode("ascii", errors="replace").decode("ascii")
            except Exception:
                forms_text = problem_text
        else:
            forms_text = ""

        ground_truth = _compute_ground_truth(domain, problem_data, metadata)

        cases.append(Case(
            name=instance_id,
            input_args=(
                problem_text,
                domain,
                rules_text,
                json.dumps(metadata, default=str),
                forms_text,
            ),
            expected_output=ground_truth,
        ))

    return Dataset(name=f"rulearena_{domain}", split=split, cases=cases)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

app = typer.Typer()


@app.callback()
def callback():
    """RuleArena benchmark: rule-guided reasoning across airline, NBA, and tax domains."""


CONFIG_DIR = Path(__file__).parent / "conf"


@app.command(context_settings={"allow_extra_args": True, "allow_interspersed_args": False})
def run(
      ctx: typer.Context,
      config_file: Optional[Path] = typer.Option(None, help="Path to YAML config (default: conf/conf.yaml)"),
      expt_name: str = typer.Option(None, help="Set evaluate.expt_name"),
  ):
    """Run RuleArena evaluation.

    Extra args are parsed as config overrides in dot notation, e.g.:
        uv run python expt.py run llm.model=gpt-4o dataset.domain=nba dataset.n=10
    """
    if config_file is None:
        config_file = Path(__file__).parent / "conf" / "conf.yaml"
    config.configure(yaml_file=config_file, dotlist=ctx.args)
    config.set_root(Path(__file__).parent)

    domain = config.require("dataset.domain")
    split = config.require("dataset.split")
    complexity = config.get("dataset.complexity") or "all"

    dataset = load_dataset(domain, split, complexity).configure(
        shuffle_seed=config.get("dataset.shuffle_seed"),
        n=config.get("dataset.n") or None,
    )
    print("dataset is", dataset.summary())

    implement_via_config(ptools, config.require("ptools"))

    evaluator = RuleArenaEvaluator()
    csv_path = evaluator.evaluate(dataset, ptools.compute_rulearena_answer)

    df = pd.read_csv(csv_path)
    print(df)
    print()
    print(df.select_dtypes(include='number').mean())

@app.command(context_settings={"allow_extra_args": True, "allow_interspersed_args": False})
def quick_test(
      ctx: typer.Context,
      config_file: Optional[Path] = typer.Option(None, help="Path to YAML config (default: conf/conf.yaml)"),
      expt_name: str = typer.Option(None, help="Set evaluate.expt_name"),
  ):
    """Run a single instance with full trace output for debugging."""
    if config_file is None:
        config_file = Path(__file__).parent / "conf" / "conf.yaml"
    config.configure(yaml_file=config_file, dotlist=ctx.args)
    config.set_root(Path(__file__).parent)
    pprint.pprint(config.GLOBAL_CONFIG)

    domain = config.require("dataset.domain")
    split = config.require("dataset.split")
    complexity = config.get("dataset.complexity") or "all"

    dataset = load_dataset(domain, split, complexity).configure(
        shuffle_seed=config.get("dataset.shuffle_seed"),
        n=config.get("dataset.n") or None,
    )
    print("dataset is", dataset.summary())

    implement_via_config(ptools, config.require("ptools"))

    input_args = dataset.cases[0].input_args
    print("input_args[:2]", input_args[:2])
    with config.configuration(
        cachier={"enable_caching": False},
        echo={
            "service": True,
            "llm_input": True,
            "llm_output": True,
            "code_eval_input": True,
            "code_eval_output": True,
        },
    ):
        with record.recorder() as records:
            predicted_output = ptools.compute_rulearena_answer(*input_args)

    print("predicted output", predicted_output)
    print("expected output ", dataset.cases[0].expected_output)
    pprint.pprint(records)


if __name__ == "__main__":
    app()
