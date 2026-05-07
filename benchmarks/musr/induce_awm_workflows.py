"""Induce AWM-style workflow descriptions from successful train ReAct trajectories.

For each task (murder / object / team), filters the corresponding train
results.jsonl to correct cases, formats them as a compact rollout listing,
prompts an LLM to extract a single step-by-step workflow, and writes the
result to a JSON file keyed by task name.

Usage:
    uv run python induce_awm_workflows.py \\
        results/<ts>.murder_react_train \\
        results/<ts>.object_react_train \\
        results/<ts>.team_react_train \\
        --output awm_workflows.json
"""

import argparse
import json
import pathlib
import sys

# Mirror expt.py path setup so this script is runnable from the benchmark dir.
_BENCHMARK_DIR = pathlib.Path(__file__).resolve().parent
_PROJECT_ROOT = _BENCHMARK_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / 'src'))
sys.path.insert(0, str(_BENCHMARK_DIR))

from secretagent import config  # noqa: E402
from secretagent.llm_util import llm  # noqa: E402


INDUCTION_PROMPT = """\
You are reading rollouts of an AI agent that solved {task_label} problems
using the ReAct paradigm. Each rollout shows the agent's tool calls
(search, lookup, finish) and its brief thoughts.

Below are {n_traces} *successful* rollouts. Your job: extract a single
step-by-step workflow that captures the strategy these successful runs
share. The workflow should be concrete and prescriptive — a future agent
reading it should know what to do.

Format requirements:
- 5–10 numbered steps.
- Each step is one or two sentences.
- Reference the tools by name (search, lookup, finish).
- Mention what kinds of queries to use, in what order, what to look for.
- The final step should be: call finish(answer_index) once you have the answer.

Do NOT include prose preamble. Output only the numbered list.

=== Rollouts ===

{rollouts}
"""


# Map MUSR split name → (json_key, human-readable label)
TASK_KEYS = {
    'murder_mysteries': ('murder', 'murder mystery'),
    'object_placements': ('object', 'object placement (theory of mind)'),
    'team_allocation': ('team', 'team allocation'),
}


def _format_rollout(case: dict) -> str:
    """Compress a single rollout into a few short lines per step."""
    rollout = case.get('rollout', [])
    formatted = []
    for entry in rollout:
        for step in (entry.get('step_info') or []):
            if 'thought' in step:
                t = (step.get('thought') or '').strip().replace('\n', ' ')[:300]
                if t:
                    formatted.append(f"  thought: {t}")
            elif 'tool_call' in step:
                args = str(step.get('args', ''))[:150]
                formatted.append(f"  call: {step['tool_call']}({args})")
            elif 'tool_return' in step:
                out = str(step.get('output', '') or '').replace('\n', ' ')[:150]
                formatted.append(f"  return: {step['tool_return']} -> {out}")
    return '\n'.join(formatted) if formatted else '  (no recorded steps)'


def _task_for(results_dir: pathlib.Path) -> tuple[str | None, str | None]:
    """Identify the task by inspecting the dir's config.yaml."""
    cfg_path = results_dir / 'config.yaml'
    if not cfg_path.exists():
        return None, None
    cfg = cfg_path.read_text()
    for split_name, (key, label) in TASK_KEYS.items():
        if split_name in cfg:
            return key, label
    return None, None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('train_dirs', nargs='+', help='train ReAct result directories')
    p.add_argument('--output', default='awm_workflows.json',
                   help='where to write the induced workflows JSON')
    p.add_argument('--model', default='together_ai/deepseek-ai/DeepSeek-V3',
                   help='LLM model used for induction')
    p.add_argument('--max-traces', type=int, default=20,
                   help='max successful rollouts to feed the inducer per task')
    args = p.parse_args()

    # Configure secretagent so llm() works (model + caching disabled).
    config.configure(cfg={'llm': {'model': args.model},
                          'cachier': {'enable_caching': False}})

    workflows: dict[str, str] = {}
    for raw_dir in args.train_dirs:
        results_dir = pathlib.Path(raw_dir).resolve()
        jsonl_path = results_dir / 'results.jsonl'
        if not jsonl_path.exists():
            print(f'WARNING: no results.jsonl in {results_dir}, skipping',
                  file=sys.stderr)
            continue

        task_key, task_label = _task_for(results_dir)
        if task_key is None:
            print(f'WARNING: cannot determine task type for {results_dir}, skipping',
                  file=sys.stderr)
            continue

        successes: list[dict] = []
        with open(jsonl_path) as f:
            for line in f:
                rec = json.loads(line)
                if rec.get('correct'):
                    successes.append(rec)

        if not successes:
            print(f'WARNING: no successes in {results_dir}, skipping',
                  file=sys.stderr)
            continue

        sampled = successes[:args.max_traces]
        rollouts_text = '\n\n---\n\n'.join(
            f'Rollout {i + 1}:\n{_format_rollout(s)}'
            for i, s in enumerate(sampled)
        )
        prompt = INDUCTION_PROMPT.format(
            task_label=task_label,
            n_traces=len(sampled),
            rollouts=rollouts_text,
        )

        print(f'[{task_key}] inducing workflow from {len(sampled)} successes...')
        text, stats = llm(prompt, args.model)
        workflows[task_key] = text.strip()
        in_t = stats.get('input_tokens', 0)
        out_t = stats.get('output_tokens', 0)
        print(f'[{task_key}] done. tokens={in_t}+{out_t}')

    if not workflows:
        print('ERROR: no workflows induced', file=sys.stderr)
        sys.exit(1)

    output_path = pathlib.Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(workflows, f, indent=2)
    print(f'\nSaved {len(workflows)} workflows to {output_path}')
    for k, v in workflows.items():
        preview = v[:400]
        print(f'\n=== {k} ===\n{preview}')


if __name__ == '__main__':
    main()
