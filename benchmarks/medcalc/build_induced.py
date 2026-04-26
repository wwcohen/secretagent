"""Step 6: build a self-contained ptools_induced.py from a winning variant.

OrchestrationLearner reads its base ptools module via inspect.getsource,
so the file must be self-contained (no `from learned_ptools import *`,
no indirection). This script takes:

  - --learned-dir: path like learned/state-oc1-mp5 (the variant root)
  - --state-aware/--no-state-aware: whether the variant uses _REACT_STATE
  - --out: output file (default benchmarks/medcalc/ptools_induced.py)

It inlines:
  - The induced @implement_via('simulate') stubs and their public wrappers
    (copied from learned_ptools.py, but with `from ptools import _REACT_STATE`
    rewritten to inline _REACT_STATE since this file is now self-contained)
  - calculate_medical_value (the public entry @interface)
  - react_calculate (state-aware variants only)
  - react_calculate_impl (the direct wrapper that resets state and calls
    react_calculate)
"""

from pathlib import Path

import typer

app = typer.Typer(no_args_is_help=True)


def _read_induced_body(learned_dir: Path) -> str:
    """Find the most recent learned_ptools.py under learned_dir and return its body
    minus the imports (we replace those with our own inlined header)."""
    candidates = sorted(
        learned_dir.glob('*calculate_medical_value__ptool_inducer/learned_ptools.py'))
    if not candidates:
        raise FileNotFoundError(
            f'no learned_ptools.py under {learned_dir}/*calculate_medical_value__ptool_inducer/')
    src = candidates[-1].read_text()
    out_lines = []
    for line in src.splitlines():
        # Drop the inducer's imports and module docstring; we provide our own
        if line.startswith('"""Induced ptools'):
            continue
        if line.startswith('from secretagent.core import implement_via'):
            continue
        if line.startswith('from ptools import'):
            continue
        out_lines.append(line)
    return '\n'.join(out_lines).strip() + '\n'


HEADER = '''"""Self-contained ptools module wrapping induced helpers.

Hand-derived from the winning induction variant in {learned_dir}.
Designed to be ingested by OrchestrationLearner via inspect.getsource:
the file MUST have no indirection — every symbol the supervisor sees
lives here.
"""

import re
from typing import Optional

from secretagent.core import interface, implement_via

# Reuse the existing medcalc machinery (formulas + calculator engine).
# Only computational helpers are imported; nothing that wires interfaces.
import calculator_simple
import calculators

'''

REACT_STATE = '''
# State plumbing for state-aware induced ptools (mirrors MUSR's pattern).
_REACT_STATE: dict = {{'patient_note': '', 'question': ''}}


def _reset_react_state(patient_note: str, question: str) -> None:
    _REACT_STATE['patient_note'] = patient_note
    _REACT_STATE['question'] = question
'''


ENTRY_DOCSTRING_LINE = (
    '"""Calculate a medical value from a patient note and question.\\n\\n'
    'Reason step by step using the induced helpers, then return the '
    'final numeric answer.\\n"""'
)


ENTRY_TEMPLATE = '''
# =============================================================================
# Public entry point — calculate_medical_value
# =============================================================================

@interface
def calculate_medical_value(patient_note: str, question: str) -> float:
    """Calculate a medical value from a patient note and question."""


{state_aware_block}

def _extract_number(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value)
    if s.startswith('**exception'):
        return None
    try:
        return float(s)
    except ValueError:
        pass
    for pat in (r'<answer>\\s*([\\d.eE+-]+)\\s*</answer>', r'ANSWER:\\s*([\\d.eE+-]+)'):
        m = re.search(pat, s)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    nums = re.findall(r'-?\\d+\\.?\\d*', s)
    if nums:
        try:
            return float(nums[-1])
        except ValueError:
            pass
    return None
'''


STATE_AWARE_BLOCK = '''
@interface
def react_calculate(patient_note: str, question: str) -> float:
    """Calculate a medical value via ReAct over the induced helpers."""


def react_calculate_impl(patient_note: str, question: str) -> float:
    """Direct entry: resets _REACT_STATE then runs the bound react_calculate."""
    _reset_react_state(patient_note, question)
    try:
        raw = react_calculate(patient_note, question)
    except Exception:
        return float('nan')
    n = _extract_number(raw)
    return float('nan') if n is None else n
'''

STATELESS_BLOCK = ''


@app.command()
def main(
    learned_dir: Path = typer.Option(..., help='Variant root, e.g. learned/state-oc1-mp5'),
    state_aware: bool = typer.Option(True, '--state-aware/--no-state-aware'),
    out: Path = typer.Option(Path('ptools_induced.py'), help='Output path'),
):
    body = _read_induced_body(learned_dir)
    state_block = STATE_AWARE_BLOCK if state_aware else STATELESS_BLOCK
    text = HEADER.format(learned_dir=str(learned_dir))
    if state_aware:
        text += REACT_STATE
    text += '\n# =============================================================================\n'
    text += '# Induced ptools (inlined from {})\n'.format(learned_dir)
    text += '# =============================================================================\n\n'
    text += body
    text += ENTRY_TEMPLATE.format(state_aware_block=state_block)
    out.write_text(text)
    print(f'wrote {out} ({len(text)} bytes)')


if __name__ == '__main__':
    app()
