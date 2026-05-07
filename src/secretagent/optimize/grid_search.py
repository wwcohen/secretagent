"""Grid search optimizer for secretagent configurations.

Searches over a discrete space of config overrides, running each
configuration as a subprocess to ensure clean state, then collects
and ranks results.

Usage:

    from secretagent.optimize import ConfigSpace, GridSearchRunner

    space = ConfigSpace(variants={
        'llm.thinking': [True, False],
        'ptools.answer_question.method': ['simulate', 'direct'],
    })

    runner = GridSearchRunner(
        command=['uv', 'run', 'python', 'expt.py', 'run',
                 '--config-file', 'conf/murder.yaml'],
        space=space,
        base_dotlist=['dataset.n=10', 'cachier.enable_caching=false'],
    )

    summary = runner.run_all()
    print(summary.sort_values('accuracy', ascending=False))
"""

import os
import shlex
import subprocess
import time
from pathlib import Path

import pandas as pd

from secretagent.optimize.config_space import ConfigSpace


def _flatten_dict(d: dict, prefix: str = '') -> list[str]:
    """Flatten a nested dict into dotlist strings like 'a.b=value'."""
    items = []
    for k, v in d.items():
        key = f'{prefix}{k}' if not prefix else f'{prefix}.{k}'
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, key))
        else:
            items.append(f'{key}={v}')
    return items


class GridSearchRunner:
    """Run a grid search over a config space via subprocesses."""

    def __init__(
        self,
        command: list[str] | str,
        space: ConfigSpace,
        base_dotlist: list[str] | None = None,
        expt_prefix: str = 'sweep',
        cwd: str | Path | None = None,
        timeout: int = 1800,
        metric: str = 'correct',
    ):
        if isinstance(command, str):
            command = shlex.split(command)
        self.command = command
        self.space = space
        self.base_dotlist = base_dotlist or []
        self.expt_prefix = expt_prefix
        self.cwd = str(cwd) if cwd else None
        self.timeout = timeout
        self.metric = metric
        self.results: list[dict] = []

    def _space_size(self) -> int:
        return len(list(self.space))

    def run_single(self, config_idx: int, config_delta: dict) -> dict:
        """Run one config point via subprocess. Returns metrics dict."""
        expt_name = f'{self.expt_prefix}_{config_idx:03d}'
        dotlist = _flatten_dict(config_delta)
        cmd = (
            self.command
            + self.base_dotlist
            + dotlist
            + [f'evaluate.expt_name={expt_name}']
        )

        # Parse config dimensions from dotlist for reporting
        config_dims = {}
        for item in dotlist:
            k, v = item.split('=', 1)
            config_dims[k] = v

        space_size = self._space_size()
        print(f'[{config_idx}/{space_size}] {expt_name}: {config_dims}')

        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.cwd,
                timeout=self.timeout,
                env=os.environ.copy(),
            )
            elapsed = time.time() - start

            # Parse accuracy from stdout
            accuracy = None
            for line in result.stdout.split('\n'):
                if 'Accuracy:' in line:
                    try:
                        pct = line.split('Accuracy: ')[1].split('%')[0]
                        accuracy = float(pct) / 100
                    except (IndexError, ValueError):
                        pass

            # Try to find and load the results CSV
            csv_path = None
            for line in result.stdout.split('\n'):
                if 'saved in' in line and '.csv' in line:
                    csv_path = line.split('saved in ')[-1].strip()

            row = {
                'config_idx': config_idx,
                'expt_name': expt_name,
                **config_dims,
                'accuracy': accuracy,
                'elapsed': elapsed,
                'csv_path': csv_path,
                'status': 'ok' if result.returncode == 0 else 'failed',
            }

            # Load detailed stats from CSV if available
            if csv_path and Path(csv_path).exists():
                try:
                    df = pd.read_csv(csv_path)
                    row['accuracy'] = df[self.metric].mean()
                    if 'cost' in df.columns:
                        row['total_cost'] = df['cost'].sum()
                        row['cost_per_q'] = df['cost'].mean()
                    if 'latency' in df.columns:
                        row['total_latency'] = df['latency'].sum()
                        row['latency_per_q'] = df['latency'].mean()
                    if 'input_tokens' in df.columns:
                        row['input_tokens_per_q'] = df['input_tokens'].mean()
                    if 'output_tokens' in df.columns:
                        row['output_tokens_per_q'] = df['output_tokens'].mean()
                except Exception:
                    pass

            if result.returncode != 0:
                # Show last few lines of stderr
                stderr_tail = '\n'.join(result.stderr.strip().split('\n')[-3:])
                print(f'  FAILED (exit {result.returncode}): {stderr_tail[:200]}')
            else:
                acc_str = f'{accuracy:.1%}' if accuracy is not None else '?'
                print(f'  {acc_str} ({elapsed:.0f}s)')

        except subprocess.TimeoutExpired:
            elapsed = time.time() - start
            row = {
                'config_idx': config_idx,
                'expt_name': expt_name,
                **config_dims,
                'accuracy': None,
                'elapsed': elapsed,
                'status': 'timeout',
            }
            print(f'  TIMEOUT after {self.timeout}s')

        except Exception as e:
            row = {
                'config_idx': config_idx,
                'expt_name': expt_name,
                **config_dims,
                'accuracy': None,
                'elapsed': 0,
                'status': f'error: {e}',
            }
            print(f'  ERROR: {e}')

        self.results.append(row)
        return row

    def run_all(self) -> pd.DataFrame:
        """Run all configs and return summary DataFrame."""
        print(f'Grid search: {self.space}')
        print(f'Command: {" ".join(self.command)}')
        print(f'Base overrides: {self.base_dotlist}')
        print()

        for idx, config_delta in enumerate(self.space):
            self.run_single(idx, config_delta)

        return self.summary()

    def summary(self) -> pd.DataFrame:
        """Return summary DataFrame sorted by accuracy."""
        df = pd.DataFrame(self.results)
        if 'accuracy' in df.columns:
            df = df.sort_values('accuracy', ascending=False)
        return df

    def save_summary(self, path: str | Path) -> None:
        """Save summary to CSV."""
        df = self.summary()
        df.to_csv(path, index=False)
        print(f'Sweep summary saved to {path}')
