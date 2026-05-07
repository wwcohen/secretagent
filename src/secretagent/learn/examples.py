"""Extract in-context examples from recorded rollouts.

Collects successful input/output pairs from experiment results and
saves them in the JSON format expected by SimulateFactory's
example_file parameter.

The format is::

    {
      "interface_name_1": [
        {"input_args": [...], "expected_output": ...},
        ...
      ],
      "interface_name_2": [...]
    }

Usage::

    from secretagent.learn.examples import extract_examples
    extract_examples(result_dirs, output_file='examples.json',
                     only_correct=True)

Or via CLI::

    uv run -m secretagent.cli.learn examples results/* \\
        --output examples.json --only-correct
"""

import json
from pathlib import Path
from secretagent import savefile


def extract_examples(
    dirs: list[Path],
    output_file: str | Path = 'examples.json',
    interfaces: list[str] | None = None,
    only_correct: bool = True,
    max_per_interface: int | None = None,
    latest: int = 1,
    check: list[str] | None = None,
) -> Path:
    """Extract in-context examples from recorded experiment results.

    Args:
        dirs: result directories containing results.jsonl with rollouts
        output_file: path to write the examples JSON
        interfaces: list of interface names to extract (None = all)
        only_correct: if True, only include examples from correct predictions
        max_per_interface: limit examples per interface (None = no limit)
        latest: keep latest k dirs per tag (passed to filter_paths)
        check: config constraint filters (passed to filter_paths)

    Returns:
        Path to the written examples file.
    """
    filtered_dirs = savefile.filter_paths(dirs, latest=latest, dotlist=check or [])
    if not filtered_dirs:
        raise ValueError(f'No directories found after filtering: {dirs}')

    # Collect examples grouped by interface name
    examples: dict[str, list[dict]] = {}

    for d in filtered_dirs:
        jsonl_path = Path(d) / 'results.jsonl'
        if not jsonl_path.exists():
            print(f'  skipping {d} (no results.jsonl)')
            continue

        with open(jsonl_path) as f:
            for line in f:
                record = json.loads(line)

                # Skip incorrect predictions if only_correct
                if only_correct and not record.get('correct', False):
                    continue

                # Extract examples from rollout
                for step in record.get('rollout', []):
                    func_name = step.get('func', '')

                    # Filter by interface name if specified
                    if interfaces and func_name not in interfaces:
                        continue

                    # Skip steps that raised exceptions
                    output = step.get('output')
                    if isinstance(output, str) and output.startswith('**exception'):
                        continue

                    example = {
                        'input_args': step.get('args', []),
                        'expected_output': output,
                    }

                    # Include input_kw if present and non-empty
                    kw = step.get('kw')
                    if kw:
                        example['input_kw'] = kw

                    if func_name not in examples:
                        examples[func_name] = []
                    examples[func_name].append(example)

    # Apply max_per_interface limit
    if max_per_interface:
        for name in examples:
            examples[name] = examples[name][:max_per_interface]

    # Write output
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(examples, f, indent=2, default=str)

    # Print summary
    total = sum(len(v) for v in examples.values())
    print(f'Extracted {total} examples for {len(examples)} interfaces:')
    for name, exs in sorted(examples.items()):
        print(f'  {name}: {len(exs)} examples')
    print(f'Saved to {output_path}')

    return output_path
