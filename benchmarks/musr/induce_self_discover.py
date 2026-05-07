"""Induce Self-Discover reasoning structures for each MUSR task.

Self-Discover (Zhou+ NeurIPS 2024) induces a reusable reasoning structure
for a task via three LLM calls:

  1. SELECT:    pick ~5 reasoning modules from a fixed pool of ~39.
  2. ADAPT:     rewrite the selected modules to be task-specific.
  3. IMPLEMENT: compose the adapted modules into a step-by-step plan.

Unlike AWM, this pipeline does NOT require training trajectories — it
only needs a task description plus a couple of example instances (from
the train split) to ground the selection.

Usage:
    uv run python induce_self_discover.py --output self_discover_structures.json
"""

import argparse
import ast
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


# (task_key, data_split, human-readable task description)
TASKS = [
    ('murder', 'murder_mysteries',
     'Murder mystery: given a narrative with a victim and several suspects, '
     'identify the killer by weighing means, motive, opportunity, alibi '
     'consistency, and physical evidence.'),
    ('object', 'object_placements',
     'Object placement with theory of mind: given a narrative where an object '
     'is moved between locations while characters come and go, determine '
     'where a specific character *believes* the object is located (which may '
     'differ from its true location).'),
    ('team', 'team_allocation',
     'Team allocation: given a narrative describing people with different '
     'strengths, weaknesses and interpersonal dynamics plus a set of tasks, '
     'pick the assignment of people to tasks that best matches skills to '
     'requirements.'),
]


SELECT_PROMPT = """\
You are selecting reasoning modules to solve a class of problems.

Task description:
{task_desc}

Here are two example instances of this task (narrative, question, choices):

--- Example 1 ---
{example_1}

--- Example 2 ---
{example_2}

Here are candidate reasoning modules:

{modules}

Select the 4-7 modules that are MOST relevant for solving this task. Output
only the selected modules, one per line, verbatim from the list above
(including the number). Do not add commentary.
"""


ADAPT_PROMPT = """\
You are adapting generic reasoning modules to a specific task.

Task description:
{task_desc}

Selected modules:
{selected}

Rephrase each selected module so that it is concretely tailored to the
task (reference the specific objects of reasoning — e.g. for murder
mystery, mention suspects / alibis / evidence). Keep it crisp: one
sentence per module. Output a numbered list and nothing else.
"""


IMPLEMENT_PROMPT = """\
You are composing adapted reasoning modules into a concrete reasoning
plan that a future solver will follow.

Task description:
{task_desc}

Adapted modules:
{adapted}

Write a 5-8 step reasoning plan that an LLM should execute for each new
instance of this task. Each step should be specific and actionable
(reference suspects, locations, characters, evidence, etc. — whichever
is relevant). The final step MUST be: "State the final answer as the
0-based index of the correct choice."

Output the plan as a numbered list and nothing else.
"""


def _load_modules() -> str:
    path = _BENCHMARK_DIR / 'self_discover_modules.txt'
    return path.read_text().strip()


def _load_example(split_name: str, idx: int) -> str:
    """Read a single example from the train data file, formatted compactly."""
    data_file = _BENCHMARK_DIR / 'data' / f'{split_name}_train.json'
    if not data_file.exists():
        data_file = _BENCHMARK_DIR / 'data' / f'{split_name}.json'
    data = json.loads(data_file.read_text())
    ex = data['examples'][idx]
    narrative = ex['narrative']
    question = ex['question']
    choices = ex['choices']
    if isinstance(choices, str):
        choices = ast.literal_eval(choices)
    # Trim narrative to keep prompts short — 1500 chars is plenty to
    # convey the task shape without blowing up the SELECT prompt.
    if len(narrative) > 1500:
        narrative = narrative[:1500] + '... [truncated]'
    choices_str = '\n'.join(f'  {i}. {c}' for i, c in enumerate(choices))
    return f'Narrative: {narrative}\n\nQuestion: {question}\n\nChoices:\n{choices_str}'


def _call(prompt: str, model: str, tag: str) -> str:
    text, stats = llm(prompt, model)
    in_t = stats.get('input_tokens', 0)
    out_t = stats.get('output_tokens', 0)
    print(f'    [{tag}] tokens={in_t}+{out_t}')
    return text.strip()


def induce_one(task_key: str, split_name: str, task_desc: str,
               modules: str, model: str) -> str:
    print(f'[{task_key}] inducing reasoning structure...')
    example_1 = _load_example(split_name, 0)
    example_2 = _load_example(split_name, 1)

    select_text = _call(
        SELECT_PROMPT.format(
            task_desc=task_desc,
            example_1=example_1,
            example_2=example_2,
            modules=modules,
        ),
        model,
        'SELECT',
    )

    adapt_text = _call(
        ADAPT_PROMPT.format(task_desc=task_desc, selected=select_text),
        model,
        'ADAPT',
    )

    implement_text = _call(
        IMPLEMENT_PROMPT.format(task_desc=task_desc, adapted=adapt_text),
        model,
        'IMPLEMENT',
    )

    return implement_text


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', default='self_discover_structures.json')
    p.add_argument('--model', default='together_ai/deepseek-ai/DeepSeek-V3')
    args = p.parse_args()

    config.configure(cfg={'llm': {'model': args.model},
                          'cachier': {'enable_caching': False}})

    modules = _load_modules()

    structures: dict[str, str] = {}
    for task_key, split_name, task_desc in TASKS:
        structures[task_key] = induce_one(
            task_key, split_name, task_desc, modules, args.model)

    out_path = pathlib.Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(structures, indent=2))
    print(f'\nSaved {len(structures)} structures to {out_path}')
    for k, v in structures.items():
        preview = v[:400]
        print(f'\n=== {k} ===\n{preview}')


if __name__ == '__main__':
    main()
