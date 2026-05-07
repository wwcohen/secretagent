"""CLI for summarizing LLM costs from cachier cache files.

Example usage:

    # Summarize costs from a cache directory
    uv run -m secretagent.cli.costs benchmarks/sports_understanding/llm_cache

    # Use the configured cachier.cache_dir
    uv run -m secretagent.cli.costs --config-file benchmarks/sports_understanding/conf/conf.yaml
"""

import typer
import pandas as pd
from typing import Optional

from secretagent import config
from secretagent.cache_util import extract_cached_stats

app = typer.Typer()


@app.command()
def main(
    cache_dir: Optional[str] = typer.Argument(None, help='Path to cachier cache directory'),
    config_file: Optional[str] = typer.Option(None, help='YAML config file to load'),
):
    """Print a summary of LLM costs extracted from the cachier cache."""
    if config_file:
        config.configure(yaml_file=config_file)

    stats = extract_cached_stats(cache_dir)
    if not stats:
        typer.echo('No cached stats found.')
        raise typer.Exit(1)

    df = pd.DataFrame(stats)
    typer.echo(f'\n{len(df)} cached LLM calls\n')
    typer.echo(df.describe().to_string())
    typer.echo('')
    totals = df[['input_tokens', 'output_tokens', 'latency', 'cost']].sum()
    typer.echo('Totals:')
    typer.echo(f'  input_tokens:  {int(totals.input_tokens)}')
    typer.echo(f'  output_tokens: {int(totals.output_tokens)}')
    typer.echo(f'  latency:       {totals.latency:.1f}s')
    typer.echo(f'  cost:          ${totals.cost:.4f}')


if __name__ == '__main__':
    app()
