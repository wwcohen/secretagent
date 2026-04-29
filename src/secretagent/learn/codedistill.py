"""Code distillation learner.

Generates Python implementations from recorded input/output examples
by prompting an LLM to write code, then iteratively refining based on
validation errors. Uses ensemble (multiple candidates per round) and
multi-round refinement for robustness.
"""

import json
import os
import re
import textwrap
from pathlib import Path
from typing import Any, Optional

import yaml

from secretagent import llm_util, savefile
from secretagent.dataset import Case, Dataset
from secretagent.learn.base import Learner


def _truncate_repr(obj, max_len: int = 2000) -> str:
    """repr(obj) truncated to max_len chars, with ellipsis marker."""
    s = repr(obj)
    if len(s) <= max_len:
        return s
    return s[:max_len] + f'...<truncated {len(s) - max_len} chars>'


def _format_cases(cases, max_cases: int = 20) -> str:
    """Format training cases as function call examples for the prompt.

    Shows examples as function calls with positional args to make the
    parameter structure clear to the LLM. Long values are truncated to
    keep prompts under control on benchmarks with large outputs.
    """
    lines = []
    parts = cases[0].name.rsplit('_', 1) if cases else ['func']
    func_name = parts[0] if len(parts) > 1 else parts[0]

    for case in cases[:max_cases]:
        args = case.input_args or []
        kw = case.input_kw or {}
        args_str = ", ".join(_truncate_repr(a, 500) for a in args)
        if kw:
            kw_str = ", ".join(f"{k}={_truncate_repr(v, 500)}" for k, v in kw.items())
            args_str = f"{args_str}, {kw_str}" if args_str else kw_str
        output_repr = _truncate_repr(case.expected_output, 2000)
        lines.append(f"  {func_name}({args_str}) -> {output_repr}")
    if len(cases) > max_cases:
        lines.append(f"  ... ({len(cases) - max_cases} more examples omitted)")
    return "\n".join(lines)


def _format_traces(cases, max_traces: int = 3) -> str:
    """Extract workflow trace context from Case.metadata.

    Shows how this interface is called within the broader workflow,
    AND the top-level task input/expected output, so the LLM understands
    the global problem this ptool serves (not just its local i/o).
    """
    traces = []
    seen = set()
    for case in cases:
        meta = case.metadata or {}
        prior_steps = meta.get('prior_steps') or []
        # Deduplicate by step sequence signature
        sig = tuple(s.get('func', '') for s in prior_steps)
        if sig in seen and prior_steps:
            continue
        seen.add(sig)

        # Top-level task header
        top_func = meta.get('top_level_func')
        top_args = meta.get('top_level_args') or []
        top_expected = meta.get('top_level_expected')
        header_lines = []
        if top_func is not None:
            top_args_str = ", ".join(_truncate_repr(a, 200) for a in top_args)
            header_lines.append(
                f"Top-level task: {top_func}({top_args_str})"
            )
            if top_expected is not None:
                header_lines.append(
                    f"  expected final output: {_truncate_repr(top_expected, 500)}"
                )

        trace_lines = []
        for step in prior_steps:
            func = step.get('func', '?')
            args = step.get('args', [])
            output = step.get('output')
            args_str = ", ".join(_truncate_repr(a, 200) for a in (args or []))
            output_str = _truncate_repr(output, 500)
            trace_lines.append(f"  {func}({args_str}) -> {output_str}")
        # Add current step
        cur_args_str = ", ".join(_truncate_repr(a, 200) for a in (case.input_args or []))
        cur_output_str = _truncate_repr(case.expected_output, 500)
        trace_lines.append(
            f"  {case.name.split('_')[0]}({cur_args_str}) -> {cur_output_str}  # <-- this function"
        )

        correct = meta.get('rollout_correct')
        status = "CORRECT" if correct else "INCORRECT" if correct is not None else "UNKNOWN"
        block = ""
        if header_lines:
            block += "\n".join(header_lines) + "\n"
        block += f"Trace ({status}):\n" + "\n".join(trace_lines)
        traces.append(block)

        if len(traces) >= max_traces:
            break

    if not traces:
        return ""
    return ("Workflow context (the global problem this function serves, "
            "and how it is called):\n\n" + "\n\n".join(traces))


def _format_errors(errors: list[dict]) -> str:
    """Format error cases as feedback for the next refinement round."""
    if not errors:
        return ""
    lines = ["The following cases were wrong. Please fix the code:\n"]
    for err in errors[:20]:
        lines.append(f"  Input: {repr(err['input_args'])}")
        lines.append(f"  Expected: {repr(err['expected'])}")
        lines.append(f"  Got: {repr(err['got'])}")
        lines.append("")
    if len(errors) > 20:
        lines.append(f"  ... ({len(errors) - 20} more errors omitted)")
    return "\n".join(lines)


def _extract_code(llm_output: str) -> Optional[str]:
    """Extract Python code from LLM output.

    Looks for ```python ... ``` blocks first, then falls back to
    the entire output if no code block is found.
    """
    match = re.search(r'```python\n(.*?)```', llm_output, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r'```\n(.*?)```', llm_output, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _compile_function(code: str, func_name: str):
    """Compile code string and extract the named function.

    Returns the function object, or None if compilation/extraction fails.
    Inference-time sandboxing is handled separately by
    secretagent.implement.learnedcode._load_learned_sandboxed; fit-time
    evaluation runs unsandboxed (we are evaluating our own LLM-generated
    research code, on our own machine).
    """
    try:
        namespace = {}
        exec(code, namespace)
        fn = namespace.get(func_name)
        return fn
    except Exception:
        return None


def _evaluate_on_cases(fn, cases) -> tuple[float, list[dict], dict]:
    """Run a function on training cases, return (accuracy, error_list, stats).

    Each error is a dict with input_args, expected, and got.
    Stats includes counts for correct, wrong (returned incorrect value),
    and abstained (returned None or raised, would backoff to LLM).
    Both wrong and abstained are added to errors so the LLM sees feedback
    in subsequent rounds (otherwise an all-None first round produces no
    feedback and round 2 just re-emits the same buggy code).
    """
    if fn is None:
        return 0.0, [{'input_args': c.input_args, 'expected': c.expected_output,
                      'got': None, 'exception': 'fn=None'} for c in cases], \
               {'correct': 0, 'wrong': 0, 'abstained': len(cases)}
    correct = 0
    wrong = 0
    abstained = 0
    errors = []
    for case in cases:
        exc = None
        try:
            args = case.input_args or []
            kw = case.input_kw or {}
            result = fn(*args, **kw)
        except Exception as ex:
            result = None
            exc = f'{type(ex).__name__}: {ex}'[:300]
        if result == case.expected_output:
            correct += 1
        elif result is None:
            abstained += 1
            errors.append({
                'input_args': case.input_args,
                'expected': case.expected_output,
                'got': None,
                'exception': exc,  # may be None if code returned None deliberately
            })
        else:
            wrong += 1
            errors.append({
                'input_args': case.input_args,
                'expected': case.expected_output,
                'got': result,
            })
    accuracy = correct / len(cases) if cases else 0.0
    stats = {'correct': correct, 'wrong': wrong, 'abstained': abstained}
    return accuracy, errors, stats


class CodeDistillLearner(Learner):
    """Learn implementations by prompting an LLM to generate Python code.

    Uses multi-round refinement (generate -> validate -> feedback errors
    -> regenerate) and ensemble (multiple candidates per round, pick best).
    """

    tag = 'codedistill'

    def __init__(self, interface_name: str, train_dir: str,
                 model: str = 'claude-opus-4-6',
                 n_candidates: int = 3,
                 max_rounds: int = 3,
                 only_correct: bool = True):
        super().__init__(
            interface_name=interface_name,
            train_dir=train_dir,
            file_under=f'{interface_name}__{self.tag}',
            only_correct=only_correct)
        self.produce_files(['learned.py'])
        self.model = model
        self.n_candidates = n_candidates
        self.max_rounds = max_rounds
        self.generated_code: Optional[str] = None
        self.generated_fn = None
        self.train_accuracy: float = 0.0
        self.train_stats: dict = {}
        self.val_accuracy: float = 0.0
        self.val_stats: dict = {}
        self.best_round: int = 0
        self.total_candidates: int = 0

    def _build_prompt(self, examples_text: str, trace_text: str,
                      error_feedback: str) -> str:
        """Construct the prompt for code generation."""
        parts = [
            f"Write a Python function named `{self.interface_name}` "
            f"that implements the behavior shown in these examples.\n",
            "Examples:\n",
            examples_text,
        ]
        if trace_text:
            parts.append("\n" + trace_text + "\n")
        if error_feedback:
            parts.append("\n" + error_feedback + "\n")
        parts.append(textwrap.dedent(f"""\
            Requirements:
            - The function must be named `{self.interface_name}`
            - Return None if the input cannot be handled confidently
            - Use only standard library imports (re, json, datetime, math, etc.)
            - Do not use any external packages
            - Write clean, correct Python code

            Return your code in a ```python ... ``` block.
        """))
        return "\n".join(parts)

    def fit(self) -> "CodeDistillLearner":
        """Generate code via multi-round refinement with ensemble."""
        examples_text = _format_cases(self.dataset.cases)
        trace_text = _format_traces(self.dataset.cases)

        best_code, best_fn, best_accuracy = None, None, 0.0
        best_stats = {'correct': 0, 'wrong': 0, 'abstained': 0}
        error_feedback = ""

        for round_idx in range(self.max_rounds):
            # Ensemble: generate n_candidates versions per round
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
                fn = _compile_function(code, self.interface_name)
                accuracy, errors, stats = _evaluate_on_cases(fn, self.dataset.cases)
                candidates.append((code, fn, accuracy, errors, stats))
                self.total_candidates += 1

            # Pick best candidate this round. Track at >= so we always
            # capture some code even at 0% (so save_implementation has
            # something to write; the runtime backoff will handle it).
            round_best = max(candidates, key=lambda x: x[2])
            captured = round_best[2] > best_accuracy or (
                best_code is None and round_best[0] is not None
            )
            if captured:
                best_code, best_fn, best_accuracy = round_best[0], round_best[1], round_best[2]
                best_stats = round_best[4] if len(round_best) > 4 else {}
                self.best_round = round_idx + 1

            stats_str = round_best[4] if len(round_best) > 4 else {}
            print(f'  round {round_idx + 1}: best accuracy = {best_accuracy:.2%} '
                  f'(this round best = {round_best[2]:.2%}, '
                  f'wrong={stats_str.get("wrong", "?")}, '
                  f'abstained={stats_str.get("abstained", "?")})')

            # Early exit if accuracy is high enough
            if best_accuracy >= 0.95:
                break

            # Round 1 hopeless: don't burn rounds 2/3 on a clearly unlearnable ptool
            if round_idx == 0 and best_accuracy < 0.10:
                print(f'  giving up: round 1 best = {best_accuracy:.2%} (< 10%)')
                break

            # Feed error cases to next round
            if round_best[3]:
                error_feedback = _format_errors(round_best[3])

        self.generated_code = best_code
        self.generated_fn = best_fn
        self.train_accuracy = best_accuracy
        self.train_stats = best_stats
        return self

    def learn(self, dirs, latest=1, check=None, holdout_fraction: float = 0.2):
        """Single-fit 80/20 holdout: shuffle cases, fit on 80% train portion,
        evaluate the resulting fn on the 20% holdout. NO refit-on-all (that
        was the v1 source of triple-cost). The implementation saved is the
        train-portion fit. The val accuracy / val wrong_rate is what
        `distill_all` uses to decide whether to ENABLE the ptool — train
        numbers can mislead via memorisation.
        """
        import random
        self.collect_distillation_data(dirs, latest, check)
        all_cases = list(self.dataset.cases)
        rng = random.Random(42)
        rng.shuffle(all_cases)
        split = max(1, int(len(all_cases) * holdout_fraction))
        val_cases = all_cases[:split]
        train_cases = all_cases[split:]
        print(f'collected {len(all_cases)} examples '
              f'(train={len(train_cases)}, val={len(val_cases)}) in {self.out_dir}')

        # Fit on train portion only (single fit, no refit)
        original = self.dataset.cases
        self.dataset.cases = train_cases
        try:
            self.fit()
        finally:
            self.dataset.cases = original

        # Evaluate fit on val portion (no LLM call — just runs generated_fn)
        if self.generated_fn is not None and val_cases:
            val_acc, _, val_stats = _evaluate_on_cases(self.generated_fn, val_cases)
        else:
            val_acc, val_stats = 0.0, {'correct': 0, 'wrong': 0, 'abstained': len(val_cases)}
        self.val_accuracy = val_acc
        self.val_stats = val_stats

        output_file = self.save_implementation()
        print(self.report())
        print(f'saved output to {output_file}')

    def val_wrong_rate(self) -> float:
        """Wrong rate on the val holdout — the metric distill_all uses."""
        stats = getattr(self, 'val_stats', None)
        if not stats:
            return 1.0
        total = sum(stats.values())
        if total == 0:
            return 1.0
        return stats.get('wrong', 0) / total

    def predict(self, input_args, input_kw=None) -> Any:
        """Predict using the generated function."""
        if self.generated_fn is None:
            return None
        try:
            args = input_args or []
            kw = input_kw or {}
            return self.generated_fn(*args, **kw)
        except Exception:
            return None

    def save_implementation(self) -> Path:
        """Write generated code to learned.py and config to implementation.yaml."""
        if self.generated_code is None:
            raise ValueError("No code was generated. Did fit() succeed?")

        learned_outpath = Path(self.created_files['learned.py'])
        learned_outpath.write_text(
            f'"""Auto-generated code-distilled implementation for '
            f'{self.interface_name}."""\n\n'
            f'{self.generated_code}\n',
            encoding='utf-8',
        )

        impl_outpath = Path(self.created_files['implementation.yaml'])
        impl = {self.interface_name: {
            'method': 'learned_code',
            'learner': self.tag,
            'backoff': True}}
        impl_outpath.write_text(yaml.dump(impl))
        return impl_outpath

    def wrong_rate(self) -> float:
        """Fraction of cases where the code returned a wrong value (not None).

        This is the key metric for deciding whether to enable codedistill:
        wrong answers hurt accuracy, while abstentions (None) safely backoff
        to the LLM.
        """
        total = sum(self.train_stats.values()) if self.train_stats else 0
        if total == 0:
            return 1.0
        return self.train_stats.get('wrong', 0) / total

    def report(self) -> str:
        """Brief report on code distillation results."""
        code_lines = len(self.generated_code.splitlines()) if self.generated_code else 0
        stats = self.train_stats or {}
        vstats = self.val_stats or {}
        return textwrap.dedent(f"""\
            train accuracy:     {self.train_accuracy:.2%}
            train correct/wrong/abstained: {stats.get('correct', 0)}/{stats.get('wrong', 0)}/{stats.get('abstained', 0)}
            train wrong rate:   {self.wrong_rate():.2%}
            val accuracy:       {self.val_accuracy:.2%}
            val correct/wrong/abstained:   {vstats.get('correct', 0)}/{vstats.get('wrong', 0)}/{vstats.get('abstained', 0)}
            val wrong rate:     {self.val_wrong_rate():.2%}
            best round:         {self.best_round}/{self.max_rounds}
            total candidates:   {self.total_candidates}
            generated code:     {code_lines} lines""")


class EndToEndDistillLearner(CodeDistillLearner):
    """Learn an end-to-end implementation directly from a dataset file.

    Instead of learning a single intermediate interface from rollout data,
    this learns a complete solution function from (input, expected_output)
    pairs in a dataset JSON file. The prompt instructs the LLM to generate
    code with a parse->solve->format structure.
    """

    tag = 'e2e_codedistill'

    def __init__(self, interface_name: str, train_dir: str,
                 dataset_file: str,
                 output_field: Optional[str] = None,
                 model: str = 'claude-opus-4-6',
                 n_candidates: int = 3,
                 max_rounds: int = 3):
        # Skip Learner.__init__ since we load data differently
        self.interface_name = interface_name
        self.train_dir = train_dir
        self.model = model
        self.n_candidates = n_candidates
        self.max_rounds = max_rounds
        self.output_field = output_field
        self.generated_code: Optional[str] = None
        self.generated_fn = None
        self.train_accuracy: float = 0.0
        self.train_stats: dict = {}
        self.best_round: int = 0
        self.total_candidates: int = 0

        # Set up output directory
        file_under = f'{interface_name}__{self.tag}'
        to_produce = ['data.json', 'learned.py', 'implementation.yaml']
        filenames = savefile.filename_list(train_dir, to_produce, file_under)
        self.out_dir = Path(filenames[0]).parent
        self.created_files = {short: full for short, full in zip(to_produce, filenames)}

        # Load dataset
        ds = Dataset.model_validate_json(Path(dataset_file).read_text())
        # Extract the target output field if needed (e.g. golden_plan from natplan)
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

        # Save dataset copy
        os.makedirs(self.out_dir, exist_ok=True)
        with open(self.created_files['data.json'], 'w') as f:
            f.write(self.dataset.model_dump_json(indent=2))

    def _build_prompt(self, examples_text: str, trace_text: str,
                      error_feedback: str) -> str:
        """Build prompt that instructs LLM to generate structured code."""
        parts = [
            f"Write a Python function named `{self.interface_name}` "
            f"that solves the task shown in these examples.\n",
            "Examples:\n",
            examples_text,
        ]
        if error_feedback:
            parts.append("\n" + error_feedback + "\n")
        parts.append(textwrap.dedent(f"""\
            Requirements:
            - The function must be named `{self.interface_name}`
            - Structure the code as: parse input -> solve/compute -> format output
            - Define helper functions for each step (e.g. parse_input, solve, format_output)
            - Return None if the input cannot be handled confidently
            - Use only standard library imports (re, json, datetime, math, itertools, etc.)
            - Do not use any external packages
            - Write clean, correct Python code
            - The output must exactly match the expected format shown in examples

            Return your code in a ```python ... ``` block.
        """))
        return "\n".join(parts)

    def learn_from_dataset(self):
        """Top-level routine: fit and save.

        Skips validate() because it would re-call fit() (expensive LLM call)
        and the regenerated code may differ. Train accuracy from fit() is
        sufficient for e2e distillation.
        """
        print(f'loaded {len(self.dataset.cases)} examples from dataset')
        self.fit()
        output_file = self.save_implementation()
        print(self.report())
        print(f'saved output to {output_file}')

    def save_implementation(self) -> Path:
        """Write generated code and config."""
        if self.generated_code is None:
            raise ValueError("No code was generated. Did fit() succeed?")

        learned_outpath = Path(self.created_files['learned.py'])
        learned_outpath.write_text(
            f'"""Auto-generated end-to-end implementation for '
            f'{self.interface_name}."""\n\n'
            f'{self.generated_code}\n',
            encoding='utf-8',
        )

        impl_outpath = Path(self.created_files['implementation.yaml'])
        impl = {self.interface_name: {
            'method': 'learned_code',
            'learner': self.tag,
            'backoff': True}}
        impl_outpath.write_text(yaml.dump(impl))
        return impl_outpath


def _discover_interfaces(dirs: list[Path], latest: int = 1,
                         check: Optional[list[str]] = None) -> list[str]:
    """Find all interface names called in recorded rollouts."""
    filtered_dirs = savefile.filter_paths(dirs, latest=latest, dotlist=check or [])
    interface_names = set()
    for d in filtered_dirs:
        jsonl_path = Path(d) / 'results.jsonl'
        if not jsonl_path.exists():
            continue
        with open(jsonl_path) as f:
            for line in f:
                record = json.loads(line)
                for step in record.get('rollout', []):
                    interface_names.add(step['func'])
    return sorted(interface_names)


def distill_all(
    dirs: list[Path],
    train_dir: str,
    max_wrong_rate: float = 0.05,
    model: str = 'claude-opus-4-6',
    n_candidates: int = 3,
    max_rounds: int = 3,
    latest: int = 1,
    check: Optional[list[str]] = None,
) -> dict:
    """Auto-distill all interfaces found in recordings.

    For each interface:
    1. Run CodeDistillLearner
    2. Check wrong_rate (fraction of cases where code returned an incorrect
       value instead of None). Abstentions (None) are safe because they
       backoff to the LLM.
    3. If wrong_rate <= max_wrong_rate, enable the interface
    4. Otherwise skip it (too risky, would hurt accuracy)

    Returns a dict mapping interface_name -> {accuracy, wrong_rate, enabled, path}.
    Also writes a combined config yaml for enabled interfaces.
    """
    interfaces = _discover_interfaces(dirs, latest=latest, check=check)
    print(f'found {len(interfaces)} interfaces: {interfaces}')

    results = {}
    enabled_configs = {}

    for iface in interfaces:
        print(f'\n{"="*60}')
        print(f'distilling: {iface}')
        print(f'{"="*60}')

        try:
            learner = CodeDistillLearner(
                interface_name=iface,
                train_dir=train_dir,
                model=model,
                n_candidates=n_candidates,
                max_rounds=max_rounds,
            )
            learner.learn(dirs, latest=latest, check=check)

            train_acc = learner.train_accuracy
            train_wr = learner.wrong_rate()
            val_acc = learner.val_accuracy
            val_wr = learner.val_wrong_rate()
            # ENABLE decision uses VAL wrong_rate (honest generalisation),
            # not train (which can be memorised). Val acc must also be > 0.
            enabled = val_wr <= max_wrong_rate and val_acc > 0

            results[iface] = {
                'train_accuracy': train_acc,
                'train_wrong_rate': train_wr,
                'val_accuracy': val_acc,
                'val_wrong_rate': val_wr,
                'train_stats': learner.train_stats,
                'val_stats': learner.val_stats,
                'enabled': enabled,
                'path': str(learner.out_dir),
            }

            if enabled:
                enabled_configs[iface] = {
                    'method': 'learned_code',
                    'learner': 'codedistill',
                    'backoff': True,
                }
                print(f'  -> ENABLED (val_wrong_rate {val_wr:.0%} <= {max_wrong_rate:.0%}, '
                      f'val_acc {val_acc:.0%}, train_acc {train_acc:.0%})')
            else:
                print(f'  -> SKIPPED (val_wrong_rate {val_wr:.0%} > {max_wrong_rate:.0%} '
                      f'or val_acc {val_acc:.0%}, train_acc {train_acc:.0%})')

        except Exception as ex:
            print(f'  -> FAILED: {ex}')
            results[iface] = {
                'train_accuracy': 0.0,
                'wrong_rate': 1.0,
                'enabled': False,
                'error': str(ex),
            }

    # Write summary
    print(f'\n{"="*60}')
    print(f'SUMMARY (max_wrong_rate={max_wrong_rate:.0%})')
    print(f'{"="*60}')
    print(f'  {"interface":40s} {"train":>6s} {"val":>5s} {"v_wrong":>7s} {"v_abst":>6s} {"status"}')
    for iface, info in sorted(results.items()):
        status = 'ENABLED' if info['enabled'] else 'skipped'
        vstats = info.get('val_stats', {})
        print(f'  {iface:40s} {info["train_accuracy"]:5.0%} '
              f'{info.get("val_accuracy", 0):4.0%} '
              f'{vstats.get("wrong", "?"):>7} '
              f'{vstats.get("abstained", "?"):>6}  {status}')

    # Write combined config for enabled interfaces
    if enabled_configs:
        config_path = Path(train_dir) / 'codedistill_config.yaml'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.dump({'ptools': enabled_configs}))
        print(f'\nconfig written to {config_path}')
        print(f'use with: --config-file {config_path}')

    return results
