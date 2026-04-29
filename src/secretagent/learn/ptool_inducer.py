"""Learner that induces ptool specs from recorded agent thoughts.

Pipeline:
  1. Collect agent thoughts from recorded rollouts (step_info[].thought)
  2. LLM categorize each thought into a short reasoning-action-type label
  3. Merge synonyms if too many unique labels
  4. For top-k categories (by frequency), LLM synthesize a ptool spec
     (func_name, display_name, short_desc, docstring)
  5. Save as learned_ptools.py with @interface stubs + implementation.yaml

The resulting learned_ptools.py can be loaded by any agent via
`tool_module='__learned__'`, `learner='ptool_inducer'`.

Two input modes:
  - 'react': extract thoughts from ReAct-style rollouts (step_info[].thought)
  - 'cot':   chunk full CoT responses (rollout[0].output) into reasoning steps

The ptool signature is configurable (default: `(focus: str) -> str`).
Benchmark-specific state injection (e.g. narrative, prompt) happens at
call time via a module-level state dict the benchmark provides.
"""

import json
import re
import yaml
from collections import Counter
from keyword import iskeyword
from pathlib import Path
from typing import Optional

from secretagent.learn.base import Learner
from secretagent.llm_util import llm


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


SYNTHESIZE_PROMPT = """\
You are designing a reusable reasoning tool (Python function) for solving
this task:

{task_desc}

The tool should capture this frequently-used reasoning action:
  "{category}"

Below are example agent thoughts that exhibit this reasoning action:

{examples_block}

The tool will be a Python function with this signature:

    {signature}

{sig_doc}

Design the tool:
  1. func_name:    snake_case Python identifier
  2. display_name: CamelCase version
  3. short_desc:   one-sentence description for the agent's system prompt
  4. docstring:    multi-line docstring covering
     - what information to extract / reason about
     - how the response should be structured
     - what the agent should pay attention to
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


_ANSWER_BLOCK_RE = re.compile(r'<answer>(.*?)</answer>', re.DOTALL)


def _extract_json(text: str, shape: str) -> Optional[str]:
    """Extract a JSON array or object from an LLM response."""
    m = _ANSWER_BLOCK_RE.search(text)
    candidates: list[str] = []
    if m:
        candidates.append(m.group(1).strip())
    candidates.append(text)

    open_ch, close_ch = ('[', ']') if shape == 'array' else ('{', '}')

    for candidate in candidates:
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


def _sanitize_identifier(name: str, used: set) -> str:
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name.strip())
    if not name or not (name[0].isalpha() or name[0] == '_'):
        name = 'p_' + name
    if iskeyword(name):
        name = name + '_'
    base = name
    i = 2
    while name in used:
        name = f'{base}_{i}'
        i += 1
    used.add(name)
    return name


def _indent_docstring(doc: str, indent: str = '    ') -> str:
    doc = doc.replace('\\n', '\n')
    doc = doc.replace('"""', '\\"\\"\\"')
    lines = doc.split('\n')
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return '\n'.join(f'{indent}{ln}' if ln.strip() else '' for ln in lines)


def _chunk_cot_response(text: str) -> list[str]:
    """Split a CoT response into reasoning chunks."""
    text = text.strip()
    if not text:
        return []
    paragraphs = re.split(r'\n\s*\n', text)
    chunks: list[str] = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if len(p) > 800:
            sub = re.split(r'\n(?=(?:###|####|\*\*Step \d+|\d+\.\s+\*\*|- \*\*))', p)
            for s in sub:
                s = s.strip()
                if s:
                    chunks.append(s)
        else:
            chunks.append(p)
    return chunks


class PtoolInducer(Learner):
    """Induce ptool specs from recorded agent thoughts.

    Args:
        interface_name: top-level interface being learned (used for naming
            the output dir; the learned ptools are *tools* for this iface).
        train_dir: base directory for learned output.
        task_desc: natural-language description of the task (goes into
            categorize/merge/synthesize prompts).
        trace_mode: 'react' → extract thoughts from step_info; 'cot' →
            chunk the full rollout output.
        state_module: module to import state from at call time, e.g.
            `ptools_common`. Required if state_expr is set.
        state_expr: expression to evaluate in that module at call time,
            e.g. `_REACT_STATE["narrative"]`. If both state_module and
            state_expr are None, stubs are exposed with a simple
            `(focus: str) -> str` signature.
        only_correct: if True, only use rollouts where `correct` is True.
        max_ptools: maximum number of ptools to synthesize.
        min_count: minimum occurrences of a category to synthesize.
        model: LLM model for categorize/merge/synthesize.
    """

    tag = 'ptool_inducer'

    def __init__(
        self,
        interface_name: str,
        train_dir: str,
        task_desc: str,
        trace_mode: str = 'react',
        state_module: Optional[str] = None,
        state_expr: Optional[str] = None,
        only_correct: bool = False,
        max_ptools: int = 5,
        min_count: int = 3,
        model: Optional[str] = None,
    ):
        if (state_module is None) != (state_expr is None):
            raise ValueError(
                'state_module and state_expr must be set together or both None')
        super().__init__(
            interface_name=interface_name,
            train_dir=train_dir,
            file_under=f'{interface_name}__{self.tag}',
        )
        self.produce_files(['learned_ptools.py', 'report.json', 'report.md'])
        self.task_desc = task_desc
        self.trace_mode = trace_mode
        self.state_module = state_module
        self.state_expr = state_expr
        self.only_correct = only_correct
        self.max_ptools = max_ptools
        self.min_count = min_count
        self.model = model or 'together_ai/deepseek-ai/DeepSeek-V3'
        self._items: list[dict] = []
        self._labels: list[Optional[str]] = []
        self._counts: list = []
        self._ptools: list[dict] = []

    def learn(self, dirs, latest=1, check=None):
        self.collect_distillation_data(dirs, latest, check)
        print(f'collected {len(self._items)} thoughts in working directory {self.out_dir}')
        self.fit()
        output_file = self.save_implementation()
        print(self.report())
        print(f'saved output to {output_file}')

    # --- override data collection to extract thoughts, not IO pairs ---

    def collect_distillation_data(self, dirs, latest=1, check=None):
        """Collect thoughts from rollouts instead of input/output pairs."""
        from secretagent import savefile
        filtered = savefile.filter_paths(dirs, latest=latest, dotlist=check or [])
        if not filtered:
            raise ValueError(f'no directories after filtering: {dirs}')

        items: list[dict] = []
        for d in filtered:
            jsonl = Path(d) / 'results.jsonl'
            if not jsonl.exists():
                continue
            with open(jsonl) as f:
                for line in f:
                    row = json.loads(line)
                    correct = bool(row.get('correct'))
                    if self.only_correct and not correct:
                        continue
                    case_name = row.get('case_name') or '?'
                    for rollout in row.get('rollout') or []:
                        if self.trace_mode == 'cot':
                            text = rollout.get('output', '')
                            for pos, chunk in enumerate(_chunk_cot_response(text)):
                                items.append({'case': case_name, 'pos': pos,
                                              'text': chunk, 'correct': correct})
                        else:  # react
                            for pos, step in enumerate(rollout.get('step_info', [])):
                                if not isinstance(step, dict):
                                    continue
                                t = step.get('thought', '')
                                if t and t.strip():
                                    items.append({'case': case_name, 'pos': pos,
                                                  'text': t.strip(),
                                                  'correct': correct})
        self._items = items
        # Save provenance
        data_path = Path(self.created_files['data.json'])
        data_path.parent.mkdir(parents=True, exist_ok=True)
        with open(data_path, 'w') as f:
            json.dump({'n_thoughts': len(items),
                       'trace_mode': self.trace_mode,
                       'only_correct': self.only_correct,
                       'items': items[:100]}, f, indent=2)
        sources = Path(self.created_files['sources.txt'])
        sources.write_text('\n'.join(str(d) for d in filtered))
        return self

    # --- main pipeline ---

    def fit(self) -> Learner:
        items = self._items
        if not items:
            raise ValueError('no thoughts collected')

        print(f'loaded {len(items)} thoughts (trace_mode={self.trace_mode}, '
              f'only_correct={self.only_correct})')

        self._labels = self._categorize(items)
        n_labeled = sum(1 for l in self._labels if l)
        print(f'categorized {n_labeled}/{len(items)} thoughts')

        self._labels = self._merge(self._labels)
        self._counts = Counter(l for l in self._labels if l).most_common()
        print(f'unique categories after merge: {len(self._counts)}')

        self._ptools = []
        for cat, count in self._counts:
            if len(self._ptools) >= self.max_ptools:
                break
            if count < self.min_count:
                break
            examples = [items[i] for i, l in enumerate(self._labels)
                        if l == cat][:5]
            spec = self._synthesize(cat, examples)
            if spec is None:
                continue
            spec['source_category'] = cat
            spec['count'] = count
            self._ptools.append(spec)

        return self

    # --- sub-steps ---

    def _categorize(self, items: list[dict], batch_size: int = 30
                    ) -> list[Optional[str]]:
        labels: list[Optional[str]] = [None] * len(items)
        for start in range(0, len(items), batch_size):
            batch = items[start:start + batch_size]
            lines = []
            for i, it in enumerate(batch):
                text = it['text'].replace('\n', ' ').strip()
                if len(text) > 400:
                    text = text[:400] + '...'
                lines.append(f'[{start + i}] {text}')
            prompt = CATEGORIZE_PROMPT.format(
                task_desc=self.task_desc,
                items_block='\n'.join(lines),
            )
            text, _ = llm(prompt, self.model)
            block = _extract_json(text, 'array')
            if not block:
                continue
            try:
                arr = json.loads(block)
            except json.JSONDecodeError:
                continue
            for entry in arr:
                if not isinstance(entry, dict):
                    continue
                try:
                    idx = int(entry.get('index', -1))
                    cat = str(entry.get('category', '')).strip()
                except (ValueError, TypeError):
                    continue
                if 0 <= idx < len(items) and cat:
                    labels[idx] = cat
        return labels

    def _merge(self, labels: list[Optional[str]],
               target_min: int = 5, target_max: int = 10
               ) -> list[Optional[str]]:
        counts = Counter(l for l in labels if l)
        if len(counts) <= target_max:
            return labels
        block = '\n'.join(f'  "{k}" — {v}' for k, v in counts.most_common())
        prompt = MERGE_PROMPT.format(
            task_desc=self.task_desc, labels_block=block,
            target_min=target_min, target_max=target_max,
        )
        text, _ = llm(prompt, self.model)
        js = _extract_json(text, 'object')
        if not js:
            return labels
        try:
            grouped = json.loads(js)
        except json.JSONDecodeError:
            return labels
        mapping: dict[str, str] = {}
        for canonical, origs in grouped.items():
            if not isinstance(origs, list):
                continue
            for o in origs:
                if isinstance(o, str):
                    mapping[o] = canonical
        lc = {k.lower(): v for k, v in mapping.items()}
        merged: list[Optional[str]] = []
        for l in labels:
            if l is None:
                merged.append(None)
            elif l in mapping:
                merged.append(mapping[l])
            elif l.lower() in lc:
                merged.append(lc[l.lower()])
            else:
                merged.append(l)
        return merged

    def _synthesize(self, category: str, examples: list[dict]
                    ) -> Optional[dict]:
        blocks = []
        for i, ex in enumerate(examples, 1):
            text = ex['text']
            if len(text) > 800:
                text = text[:800] + '...'
            blocks.append(
                f'--- Example {i} (case {ex["case"]}, pos {ex["pos"]}) ---\n{text}'
            )
        if self.state_expr:
            signature = 'def {func_name}(context: str, focus: str) -> str'
            sig_doc = (
                'Where `context` is the full problem text (narrative, prompt, '
                'etc.) and `focus` is what specific aspect the agent wants to '
                'reason about (e.g. a person, a location, a constraint type). '
                'Returns a structured string.'
            )
        else:
            signature = 'def {func_name}(focus: str) -> str'
            sig_doc = (
                'Where `focus` is what specific aspect the agent wants to '
                'reason about. Returns a structured string.'
            )
        prompt = SYNTHESIZE_PROMPT.format(
            task_desc=self.task_desc, category=category,
            examples_block='\n\n'.join(blocks),
            signature=signature,
            sig_doc=sig_doc,
        )
        text, _ = llm(prompt, self.model)
        js = _extract_json(text, 'object')
        if not js:
            return None
        try:
            return json.loads(js)
        except json.JSONDecodeError:
            try:
                return json.loads(re.sub(r'(?<!\\)\n', r'\\n', js))
            except json.JSONDecodeError:
                return None

    # --- output ---

    def save_implementation(self) -> Path:
        used_stub: set = set()
        used_wrap: set = set()
        wrapper_names: list[str] = []
        parts = [
            f'"""Induced ptools for {self.interface_name}."""\n\n',
            'from secretagent.core import implement_via\n',
        ]
        # Import state dict symbol (root identifier before any brackets)
        if self.state_module and self.state_expr:
            root = re.match(r'[A-Za-z_][A-Za-z0-9_]*', self.state_expr).group(0)
            parts.append(f'from {self.state_module} import {root}\n')
        parts.append('\n\n')

        for p in self._ptools:
            raw = p.get('func_name') or ''
            if not raw:
                continue
            wrap_name = _sanitize_identifier(raw, used_wrap)
            doc_body = _indent_docstring(
                p.get('docstring') or p.get('short_desc') or wrap_name)
            short_desc = (p.get('short_desc') or '').strip()

            if self.state_expr:
                # Stub takes (context, focus); wrapper takes (focus) only
                stub_name = _sanitize_identifier(
                    f'_{wrap_name}_impl', used_stub)
                parts.append("@implement_via('simulate')\n")
                parts.append(
                    f'def {stub_name}(context: str, focus: str) -> str:\n')
                parts.append('    """\n')
                if doc_body:
                    parts.append(doc_body + '\n')
                parts.append('    """\n\n\n')

                wrap_doc = short_desc or f'Induced reasoning helper: {wrap_name}.'
                wrap_doc = wrap_doc.replace('"""', '\\"\\"\\"')
                parts.append(f'def {wrap_name}(focus: str) -> str:\n')
                parts.append(f'    """{wrap_doc}"""\n')
                parts.append(
                    f'    return {stub_name}({self.state_expr}, focus)\n\n\n'
                )
                wrapper_names.append(wrap_name)
            else:
                # Single @interface stub exposed directly via simulate
                parts.append("@implement_via('simulate')\n")
                parts.append(f'def {wrap_name}(focus: str) -> str:\n')
                parts.append('    """\n')
                if doc_body:
                    parts.append(doc_body + '\n')
                parts.append('    """\n\n\n')
                wrapper_names.append(wrap_name)

        Path(self.created_files['learned_ptools.py']).write_text(
            ''.join(parts))

        # implementation.yaml: explicit tool list (not __all__) so plain
        # wrapper callables get picked up correctly. tool_module is
        # __learned__ so resolve_dotted prefixes bare names with the
        # loaded module path.
        impl = {self.interface_name: {
            'method': 'simulate_pydantic',
            'tools': list(wrapper_names),
            'tool_module': '__learned__',
            'learner': self.tag,
        }}
        impl_path = Path(self.created_files['implementation.yaml'])
        impl_path.write_text(yaml.dump(impl))

        # report.json + report.md for inspection
        report = {
            'interface': self.interface_name,
            'trace_mode': self.trace_mode,
            'only_correct': self.only_correct,
            'model': self.model,
            'n_thoughts': len(self._items),
            'n_labeled': sum(1 for l in self._labels if l),
            'n_unique_categories': len(self._counts),
            'ptools': self._ptools,
            'categories': [
                {'category': c, 'count': n}
                for c, n in self._counts
            ],
        }
        Path(self.created_files['report.json']).write_text(
            json.dumps(report, indent=2, ensure_ascii=False))
        Path(self.created_files['report.md']).write_text(
            self._render_markdown(report))

        return impl_path

    def _render_markdown(self, report: dict) -> str:
        lines = [
            f'# PtoolInducer report — {report["interface"]}',
            '',
            f'- Trace mode: `{report["trace_mode"]}`',
            f'- Only correct: {report["only_correct"]}',
            f'- Model: `{report["model"]}`',
            f'- Thoughts: {report["n_thoughts"]}, labeled: {report["n_labeled"]}',
            f'- Unique categories: {report["n_unique_categories"]}',
            f'- Synthesized ptools: {len(report["ptools"])}',
            '',
            '## Synthesized ptools',
            '',
        ]
        for i, p in enumerate(report['ptools'], 1):
            lines.append(f'### {i}. {p.get("display_name") or p.get("func_name")}')
            lines.append(f'- Source category: **{p.get("source_category")}** ({p.get("count")} occurrences)')
            lines.append(f'- short_desc: {p.get("short_desc", "")}')
            lines.append('')
        return '\n'.join(lines)

    def report(self) -> str:
        return (
            f'induced {len(self._ptools)} ptools from '
            f'{sum(1 for l in self._labels if l)} labeled thoughts '
            f'(mode={self.trace_mode}, only_correct={self.only_correct})'
        )
