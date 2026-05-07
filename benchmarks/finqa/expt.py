"""FinQA benchmark runner (config file + FinQAEvaluator).

From ``benchmarks/finqa``::

    uv run python expt.py run --config-file conf/conf.yaml dataset.n=5
    uv run python expt.py run --config-file conf/zeroshot_prompt.yaml evaluate.expt_name=zp

Or use the generic CLI (same cwd)::

    uv run python -m secretagent.cli.expt run --interface ptools.answer_finqa \\
      --evaluator evaluator.FinQAEvaluator evaluate.expt_name=sim
"""

from __future__ import annotations

import pprint
import sys
from pathlib import Path

import pandas as pd
import typer

_BENCHMARK_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BENCHMARK_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))
sys.path.insert(0, str(_BENCHMARK_DIR))

from secretagent import config, record
from secretagent.core import implement_via_config
from secretagent.dataset import Dataset

import evaluator as finqa_evaluator
import ptools

_EXTRA_ARGS = {"allow_extra_args": True, "allow_interspersed_args": False}

app = typer.Typer()


def _setup(config_file: str, extra_args: list[str]) -> Dataset:
    cfg_path = Path(config_file)
    if not cfg_path.is_absolute():
        cfg_path = _BENCHMARK_DIR / cfg_path
    config.configure(yaml_file=str(cfg_path), dotlist=extra_args)
    config.set_root(_BENCHMARK_DIR)

    split = config.require("dataset.split")
    dataset_path = _BENCHMARK_DIR / "data" / f"{split}.json"
    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Missing {dataset_path}. Run:\n"
            "  uv run python benchmarks/finqa/data/download.py\n"
            "  uv run python benchmarks/finqa/data/build_datasets.py"
        )
    dataset = Dataset.model_validate_json(dataset_path.read_text())
    dataset.configure(
        shuffle_seed=config.get("dataset.shuffle_seed"),
        n=config.get("dataset.n") or None,
    )
    implement_via_config(ptools, config.require("ptools"))
    print("dataset:", dataset.summary())
    return dataset


@app.command(context_settings=_EXTRA_ARGS)
def run(
    ctx: typer.Context,
    config_file: str = typer.Option("conf/conf.yaml", help="YAML config under finqa/"),
):
    """Evaluate ``ptools.answer_finqa`` on the configured split."""
    dataset = _setup(config_file, ctx.args)
    ev = finqa_evaluator.FinQAEvaluator()
    iface = ptools.answer_finqa
    csv_path = ev.evaluate(dataset, iface)
    df = pd.read_csv(csv_path)
    print(df)
    if "scored" in df.columns:
        scored = df[df["scored"] == True]  # noqa: E712
        if len(scored):
            print(f"\nAccuracy (labeled only): {scored['correct'].mean():.1%} ({len(scored)} cases)")
    elif "correct" in df.columns:
        print(f"\nAccuracy: {df['correct'].mean():.1%}")


@app.command(context_settings=_EXTRA_ARGS)
def quick_test(
    ctx: typer.Context,
    config_file: str = typer.Option("conf/conf.yaml", help="YAML config"),
):
    """Run one example with caching off and verbose echo."""
    dataset = _setup(config_file, ctx.args)
    case = dataset.cases[0]
    pprint.pprint(config.GLOBAL_CONFIG)
    print("input (truncated):", str(case.input_args[0])[:1200], "...")
    with config.configuration(
        cachier={"enable_caching": False},
        echo={
            "model": True,
            "llm_input": True,
            "llm_output": True,
        },
    ):
        with record.recorder() as rec:
            out = ptools.answer_finqa(*case.input_args)
    print("predicted:", out)
    print("expected: ", case.expected_output)
    print(finqa_evaluator.FinQAEvaluator().compare_predictions(out, case.expected_output))
    pprint.pprint(rec)


if __name__ == "__main__":
    app()
