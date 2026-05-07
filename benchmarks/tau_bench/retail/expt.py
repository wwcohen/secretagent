"""tau-bench retail benchmark experiment.

Example CLI commands (run from project root):

    # Download data first
    uv run benchmarks/tau_bench_retail/data/download.py

    # ReAct agent baseline (n=10 smoke test)
    uv run python benchmarks/tau_bench_retail/expt.py run --config-file conf/react.yaml dataset.n=10

    # Unstructured baseline
    uv run python benchmarks/tau_bench_retail/expt.py run --config-file conf/unstructured_baseline.yaml dataset.n=10

    # Single example with verbose output
    uv run python benchmarks/tau_bench_retail/expt.py quick-test --config-file conf/react.yaml

    # Override n and model
    uv run python benchmarks/tau_bench_retail/expt.py run --config-file conf/react.yaml dataset.n=50
"""

import json
import pprint
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import typer

_BENCHMARK_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BENCHMARK_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))
sys.path.insert(0, str(_BENCHMARK_DIR))

from secretagent import config, record
from secretagent.core import implement_via_config
from secretagent.dataset import Dataset, Case
from secretagent.evaluate import Evaluator

import ptools
from tau_env import TauEnv

# ---------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------

DATA_DIR = _BENCHMARK_DIR / "data"
DB_PATH = DATA_DIR / "db.json"
TASKS_PATH = DATA_DIR / "tasks.json"


def load_task_split(split_name: str = "base") -> list[str]:
    """Load task ids for a given split.

    Falls back to using ALL tasks if no split file or matching split found.
    """
    split_file = DATA_DIR / "tasks_split.json"
    if split_file.exists():
        splits = json.loads(split_file.read_text())
        if split_name in splits:
            return splits[split_name]

    # Fall back: use all task ids from tasks.json
    all_tasks = json.loads(TASKS_PATH.read_text())
    return [t["id"] for t in all_tasks]


def load_dataset(split_name: str = "base") -> Dataset:
    """Load tau-bench retail tasks as a Dataset of Cases.

    Each Case:
      input_args = (task_id,)    — matches tau_solve signature
      expected_output = "1.0"   — reward target (agent should achieve 1.0)
    """
    task_ids = load_task_split(split_name)

    # Load task metadata for metadata fields
    all_tasks = json.loads(TASKS_PATH.read_text())
    task_meta = {t["id"]: t for t in all_tasks}

    cases = []
    for task_id in task_ids:
        meta = task_meta.get(task_id, {})
        reward_basis = []
        if meta.get("evaluation_criteria"):
            reward_basis = meta["evaluation_criteria"].get("reward_basis", [])
        cases.append(Case(
            name=task_id,
            input_args=(task_id,),
            expected_output="1.0",
            metadata={"reward_basis": reward_basis},
        ))

    return Dataset(name="tau_bench_retail", split=split_name, cases=cases)


# ---------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------

class TauBenchEvaluator(Evaluator):
    """Evaluate tau-bench retail tasks.

    predicted_output is the reward string returned by tau_solve ('0.0' or '1.0').
    correct = True when reward >= 0.5 (i.e. the task was solved).
    """

    def compare_predictions(self, predicted_output, expected_output) -> dict[str, Any]:
        try:
            reward = float(predicted_output)
        except (ValueError, TypeError):
            reward = 0.0
        return dict(correct=(reward >= 0.5), reward=reward)


# ---------------------------------------------------------------
# CLI
# ---------------------------------------------------------------

app = typer.Typer()
_EXTRA_ARGS = {"allow_extra_args": True, "allow_interspersed_args": False}


def _setup(config_file: str, extra_args: list[str]) -> Dataset:
    """Load config, initialize environment, implement ptools, load dataset."""
    cfg_path = Path(config_file)
    if not cfg_path.is_absolute():
        cfg_path = _BENCHMARK_DIR / cfg_path
    config.configure(yaml_file=str(cfg_path), dotlist=extra_args)
    config.set_root(_BENCHMARK_DIR)

    # Validate data files exist
    if not DB_PATH.exists() or not TASKS_PATH.exists():
        raise FileNotFoundError(
            f"Data files not found. Run: uv run benchmarks/tau_bench_retail/data/download.py"
        )

    # Initialize the shared TauEnv (loaded once, reset per task inside tau_solve)
    env = TauEnv(DB_PATH, TASKS_PATH)
    ptools.load_env(env)

    split = config.get("dataset.split", "base")
    dataset = load_dataset(split).configure(
        shuffle_seed=config.get("dataset.shuffle_seed"),
        n=config.get("dataset.n"),
    )
    print(f"dataset: {dataset.summary()}")
    print(f"db stats: {env._base_db.statistics()}")

    # Implement all ptools from config
    implement_via_config(ptools, config.require("ptools"))
    return dataset


@app.command(context_settings=_EXTRA_ARGS)
def run(ctx: typer.Context,
        config_file: str = typer.Option(..., help="Config YAML file")):
    """Run tau-bench retail evaluation."""
    dataset = _setup(config_file, ctx.args)

    evaluator = TauBenchEvaluator()
    csv_path = evaluator.evaluate(dataset, ptools.tau_solve)
    df = pd.read_csv(csv_path)
    print(f"\nAccuracy: {df['correct'].mean():.1%} ({df['correct'].sum()}/{len(df)})")
    print(f"Avg reward: {df['reward'].mean():.3f}")
    if "cost" in df.columns:
        print(f"Avg cost: ${df['cost'].mean():.4f}/task")


@app.command(context_settings=_EXTRA_ARGS)
def quick_test(ctx: typer.Context,
               config_file: str = typer.Option(..., help="Config YAML file")):
    """Run a single task with verbose output for debugging."""
    dataset = _setup(config_file, ctx.args)
    pprint.pprint(config.GLOBAL_CONFIG)

    case = dataset.cases[0]
    task_id = case.input_args[0]
    task = ptools._CURRENT_ENV.get_task(task_id)

    print(f"\n--- Task {task_id} ---")
    if task.user_scenario and task.user_scenario.instructions:
        inst = task.user_scenario.instructions
        print(f"Request: {inst.reason_for_call}")
        print(f"Known:   {inst.known_info}")
        print(f"Unknown: {inst.unknown_info}")

    with config.configuration(
        cachier={"enable_caching": False},
        echo={"service": True, "llm_input": True, "llm_output": True},
    ):
        with record.recorder() as records:
            predicted = ptools.tau_solve(task_id)

    print(f"\nReward: {predicted}")
    print(f"\nRecords ({len(records)} steps):")
    for r in records:
        func = r.get("func", "?")
        cost = r.get("stats", {}).get("cost", 0)
        print(f"  {func}: cost=${cost:.4f}")


if __name__ == "__main__":
    app()
