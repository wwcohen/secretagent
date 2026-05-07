"""Extract and format Program Trace Prompting (PTP) examples.

PTP shows execution traces of a workflow as in-context examples,
using variable names instead of full values for long inputs.
This is much more compact than full I/O examples.

Usage::

    from secretagent.learn.traces import extract_ptp_traces

    extract_ptp_traces(
        result_dirs, output_file='traces.txt',
        only_correct=True, max_traces=3, max_output_chars=200)
"""

import json
from pathlib import Path
from secretagent import savefile


def _abbreviate_arg(arg, max_chars: int = 50) -> str:
    """Abbreviate a function argument for display in a trace.

    Long strings become variable names, short values stay as-is.
    """
    if isinstance(arg, str) and len(arg) > max_chars:
        return 'narrative'  # convention: long strings are narratives
    if isinstance(arg, list) and len(str(arg)) > max_chars:
        return 'choices'
    return repr(arg)


def _abbreviate_output(output, max_chars: int = 200) -> str:
    """Abbreviate output for display, keeping the first max_chars."""
    s = str(output)
    if len(s) <= max_chars:
        return repr(output) if isinstance(output, str) else s
    return repr(s[:max_chars] + '...')


def format_single_trace(rollout: list[dict], max_output_chars: int = 200) -> str:
    """Format one rollout as a PTP-style doctest trace.

    Returns a string like:
        >>> evidence = extract_suspects_and_evidence(narrative)
        'victim: Jimmy\\ncrime_details: ...'
        >>> verified = verify_alibis(narrative, evidence)
        'Suspect Randy:\\n- alibi_holds: False...'
        >>> answer = deduce_murderer(narrative, verified, question, choices)
        'Randy'
        >>> extract_index(answer, choices)
        1
    """
    lines = []
    var_names = {}  # map step index -> variable name
    var_counter = {}  # track variable naming

    for i, step in enumerate(rollout):
        func = step['func']
        args = step.get('args', [])
        output = step.get('output')

        # Skip exception steps
        if isinstance(output, str) and output.startswith('**exception'):
            continue

        # Build argument string using variable names for previous outputs
        arg_strs = []
        for arg in args:
            # Check if this arg matches a previous step's output
            matched = False
            for prev_idx, prev_step in enumerate(rollout[:i]):
                prev_out = prev_step.get('output')
                if prev_out is not None and arg == prev_out and prev_idx in var_names:
                    arg_strs.append(var_names[prev_idx])
                    matched = True
                    break
            if not matched:
                arg_strs.append(_abbreviate_arg(arg))

        # Determine variable name for this step's output
        # Use descriptive names based on function name
        var_name = func.split('_')[-1] if '_' in func else func
        # Avoid collision
        if var_name in var_counter:
            var_counter[var_name] += 1
            var_name = f'{var_name}_{var_counter[var_name]}'
        else:
            var_counter[var_name] = 0
        var_names[i] = var_name

        # Format the call
        call_str = f'{func}({", ".join(arg_strs)})'

        # Last step: no variable assignment
        if i == len(rollout) - 1:
            lines.append(f'>>> {call_str}')
        else:
            lines.append(f'>>> {var_name} = {call_str}')

        # Format the output (abbreviated)
        lines.append(_abbreviate_output(output, max_output_chars))

    return '\n'.join(lines)


def extract_ptp_traces(
    dirs: list[Path],
    output_file: str | Path = 'traces.txt',
    only_correct: bool = True,
    max_traces: int = 3,
    max_output_chars: int = 200,
    latest: int = 1,
    check: list[str] | None = None,
) -> Path:
    """Extract PTP traces from recorded experiment results.

    Args:
        dirs: result directories containing results.jsonl with rollouts
        output_file: path to write the formatted traces
        only_correct: only include traces from correct predictions
        max_traces: maximum number of traces to include
        max_output_chars: max chars for each step's output
        latest: keep latest k dirs per tag
        check: config constraint filters

    Returns:
        Path to the written traces file.
    """
    filtered_dirs = savefile.filter_paths(dirs, latest=latest, dotlist=check or [])
    if not filtered_dirs:
        raise ValueError(f'No directories found after filtering: {dirs}')

    traces = []

    for d in filtered_dirs:
        jsonl_path = Path(d) / 'results.jsonl'
        if not jsonl_path.exists():
            continue

        with open(jsonl_path) as f:
            for line in f:
                record = json.loads(line)

                if only_correct and not record.get('correct', False):
                    continue

                rollout = record.get('rollout', [])
                if len(rollout) < 2:
                    continue

                trace_text = format_single_trace(rollout, max_output_chars)
                if trace_text.strip():
                    traces.append(trace_text)

                if len(traces) >= max_traces:
                    break

        if len(traces) >= max_traces:
            break

    # Format as PTP examples block
    output_parts = ["Here are some example traces showing how to solve similar problems:\n"]
    for i, trace in enumerate(traces):
        output_parts.append(f"Example {i+1}:")
        output_parts.append(trace)
        output_parts.append("")

    output_text = '\n'.join(output_parts)

    # Write output
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_text)

    print(f'Extracted {len(traces)} PTP traces')
    print(f'Saved to {output_path}')
    print(f'Preview:\n{output_text[:500]}...')

    return output_path


def load_ptp_traces(trace_file: str | Path) -> str:
    """Load formatted PTP traces from a file."""
    return Path(trace_file).read_text()
