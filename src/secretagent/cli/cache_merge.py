"""CLI for merging two llm_cache directories.

Example usage:

    # Merge two cache directories into a new output directory
    uv run -m secretagent.cli.cache_merge dir1/llm_cache dir2/llm_cache -o merged/llm_cache

    # Merge in-place (update dir1 with entries from dir2)
    uv run -m secretagent.cli.cache_merge dir1/llm_cache dir2/llm_cache -o dir1/llm_cache
"""

import os
import pickle

import typer

app = typer.Typer()


@app.command()
def main(
    cache_dir1: str = typer.Argument(..., help='First cache directory'),
    cache_dir2: str = typer.Argument(..., help='Second cache directory'),
    output: str = typer.Option(None, '-o', '--output', help='Output directory (default: update cache_dir1 in place)'),
):
    """Merge two cachier llm_cache directories."""
    if output is None:
        output = cache_dir1

    if not os.path.isdir(cache_dir1):
        typer.echo(f'Error: {cache_dir1} is not a directory')
        raise typer.Exit(1)
    if not os.path.isdir(cache_dir2):
        typer.echo(f'Error: {cache_dir2} is not a directory')
        raise typer.Exit(1)

    os.makedirs(output, exist_ok=True)

    names1 = set(f for f in os.listdir(cache_dir1) if os.path.isfile(os.path.join(cache_dir1, f)))
    names2 = set(f for f in os.listdir(cache_dir2) if os.path.isfile(os.path.join(cache_dir2, f)))
    all_names = names1 | names2

    if not all_names:
        typer.echo('No cache files found.')
        raise typer.Exit(1)

    for name in sorted(all_names):
        p1 = os.path.join(cache_dir1, name)
        p2 = os.path.join(cache_dir2, name)
        merged = {}
        for p in [p1, p2]:
            if os.path.isfile(p):
                try:
                    with open(p, 'rb') as f:
                        d = pickle.load(f)
                    if isinstance(d, dict):
                        merged.update(d)
                except (pickle.UnpicklingError, EOFError, Exception) as e:
                    typer.echo(f'  Warning: could not read {p}: {e}')
        out_path = os.path.join(output, name)
        with open(out_path, 'wb') as f:
            pickle.dump(merged, f)
        typer.echo(f'  {name}: {len(merged)} entries')

    typer.echo(f'\nMerged {len(all_names)} cache files into {output}')


if __name__ == '__main__':
    app()
