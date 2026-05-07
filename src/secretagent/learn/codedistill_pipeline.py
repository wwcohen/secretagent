"""End-to-end pipeline: induce ptools from ReAct traces, then codedistill each.

Stage A: PtoolInducer on ReAct/CoT rollouts -> learned_ptools.py + impl.yaml
Stage B: Subprocess re-run of benchmark with induced ptools + record_details
Stage B.5: Rewrite recording so individual tool calls appear as top-level
           rollout entries (simulate_pydantic puts them in step_info)
Stage C: distill_all on the new recording -> codedistill_config.yaml
Stage D: Merge Stage A's top-level binding with Stage C's per-ptool overrides
         into induced_codedistill_config.yaml
"""

import collections
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import yaml

from secretagent.learn.codedistill import distill_all
from secretagent.learn.ptool_inducer import PtoolInducer


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def _run_stage_a(
    dirs: list[Path],
    interface_name: str,
    train_dir: str,
    task_desc: str,
    trace_mode: str,
    state_module: Optional[str],
    state_expr: Optional[str],
    only_correct: bool,
    max_ptools: int,
    min_count: int,
    model: Optional[str],
    latest: int,
    check: Optional[list[str]],
) -> tuple[Path, dict]:
    """Run PtoolInducer; return (implementation.yaml path, parsed impl dict)."""
    print(f'\n{"#"*60}\n# Stage A: PtoolInducer ({interface_name})\n{"#"*60}')
    learner = PtoolInducer(
        interface_name=interface_name,
        train_dir=train_dir,
        task_desc=task_desc,
        trace_mode=trace_mode,
        state_module=state_module,
        state_expr=state_expr,
        only_correct=only_correct,
        max_ptools=max_ptools,
        min_count=min_count,
        model=model,
    )
    # PtoolInducer does not populate self.dataset, so we invoke its pipeline
    # stages directly instead of calling the base class learn() method.
    learner.collect_distillation_data(dirs, latest=latest, check=check)
    learner.fit()
    learner.save_implementation()
    print(learner.report())
    impl_path = Path(learner.created_files['implementation.yaml'])
    impl = _read_yaml(impl_path)
    print(f'Stage A impl: {impl_path}')
    return impl_path, impl


def _build_overrides_for_stage_b(
    interface_name: str,
    impl: dict,
    train_dir: str,
    record_dir: Path,
    record_expt_name: str,
) -> list[str]:
    """Build dotlist overrides to tell the benchmark to use induced ptools."""
    iface_cfg = impl.get(interface_name, {})
    tools = iface_cfg.get('tools') or []
    tools_str = '[' + ','.join(tools) + ']'
    return [
        f'learn.train_dir={train_dir}',
        f'ptools.{interface_name}.method={iface_cfg.get("method", "simulate_pydantic")}',
        f'ptools.{interface_name}.tools={tools_str}',
        f'ptools.{interface_name}.tool_module={iface_cfg.get("tool_module", "__learned__")}',
        f'ptools.{interface_name}.learner={iface_cfg.get("learner", "ptool_inducer")}',
        f'evaluate.record_details=true',
        f'evaluate.result_dir={record_dir}',
        f'evaluate.expt_name={record_expt_name}',
    ]


def _run_stage_b(
    expt_cmd: str,
    overrides: list[str],
    cwd: Optional[str],
) -> Path:
    """Invoke the benchmark's expt.py as a subprocess with induced ptools."""
    print(f'\n{"#"*60}\n# Stage B: re-record with induced ptools\n{"#"*60}')
    cmd = shlex.split(expt_cmd) + overrides
    print('command:')
    print('  ' + ' '.join(shlex.quote(c) for c in cmd))
    if cwd:
        print(f'  cwd={cwd}')
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(
            f'Stage B subprocess failed with exit code {result.returncode}')


def _rewrite_step_info_as_rollout(record_dir: Path, induced_tools: set[str]) -> None:
    """Rewrite each results.jsonl in record_dir so induced tool calls appear
    as top-level rollout entries. simulate_pydantic records tool calls inside
    step_info, but codedistill looks at rollout[].func/args/output. Keep only
    calls to induced tools so we don't pollute with final_result etc.

    Pairs tool_call entries with their matching tool_return entries by
    scanning in order and matching on name (multiple calls in flight are
    paired FIFO within the same tool name).
    """
    for d in record_dir.iterdir():
        jl = d / 'results.jsonl'
        if not jl.exists():
            continue
        new_lines = []
        for line in jl.open():
            row = json.loads(line)
            old_rollout = row.get('rollout') or []
            new_rollout = list(old_rollout)  # keep original entries
            for entry in old_rollout:
                step_info = entry.get('step_info') or []
                # Queue pending calls per tool, pair FIFO with returns
                pending = collections.defaultdict(list)
                for step in step_info:
                    if not isinstance(step, dict):
                        continue
                    tool_call = step.get('tool_call')
                    tool_return = step.get('tool_return')
                    if tool_call and tool_call in induced_tools:
                        args_str = step.get('args') or '{}'
                        try:
                            args_obj = json.loads(args_str) if isinstance(args_str, str) else args_str
                        except json.JSONDecodeError:
                            args_obj = {}
                        pending[tool_call].append(args_obj)
                    elif tool_return and tool_return in induced_tools:
                        if pending[tool_return]:
                            args_obj = pending[tool_return].pop(0)
                        else:
                            args_obj = {}
                        if isinstance(args_obj, dict):
                            positional = list(args_obj.values())
                            kw = {}
                        else:
                            positional = [args_obj]
                            kw = {}
                        new_rollout.append({
                            'func': tool_return,
                            'args': positional,
                            'kw': kw,
                            'output': step.get('output'),
                            'stats': {},
                        })
            row['rollout'] = new_rollout
            new_lines.append(json.dumps(row))
        jl.write_text('\n'.join(new_lines) + '\n')


def _run_stage_c(
    record_dir: Path,
    train_dir: str,
    max_wrong_rate: float,
    model: str,
    n_candidates: int,
    max_rounds: int,
    induced_tools: set[str],
) -> dict:
    """Run distill_all on the newly recorded induced rollouts."""
    print(f'\n{"#"*60}\n# Stage C: codedistill-all on induced ptools\n{"#"*60}')
    record_dirs = [d for d in record_dir.iterdir() if d.is_dir()]
    if not record_dirs:
        raise RuntimeError(
            f'no induced recordings found in {record_dir}; Stage B produced no output')
    _rewrite_step_info_as_rollout(record_dir, induced_tools)
    return distill_all(
        dirs=record_dirs,
        train_dir=train_dir,
        max_wrong_rate=max_wrong_rate,
        model=model,
        n_candidates=n_candidates,
        max_rounds=max_rounds,
        latest=0,  # keep all induced recordings
    )


def _run_stage_d(
    interface_name: str,
    stage_a_impl: dict,
    stage_c_results: dict,
    train_dir: str,
) -> Path:
    """Merge Stage A top-level binding + Stage C per-ptool overrides."""
    print(f'\n{"#"*60}\n# Stage D: merge configs\n{"#"*60}')
    merged: dict = {}

    # Top-level interface binding from Stage A
    if interface_name in stage_a_impl:
        merged[interface_name] = stage_a_impl[interface_name]

    # Enabled ptools from Stage C get the codedistill override. Skip the
    # top-level interface — it must stay simulate_pydantic (the ReAct
    # orchestrator); distilling it would break the tool-calling loop.
    for iface, info in stage_c_results.items():
        if iface == interface_name:
            continue
        if info.get('enabled'):
            merged[iface] = {
                'method': 'learned_code',
                'learner': 'codedistill',
                'backoff': True,
            }

    out_path = Path(train_dir) / 'induced_codedistill_config.yaml'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.dump({'ptools': merged}))
    print(f'merged config written to: {out_path}')
    print(f'use with: --config-file {out_path}')
    return out_path


def codedistill_induced_ptools(
    dirs: list[Path],
    interface_name: str,
    task_desc: str,
    expt_cmd: str,
    trace_mode: str = 'react',
    state_module: Optional[str] = None,
    state_expr: Optional[str] = None,
    only_correct: bool = False,
    max_ptools: int = 5,
    min_count: int = 3,
    induce_model: Optional[str] = None,
    learned_dir: str = 'learned',
    max_wrong_rate: float = 0.10,
    codedistill_model: str = 'claude-opus-4-6',
    n_candidates: int = 3,
    max_rounds: int = 3,
    latest: int = 1,
    check: Optional[list[str]] = None,
    cwd: Optional[str] = None,
    skip_stage_b: bool = False,
) -> Path:
    """Orchestrate the 4-stage pipeline. Returns path to merged config."""
    learned_dir_abs = str(Path(learned_dir).resolve())
    record_dir = Path(learned_dir_abs) / 'induced_recordings'
    record_expt_name = f'{interface_name}_induced_record'

    # Stage A
    _, stage_a_impl = _run_stage_a(
        dirs=dirs,
        interface_name=interface_name,
        train_dir=learned_dir_abs,
        task_desc=task_desc,
        trace_mode=trace_mode,
        state_module=state_module,
        state_expr=state_expr,
        only_correct=only_correct,
        max_ptools=max_ptools,
        min_count=min_count,
        model=induce_model,
        latest=latest,
        check=check,
    )

    # Stage B
    if not skip_stage_b:
        overrides = _build_overrides_for_stage_b(
            interface_name=interface_name,
            impl=stage_a_impl,
            train_dir=learned_dir_abs,
            record_dir=record_dir,
            record_expt_name=record_expt_name,
        )
        _run_stage_b(expt_cmd=expt_cmd, overrides=overrides, cwd=cwd)

    # Stage C (induced_tools set = tools from Stage A impl)
    induced_tools = set(stage_a_impl.get(interface_name, {}).get('tools') or [])
    stage_c_results = _run_stage_c(
        record_dir=record_dir,
        train_dir=learned_dir_abs,
        max_wrong_rate=max_wrong_rate,
        model=codedistill_model,
        n_candidates=n_candidates,
        max_rounds=max_rounds,
        induced_tools=induced_tools,
    )

    # Stage D
    return _run_stage_d(
        interface_name=interface_name,
        stage_a_impl=stage_a_impl,
        stage_c_results=stage_c_results,
        train_dir=learned_dir_abs,
    )
