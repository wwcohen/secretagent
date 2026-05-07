"""CLI for debugging experiment results.

Commands:
    errors    Report exceptions found in experiment outputs.

Experiment directories (or CSV files within them) are passed as extra
positional arguments after the subcommand.  Results are filtered through
savefile.filter_paths(), which supports ``--latest`` (keep k most recent
per tag) and ``--check`` (config-key constraints).
"""

from collections import Counter
import pprint
import typer
import pandas as pd
from pathlib import Path
from typing import Optional

from secretagent import config, record, savefile
from secretagent.cli.expt import setup_and_load_dataset
from secretagent.implement.util import resolve_dotted

app = typer.Typer()

_EXTRA_ARGS = {"allow_extra_args": True, "allow_interspersed_args": False}


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


@app.command(context_settings=_EXTRA_ARGS)
def errors(
    ctx: typer.Context,
    latest: int = typer.Option(1, help='Keep latest k dirs per tag; 0 for all'),
    check: Optional[list[str]] = typer.Option(None, help='Config constraint like key=value'),
):
    """Report exceptions found in experiment outputs.

    Looks for outputs starting with '**exception raised**:' in the
    predicted_output column and reports each unique exception message
    with a count and an example case name.
    """
    column = 'predicted_output'
    dirs = _get_dirs(ctx, latest=latest, check=check)
    for d in dirs:
        df = pd.read_csv(d / 'results.csv')
        if column not in df.columns:
            print(f'{d.name}: column "{column}" not found')
            continue
        prefix = '**exception raised**:'
        mask = df[column].astype(str).str.startswith(prefix)
        exc_df = df[mask]
        if exc_df.empty:
            print(f'{d.name}: no exceptions')
            continue
        exc_msgs = exc_df[column].astype(str).str[len(prefix):].str.strip()
        counts = Counter(exc_msgs)
        # Find one example case_name per unique exception
        case_col = 'case_name' if 'case_name' in df.columns else None
        examples: dict[str, str] = {}
        for idx, msg in exc_msgs.items():
            if msg not in examples:
                examples[msg] = str(exc_df.loc[idx, case_col]) if case_col else f'row {idx}'
        print(f'{d.name}: {len(exc_df)} exceptions ({len(counts)} unique)')
        for msg, count in counts.most_common():
            print(f'  [{count}x] (e.g. {examples[msg]}) {msg}')


@app.command(context_settings=_EXTRA_ARGS)
def replay(
    ctx: typer.Context,
    interface: str = typer.Option(..., help="Top-level interface as 'module.name'"),
    case_name: str = typer.Option(..., help='Case name to replay'),
    latest: int = typer.Option(1, help='Keep latest k dirs per tag; 0 for all'),
    check: Optional[list[str]] = typer.Option(None, help='Config constraint like key=value'),
):
    """Replay a single case from an experiment with full tracing.

    Loads config from the result directory's config.yaml, finds the
    named case in the dataset, and runs the top-level interface with
    echo flags enabled.

    Takes the same result-directory arguments as the errors command,
    but uses only the first matching directory.
    """
    dirs = _get_dirs(ctx, latest=latest, check=check)
    if len(dirs) > 1:
        import warnings
        warnings.warn(
            f'Multiple result directories found ({len(dirs)}), using first: {dirs[0]}'
        )
    result_path = Path(dirs[0])
    config_file = result_path / 'config.yaml'
    if not config_file.exists():
        raise ValueError(f'No config.yaml in {result_path}')

    dataset = setup_and_load_dataset([], config_file=config_file)

    # Find the case by name
    matching = [c for c in dataset.cases if c.name == case_name]
    if not matching:
        available = [c.name for c in dataset.cases[:10]]
        raise ValueError(
            f'Case "{case_name}" not found. Examples: {available}')
    case = matching[0]

    top_level = resolve_dotted(interface)
    pprint.pprint(config.GLOBAL_CONFIG)

    print('input_args', case.input_args)
    with config.configuration(
            echo={
                'model': True,
                'llm_input': True, 'llm_output': True,
                'code_eval_input': True, 'code_eval_output': True}
    ):
        with record.recorder() as records:
            predicted_output = top_level(*case.input_args)
    print('predicted output', predicted_output)
    pprint.pprint(records)


@app.callback()
def main(
    config_file: Optional[str] = typer.Option(None, help='YAML config file to load'),
):
    """Debug experiment results.
    """
    if config_file:
        config.configure(yaml_file=config_file)


if __name__ == '__main__':
    app()
