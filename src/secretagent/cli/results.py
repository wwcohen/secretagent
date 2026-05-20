"""CLI for analyzing experiment results saved by savefile.

Commands:
    list      Show available experiments and number of examples
    average   Report mean +/- stderr of metrics grouped by experiment.
    pair      Run paired t-tests on metrics across experiments.
    compare   Show configuration differences between experiments.

Experiment directories (or CSV files within them) are passed as extra
positional arguments after the subcommand.  Results are filtered through
savefile.filter_paths(), which supports ``--latest`` (keep k most recent
per tag) and ``--check`` (config-key constraints).

Example usage:

    # List all experiments under a directory
    uv run -m secretagent.cli.results list results/20260301.* --latest 0

    # List only the most recent experiment per tag (default)
    uv run -m secretagent.cli.results list results/*

    # Show averages with a config constraint
    uv run -m secretagent.cli.results average results/* --check llm.model=gpt-4o

    # Paired t-test between experiments
    uv run -m secretagent.cli.results pair results/* --latest 0

    # Compare configs across experiments
    uv run -m secretagent.cli.results compare results/* --latest 0
"""

from collections import Counter
import shutil
import typer
import pandas as pd
from itertools import combinations
from pathlib import Path
from typing import Optional

from scipy import stats as scipy_stats

from secretagent import config, savefile

app = typer.Typer()

_EXTRA_ARGS = {"allow_extra_args": True, "allow_interspersed_args": False}


def parse_metric(spec: str) -> tuple[str, bool]:
    """Parse a metric spec like 'cost-' into (name, maximize).

    A trailing '-' means minimize; otherwise maximize.
    """
    if spec.endswith('-'):
        return spec[:-1], False
    return spec, True


def parse_metrics(specs: list[str]) -> tuple[list[str], dict[str, bool]]:
    """Parse a list of metric specs into (names, directions).

    Returns:
        names: list of metric column names (without '-' suffix)
        directions: dict mapping name -> True if maximize, False if minimize
    """
    names = []
    directions = {}
    for spec in specs:
        name, maximize = parse_metric(spec)
        names.append(name)
        directions[name] = maximize
    return names, directions


def _get_dirs(ctx: typer.Context, latest: int = 1, check: Optional[list[str]] = None) -> list[Path]:
    """Resolve experiment directories from extra CLI args.

    Extra args in ctx.args are files or directories.
    files are mapped to their parent directory.
    Results are filtered through savefile.filter_paths.
    """
    if not ctx.args:
        raise ValueError('No paths provided.')
    dirs = savefile.filter_paths(ctx.args, latest=latest, dotlist=check or [])
    if not dirs:
        raise ValueError('No matching experiment directories found.')
    for d in dirs:
        if not (Path(d) / 'results.csv').exists():
            raise ValueError(f'No results.csv in {d}')
    return dirs



@app.command('list', context_settings=_EXTRA_ARGS)
def list_experiments(
    ctx: typer.Context,
    latest: int = typer.Option(1, help='Keep latest k dirs per tag; 0 for all'),
    check: Optional[list[str]] = typer.Option(None, help='Config constraint like key=value'),
):
    """Show available experiment directories and row counts.

    Extra args are CSV files or directories to inspect.
    """
    dirs = _get_dirs(ctx, latest=latest, check=check)
    for d in dirs:
        csv_path = d / 'results.csv'
        n = len(pd.read_csv(csv_path))
        print(f'{n:5d} examples in {d.name}')


@app.command(context_settings=_EXTRA_ARGS)
def average(
        ctx: typer.Context,
        latest: int = typer.Option(1, help='Keep latest k dirs per tag; 0 for all'),
        check: Optional[list[str]] = typer.Option(None, help='Config constraint like key=value'),
        metric: Optional[list[str]] = typer.Option(None, help='Metrics to average'),
        pareto: bool = typer.Option(False, help='Only show Pareto-optimal experiments'),
        shorten_path: bool = typer.Option(False, '--shorten-path', help='Show only the file_under tag instead of full path'),
):
    """Report mean +/- stderr of a metric and latency, grouped by experiment."""
    if metric is None:
        metric = ['cost-', 'correct']
    names, directions = parse_metrics(metric)
    dirs = _get_dirs(ctx, latest=latest, check=check)
    dfs = [pd.read_csv(d / 'results.csv') for d in dirs]
    if pareto and len(dfs) >= 2:
        pair_df = paired_result_df(dirs, dfs, names)
        optimal = set(find_pareto_optimal(pair_df, names, directions=directions))
        filtered = [(d, df) for d, df in zip(dirs, dfs)
                     if savefile.file_under_part(d) in optimal]
        dirs, dfs = [list(t) for t in zip(*filtered)] if filtered else ([], [])
    for path, df in zip(dirs, dfs):
        label = savefile.file_under_part(path) if shorten_path else str(path)
        df['path'] = [label] * len(df)
    if not dfs:
        print('No experiments to show.')
        return
    result = pd.concat(dfs).groupby('path')[names].agg(['mean', 'sem'])
    result = result.sort_values((names[0], 'mean'), ascending=not directions.get(names[0], True))
    print(result)


def paired_result_df(
    dirs: list[Path],
    dfs: list[pd.DataFrame],
    metrics: list[str],
) -> pd.DataFrame:
    """Build a DataFrame of pairwise paired t-test results.

    Each row compares two experiments on every metric. Columns include
    expt_a, expt_b, n, and for each metric m: m_t and m_p.

    If a metric has zero variance in both experiments (identical values),
    reports m_t=0 and m_p=1.0 instead of NaN.
    """
    # Sort by mean of the first metric so comparisons read in order
    paired = sorted(zip(dirs, dfs), key=lambda x: x[1][metrics[0]].mean(), reverse=True)
    dirs, dfs = [list(t) for t in zip(*paired)]
    rows = []
    for (pa, da), (pb, db) in combinations(zip(dirs, dfs), 2):
        fua = savefile.file_under_part(pa)
        fub = savefile.file_under_part(pb)
        joined = da.join(db, lsuffix='_a', rsuffix='_b', how='inner')
        n = len(joined)
        if n == 0:
            continue
        row = {
            'expt_a': fua,
            'expt_b': fub,
            'n': n,
        }
        for m in metrics:
            col_a, col_b = joined[f'{m}_a'].astype(float), joined[f'{m}_b'].astype(float)
            if (col_a == col_b).all():
                row[f'{m}_t'] = 0.0
                row[f'{m}_p'] = 1.0
            else:
                t, p = scipy_stats.ttest_rel(col_a, col_b)
                row[f'{m}_t'] = t
                row[f'{m}_p'] = p
        rows.append(row)
    return pd.DataFrame(rows)


def find_pareto_optimal(
    pair_df: pd.DataFrame,
    metrics: list[str],
    alpha: float = 0.05,
    directions: dict[str, bool] | None = None,
) -> list[str]:
    """Return experiments that are not dominated on every metric.

    An experiment x1 is dominated by x2 if for every metric m,
    x2 is significantly better than x1 (p < alpha).  "Better" means
    higher for maximized metrics and lower for minimized metrics.

    Args:
        directions: maps metric name -> True (maximize) or False (minimize).
            Defaults to maximize for all metrics.
    """
    if directions is None:
        directions = {m: True for m in metrics}

    # Collect all experiment names
    expts = sorted(set(pair_df['expt_a']) | set(pair_df['expt_b']))

    # Index pair_df for quick lookup: (expt_a, expt_b) -> row
    lookup = {}
    for _, row in pair_df.iterrows():
        lookup[(row['expt_a'], row['expt_b'])] = row
        lookup[(row['expt_b'], row['expt_a'])] = row

    dominated = set()
    for x1 in expts:
        for x2 in expts:
            if x1 == x2 or x2 in dominated:
                continue
            key = (x2, x1)
            if key not in lookup:
                continue
            row = lookup[key]
            # Check if x2 is significantly better than x1 on every metric.
            # t_val is from ttest_rel(x2, x1), so positive t means x2 > x1.
            # For maximized metrics, x2 better means t > 0.
            # For minimized metrics, x2 better means t < 0.
            all_sig = True
            for m in metrics:
                if row['expt_a'] == x2:
                    t_val = row[f'{m}_t']
                    p_val = row[f'{m}_p']
                else:
                    t_val = -row[f'{m}_t']
                    p_val = row[f'{m}_p']
                if p_val >= alpha:
                    all_sig = False
                    break
                # Check direction: for maximize, x2 better means t > 0
                # For minimize, x2 better means t < 0
                if directions.get(m, True) and t_val <= 0:
                    all_sig = False
                    break
                if not directions.get(m, True) and t_val >= 0:
                    all_sig = False
                    break
            if all_sig:
                dominated.add(x1)
                break

    return [x for x in expts if x not in dominated]


def compute_hypervolume(
    points: list[list[float]],
    ref: list[float],
) -> float:
    """Compute hypervolume indicator for a set of points and a reference point.

    All values are assumed to be in "maximize" orientation: higher is better.
    The reference point should be worse than all points in every dimension.

    For 2D, uses an O(n log n) sweep. For higher dimensions, uses
    inclusion-exclusion (practical for small point sets).
    """
    # Filter to points that dominate the reference
    pts = [p for p in points if all(p[i] > ref[i] for i in range(len(ref)))]
    if not pts:
        return 0.0
    d = len(ref)
    if d == 1:
        return max(p[0] for p in pts) - ref[0]
    if d == 2:
        # Sort by first coordinate descending
        pts.sort(key=lambda p: -p[0])
        vol = 0.0
        y_max = ref[1]
        for p in pts:
            if p[1] > y_max:
                vol += (p[0] - ref[0]) * (p[1] - y_max)
                y_max = p[1]
        return vol
    # General case: inclusion-exclusion over dominated boxes
    # For each subset S of points, the intersection of their dominated boxes
    # contributes (-1)^(|S|+1) * volume(intersection box bounded by ref).
    from itertools import combinations
    n = len(pts)
    total = 0.0
    for size in range(1, n + 1):
        sign = (-1) ** (size + 1)
        for combo in combinations(pts, size):
            # Intersection box: max of coords per dimension (since we maximize)
            corner = [max(c[i] for c in combo) for i in range(d)]
            vol = 1.0
            for i in range(d):
                extent = corner[i] - ref[i]
                if extent <= 0:
                    vol = 0.0
                    break
                vol *= extent
            total += sign * vol
    return total


def _build_points(
    dfs: list[pd.DataFrame],
    names: list[str],
    directions: dict[str, bool],
) -> list[list[float]]:
    """Build points in maximize orientation from experiment DataFrames."""
    points = []
    for df in dfs:
        pt = []
        for m in names:
            val = df[m].mean()
            if not directions.get(m, True):
                val = -val
            pt.append(val)
        points.append(pt)
    return points


def _worst_ref(points: list[list[float]]) -> list[float]:
    """Compute worst (minimum) per dimension across points."""
    return [min(p[i] for p in points) for i in range(len(points[0]))]


@app.command(context_settings=_EXTRA_ARGS)
def refpoint(
    ctx: typer.Context,
    latest: int = typer.Option(1, help='Keep latest k dirs per tag; 0 for all'),
    check: Optional[list[str]] = typer.Option(None, help='Config constraint like key=value'),
    metric: Optional[list[str]] = typer.Option(None, help='Metrics to compute reference for'),
):
    """Print the reference point that the hypervolume command would use for these results.

    For each metric, prints the worst observed mean value (in maximize
    orientation: minimized metrics are negated). Output is in comma-separated
    format suitable for passing to hypervolume --ref.

    """
    if not metric:
        metric = ['cost-', 'correct']
    names, directions = parse_metrics(metric)
    dirs = _get_dirs(ctx, latest=latest, check=check)
    dfs = [pd.read_csv(d / 'results.csv') for d in dirs]
    if not dfs:
        print('No experiments found.')
        return
    points = _build_points(dfs, names, directions)
    ref = _worst_ref(points)
    print(",".join(f"{v:.6f}" for v in ref))


@app.command(context_settings=_EXTRA_ARGS)
def hypervolume(
    ctx: typer.Context,
    latest: int = typer.Option(1, help='Keep latest k dirs per tag; 0 for all'),
    check: Optional[list[str]] = typer.Option(None, help='Config constraint like key=value'),
    metric: Optional[list[str]] = typer.Option(None, help='Metrics for hypervolume'),
    ref: Optional[str] = typer.Option(None, help='Reference point as comma-separated values (in maximize orientation)'),
    verbose: int = typer.Option(0, help='Print debug information'),
):
    """Compute the hypervolume indicator over experiment mean metrics.

    Each experiment becomes a point (mean of each metric). Minimized metrics
    (with '-' suffix) are negated so that higher is always better.

    Use --ref to set a fixed reference point (comma-separated). If
    omitted, uses the worst observed value per metric, which means
    that hypervolumes over different sets of results are not
    comparable.
    """
    if not metric:
        metric = ['cost-', 'correct']
    names, directions = parse_metrics(metric)
    dirs = _get_dirs(ctx, latest=latest, check=check)
    dfs = [pd.read_csv(d / 'results.csv') for d in dirs]

    if not dfs:
        print('No experiments to compute hypervolume.')
        return

    points = _build_points(dfs, names, directions)

    if ref is not None:
        ref_point = [float(v) for v in ref.split(',')]
        if len(ref_point) != len(names):
            raise ValueError(f'--ref needs {len(names)} values, got {len(ref_point)}')
    else:
        ref_point = _worst_ref(points)

    hv = compute_hypervolume(points, ref_point)
    print(f'Hypervolume: {hv:.6f}')
    print(f'Metrics: {", ".join(metric)}')
    print(f'Reference point: {ref_point}')
    if (verbose):
        print(f'Points ({len(points)}):')
        for d, pt in zip(dirs, points):
            label = savefile.file_under_part(d)
            print(f'  {label}: {pt}')


@app.command(context_settings=_EXTRA_ARGS)
def pair(
    ctx: typer.Context,
    latest: int = typer.Option(1, help='Keep latest k dirs per tag; 0 for all'),
    check: Optional[list[str]] = typer.Option(None, help='Config constraint like key=value'),
    metric: Optional[list[str]] = typer.Option(None, help='Metrics to pair'),
):
    """Run paired t-tests across experiments."""
    if not metric:
        metric = ['cost-', 'correct']
    names, _directions = parse_metrics(metric)
    dirs = _get_dirs(ctx, latest=latest, check=check)
    dfs = [pd.read_csv(d / 'results.csv') for d in dirs]
    if len(dfs) < 2:
        raise ValueError('Need at least 2 experiments for paired comparison')
    df = paired_result_df(dirs, dfs, names)
    p_cols = [c for c in df.columns if c.endswith('_p')]
    for c in p_cols:
        df[c] = df[c].map(lambda x: f'{x:.5f}')
    print(df)


@app.command(context_settings=_EXTRA_ARGS)
def plot(
    ctx: typer.Context,
    latest: int = typer.Option(1, help='Keep latest k dirs per tag; 0 for all'),
    check: Optional[list[str]] = typer.Option(None, help='Config constraint like key=value'),
    metric: Optional[list[str]] = typer.Option(None, help='Exactly two metrics to plot'),
    pareto: bool = typer.Option(False, help='Only show Pareto-optimal experiments'),
    output: str = typer.Option('results_plot.png', help='Output PNG file path'),
):
    """Plot experiments as points with error boxes on two metrics."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    if not metric:
        metric = ['cost-', 'correct']
    if len(metric) != 2:
        raise ValueError('Exactly two --metric options are required for plot')
    names, directions = parse_metrics(metric)
    mx, my = names

    dirs = _get_dirs(ctx, latest=latest, check=check)
    dfs = [pd.read_csv(d / 'results.csv') for d in dirs]

    # Compute pareto set for marker styling (even if not filtering)
    optimal_set: set[str] = set()
    if len(dfs) >= 2:
        pair_df = paired_result_df(dirs, dfs, names)
        optimal_set = set(find_pareto_optimal(pair_df, names, directions=directions))

    if pareto:
        filtered = [(d, df) for d, df in zip(dirs, dfs)
                     if savefile.file_under_part(d) in optimal_set]
        dirs, dfs = [list(t) for t in zip(*filtered)] if filtered else ([], [])

    if not dfs:
        print('No experiments to plot.')
        return

    fig, ax = plt.subplots(figsize=(10, 7))

    for d, df in zip(dirs, dfs):
        label = savefile.file_under_part(d)
        x_mean, x_sem = df[mx].mean(), df[mx].sem()
        y_mean, y_sem = df[my].mean(), df[my].sem()

        marker = '*' if label in optimal_set else 'o'
        msize = 12 if label in optimal_set else 6
        ax.plot(x_mean, y_mean, marker, markersize=msize, label=label)
        color = ax.lines[-1].get_color()
        rect = Rectangle(
            (x_mean - x_sem, y_mean - y_sem),
            2 * x_sem, 2 * y_sem,
            linewidth=1, edgecolor=color, facecolor=color, alpha=0.25,
        )
        ax.add_patch(rect)

    ax.set_xlabel(f'{mx} ({"maximize" if directions.get(mx, True) else "minimize"})')
    ax.set_ylabel(f'{my} ({"maximize" if directions.get(my, True) else "minimize"})')
    ax.set_title(f'{mx} vs {my}')
    ax.legend(fontsize=8, loc='best')
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f'Plot saved to {output}')


@app.command(context_settings=_EXTRA_ARGS)
def compare_configs(
    ctx: typer.Context,
    latest: int = typer.Option(1, help='Keep latest k dirs per tag; 0 for all'),
    check: Optional[list[str]] = typer.Option(None, help='Config constraint like key=value'),
):
    """Show configuration differences between experiments."""
    dirs = _get_dirs(ctx, latest=latest, check=check)
    ctr: Counter[str] = Counter()
    all_pairs = {}
    for d in dirs:
        cfg = config.load_yaml_cfg(d / 'config.yaml')
        all_pairs[d] = config.to_dotlist(cfg)
        for pair in all_pairs[d]:
            ctr[pair] += 1
    for d, pairs in all_pairs.items():
        uncommon_pairs = [
            pair for pair in pairs
            if ctr[pair] < len(dirs)
        ]
        print(f'properties of {d}:')
        for p in uncommon_pairs:
            print(f'  {p}')


_DEFAULT_REQUIRED_FILES = ['config.yaml', 'results.csv']


@app.command(context_settings=_EXTRA_ARGS)
def validate(
    ctx: typer.Context,
    latest: int = typer.Option(1, help='Keep latest k dirs per tag; 0 for all'),
    check: Optional[list[str]] = typer.Option(None, help='Config constraint like key=value'),
    require: Optional[list[str]] = typer.Option(None, help='Additional required files'),
    norequire: Optional[list[str]] = typer.Option(None, help='Remove a default required file'),
    purge: bool = typer.Option(False, help='Delete directories that fail validation'),
):
    """Check that experiment directories contain required files."""
    required = set(_DEFAULT_REQUIRED_FILES)
    for f in (require or []):
        required.add(f)
    for f in (norequire or []):
        required.discard(f)
    dirs = savefile.filter_paths(ctx.args, latest=latest, dotlist=check or [])
    bad_dirs = []
    for d in dirs:
        missing = [f for f in sorted(required) if not (d / f).exists()]
        if missing:
            print(f'{d}: missing {", ".join(missing)}')
            bad_dirs.append(d)
    if not bad_dirs:
        print('All directories OK.')
        return
    if purge:
        answer = input(f'Delete {len(bad_dirs)} directories? [y/N] ')
        if answer.strip().lower() == 'y':
            for d in bad_dirs:
                shutil.rmtree(d)
                print(f'  deleted {d}')


@app.command(context_settings=_EXTRA_ARGS)
def delete_obsolete(
    ctx: typer.Context,
    latest: int = typer.Option(1, help='Keep latest k dirs per tag; 0 for all'),
    check: Optional[list[str]] = typer.Option(None, help='Config constraint like key=value'),
):
    """Delete experiment directories not retained by filter_paths."""
    all_dirs = {Path(p) for p in ctx.args if Path(p).is_dir()}
    keep = set(savefile.filter_paths(ctx.args, latest=latest, dotlist=check or []))
    to_delete = sorted(all_dirs - keep)
    if not to_delete:
        print('Nothing to delete.')
        return
    print('Keeping:')
    for d in sorted(keep):
        print(f'  {d}')
    print(f'\nWill delete {len(to_delete)} directories:')
    for d in to_delete:
        print(f'  {d}')
    answer = input('Proceed? [y/N] ')
    if answer.strip().lower() == 'y':
        for d in to_delete:
            shutil.rmtree(d)
            print(f'  deleted {d}')
        print('\nIf these dirs were tracked in git, run `git add -u` to stage the deletions.')


def _find_benchmarks_dir() -> Path:
    """Walk up from cwd to find the 'benchmarks' directory."""
    cwd = Path.cwd().resolve()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / 'benchmarks'
        if candidate.is_dir():
            return candidate
    raise ValueError('Cannot find benchmarks/ directory above cwd')


@app.command('export', context_settings=_EXTRA_ARGS)
def export_results(
    ctx: typer.Context,
    latest: int = typer.Option(1, help='Keep latest k dirs per tag; 0 for all'),
    check: Optional[list[str]] = typer.Option(None, help='Config constraint like key=value'),
    as_path: Optional[str] = typer.Option(None, '--as', help='Override relative path under paper/results/results/'),
):
    """Copy filtered result directories to paper/results/results/<relative_path>.

    Run from a benchmark directory (e.g. benchmarks/bbh/sports_understanding).
    Copies each filtered result directory to
    paper/results/results/<path_from_benchmarks>/<result_dir_name>.
    Use --as to override the relative path.
    """
    dirs = _get_dirs(ctx, latest=latest, check=check)
    benchmarks_dir = _find_benchmarks_dir()

    if as_path is not None:
        rel = Path(as_path)
    else:
        cwd = Path.cwd().resolve()
        try:
            rel = cwd.relative_to(benchmarks_dir)
        except ValueError:
            raise ValueError(
                f'cwd ({cwd}) is not under benchmarks/ ({benchmarks_dir})')

    dest_base = benchmarks_dir.parent / 'paper' / 'results' / 'results' / rel
    dest_base.mkdir(parents=True, exist_ok=True)

    for d in dirs:
        dest = dest_base / d.name
        if dest.exists():
            print(f'  skipping {d.name} (already exists)')
            continue
        shutil.copytree(d, dest)
        print(f'  {d} -> {dest}')

    print(f'\nExported {len(dirs)} directories to {dest_base}')


@app.callback()
def main(
    config_file: Optional[str] = typer.Option(None, help='YAML config file to load'),
):
    """Analyze experiment results saved by savefile.
    """
    if config_file:
        config.configure(yaml_file=config_file)


if __name__ == '__main__':
    app()
