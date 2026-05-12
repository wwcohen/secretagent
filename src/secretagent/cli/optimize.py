"""CLI for optimization over config spaces.

Usage::

    # Grid sweep from a YAML space definition
    uv run -m secretagent.cli.optimize sweep \\
        --command "uv run python benchmarks/musr/expt.py run --config-file conf/murder.yaml" \\
        --space-file sweep_space.yaml \\
        dataset.n=10 cachier.enable_caching=false

    # NSGA-II multi-objective search over a modular space
    uv run -m secretagent.cli.optimize nsga2 \\
        --interface ptools.compute_airline_answer \\
        --evaluator evaluator.AirlineEvaluator \\
        --space search_spaces.airline_modular_space \\
        --cwd airline --pop-size 12 --n-gen 5 \\
        dataset.n=10

    # Load and display sweep results
    uv run -m secretagent.cli.optimize summary sweep_results.csv
"""

from pathlib import Path

import typer
import yaml

from secretagent.optimize import ConfigSpace, GridSearchRunner

app = typer.Typer()

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_BENCH_ROOT = _PROJECT_ROOT / "benchmarks"

NSGA2_SPACES = {
    "airline": {"cwd": "rulearena/airline", "space_file": "rulearena/nsga2_airline.yaml"},
    "nba": {"cwd": "rulearena/nba", "space_file": "rulearena/nsga2_nba.yaml"},
    "tax": {"cwd": "rulearena/tax", "space_file": "rulearena/nsga2_tax.yaml"},
    "finqa": {"cwd": "finqa", "space_file": "finqa/nsga2.yaml"},
    "medcalc": {"cwd": "medcalc", "space_file": "medcalc/nsga2.yaml"},
    "tabmwp": {"cwd": "tabmwp", "space_file": "tabmwp/nsga2.yaml"},
    "sports": {"cwd": "bbh/sports_understanding", "space_file": "bbh/sports_understanding/nsga2.yaml"},
}


@app.callback()
def callback():
    """Grid search optimizer for secretagent configurations."""


_EXTRA_ARGS = {"allow_extra_args": True, "allow_interspersed_args": False}


@app.command(context_settings=_EXTRA_ARGS)
def sweep(
    ctx: typer.Context,
    command: str = typer.Option(..., help="Base command to run (quoted)"),
    space_file: str = typer.Option(..., help="YAML file defining search space"),
    prefix: str = typer.Option("sweep", help="Experiment name prefix"),
    cwd: str = typer.Option(None, help="Working directory for subprocess"),
    timeout: int = typer.Option(1800, help="Timeout per config in seconds"),
    metric: str = typer.Option("correct", help="Metric column to optimize"),
    output: str = typer.Option("sweep_summary.csv", help="Output summary CSV path"),
):
    """Run grid search over a config space."""
    # Load search space from YAML
    with open(space_file) as f:
        space_dict = yaml.safe_load(f)

    # Support both top-level dict and nested under 'variants' key
    if 'variants' not in space_dict:
        # Treat the whole file as the variants dict
        space_dict = {'variants': space_dict}

    space = ConfigSpace(**space_dict)

    runner = GridSearchRunner(
        command=command,
        space=space,
        base_dotlist=ctx.args,
        expt_prefix=prefix,
        cwd=cwd,
        timeout=timeout,
        metric=metric,
    )

    df = runner.run_all()

    # Save and display
    if output:
        runner.save_summary(output)

    print('\n' + '=' * 60)
    print('SWEEP RESULTS (sorted by accuracy)')
    print('=' * 60)
    display_cols = [c for c in df.columns
                    if c not in ('csv_path', 'config_idx')]
    print(df[display_cols].to_string(index=False))

    # Print best config
    best = df.iloc[0] if not df.empty else None
    if best is not None and best.get(metric) is not None:
        print(f'\nBest: {best["expt_name"]} — {metric}={best[metric]:.3f}')
        for k in space.variants.keys():
            print(f'  {k} = {best.get(k, "?")}')


@app.command(context_settings=_EXTRA_ARGS)
def nsga2(
    ctx: typer.Context,
    interface: str = typer.Option(None, help="Top-level interface (module.name)"),
    evaluator: str = typer.Option(None, help="Evaluator class (module.Class)"),
    space: str = typer.Option(None, help="Space function (module.func) returning (dims, compound_overrides)"),
    space_file: str = typer.Option(None, help="YAML file defining the modular search space"),
    cwd: str = typer.Option(".", help="Working directory for subprocesses"),
    pop_size: int = typer.Option(12, help="NSGA-II population size"),
    n_gen: int = typer.Option(5, help="Number of generations"),
    timeout: int = typer.Option(600, help="Timeout per config (seconds)"),
    metric: str = typer.Option("correct", help="Metric column to optimize"),
    seed: int = typer.Option(42, help="Random seed"),
    no_plot: bool = typer.Option(False, help="Skip plot generation"),
    dry_run: bool = typer.Option(False, help="Print sample commands without running"),
    output: str = typer.Option(None, help="Plot output path (default: results/nsga2.png)"),
):
    """Run NSGA-II multi-objective search over a modular config space.

    Define the space via YAML (--space-file) or Python (--space).

    YAML mode (recommended)::

        uv run -m secretagent.cli.optimize nsga2 \\
            --space-file nsga2_airline.yaml \\
            --cwd airline dataset.n=10

    Python mode::

        uv run -m secretagent.cli.optimize nsga2 \\
            --interface ptools.compute_airline_answer \\
            --space search_spaces.airline_modular_space \\
            --cwd airline dataset.n=10
    """
    import math
    import random
    import time
    from pathlib import Path

    from secretagent.implement.util import resolve_dotted
    from secretagent.optimize.encoder import (
        decode_dict, decode_modular, modular_space_from_yaml, space_size,
    )
    from secretagent.optimize.pareto import run_nsga2 as _run_nsga2
    from secretagent.optimize.viz import plot_pareto_frontier

    if space_file:
        dims, compound, metadata = modular_space_from_yaml(space_file)
        interface = interface or metadata.get("interface")
        evaluator = evaluator or metadata.get("evaluator")
    elif space:
        space_fn = resolve_dotted(space)
        dims, compound = space_fn()
    else:
        raise typer.BadParameter("Provide --space-file (YAML) or --space (Python function)")

    custom_command = metadata.get("command") if space_file else None
    if custom_command:
        import shlex
        base_command = shlex.split(custom_command)
    else:
        if not interface:
            raise typer.BadParameter("--interface is required (or set 'interface' or 'command' in YAML)")
        base_command = [
            "uv", "run", "python", "-m", "secretagent.cli.expt", "run",
            "--interface", interface,
        ]
        if evaluator:
            base_command += ["--evaluator", evaluator]
    base_dotlist = list(ctx.args)

    cwd_path = str(Path(cwd).resolve())

    total = space_size(dims)
    print(f"NSGA-II search: {len(dims)} dimensions, {total:,} configs")
    print(f"  cwd: {cwd_path}")
    print(f"  Genes:")
    for i, dim in enumerate(dims):
        tag = " (compound)" if dim.key in compound else ""
        print(f"    [{i}] {dim.key}: {dim.size} values{tag}")
    print()

    def label_fn(dims, vec):
        d = decode_dict(dims, vec)
        method = d.get("toplevel_method", "?")
        model = d.get("llm.model", "?").split("/")[-1]
        return f"{method}/{model}"

    if dry_run:
        random.seed(seed)
        dsizes = [d.size for d in dims]
        print("=== Dry run: sample chromosomes ===\n")
        for i in range(4):
            vec = [random.randint(0, s - 1) for s in dsizes]
            dotlist = decode_modular(dims, vec, compound)
            label = label_fn(dims, vec)
            print(f"Sample {i+1}: {vec}  ({label})")
            cmd = base_command + base_dotlist + dotlist + [f"evaluate.expt_name=nsga_{i+1:03d}"]
            print(f"  Command: {' '.join(cmd)}")
            print()
        return

    t0 = time.time()
    frontier, all_evaluated, gen_log = _run_nsga2(
        dims=dims,
        fixed_overrides=[],
        base_command=base_command,
        base_dotlist=base_dotlist,
        cwd=cwd_path,
        timeout=timeout,
        metric=metric,
        expt_prefix="nsga",
        pop_size=pop_size,
        n_gen=n_gen,
        seed=seed,
        label_fn=label_fn,
        compound_overrides=compound,
    )
    elapsed = time.time() - t0

    valid = [(c, a, cost) for c, a, cost in all_evaluated if cost < math.inf]
    failed = [(c, a, cost) for c, a, cost in all_evaluated if cost >= math.inf]

    print()
    print("=" * 70)
    print(f"PARETO FRONTIER ({len(valid)} valid / {len(all_evaluated)} evaluated)")
    print("=" * 70)
    print(f"  {'Config':<35} {metric:>10} {'Cost/q':>10}")
    for chrom, acc, cost in frontier:
        label = label_fn(dims, chrom)
        print(f"  {label:<35} {acc:>9.1%} ${cost:>9.4f}")

    if failed:
        print(f"\n  {len(failed)} configs failed (scored as 0%, inf cost)")

    print(f"\n  {len(frontier)} Pareto-optimal / {len(valid)} valid / {len(all_evaluated)} total")
    print(f"  Wall clock: {elapsed:.0f}s ({elapsed/60:.1f}m)")

    # Save structured results CSV
    import pandas as pd
    frontier_set = {tuple(c) for c, _, _ in frontier}
    rows = []
    for chrom, acc, cost in all_evaluated:
        label = label_fn(dims, chrom)
        method, model = (label.split("/", 1) + [""])[:2]
        rows.append({
            "config": label,
            "method": method,
            "model": model,
            metric: acc,
            "cost": cost,
            "frontier": tuple(chrom) in frontier_set,
            "valid": cost < math.inf,
        })
    summary_df = pd.DataFrame(rows)
    summary_path = Path(cwd_path) / "results" / "nsga2_summary.csv"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(summary_path, index=False)
    print(f"\n  Summary saved to {summary_path}")

    # Save per-generation convergence log
    if gen_log:
        gen_df = pd.DataFrame(gen_log)
        gen_path = Path(cwd_path) / "results" / "nsga2_generations.csv"
        gen_df.to_csv(gen_path, index=False)
        print(f"  Generation log saved to {gen_path}")

    if not no_plot and valid:
        plot_output = output or str(Path(cwd_path) / "results" / "nsga2.png")
        plot_results = [
            (label_fn(dims, chrom), acc, cost)
            for chrom, acc, cost in valid
        ]
        plot_pareto_frontier(
            results=plot_results,
            title=f"Cost vs {metric} (NSGA-II)",
            output_path=plot_output,
            metric_name=metric,
            show=False,
        )


@app.command(name="run-all", context_settings=_EXTRA_ARGS)
def run_all(
    ctx: typer.Context,
    benchmarks: list[str] = typer.Option(None, "--benchmark", "-b", help="Benchmark names (default: all)"),
    pop_size: int = typer.Option(12, help="NSGA-II population size"),
    n_gen: int = typer.Option(5, help="Number of generations"),
    timeout: int = typer.Option(600, help="Timeout per config (seconds)"),
    metric: str = typer.Option("correct", help="Metric column to optimize"),
    seed: int = typer.Option(42, help="Random seed"),
    dry_run: bool = typer.Option(False, help="Print commands without running"),
    no_plot: bool = typer.Option(False, help="Skip plot generation"),
):
    """Run NSGA-II across multiple benchmarks sequentially.

    By default runs all registered benchmarks. Use -b to select specific ones::

        uv run -m secretagent.cli.optimize run-all -b airline -b nba dataset.n=20
        uv run -m secretagent.cli.optimize run-all --pop-size 16 --n-gen 8
    """
    import subprocess
    import sys

    targets = benchmarks or list(NSGA2_SPACES.keys())
    unknown = [t for t in targets if t not in NSGA2_SPACES]
    if unknown:
        print(f"Unknown benchmarks: {', '.join(unknown)}")
        print(f"Available: {', '.join(NSGA2_SPACES.keys())}")
        raise typer.Exit(1)

    print(f"NSGA-II run-all: {', '.join(targets)}")
    print(f"  pop_size={pop_size}, n_gen={n_gen}, timeout={timeout}, metric={metric}")
    print()

    results = {}
    for name in targets:
        entry = NSGA2_SPACES[name]
        cwd = str(_BENCH_ROOT / entry["cwd"])
        space_file = str(_BENCH_ROOT / entry["space_file"])

        cmd = [
            sys.executable, "-m", "secretagent.cli.optimize", "nsga2",
            "--space-file", space_file,
            "--cwd", cwd,
            "--pop-size", str(pop_size),
            "--n-gen", str(n_gen),
            "--timeout", str(timeout),
            "--metric", metric,
            "--seed", str(seed),
        ]
        if dry_run:
            cmd.append("--dry-run")
        if no_plot:
            cmd.append("--no-plot")
        cmd.extend(ctx.args)

        print("=" * 70)
        print(f"  BENCHMARK: {name}")
        print(f"  {' '.join(cmd)}")
        print("=" * 70)

        rc = subprocess.call(cmd)
        results[name] = rc
        print()

    print("=" * 70)
    print("  RUN-ALL SUMMARY")
    print("=" * 70)
    for name, rc in results.items():
        status = "OK" if rc == 0 else f"FAILED (exit {rc})"
        print(f"  {name:<20} {status}")

    # Auto-run cross-summary if all succeeded and not dry-run
    if not dry_run and all(rc == 0 for rc in results.values()):
        csv_paths = [
            str(_BENCH_ROOT / NSGA2_SPACES[name]["cwd"] / "results" / "nsga2_summary.csv")
            for name in targets
        ]
        existing = [p for p in csv_paths if Path(p).exists()]
        if existing:
            print(f"\n  Cross-summary from {len(existing)} benchmarks:")
            subprocess.call([
                sys.executable, "-m", "secretagent.cli.optimize", "cross-summary",
                "--metric", metric,
            ] + existing)


@app.command(name="cross-summary")
def cross_summary(
    csv_paths: list[str] = typer.Argument(..., help="Paths to nsga2_summary.csv files"),
    metric: str = typer.Option("correct", help="Metric column name"),
    ref_cost: float = typer.Option(None, help="Reference cost for hypervolume (default: auto)"),
    output: str = typer.Option(None, help="Save markdown table to file"),
):
    """Cross-benchmark comparison from NSGA-II summary CSVs.

    Pass one nsga2_summary.csv per benchmark::

        uv run -m secretagent.cli.optimize cross-summary \\
            airline/results/nsga2_summary.csv \\
            nba/results/nsga2_summary.csv \\
            tax/results/nsga2_summary.csv
    """
    import math
    from pathlib import Path

    import pandas as pd

    from secretagent.optimize.metrics import compute_hypervolume

    benchmarks = {}
    for path in csv_paths:
        df = pd.read_csv(path)
        parts = Path(path).parts
        # Two supported layouts:
        #   <bench>/results/<file>      -> name = parts[-3]   (canonical sweep cwd)
        #   <...>/<bench>/<file>        -> name = parts[-2]   (snapshot dirs under
        #                                                     paper/results/optimize-results/<bench>/)
        if len(parts) >= 3 and parts[-2] == "results":
            name = parts[-3]
        elif len(parts) >= 2:
            name = parts[-2]
        else:
            name = Path(path).stem
        benchmarks[name] = df

    auto_ref_cost = ref_cost or max(
        df.loc[df["valid"], "cost"].max()
        for df in benchmarks.values()
        if df["valid"].any()
    ) * 1.1

    print("=" * 72)
    print("CROSS-BENCHMARK NSGA-II SUMMARY")
    print("=" * 72)

    rows = []
    for name, df in benchmarks.items():
        valid = df[df["valid"]]
        front = df[df["frontier"] & df["valid"]]
        best_acc = valid[metric].max() if not valid.empty else 0.0
        cheapest_cost = valid["cost"].min() if not valid.empty else math.inf
        frontier_pts = list(zip(front[metric], front["cost"])) if not front.empty else []
        hv = compute_hypervolume(frontier_pts, (0.0, auto_ref_cost))
        rows.append({
            "benchmark": name,
            "evaluated": len(df),
            "valid": len(valid),
            "frontier": len(front),
            f"best_{metric}": best_acc,
            "cheapest_cost": cheapest_cost,
            "hypervolume": hv,
        })

    summary_df = pd.DataFrame(rows)
    print("\n## Per-benchmark\n")
    print(summary_df.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    all_frontiers = pd.concat(
        [df[df["frontier"] & df["valid"]].assign(benchmark=name) for name, df in benchmarks.items()],
        ignore_index=True,
    )

    if not all_frontiers.empty:
        print("\n## Method frequency on frontiers\n")
        method_counts = all_frontiers["method"].value_counts()
        for method, count in method_counts.items():
            total = len(all_frontiers)
            print(f"  {method:<30} {count:>3} / {total} ({count/total:.0%})")

        print("\n## Model frequency on frontiers\n")
        model_counts = all_frontiers["model"].value_counts()
        for model, count in model_counts.items():
            total = len(all_frontiers)
            print(f"  {model:<40} {count:>3} / {total} ({count/total:.0%})")

    print(f"\n  Reference cost for hypervolume: ${auto_ref_cost:.4f}")

    if output:
        with open(output, "w") as f:
            f.write("# Cross-Benchmark NSGA-II Results\n\n")
            f.write(summary_df.to_markdown(index=False))
            f.write("\n")
        print(f"\n  Saved to {output}")


@app.command()
def summary(
    csv_path: str = typer.Argument(..., help="Path to summary CSV (nsga2_summary.csv or sweep_summary.csv)"),
    top_n: int = typer.Option(10, help="Show top N results"),
    metric: str = typer.Option("correct", help="Metric column to sort by; append '-' to minimize (e.g. 'cost-')"),
):
    """Display results from a saved sweep or NSGA-II summary."""
    import pandas as pd
    df = pd.read_csv(csv_path)
    minimize = metric.endswith('-')
    metric_col = metric.rstrip('-')
    if metric_col not in df.columns:
        if 'accuracy' in df.columns:
            metric_col = 'accuracy'
        else:
            print(f"Available columns: {list(df.columns)}")
            raise typer.BadParameter(f"Metric '{metric_col}' not found in {csv_path}")
    df = df.sort_values(metric_col, ascending=minimize).head(top_n)
    print(df.to_string(index=False))


if __name__ == '__main__':
    app()
