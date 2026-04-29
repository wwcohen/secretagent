"""Workflow-level code distillation.

Generates a top-level workflow function that calls existing benchmark
ptools (pure-Python helpers and/or simulate LLM ptools). Differs from
EndToEndDistillLearner by introspecting an existing tool module and
exposing those callable signatures to the LLM, plus optional reference
workflows from other benchmarks (few-shot structural inspiration) and
optional execution traces from existing rollouts (data flow inspiration).

Inputs:
- dataset_file: top-level (input → expected_output) JSON
- tool_module: dotted module path with hand-written ptools (e.g. "ptools_meeting")
- reference_workflow_files: list of .py files from other benchmarks (few-shot)
- trace_dirs: list of recording dirs (results.jsonl) — sample 2-3 successful
  rollouts to show tool call sequences

Output:
- learned.py: generated workflow function + `from <tool_module> import *`
- implementation.yaml: binds top-level interface to learned_code
"""

import importlib
import inspect
import json
import os
import random
import textwrap
from pathlib import Path
from typing import Any, Optional

import yaml

from secretagent import savefile
from secretagent.dataset import Case, Dataset
from secretagent.learn.codedistill import (
    CodeDistillLearner, _evaluate_on_cases, _extract_code,
    _compile_function, _format_errors, _truncate_repr,
)
from secretagent import llm_util


def _load_tool_module(module_spec: str):
    """Load a tool module either by dotted name (importlib) or by file path.

    File-path mode is needed for Class 3, where the tool module is the
    induced_ptools.py produced by PtoolInducer at a non-importable path.
    """
    p = Path(module_spec)
    if p.suffix == '.py' and p.exists():
        import importlib.util as iu
        spec = iu.spec_from_file_location('_tool_module_dyn', p)
        mod = iu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return importlib.import_module(module_spec)


def _introspect_tool_module(module_path: str, tool_filter: Optional[list[str]] = None) -> str:
    """Introspect a tool module and return its callables as Python signatures.

    For each public callable in the module, render:
        def name(arg1: T, arg2: T) -> R:
            \"\"\"docstring (first 600 chars)\"\"\"

    If tool_filter is given, restrict to those names.
    """
    mod = _load_tool_module(module_path)
    lines = []
    names = sorted(n for n in dir(mod) if not n.startswith('_'))
    for name in names:
        if tool_filter and name not in tool_filter:
            continue
        obj = getattr(mod, name)
        if not callable(obj) or inspect.isclass(obj):
            continue
        try:
            sig = inspect.signature(obj)
        except (ValueError, TypeError):
            continue
        doc = (inspect.getdoc(obj) or '').strip()
        if len(doc) > 600:
            doc = doc[:600] + '...'
        block = f"def {name}{sig}:"
        if doc:
            block += f'\n    """{doc}"""'
        else:
            block += "\n    ..."
        lines.append(block)
    return "\n\n".join(lines)


def _format_workflow_examples(cases, max_cases: int = 10) -> str:
    """Format dataset (input → expected_output) for the prompt."""
    lines = []
    for case in cases[:max_cases]:
        args = case.input_args or []
        kw = case.input_kw or {}
        args_str = ", ".join(_truncate_repr(a, 600) for a in args)
        if kw:
            kw_str = ", ".join(f"{k}={_truncate_repr(v, 600)}" for k, v in kw.items())
            args_str = f"{args_str}, {kw_str}" if args_str else kw_str
        out = _truncate_repr(case.expected_output, 1500)
        lines.append(f"  Input: ({args_str})\n  Expected output: {out}\n")
    return "\n".join(lines)


def _load_reference_workflows(files: list[Path], max_chars: int = 4000) -> str:
    """Load reference hand-written workflow files as few-shot inspiration."""
    blocks = []
    for f in files:
        if not Path(f).exists():
            continue
        text = Path(f).read_text(encoding='utf-8')
        if len(text) > max_chars:
            text = text[:max_chars] + '\n# ... (truncated)\n'
        blocks.append(f"# === Reference: {Path(f).name} ===\n{text}")
    return "\n\n".join(blocks)


def _sample_traces(trace_dirs: list[Path], top_func: Optional[str] = None,
                   max_traces: int = 3, only_correct: bool = True,
                   include_step_info: bool = True) -> str:
    """Sample 2-3 successful rollouts from existing recordings.

    Each trace is rendered as:
        INPUT: (top-level args truncated)
          step 1: ptool(args) -> output
          step 2: ...
        EXPECTED: <expected_output>

    For ReAct (simulate_pydantic) recordings, tool calls live in
    rollout[0].step_info as tool_call/tool_return pairs. Walk those when
    available to expose the agent's actual tool-call sequence.

    Picks distinct rollouts (no duplicate signatures).
    """
    rollouts = []
    seen_sigs = set()
    for d in trace_dirs:
        jl = Path(d) / 'results.jsonl'
        if not jl.exists():
            continue
        for line in jl.open():
            rec = json.loads(line)
            if only_correct and not rec.get('correct'):
                continue
            rollout = rec.get('rollout') or []
            if not rollout:
                continue
            # Restrict to records where top-level func matches the target
            if top_func is not None and rollout[0].get('func') != top_func:
                continue
            sig = tuple(s.get('func', '') for s in rollout)
            if sig in seen_sigs:
                continue
            seen_sigs.add(sig)
            rollouts.append(rec)
            if len(rollouts) >= max_traces * 4:
                break
        if len(rollouts) >= max_traces * 4:
            break

    if not rollouts:
        return ""

    rng = random.Random(42)
    rng.shuffle(rollouts)
    rollouts = rollouts[:max_traces]

    blocks = []
    for rec in rollouts:
        rollout = rec.get('rollout') or []
        top = rollout[0]
        top_args_str = ", ".join(
            _truncate_repr(a, 200) for a in (top.get('args') or []))
        lines = [f"INPUT: ({top_args_str})"]

        # Workflow-style trace: rollout[1:] are sub-step interface calls
        for step in rollout[1:]:
            func = step.get('func', '?')
            args = step.get('args') or []
            output = step.get('output')
            args_str = ", ".join(_truncate_repr(a, 150) for a in args)
            out_str = _truncate_repr(output, 300)
            lines.append(f"  {func}({args_str}) -> {out_str}")

        # ReAct-style trace: rollout[0].step_info has tool_call/tool_return events
        if include_step_info:
            step_info = top.get('step_info') or []
            for step in step_info:
                if not isinstance(step, dict):
                    continue
                tc = step.get('tool_call')
                tr = step.get('tool_return')
                if tc:
                    args_str = _truncate_repr(step.get('args'), 150)
                    lines.append(f"  [react] call {tc}({args_str})")
                elif tr:
                    out_str = _truncate_repr(step.get('output'), 200)
                    lines.append(f"  [react] return {tr} -> {out_str}")

        expected = rec.get('expected_output')
        lines.append(f"EXPECTED: {_truncate_repr(expected, 300)}")
        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


def _sample_cross_benchmark_io(dataset_files: list[Path], max_per_file: int = 2) -> str:
    """Pull 1-2 (input → output) example pairs from each cross-benchmark
    dataset, to give the LLM a sense of the kinds of i/o problems other
    benchmarks solve. NOT intended as direct training data — purely as
    structural inspiration that a workflow can be a parse→solve→format
    pipeline of varied shape.
    """
    blocks = []
    for f in dataset_files:
        if not Path(f).exists():
            continue
        try:
            ds = json.loads(Path(f).read_text())
        except Exception:
            continue
        cases = ds.get('cases') if isinstance(ds, dict) else None
        if not cases:
            continue
        rng = random.Random(42)
        sampled = rng.sample(cases, min(max_per_file, len(cases)))
        ds_name = ds.get('name') or Path(f).stem
        lines = [f"# from benchmark: {ds_name}"]
        for c in sampled:
            args = c.get('input_args') or []
            args_str = ", ".join(_truncate_repr(a, 250) for a in args)
            out = _truncate_repr(c.get('expected_output'), 300)
            lines.append(f"  Input: ({args_str})")
            lines.append(f"  Output: {out}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


class WorkflowDistillLearner(CodeDistillLearner):
    """Learn a top-level workflow that calls hand-written tools.

    Reuses CodeDistillLearner's fit() multi-round + ensemble framework,
    but overrides _build_prompt to inject:
    - the introspected tool module signatures
    - reference workflows from other benchmarks
    - sampled traces from existing rollouts (NEW)
    Also runs an 80/20 train/val holdout to estimate generalization.
    """

    tag = 'workflow_distill'

    def __init__(self, interface_name: str, train_dir: str,
                 dataset_file: str,
                 tool_module: str,
                 output_field: Optional[str] = None,
                 tool_filter: Optional[list[str]] = None,
                 reference_workflow_files: Optional[list[str]] = None,
                 trace_dirs: Optional[list[str]] = None,
                 trace_top_func: Optional[str] = None,
                 react_trace_dirs: Optional[list[str]] = None,
                 cross_trace_dirs: Optional[list[str]] = None,
                 cross_dataset_files: Optional[list[str]] = None,
                 conf_file: Optional[str] = None,
                 model: str = 'claude-opus-4-6',
                 n_candidates: int = 3,
                 max_rounds: int = 3,
                 holdout_fraction: float = 0.2,
                 backoff: bool = True,
                 backoff_method: str = 'simulate'):
        # Skip parent __init__ because we don't load data from recordings.
        self.interface_name = interface_name
        self.train_dir = train_dir
        self.model = model
        self.n_candidates = n_candidates
        self.max_rounds = max_rounds
        self.tool_module = tool_module
        self.output_field = output_field
        self.tool_filter = tool_filter
        self.reference_workflow_files = [Path(f) for f in (reference_workflow_files or [])]
        self.trace_dirs = [Path(d) for d in (trace_dirs or [])]
        self.react_trace_dirs = [Path(d) for d in (react_trace_dirs or [])]
        self.cross_trace_dirs = [Path(d) for d in (cross_trace_dirs or [])]
        self.cross_dataset_files = [Path(f) for f in (cross_dataset_files or [])]
        self.conf_file = conf_file
        self.trace_top_func = trace_top_func or interface_name
        self.holdout_fraction = holdout_fraction
        self.backoff = backoff
        self.backoff_method = backoff_method
        self.generated_code: Optional[str] = None
        self.generated_fn = None
        self.train_accuracy: float = 0.0
        self.train_stats: dict = {}
        self.val_accuracy: float = 0.0
        self.val_stats: dict = {}
        self.best_round: int = 0
        self.total_candidates: int = 0

        # Set up output directory + files. Include source_configs/ so
        # LearnedCodeFactory can build a backoff impl (we write a synthetic
        # source-config that points the top-level interface at `simulate`,
        # giving a pure-LLM fallback when the generated workflow returns None).
        file_under = f'{interface_name}__{self.tag}'
        to_produce = ['data.json', 'learned.py', 'implementation.yaml',
                      'source_configs']
        filenames = savefile.filename_list(train_dir, to_produce, file_under)
        self.out_dir = Path(filenames[0]).parent
        self.created_files = {short: full for short, full in zip(to_produce, filenames)}

        # Load dataset
        ds = Dataset.model_validate_json(Path(dataset_file).read_text())
        if output_field:
            cases = []
            for c in ds.cases:
                if isinstance(c.expected_output, dict):
                    target = c.expected_output.get(output_field)
                else:
                    target = c.expected_output
                cases.append(Case(
                    name=c.name,
                    input_args=c.input_args,
                    input_kw=c.input_kw,
                    expected_output=target,
                ))
            self.dataset = Dataset(name=ds.name, cases=cases)
        else:
            self.dataset = ds

        os.makedirs(self.out_dir, exist_ok=True)
        with open(self.created_files['data.json'], 'w') as f:
            f.write(self.dataset.model_dump_json(indent=2))

    def _build_prompt(self, examples_text: str, trace_text: str,
                      error_feedback: str) -> str:
        """Construct prompt with tools, reference workflows, traces, examples."""
        tools_block = _introspect_tool_module(self.tool_module, self.tool_filter)
        ref_block = _load_reference_workflows(self.reference_workflow_files)
        in_domain_traces = _sample_traces(
            self.trace_dirs, top_func=self.trace_top_func,
            max_traces=3, only_correct=True)
        react_traces = _sample_traces(
            self.react_trace_dirs, top_func=self.trace_top_func,
            max_traces=3, only_correct=True, include_step_info=True)
        cross_traces = _sample_traces(
            self.cross_trace_dirs, top_func=None,
            max_traces=2, only_correct=True)
        cross_io = _sample_cross_benchmark_io(self.cross_dataset_files, max_per_file=2)

        parts = [
            f"You are writing the workflow function `{self.interface_name}` "
            f"that solves a task end-to-end by orchestrating existing tools.\n",
            f"Task examples (input → expected output):\n",
            examples_text,
        ]

        if tools_block:
            parts.append(textwrap.dedent("""
                Available tools (importable from the tool module — you can call any
                of these from inside your workflow). Some are pure-Python helpers
                (free, no LLM call); others are LLM-backed `simulate` ptools — prefer
                the pure-Python ones when possible:
            """))
            parts.append(tools_block)

        if in_domain_traces:
            parts.append("\nIn-domain tool-call traces from successful rollouts of "
                         "the existing baseline workflow (these show what tools were "
                         "called and what intermediate outputs look like — but the "
                         "actual workflow source code is hidden from you):\n")
            parts.append(in_domain_traces)

        if react_traces:
            parts.append("\nReAct agent traces (the agent reasoned and called tools "
                         "freely; useful as a sequence-of-thought inspiration):\n")
            parts.append(react_traces)

        if cross_io:
            parts.append("\nCross-benchmark i/o examples (from OTHER benchmarks — "
                         "different tasks, just to remind you that workflows can take "
                         "many shapes):\n")
            parts.append(cross_io)

        if cross_traces:
            parts.append("\nCross-benchmark tool-call traces (other benchmarks' "
                         "successful rollouts — structural inspiration only):\n")
            parts.append(cross_traces)

        if ref_block:
            parts.append(textwrap.dedent("""
                Reference hand-written workflows from OTHER benchmarks (structural
                inspiration only — these solve different tasks; do not copy their
                problem-specific logic):
            """))
            parts.append(ref_block)

        if trace_text:
            parts.append("\n" + trace_text + "\n")

        if error_feedback:
            parts.append("\n" + error_feedback + "\n")

        parts.append(textwrap.dedent(f"""
            Requirements:
            - Define `def {self.interface_name}(...)` matching the input signature
              shown in the examples
            - Inside the function, call the available tools as helpers; the file
              will start with `from {self.tool_module} import *` so the tools are
              already in scope
            - Prefer pure-Python helpers when possible (cheaper)
            - **Return None whenever the function cannot produce a confident,
              correctly-formatted answer** — e.g. if a tool call returns
              something unparseable, if a regex fails, if a required field
              is missing, if a numeric result is implausible. The runtime
              will fall back to a pure-LLM zero-shot call when you return
              None. **Returning a wrong answer is much worse than returning
              None** because backoff cannot rescue you when the answer is
              non-None.
            - Output must exactly match the format shown in the expected outputs
            - Use only standard library imports beyond the tool module
            - Write clean, correct, defensive Python code

            Return the workflow code in a ```python ... ``` block. Do not include
            the `from {self.tool_module} import *` line — it will be added at save
            time.
        """))
        return "\n".join(parts)

    def _bind_ptools_for_eval(self):
        """Bind the benchmark's simulate / direct ptools so that the
        generated workflow can call them during fit-time evaluation. We skip
        the target interface itself (that's what we are learning).

        Without this, calling an unbound simulate ptool inside the generated
        code raises and `_evaluate_on_cases` records it as abstained — train
        acc 0% even when the generated structure is correct.
        """
        if not self.conf_file:
            return
        from secretagent import config
        from secretagent.core import implement_via_config
        from omegaconf import OmegaConf
        import importlib
        config.configure(yaml_file=self.conf_file)
        ptool_module = _load_tool_module(self.tool_module)
        ptools_cfg = config.get('ptools')
        # OmegaConf DictConfig is NOT a dict subclass; convert to plain dict.
        if ptools_cfg is None:
            ptools_cfg = {}
        else:
            ptools_cfg = OmegaConf.to_container(ptools_cfg, resolve=True)
        # Skip the target interface and any 'DEFAULT'/unconfigured ptools.
        filtered = {}
        for name, cfg in ptools_cfg.items():
            if name == self.interface_name:
                continue
            if not isinstance(cfg, dict):
                continue
            if cfg.get('method') in (None, 'DEFAULT'):
                continue
            filtered[name] = dict(cfg)
        if filtered:
            print(f'  binding {len(filtered)} ptools from {self.conf_file}: '
                  f'{sorted(filtered.keys())}')
            implement_via_config(ptool_module, filtered)
        else:
            print(f'  no ptools to bind from {self.conf_file} '
                  f'(target={self.interface_name})')

    def fit(self) -> "WorkflowDistillLearner":
        """Multi-round + ensemble fit on train portion; report val acc on holdout."""
        # Bind benchmark ptools so generated workflows can actually call them
        self._bind_ptools_for_eval()

        rng = random.Random(42)
        all_cases = list(self.dataset.cases)
        rng.shuffle(all_cases)
        split = max(1, int(len(all_cases) * self.holdout_fraction))
        val_cases = all_cases[:split]
        train_cases = all_cases[split:]

        examples_text = _format_workflow_examples(train_cases)
        trace_text = ""  # workflow learner uses sampled traces in _build_prompt instead

        best_code, best_fn, best_accuracy = None, None, 0.0
        best_stats = {'correct': 0, 'wrong': 0, 'abstained': 0}
        error_feedback = ""

        for round_idx in range(self.max_rounds):
            candidates = []
            for _ in range(self.n_candidates):
                prompt = self._build_prompt(examples_text, trace_text, error_feedback)
                try:
                    llm_output, _ = llm_util.llm(prompt, self.model)
                except Exception as ex:
                    print(f'  LLM call failed: {ex}')
                    candidates.append((None, None, 0.0, [], {}))
                    continue
                code = _extract_code(llm_output)
                if code is None:
                    candidates.append((None, None, 0.0, [], {}))
                    continue
                # Make tool symbols visible to the generated workflow.
                # When tool_module is a dotted name we use `from X import *`;
                # when it's a file path we exec the module's source first.
                p = Path(self.tool_module)
                if p.suffix == '.py' and p.exists():
                    tool_src = p.read_text(encoding='utf-8')
                    exec_code = tool_src + '\n' + code
                else:
                    exec_code = f"from {self.tool_module} import *\n{code}"
                fn = _compile_function(exec_code, self.interface_name)
                accuracy, errors, stats = _evaluate_on_cases(fn, train_cases)
                candidates.append((code, fn, accuracy, errors, stats))
                self.total_candidates += 1

            round_best = max(candidates, key=lambda x: x[2])
            captured = round_best[2] > best_accuracy or (
                best_code is None and round_best[0] is not None
            )
            if captured:
                best_code, best_fn, best_accuracy = round_best[0], round_best[1], round_best[2]
                best_stats = round_best[4] if len(round_best) > 4 else {}
                self.best_round = round_idx + 1

            stats_str = round_best[4] if len(round_best) > 4 else {}
            print(f'  round {round_idx + 1}: train acc = {best_accuracy:.2%} '
                  f'(this round = {round_best[2]:.2%}, '
                  f'wrong={stats_str.get("wrong", "?")}, '
                  f'abstained={stats_str.get("abstained", "?")})')

            if best_accuracy >= 0.95:
                break
            # No round-1 early-stop for workflow distill: workflows are
            # complex enough that an initial 0% (often a parse / call-signature
            # bug) can be repaired by the next round's error feedback.

            if round_best[3]:
                error_feedback = _format_errors(round_best[3])

        self.generated_code = best_code
        self.generated_fn = best_fn
        self.train_accuracy = best_accuracy
        self.train_stats = best_stats

        # Report val accuracy on holdout (no extra LLM call)
        if best_fn is not None and val_cases:
            val_acc, _, val_stats = _evaluate_on_cases(best_fn, val_cases)
            self.val_accuracy = val_acc
            self.val_stats = val_stats
            print(f'  val (holdout {len(val_cases)}): acc = {val_acc:.2%}, '
                  f'wrong={val_stats.get("wrong", 0)}, '
                  f'abstained={val_stats.get("abstained", 0)}')
        return self

    def save_implementation(self) -> Path:
        """Write generated workflow with tool import + bind config."""
        if self.generated_code is None:
            raise ValueError("No code was generated. Did fit() succeed?")

        learned_outpath = Path(self.created_files['learned.py'])
        p = Path(self.tool_module)
        if p.suffix == '.py' and p.exists():
            # Inline the tool module's source (Class 3 style: induced ptool
            # module isn't importable from a normal sys.path)
            header = (
                f'"""Auto-generated workflow-distilled implementation for '
                f'{self.interface_name}.\n\n'
                f'Tools from {self.tool_module} are inlined below.\n"""\n\n'
            )
            tool_src = p.read_text(encoding='utf-8')
            content = header + tool_src + '\n\n' + self.generated_code + '\n'
        else:
            header = (
                f'"""Auto-generated workflow-distilled implementation for '
                f'{self.interface_name}.\n\n'
                f'Calls existing tools from {self.tool_module}.\n"""\n\n'
                f'from {self.tool_module} import *\n\n'
            )
            content = header + self.generated_code + '\n'
        learned_outpath.write_text(content, encoding='utf-8')

        impl_outpath = Path(self.created_files['implementation.yaml'])
        impl = {self.interface_name: {
            'method': 'learned_code',
            'learner': self.tag,
            'backoff': self.backoff}}
        impl_outpath.write_text(yaml.dump(impl))

        # Write a synthetic source_configs/<top>.yaml so LearnedCodeFactory
        # can build a backoff implementation when the generated workflow
        # returns None. The backoff is intentionally NOT the hand-written
        # workflow (we are trying to beat it). Instead we point to a pure-
        # LLM `simulate` call on the same interface — i.e. zero-shot LLM.
        if self.backoff:
            sc_dir = Path(self.created_files['source_configs'])
            os.makedirs(sc_dir, exist_ok=True)
            backoff_cfg = {
                'ptools': {
                    self.interface_name: {'method': self.backoff_method}
                }
            }
            (sc_dir / f'{self.interface_name}_backoff.yaml').write_text(
                yaml.dump(backoff_cfg))
        return impl_outpath

    def report(self) -> str:
        code_lines = len(self.generated_code.splitlines()) if self.generated_code else 0
        stats = self.train_stats or {}
        vstats = self.val_stats or {}
        return textwrap.dedent(f"""\
            train accuracy:          {self.train_accuracy:.2%}
            train correct/wrong/abstained: {stats.get('correct', 0)}/{stats.get('wrong', 0)}/{stats.get('abstained', 0)}
            val accuracy (holdout):  {self.val_accuracy:.2%}
            val correct/wrong/abstained:  {vstats.get('correct', 0)}/{vstats.get('wrong', 0)}/{vstats.get('abstained', 0)}
            best round:              {self.best_round}/{self.max_rounds}
            total candidates:        {self.total_candidates}
            generated code:          {code_lines} lines""")

    def learn_from_dataset(self):
        """Top-level routine: fit and save."""
        print(f'loaded {len(self.dataset.cases)} examples from dataset')
        if self.trace_dirs:
            print(f'  trace_dirs: {[str(d) for d in self.trace_dirs]}')
        if self.reference_workflow_files:
            print(f'  reference workflows: {[str(f) for f in self.reference_workflow_files]}')
        self.fit()
        output_file = self.save_implementation()
        print(self.report())
        print(f'saved output to {output_file}')
