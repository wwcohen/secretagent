"""Run Pareto optimization on MedCalc benchmark across levels and models."""

import math

import typer

from search_spaces import LEVELS, MODELS, medcalc_space
from secretagent.optimize.encoder import decode_dict
from secretagent.optimize.pareto import EvalCache
from secretagent.optimize.viz import plot_pareto_frontier

app = typer.Typer()

_MODEL_LABELS = {
    "together_ai/deepseek-ai/DeepSeek-V3": "DSv3",
    "together_ai/deepseek-ai/DeepSeek-V3.1": "DSv3.1",
}


def _model_label(model: str) -> str:
    return _MODEL_LABELS.get(model, model.split("/")[-1])


def _dominates(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return (a[0] >= b[0] and a[1] <= b[1]) and (a[0] > b[0] or a[1] < b[1])


@app.command()
def main(
    dataset_n: int = typer.Option(5, help="Instances per evaluation"),
    timeout: int = typer.Option(600, help="Timeout per config (seconds)"),
    no_plot: bool = typer.Option(False, help="Skip plot generation"),
    levels: str = typer.Option(
        ",".join(LEVELS), help="Comma-separated levels to search"
    ),
):
    """Run exhaustive search over MedCalc levels x models."""
    selected = {l.strip(): LEVELS[l.strip()] for l in levels.split(",")}
    dims, fixed = medcalc_space()
    total = len(selected) * len(MODELS)

    print(f"MedCalc Pareto search: {len(selected)} levels x {len(MODELS)} models = {total} configs")
    print(f"  Levels: {list(selected)}")
    print(f"  Models: {[_model_label(m) for m in MODELS]}")
    print()

    all_results: list[tuple[str, float, float]] = []

    for level_name, config_file in selected.items():
        print(f"=== {level_name} ({config_file}) ===")
        base_command = f"uv run python expt.py run --config-file {config_file}"
        base_dotlist = [f"dataset.n={dataset_n}"]

        eval_cache = EvalCache(
            dims=dims,
            fixed_overrides=fixed,
            base_command=base_command,
            base_dotlist=base_dotlist,
            timeout=timeout,
            metric="correct",
            expt_prefix=f"pareto_{level_name}",
            label_fn=lambda d, c, _ln=level_name: _ln,
        )

        for model_idx in range(len(MODELS)):
            acc, cost = eval_cache([model_idx])
            all_results.append((level_name, acc, cost))
        print()

    # Compute Pareto frontier
    frontier = []
    for i, (label_i, acc_i, cost_i) in enumerate(all_results):
        dominated = False
        for j, (label_j, acc_j, cost_j) in enumerate(all_results):
            if i != j and _dominates((acc_j, cost_j), (acc_i, cost_i)):
                dominated = True
                break
        if not dominated and cost_i < math.inf:
            frontier.append((label_i, acc_i, cost_i))

    frontier.sort(key=lambda x: -x[1])

    print("=" * 70)
    print(f"PARETO FRONTIER (MedCalc, {total} total configs)")
    print("=" * 70)
    print(f"  {'Config':<10} {'Correct':>10} {'Cost/q':>10}")
    for label, acc, cost in frontier:
        print(f"  {label:<10} {acc:>9.1%} ${cost:>9.4f}")

    print()
    if len(all_results) > len(frontier):
        frontier_set = {(l, a, c) for l, a, c in frontier}
        print("Dominated configs:")
        for label, acc, cost in all_results:
            if (label, acc, cost) not in frontier_set:
                print(f"  {label:<10} {acc:>9.1%} ${cost:>9.4f}")
        print()

    print(f"{len(frontier)} Pareto-optimal / {len(all_results)} total evaluated")

    if not no_plot:
        plot_pareto_frontier(
            results=all_results,
            title="cost vs correct",
            output_path="results/pareto_medcalc.png",
            metric_name="correct",
            show=False,
        )


if __name__ == "__main__":
    app()
