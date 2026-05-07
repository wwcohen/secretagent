"""Induction pipeline for MUSR — first variant: original method.

Replicates the pipeline from the old secretagent-reasoning repo:
  1. Load a ReAct (simulate_pydantic) trace's thoughts
  2. LLM categorize each thought into a short reasoning-action-type label
  3. Merge synonyms if too many unique labels
  4. For each top category (by frequency), LLM synthesize a ptool spec
     (func_name / display_name / short_desc / docstring)

This is iter-1 induction consuming an iter-0 ReAct trace; no acceptance
gate, no iteration, no ReAct-loop integration yet — the output is just a
set of ptool specs for human inspection.

Usage:
    uv run python induction.py --task team
    uv run python induction.py --task all
    uv run python induction.py --task team --variant original --max-ptools 5

Output: induction_out/<variant>/<task>/{report.json, report.md}
"""

import argparse
import json
import pathlib
import re
import sys
from collections import Counter

# Path setup — mirror induce_self_discover.py
_BENCHMARK_DIR = pathlib.Path(__file__).resolve().parent
_PROJECT_ROOT = _BENCHMARK_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / 'src'))
sys.path.insert(0, str(_BENCHMARK_DIR))

from secretagent import config  # noqa: E402
from secretagent.llm_util import llm  # noqa: E402


# ---------------------------------------------------------------------------
# Task metadata — descriptions match induce_self_discover.py verbatim so
# the categorize/synthesize prompts stay consistent across baselines.
# ---------------------------------------------------------------------------

TASK_DESCRIPTIONS = {
    'murder': (
        'Murder mystery: given a narrative with a victim and several suspects, '
        'identify the killer by weighing means, motive, opportunity, alibi '
        'consistency, and physical evidence.'
    ),
    'object': (
        'Object placement with theory of mind: given a narrative where an '
        'object is moved between locations while characters come and go, '
        'determine where a specific character BELIEVES the object is located '
        '(which may differ from its true location).'
    ),
    'team': (
        'Team allocation: given a narrative describing people with different '
        'strengths, weaknesses and interpersonal dynamics plus a set of tasks, '
        'pick the assignment of people to tasks that best matches skills to '
        'requirements.'
    ),
}

# Default trace sources — the `*_react_train` runs from 2026-04-09.
# These are method: simulate_pydantic with record_details: true, so
# each rollout's step_info contains interleaved {thought}, {tool_call},
# and {tool_return} entries.
DEFAULT_TRACE_PATHS = {
    'murder': 'results/20260409.014724.murder_react_train/results.jsonl',
    'object': 'results/20260409.021643.object_react_train/results.jsonl',
    'team':   'results/20260409.023902.team_react_train/results.jsonl',
}


# ---------------------------------------------------------------------------
# Stage 1 — trace adapter: pydantic-ai ReAct trace → flat list of thoughts
# ---------------------------------------------------------------------------

def load_thoughts(trace_path: pathlib.Path) -> list[dict]:
    """Extract thought steps from a results.jsonl file.

    Each row has rollout[].step_info which is a flat sequence of dicts
    shaped like {thought: ...}, {tool_call: ..., args: ...}, or
    {tool_return: ..., output: ...}. We pull every non-empty {thought}
    entry, tagged with case_name + its position in step_info.
    """
    items: list[dict] = []
    with open(trace_path) as f:
        for line in f:
            row = json.loads(line)
            case = row.get('case_name') or '???'
            correct = bool(row.get('correct'))
            for call in row.get('rollout', []):
                for pos, step in enumerate(call.get('step_info', [])):
                    text = step.get('thought', '') if isinstance(step, dict) else ''
                    if text and text.strip():
                        items.append({
                            'case': case,
                            'pos': pos,
                            'text': text.strip(),
                            'correct': correct,
                        })
    return items


# ---------------------------------------------------------------------------
# Stage 2 — LLM categorization (batched)
# ---------------------------------------------------------------------------

CATEGORIZE_PROMPT = """\
You are analyzing thoughts produced by an AI agent solving this task:

{task_desc}

Categorize each thought into a SHORT, REUSABLE reasoning-action-type
label (3 to 6 words).

Rules:
- Describe WHAT the agent is DOING (its reasoning move), not the specific
  content of this particular case. Do not use names, places, or
  case-specific details in your label.
- Use consistent canonical names so synonyms collapse to the same label.
- Labels must be functionally distinct from each other.
- Output ONLY a JSON array inside <answer>...</answer> tags, no prose.

Thoughts to categorize:

{items_block}

<answer>
[{{"index": 0, "category": "..."}}, ...]
</answer>
"""


def _format_batch(batch: list[dict], start: int, char_limit: int = 400) -> str:
    lines = []
    for i, item in enumerate(batch):
        idx = start + i
        text = item['text'].replace('\n', ' ').strip()
        if len(text) > char_limit:
            text = text[:char_limit] + '...'
        lines.append(f'[{idx}] {text}')
    return '\n'.join(lines)


_ANSWER_BLOCK_RE = re.compile(r'<answer>(.*?)</answer>', re.DOTALL)


_DEBUG_DIR: pathlib.Path | None = None


def _dump_debug(tag: str, prompt: str, response: str) -> None:
    if _DEBUG_DIR is None:
        return
    _DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    idx = len(list(_DEBUG_DIR.glob(f'{tag}_*.txt')))
    path = _DEBUG_DIR / f'{tag}_{idx:03d}.txt'
    path.write_text(
        f'=== PROMPT ===\n{prompt}\n\n=== RESPONSE ===\n{response}\n'
    )


def _extract_json(text: str, shape: str) -> str | None:
    """Extract a JSON array or object from an LLM response.

    Tries in order:
      1. Content inside <answer>...</answer> tags (stripped)
      2. The largest balanced JSON literal of the requested shape in the text
    `shape` is either 'array' or 'object'.
    """
    m = _ANSWER_BLOCK_RE.search(text)
    candidates: list[str] = []
    if m:
        candidates.append(m.group(1).strip())
    candidates.append(text)

    open_ch, close_ch = ('[', ']') if shape == 'array' else ('{', '}')

    for candidate in candidates:
        # Find the FIRST opening bracket, then walk to its matching close
        start = candidate.find(open_ch)
        while start != -1:
            depth = 0
            in_str = False
            esc = False
            end = -1
            for i in range(start, len(candidate)):
                ch = candidate[i]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == '\\':
                        esc = True
                    elif ch == '"':
                        in_str = False
                    continue
                if ch == '"':
                    in_str = True
                elif ch == open_ch:
                    depth += 1
                elif ch == close_ch:
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            if end != -1:
                return candidate[start:end + 1]
            start = candidate.find(open_ch, start + 1)
    return None


def _parse_categorize(text: str) -> list[tuple[int, str]]:
    """Extract (index, category) pairs; tolerant to minor formatting drift."""
    block = _extract_json(text, 'array')
    if not block:
        return []
    try:
        arr = json.loads(block)
    except json.JSONDecodeError:
        return []
    out: list[tuple[int, str]] = []
    for entry in arr:
        if not isinstance(entry, dict):
            continue
        if 'index' not in entry or 'category' not in entry:
            continue
        try:
            out.append((int(entry['index']), str(entry['category']).strip()))
        except (ValueError, TypeError):
            continue
    return out


def categorize_items(items: list[dict], task_key: str, model: str,
                     batch_size: int = 30) -> list[str | None]:
    """Label each thought with a reasoning-action-type category.

    Returns a list parallel to `items` with the category (or None if the
    LLM failed to assign one).
    """
    task_desc = TASK_DESCRIPTIONS[task_key]
    labels: list[str | None] = [None] * len(items)

    for start in range(0, len(items), batch_size):
        batch = items[start:start + batch_size]
        prompt = CATEGORIZE_PROMPT.format(
            task_desc=task_desc,
            items_block=_format_batch(batch, start),
        )
        text, stats = llm(prompt, model)
        n_in = stats.get('input_tokens', 0)
        n_out = stats.get('output_tokens', 0)
        print(f'  [categorize {start}-{start + len(batch) - 1}] '
              f'tokens={n_in}+{n_out}')

        for idx, cat in _parse_categorize(text):
            if 0 <= idx < len(items):
                labels[idx] = cat
    return labels


# ---------------------------------------------------------------------------
# Stage 3 — merge synonyms if there are too many unique labels
# ---------------------------------------------------------------------------

MERGE_PROMPT = """\
You are consolidating reasoning-action-type labels extracted from an AI
agent solving this task:

{task_desc}

Here are the current labels with their counts:

{labels_block}

Merge synonyms and near-duplicates so we end up with {target_min} to
{target_max} canonical labels. Each canonical label must be:
- 3 to 6 words
- functionally distinct from the others
- describe WHAT the agent is doing (the reasoning move), not case specifics

Output a JSON object mapping each CANONICAL label to the list of ORIGINAL
labels (verbatim, exactly as shown above) that should map to it. Every
original label must appear in exactly one canonical group. Wrap in
<answer>...</answer>.

<answer>
{{
  "canonical label 1": ["original a", "original b", "original c"],
  "canonical label 2": ["original d"]
}}
</answer>
"""

def merge_categories(labels: list[str | None], task_key: str, model: str,
                     target_min: int = 5, target_max: int = 10
                     ) -> list[str | None]:
    counts = Counter(l for l in labels if l)
    if len(counts) <= target_max:
        return labels

    labels_block = '\n'.join(f'  "{k}" — {v}' for k, v in counts.most_common())
    prompt = MERGE_PROMPT.format(
        task_desc=TASK_DESCRIPTIONS[task_key],
        labels_block=labels_block,
        target_min=target_min,
        target_max=target_max,
    )
    text, stats = llm(prompt, model)
    n_in = stats.get('input_tokens', 0)
    n_out = stats.get('output_tokens', 0)
    print(f'  [merge {len(counts)} labels] tokens={n_in}+{n_out}')

    block = _extract_json(text, 'object')
    if not block:
        _dump_debug('merge_fail', prompt, text)
        print('  WARNING: merge response unparseable, keeping original labels')
        return labels
    try:
        grouped = json.loads(block)
    except json.JSONDecodeError:
        _dump_debug('merge_fail', prompt, text)
        print('  WARNING: merge JSON invalid, keeping original labels')
        return labels

    # grouped is {canonical: [orig, orig, ...]}; invert to {orig: canonical}
    mapping: dict[str, str] = {}
    for canonical, originals in grouped.items():
        if not isinstance(originals, list):
            continue
        for orig in originals:
            if isinstance(orig, str):
                mapping[orig] = canonical
    lc_mapping = {k.lower(): v for k, v in mapping.items()}

    n_canonical = len(grouped)
    n_mapped = sum(1 for l in labels if l in mapping or (l and l.lower() in lc_mapping))
    n_unmapped = sum(1 for l in labels if l and l not in mapping and l.lower() not in lc_mapping)
    print(f'  merged into {n_canonical} canonical labels '
          f'({n_mapped} mapped, {n_unmapped} unmapped kept as-is)')

    merged: list[str | None] = []
    for l in labels:
        if l is None:
            merged.append(None)
        elif l in mapping:
            merged.append(mapping[l])
        elif l.lower() in lc_mapping:
            merged.append(lc_mapping[l.lower()])
        else:
            merged.append(l)
    return merged


# ---------------------------------------------------------------------------
# Stage 4 — synthesize a ptool spec per selected category
# ---------------------------------------------------------------------------

SYNTHESIZE_PROMPT = """\
You are designing a reusable reasoning tool (Python function) for solving
this task:

{task_desc}

The tool should capture this frequently-used reasoning action:
  "{category}"

Below are example agent thoughts that exhibit this reasoning action:

{examples_block}

The tool will be a Python function with this signature:

    def {{func_name}}(narrative: str, focus: str) -> str

Where:
  - narrative: the full narrative text of the problem
  - focus:     what specific aspect the agent wants to focus on (e.g. a
               target person, a role, a constraint type, a belief state)
  - returns:   a structured string (plain text or JSON-shaped) with the
               tool's output

Design the tool:
  1. func_name:    snake_case Python identifier
  2. display_name: CamelCase version
  3. short_desc:   one-sentence description for the agent's system prompt
  4. docstring:    multi-line docstring covering
     - what information to extract / reason about
     - how the response should be structured
     - what the agent should pay attention to (hard disqualifiers, tricky
       aspects, theory-of-mind issues, etc.)
     - a concrete "Returns:" example showing the output shape

Output as JSON inside <answer>...</answer>. The docstring should use
literal "\\n" escape sequences for newlines so the JSON is valid.

<answer>
{{
  "func_name": "snake_case_name",
  "display_name": "CamelCaseName",
  "short_desc": "one sentence.",
  "docstring": "multi-line docstring with \\n escapes..."
}}
</answer>
"""


def synthesize_ptool(category: str, examples: list[dict], task_key: str,
                     model: str) -> dict | None:
    blocks = []
    for i, ex in enumerate(examples, 1):
        text = ex['text']
        if len(text) > 800:
            text = text[:800] + '...'
        blocks.append(
            f'--- Example {i} (case {ex["case"]}, pos {ex["pos"]}) ---\n{text}'
        )
    examples_block = '\n\n'.join(blocks)

    prompt = SYNTHESIZE_PROMPT.format(
        task_desc=TASK_DESCRIPTIONS[task_key],
        category=category,
        examples_block=examples_block,
    )
    text, stats = llm(prompt, model)
    n_in = stats.get('input_tokens', 0)
    n_out = stats.get('output_tokens', 0)
    print(f'  [synthesize "{category}"] tokens={n_in}+{n_out}')

    block = _extract_json(text, 'object')
    if not block:
        _dump_debug('synth_fail', prompt, text)
        print(f'  WARNING: synthesis response unparseable for {category!r}')
        return None
    try:
        spec = json.loads(block)
    except json.JSONDecodeError:
        # Try a crude repair: escape bare newlines inside string values
        try:
            spec = json.loads(re.sub(r'(?<!\\)\n', r'\\n', block))
        except json.JSONDecodeError:
            _dump_debug('synth_fail', prompt, text)
            print(f'  WARNING: synthesis JSON invalid for {category!r}')
            return None
    return spec


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run_one_task(task_key: str, trace_path: pathlib.Path, model: str,
                 output_dir: pathlib.Path, min_count: int, max_ptools: int
                 ) -> dict:
    print(f'\n=== {task_key} ===')
    print(f'trace: {trace_path}')

    items = load_thoughts(trace_path)
    print(f'loaded {len(items)} thoughts')
    if not items:
        return {'task': task_key, 'error': 'no thoughts'}

    labels = categorize_items(items, task_key, model)
    n_labeled = sum(1 for l in labels if l)
    print(f'categorized {n_labeled}/{len(items)} thoughts')

    labels = merge_categories(labels, task_key, model)
    counts = Counter(l for l in labels if l).most_common()
    print(f'unique categories after merge: {len(counts)}')

    categories_report = []
    for cat, count in counts:
        examples_of_cat = [items[i] for i, l in enumerate(labels) if l == cat]
        categories_report.append({
            'category': cat,
            'count': count,
            'sample_thoughts': [
                {
                    'case': e['case'],
                    'pos': e['pos'],
                    'correct': e['correct'],
                    'text': e['text'][:500],
                }
                for e in examples_of_cat[:5]
            ],
        })

    ptools = []
    for cat, count in counts:
        if len(ptools) >= max_ptools:
            break
        if count < min_count:
            break
        examples_of_cat = [items[i] for i, l in enumerate(labels) if l == cat][:5]
        spec = synthesize_ptool(cat, examples_of_cat, task_key, model)
        if spec is None:
            continue
        spec['source_category'] = cat
        spec['count'] = count
        spec['example_cases'] = [
            f'{e["case"]}:pos{e["pos"]}' for e in examples_of_cat
        ]
        ptools.append(spec)

    task_dir = output_dir / task_key
    task_dir.mkdir(parents=True, exist_ok=True)

    report = {
        'task': task_key,
        'trace_path': str(trace_path),
        'model': model,
        'n_thoughts': len(items),
        'n_labeled': n_labeled,
        'n_unique_categories': len(counts),
        'min_count': min_count,
        'max_ptools': max_ptools,
        'categories': categories_report,
        'ptools': ptools,
    }
    (task_dir / 'report.json').write_text(
        json.dumps(report, indent=2, ensure_ascii=False)
    )
    (task_dir / 'report.md').write_text(render_markdown(report))
    print(f'wrote {task_dir}/report.json and report.md')
    return report


def render_markdown(report: dict) -> str:
    lines: list[str] = []
    lines.append(f'# Induction report — {report["task"]} (original method)')
    lines.append('')
    lines.append(f'- Trace: `{report["trace_path"]}`')
    lines.append(f'- Model: `{report["model"]}`')
    lines.append(f'- Thoughts: {report["n_thoughts"]} loaded, '
                 f'{report["n_labeled"]} labeled')
    lines.append(f'- Unique categories: {report["n_unique_categories"]}')
    lines.append(f'- Synthesized ptools: {len(report["ptools"])} '
                 f'(min_count={report["min_count"]}, '
                 f'max_ptools={report["max_ptools"]})')
    lines.append('')

    lines.append('## Categories (by frequency)')
    lines.append('')
    for c in report['categories']:
        lines.append(f'### {c["category"]} — {c["count"]}')
        for ex in c['sample_thoughts'][:3]:
            text = ex['text'].replace('\n', ' ').strip()
            if len(text) > 240:
                text = text[:240] + '...'
            mark = 'Y' if ex['correct'] else 'N'
            lines.append(
                f'- [{mark}] `{ex["case"]}:pos{ex["pos"]}` — {text}'
            )
        lines.append('')

    lines.append('## Synthesized ptools')
    lines.append('')
    for i, p in enumerate(report['ptools'], 1):
        name = p.get('display_name') or p.get('func_name') or '?'
        lines.append(f'### {i}. {name}')
        lines.append(
            f'- Source category: **{p["source_category"]}** '
            f'({p["count"]} occurrences)'
        )
        lines.append(f'- func_name: `{p.get("func_name", "?")}`')
        lines.append(f'- short_desc: {p.get("short_desc", "")}')
        lines.append('')
        lines.append('```python')
        lines.append(
            f'def {p.get("func_name", "unknown")}'
            '(narrative: str, focus: str) -> str:'
        )
        doc = p.get('docstring', '')
        lines.append('    """')
        for dl in doc.split('\n'):
            lines.append(f'    {dl}' if dl else '')
        lines.append('    """')
        lines.append('```')
        lines.append('')
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task', choices=['murder', 'object', 'team', 'all'],
                   default='all')
    p.add_argument('--trace', default=None,
                   help='Override trace path (only valid with single --task)')
    p.add_argument('--variant', default='original',
                   help='Variant label for output subdirectory')
    p.add_argument('--model',
                   default='together_ai/deepseek-ai/DeepSeek-V3')
    p.add_argument('--output-dir', default='induction_out')
    p.add_argument('--min-count', type=int, default=3)
    p.add_argument('--max-ptools', type=int, default=5)
    args = p.parse_args()

    if args.trace and args.task == 'all':
        raise SystemExit('--trace requires a single --task')

    config.configure(cfg={
        'llm': {'model': args.model, 'max_tokens': 8192},
        'cachier': {
            'cache_dir': str(_BENCHMARK_DIR / 'llm_cache'),
            'enable_caching': True,
        },
    })

    out_dir = _BENCHMARK_DIR / args.output_dir / args.variant
    global _DEBUG_DIR
    _DEBUG_DIR = out_dir / '_debug'

    tasks = ['murder', 'object', 'team'] if args.task == 'all' else [args.task]

    summaries = []
    for task in tasks:
        if args.trace:
            trace_path = pathlib.Path(args.trace)
        else:
            trace_path = _BENCHMARK_DIR / DEFAULT_TRACE_PATHS[task]
        if not trace_path.exists():
            print(f'WARNING: {trace_path} not found, skipping')
            continue
        report = run_one_task(
            task, trace_path, args.model, out_dir,
            args.min_count, args.max_ptools,
        )
        summaries.append(
            {'task': task, 'n_ptools': len(report.get('ptools', []))}
        )

    print('\n=== summary ===')
    for s in summaries:
        print(f'  {s["task"]}: {s["n_ptools"]} ptools')


if __name__ == '__main__':
    main()
