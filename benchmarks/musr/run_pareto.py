"""Run Pareto optimization on MuSR benchmark across levels and models."""

import math
import time

import typer

from search_spaces import DOMAIN_LEVELS, DOMAIN_SPACES, MODELS
from secretagent.optimize.pareto import EvalCache
from secretagent.optimize.viz import plot_pareto_frontier

app = typer.Typer()

_MODEL_LABELS = {
    "together_ai/deepseek-ai/DeepSeek-V3.1": "DSv3.1",
    "together_ai/openai/gpt-oss-20b": "GPToss20B",
    "together_ai/openai/gpt-oss-120b": "GPToss120B",
}


def _model_label(model: str) -> str:
    return _MODEL_LABELS.get(model, model.split("/")[-1])


def _dominates(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """True if a dominates b (higher accuracy AND lower cost)."""
    return (a[0] >= b[0] and a[1] <= b[1]) and (a[0] > b[0] or a[1] < b[1])


@app.command()
def main(
    domain: str = typer.Option("murder", help="Domain: murder, object, team"),
    dataset_n: int = typer.Option(5, help="Instances per evaluation"),
    timeout: int = typer.Option(600, help="Timeout per config (seconds)"),
    metric: str = typer.Option("correct", help="Metric column to optimize"),
    no_plot: bool = typer.Option(False, help="Skip plot generation"),
):
    """Run exhaustive search over MuSR levels x models."""
    if domain not in DOMAIN_LEVELS:
        raise typer.BadParameter(
            f"Unknown domain: {domain}. Choose from {list(DOMAIN_LEVELS)}"
        )

    levels = DOMAIN_LEVELS[domain]
    dims, fixed = DOMAIN_SPACES[domain]()
    total = len(levels) * len(MODELS)

    print(f"MuSR Pareto search ({domain}): {len(levels)} levels x {len(MODELS)} models = {total} configs")
    print(f"  Levels: {list(levels)}")
    print(f"  Models: {[_model_label(m) for m in MODELS]}")
    print()

    t0 = time.time()
    all_results: list[tuple[str, float, float]] = []

    for level_name, config_file in levels.items():
        print(f"=== {level_name} ({config_file}) ===")
        base_command = f"uv run python expt.py run --config-file {config_file}"
        base_dotlist = [f"dataset.n={dataset_n}"]

        eval_cache = EvalCache(
            dims=dims,
            fixed_overrides=fixed,
            base_command=base_command,
            base_dotlist=base_dotlist,
            timeout=timeout,
            metric=metric,
            expt_prefix=f"pareto_{domain}_{level_name}",
            label_fn=lambda d, c, _ln=level_name: _ln,
        )

        for model_idx in range(len(MODELS)):
            acc, cost = eval_cache([model_idx])
            label = f"{level_name}/{_model_label(MODELS[model_idx])}"
            all_results.append((label, acc, cost))
        print()

    elapsed = time.time() - t0

    # Filter out failed configs (inf cost) for frontier and plotting
    valid_results = [(l, a, c) for l, a, c in all_results if c < math.inf]
    failed = [(l, a, c) for l, a, c in all_results if c >= math.inf]

    # Compute Pareto frontier
    frontier = []
    for i, (label_i, acc_i, cost_i) in enumerate(valid_results):
        dominated = False
        for j, (label_j, acc_j, cost_j) in enumerate(valid_results):
            if i != j and _dominates((acc_j, cost_j), (acc_i, cost_i)):
                dominated = True
                break
        if not dominated:
            frontier.append((label_i, acc_i, cost_i))

    frontier.sort(key=lambda x: -x[1])

    print("=" * 70)
    print(f"PARETO FRONTIER ({domain}, {total} total configs)")
    print("=" * 70)
    print(f"  {'Config':<30} {metric:>10} {'Cost/q':>10}")
    for label, acc, cost in frontier:
        print(f"  {label:<30} {acc:>9.1%} ${cost:>9.4f}")

    print()
    if len(valid_results) > len(frontier):
        frontier_set = {(l, a, c) for l, a, c in frontier}
        print("Dominated configs:")
        for label, acc, cost in valid_results:
            if (label, acc, cost) not in frontier_set:
                print(f"  {label:<30} {acc:>9.1%} ${cost:>9.4f}")
        print()

    if failed:
        print(f"Failed configs ({len(failed)}):")
        for label, acc, cost in failed:
            print(f"  {label:<30} (subprocess error)")
        print()

    print(f"{len(frontier)} Pareto-optimal / {len(valid_results)} valid / {len(all_results)} total")
    print(f"Wall clock: {elapsed:.0f}s ({elapsed/60:.1f}m)")
    print(f"Check API costs: uv run python -m secretagent.cli.costs llm_cache")

    if not no_plot and valid_results:
        plot_pareto_frontier(
            results=valid_results,
            title=f"MuSR {domain}: cost vs {metric}",
            output_path=f"results/pareto_{domain}.png",
            metric_name=metric,
            show=False,
        )


if __name__ == "__main__":
    app()
