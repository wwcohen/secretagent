"""Run the induction matrix and held-out evaluation matrix.

Step 4: induce-matrix — sweep induction over
  state {stateless, state-aware} x only-correct {0, 1} x max-ptools {3, 5, 8}
  = 12 variants.

Step 5: eval-matrix — evaluate each induced variant on the held-out set.

Each variant writes its learned ptools to learned/<tag>/ and its eval
results to results/<TS>.induced_<tag>_eval/.
"""

import shlex
import subprocess
from pathlib import Path

import typer

app = typer.Typer(no_args_is_help=True)

TASK_DESC = (
    "Solve a medical-calculator question by extracting clinical values "
    "from a patient note and applying the right formula or score."
)
INDUCER_MODEL = 'gemini/gemini-3.1-flash-lite-preview'
EVAL_MODEL = 'gemini/gemini-3.1-flash-lite-preview'


def _variants():
    """Yield (tag, state_aware, only_correct, max_ptools) for the 12-variant matrix."""
    for state_aware in (False, True):
        prefix = 'state' if state_aware else 'stateless'
        for only_correct in (False, True):
            oc_tag = '1' if only_correct else '0'
            for max_ptools in (3, 5, 8):
                tag = f'{prefix}-oc{oc_tag}-mp{max_ptools}'
                yield tag, state_aware, only_correct, max_ptools


def _run(cmd: list[str], dry_run: bool = False) -> int:
    print('+', shlex.join(cmd), flush=True)
    if dry_run:
        return 0
    return subprocess.call(cmd)


@app.command()
def induce(dry_run: bool = typer.Option(False, '--dry-run')):
    """Step 4: run the 12-variant induction matrix."""
    failed = []
    for tag, state_aware, only_correct, max_ptools in _variants():
        src = 'results/*.react_state_train' if state_aware else 'results/*.react_train'
        cmd = [
            'uv', 'run', 'python', 'run_inducer.py',
            '--interface', 'calculate_medical_value',
            '--task-desc', TASK_DESC,
            '--trace-mode', 'react',
            '--max-ptools', str(max_ptools),
            '--min-count', '3',
            '--model', INDUCER_MODEL,
            '--learned-dir', f'learned/{tag}',
        ]
        if state_aware:
            cmd += ['--state-module', 'ptools',
                    '--state-expr', '_REACT_STATE["patient_note"]']
        if only_correct:
            cmd.append('--only-correct')
        # glob expansion via shell:
        full = shlex.join(cmd) + ' ' + src
        print(f'\n===== INDUCE {tag} =====', flush=True)
        if dry_run:
            print('+', full)
            continue
        rc = subprocess.call(full, shell=True)
        if rc != 0:
            failed.append(tag)
            print(f'!! {tag} failed (rc={rc})')
    if failed:
        print(f'\n{len(failed)} variants failed: {failed}')
        raise typer.Exit(1)


@app.command()
def evaluate_matrix(dry_run: bool = typer.Option(False, '--dry-run')):
    """Step 5: evaluate each induced variant on the held-out set."""
    failed = []
    for tag, state_aware, _oc, _mp in _variants():
        learned_dir = Path(f'learned/{tag}')
        if not list(learned_dir.glob('*calculate_medical_value__ptool_inducer')):
            print(f'!! {tag}: no learned dir, skipping')
            continue
        if state_aware:
            cfg = 'conf/react_state_eval.yaml'
            agent_iface = 'react_calculate'
        else:
            cfg = 'conf/react_eval.yaml'
            agent_iface = 'calculate_medical_value'
        cmd = [
            'uv', 'run', 'python', 'expt.py', 'run',
            '--config-file', cfg,
            f'llm.model={EVAL_MODEL}',
            f'learn.train_dir=learned/{tag}',
            f'ptools.{agent_iface}.method=simulate_pydantic',
            f'ptools.{agent_iface}.tool_module=__learned__',
            f'ptools.{agent_iface}.learner=ptool_inducer',
            f'ptools.{agent_iface}.tools=__all__',
            f'evaluate.expt_name=induced_{tag}_eval',
        ]
        print(f'\n===== EVAL {tag} =====', flush=True)
        rc = _run(cmd, dry_run=dry_run)
        if rc != 0:
            failed.append(tag)
            print(f'!! {tag} eval failed (rc={rc})')
    if failed:
        print(f'\n{len(failed)} variants failed: {failed}')
        raise typer.Exit(1)


if __name__ == '__main__':
    app()
