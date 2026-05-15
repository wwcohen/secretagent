"""Orchestration Learner: supervisor-driven pipeline hill climbing as a Learner.

Wraps `improve_with_supervisor` in the standard `Learner` framework so its
outputs sit under a savefile-style training directory alongside rote,
codedistill, and ptool_inducer. Emits `implementation.yaml` referencing
`fn: __learned__.<entry_point>, learner: orch_learner` for eval-time binding.

The existing `secretagent.cli.orchestration_learner` is a thin wrapper around
this class.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import json
import os
import random
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from secretagent import config, savefile
from secretagent.learn.base import Learner


# ---------------------------------------------------------------------------
# HTML / plot helpers — moved from cli/orchestration_learner.py so the CLI and
# the `view` subcommand can import them here without circular dependencies.
# ---------------------------------------------------------------------------


def generate_html_report(report, output_dir: Path):
    """Generate a self-contained HTML report with full iteration visibility."""
    import html as html_mod

    iter_dir = output_dir / 'iterations'
    iterations_data = []

    for rec in report.iterations:
        iter_name = f'iter_{rec.iteration:03d}' if rec.iteration > 0 else 'iter_000_baseline'
        idir = iter_dir / iter_name
        entry = {
            'iteration': rec.iteration,
            'train_accuracy': rec.train_accuracy,
            'eval_accuracy': rec.eval_accuracy,
            'train_cost': rec.train_cost,
            'supervisor_cost': rec.supervisor_cost,
            'kept': rec.kept,
            'reasoning': rec.reasoning or '',
            'config_overrides': rec.config_overrides,
        }
        for fname in ('profiling_summary.txt', 'failure_traces.txt',
                      'supervisor_prompt.txt', 'supervisor_response.txt',
                      'outcome.txt', 'iteration_history.txt'):
            fpath = idir / fname
            if fpath.exists():
                entry[fname.replace('.txt', '')] = fpath.read_text()

        before = idir / 'ptools_before.py'
        after = idir / 'ptools_after.py'
        if before.exists() and after.exists():
            import difflib
            b_lines = before.read_text().splitlines(keepends=True)
            a_lines = after.read_text().splitlines(keepends=True)
            diff = list(difflib.unified_diff(b_lines, a_lines,
                                             fromfile='before', tofile='after',
                                             n=3))
            entry['diff'] = ''.join(diff) if diff else '(no changes)'
        iterations_data.append(entry)

    def esc(s):
        return html_mod.escape(str(s)) if s else ''

    iters_json = json.dumps(iterations_data, default=str)

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Orchestration Learner Report — {output_dir.name}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #0d1117; color: #c9d1d9; padding: 20px; line-height: 1.5; }}
  h1 {{ color: #58a6ff; margin-bottom: 8px; }}
  h2 {{ color: #58a6ff; margin: 24px 0 12px; font-size: 1.2em; }}
  .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
              gap: 12px; margin: 16px 0; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
           padding: 16px; text-align: center; }}
  .card .value {{ font-size: 2em; font-weight: bold; color: #58a6ff; }}
  .card .label {{ font-size: 0.85em; color: #8b949e; }}
  .chart-container {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
                      padding: 16px; margin: 16px 0; }}
  canvas {{ width: 100% !important; height: 300px !important; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
  th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #21262d; }}
  th {{ background: #161b22; color: #58a6ff; font-size: 0.85em; }}
  tr:hover {{ background: #161b22; }}
  .kept {{ color: #3fb950; font-weight: bold; }}
  .rollback {{ color: #f85149; }}
  .baseline {{ color: #8b949e; }}
  .iter-detail {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
                  margin: 12px 0; overflow: hidden; }}
  .iter-header {{ padding: 12px 16px; cursor: pointer; display: flex;
                  justify-content: space-between; align-items: center;
                  background: #161b22; border-bottom: 1px solid #21262d; }}
  .iter-header:hover {{ background: #1c2128; }}
  .iter-header .arrow {{ transition: transform 0.2s; color: #8b949e; }}
  .iter-header.open .arrow {{ transform: rotate(90deg); }}
  .iter-body {{ display: none; padding: 16px; }}
  .iter-body.open {{ display: block; }}
  .section {{ margin: 12px 0; }}
  .section-title {{ font-weight: bold; color: #58a6ff; margin-bottom: 4px;
                    cursor: pointer; user-select: none; }}
  .section-title:hover {{ text-decoration: underline; }}
  .section-content {{ display: none; background: #0d1117; border: 1px solid #21262d;
                      border-radius: 4px; padding: 12px; margin-top: 4px;
                      max-height: 600px; overflow: auto; }}
  .section-content.open {{ display: block; }}
  pre {{ white-space: pre-wrap; word-wrap: break-word; font-size: 0.85em;
         font-family: "Fira Code", "Cascadia Code", monospace; }}
  .diff-add {{ color: #3fb950; }}
  .diff-del {{ color: #f85149; }}
  .diff-hdr {{ color: #58a6ff; }}
  .tag {{ display: inline-block; padding: 2px 8px; border-radius: 12px;
          font-size: 0.75em; font-weight: bold; }}
  .tag-kept {{ background: #0f2d1a; color: #3fb950; border: 1px solid #238636; }}
  .tag-roll {{ background: #2d1117; color: #f85149; border: 1px solid #da3633; }}
  .tag-base {{ background: #1c1e23; color: #8b949e; border: 1px solid #30363d; }}
  .acc-bar {{ height: 6px; border-radius: 3px; margin-top: 4px; }}
</style>
</head>
<body>

<h1>🎛️ Orchestration Learner Report</h1>
<p style="color:#8b949e">{esc(output_dir.name)}</p>

<div class="summary">
  <div class="card">
    <div class="value">{report.best_train_accuracy:.1%}</div>
    <div class="label">Best Train Accuracy (iter {report.best_iteration})</div>
  </div>
  <div class="card">
    <div class="value">{f"{report.final_eval_accuracy:.1%}" if report.final_eval_accuracy is not None else "—"}</div>
    <div class="label">Final Eval Accuracy</div>
  </div>
  <div class="card">
    <div class="value">{len(report.iterations)}</div>
    <div class="label">Iterations</div>
  </div>
  <div class="card">
    <div class="value">${report.total_supervisor_cost:.2f}</div>
    <div class="label">Supervisor Cost</div>
  </div>
</div>

<h2>Accuracy Curve</h2>
<div class="chart-container">
  <canvas id="accChart"></canvas>
</div>

<h2>Iteration Log</h2>
<table>
  <thead>
    <tr><th>Iter</th><th>Train</th><th>Fail</th><th>TO</th><th>Eval</th><th>Cost/case</th><th>Sup $</th><th>Status</th></tr>
  </thead>
  <tbody id="iterTable"></tbody>
</table>

<h2>Iteration Details</h2>
<div id="iterDetails"></div>

<script>
const DATA = {iters_json};

// --- Populate table ---
const tbody = document.getElementById('iterTable');
DATA.forEach(d => {{
  const status = d.kept ? (d.iteration === 0 ? 'BASELINE' : 'KEPT') : 'ROLLBACK';
  const cls = d.kept ? (d.iteration === 0 ? 'baseline' : 'kept') : 'rollback';
  const evalStr = d.eval_accuracy !== null ? (d.eval_accuracy * 100).toFixed(1) + '%' : '—';
  const tr = document.createElement('tr');
  tr.innerHTML = `<td>${{d.iteration}}</td>
    <td>${{(d.train_accuracy * 100).toFixed(1)}}%</td>
    <td>${{d.train_failures || 0}}</td>
    <td>${{d.train_timeouts || 0}}</td>
    <td>${{evalStr}}</td>
    <td>${{d.train_cost ? '$' + d.train_cost.toFixed(4) : '—'}}</td>
    <td>${{d.supervisor_cost ? '$' + d.supervisor_cost.toFixed(4) : '—'}}</td>
    <td class="${{cls}}">${{status}}</td>`;
  tbody.appendChild(tr);
}});

// --- Populate details ---
const details = document.getElementById('iterDetails');
function makeSection(title, content, startOpen) {{
  if (!content || content === '(no changes)') return '';
  const id = 'sec_' + Math.random().toString(36).substr(2);
  const openCls = startOpen ? 'open' : '';
  let escaped = content.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  if (title.includes('Diff')) {{
    escaped = escaped.split('\\n').map(line => {{
      if (line.startsWith('+') && !line.startsWith('+++')) return `<span class="diff-add">${{line}}</span>`;
      if (line.startsWith('-') && !line.startsWith('---')) return `<span class="diff-del">${{line}}</span>`;
      if (line.startsWith('@@')) return `<span class="diff-hdr">${{line}}</span>`;
      return line;
    }}).join('\\n');
  }}
  return `<div class="section">
    <div class="section-title" onclick="document.getElementById('${{id}}').classList.toggle('open');
      this.textContent = this.textContent.startsWith('▸') ?
        '▾' + this.textContent.slice(1) : '▸' + this.textContent.slice(1);">
      ${{startOpen ? '▾' : '▸'}} ${{title}} (${{content.length > 1000 ? (content.length/1024).toFixed(0) + 'KB' : content.length + ' chars'}})
    </div>
    <div id="${{id}}" class="section-content ${{openCls}}"><pre>${{escaped}}</pre></div>
  </div>`;
}}

DATA.forEach(d => {{
  const status = d.kept ? (d.iteration === 0 ? 'BASELINE' : 'KEPT') : 'ROLLBACK';
  const tagCls = d.kept ? (d.iteration === 0 ? 'tag-base' : 'tag-kept') : 'tag-roll';
  const evalStr = d.eval_accuracy !== null ? ` | eval: ${{(d.eval_accuracy*100).toFixed(1)}}%` : '';
  const div = document.createElement('div');
  div.className = 'iter-detail';
  div.innerHTML = `
    <div class="iter-header" onclick="this.classList.toggle('open');
      this.nextElementSibling.classList.toggle('open');">
      <span><strong>Iteration ${{d.iteration}}</strong> — train: ${{(d.train_accuracy*100).toFixed(1)}}%${{evalStr}}
        <span class="tag ${{tagCls}}">${{status}}</span></span>
      <span class="arrow">▸</span>
    </div>
    <div class="iter-body">
      ${{d.reasoning ? '<div style="margin-bottom:12px"><strong>Reasoning:</strong><br>' +
        d.reasoning.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\\n/g,'<br>') + '</div>' : ''}}
      ${{makeSection('Code Diff', d.diff, true)}}
      ${{makeSection('Profiling Summary', d.profiling_summary, false)}}
      ${{makeSection('Failure Traces', d.failure_traces, false)}}
      ${{makeSection('Iteration History (sent to supervisor)', d.iteration_history, false)}}
      ${{makeSection('Supervisor Prompt (full)', d.supervisor_prompt, false)}}
      ${{makeSection('Supervisor Response (full)', d.supervisor_response, false)}}
      ${{makeSection('Outcome', d.outcome, false)}}
    </div>`;
  details.appendChild(div);
}});

// --- Chart (simple canvas) ---
const canvas = document.getElementById('accChart');
const ctx = canvas.getContext('2d');
function drawChart() {{
  const W = canvas.width = canvas.offsetWidth;
  const H = canvas.height = 300;
  const pad = {{ t: 30, r: 20, b: 40, l: 55 }};
  const cw = W - pad.l - pad.r;
  const ch = H - pad.t - pad.b;

  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = '#161b22';
  ctx.fillRect(0, 0, W, H);

  const n = DATA.length;
  if (n < 2) return;
  const allAcc = [...DATA.map(d => d.train_accuracy),
                   ...DATA.filter(d=>d.eval_accuracy!==null).map(d=>d.eval_accuracy)];
  const maxAcc = Math.min(1.0, Math.max(...allAcc) + 0.05);
  const minAcc = Math.max(0, Math.min(...allAcc) - 0.05);

  function x(i) {{ return pad.l + (i / (n - 1)) * cw; }}
  function y(v) {{ return pad.t + (1 - (v - minAcc) / (maxAcc - minAcc)) * ch; }}

  ctx.strokeStyle = '#21262d'; ctx.lineWidth = 1;
  const step = (maxAcc - minAcc) > 0.3 ? 0.1 : 0.05;
  for (let v = Math.ceil(minAcc/step)*step; v <= maxAcc; v += step) {{
    ctx.beginPath(); ctx.moveTo(pad.l, y(v)); ctx.lineTo(W-pad.r, y(v)); ctx.stroke();
    ctx.fillStyle = '#8b949e'; ctx.font = '11px sans-serif'; ctx.textAlign = 'right';
    ctx.fillText((v*100).toFixed(0)+'%', pad.l-8, y(v)+4);
  }}
  ctx.textAlign = 'center';
  DATA.forEach((d,i) => {{ ctx.fillText(d.iteration, x(i), H-pad.b+18); }});
  ctx.fillText('Iteration', W/2, H-5);

  ctx.strokeStyle = '#58a6ff'; ctx.lineWidth = 2;
  ctx.beginPath();
  DATA.forEach((d,i) => {{ i === 0 ? ctx.moveTo(x(i), y(d.train_accuracy)) : ctx.lineTo(x(i), y(d.train_accuracy)); }});
  ctx.stroke();

  const evalData = DATA.filter(d => d.eval_accuracy !== null);
  if (evalData.length > 1) {{
    ctx.strokeStyle = '#f0883e'; ctx.lineWidth = 2; ctx.setLineDash([5,5]);
    ctx.beginPath();
    evalData.forEach((d,i) => {{
      const xi = x(DATA.indexOf(d));
      i === 0 ? ctx.moveTo(xi, y(d.eval_accuracy)) : ctx.lineTo(xi, y(d.eval_accuracy));
    }});
    ctx.stroke();
    ctx.setLineDash([]);
  }}

  DATA.forEach((d,i) => {{
    ctx.fillStyle = d.kept ? '#3fb950' : '#f85149';
    ctx.beginPath(); ctx.arc(x(i), y(d.train_accuracy), 5, 0, Math.PI*2); ctx.fill();
    if (d.eval_accuracy !== null) {{
      ctx.fillStyle = '#f0883e';
      ctx.beginPath(); ctx.arc(x(DATA.indexOf(d)), y(d.eval_accuracy), 4, 0, Math.PI*2); ctx.fill();
    }}
  }});

  ctx.font = '12px sans-serif';
  const lx = pad.l + 10, ly = pad.t + 10;
  ctx.fillStyle = '#58a6ff'; ctx.fillRect(lx, ly, 16, 3); ctx.fillText('Train', lx+22, ly+5);
  if (evalData.length > 0) {{
    ctx.fillStyle = '#f0883e'; ctx.fillRect(lx, ly+16, 16, 3); ctx.fillText('Eval', lx+22, ly+21);
  }}
  ctx.fillStyle = '#3fb950'; ctx.beginPath(); ctx.arc(lx+100, ly+3, 4, 0, Math.PI*2); ctx.fill();
  ctx.fillStyle = '#c9d1d9'; ctx.fillText('Kept', lx+110, ly+5);
  ctx.fillStyle = '#f85149'; ctx.beginPath(); ctx.arc(lx+150, ly+3, 4, 0, Math.PI*2); ctx.fill();
  ctx.fillText('Rollback', lx+160, ly+5);
}}
drawChart();
window.addEventListener('resize', drawChart);
</script>

</body>
</html>'''

    report_path = output_dir / 'report.html'
    report_path.write_text(html_content)
    print(f'[report] saved {report_path}')


def generate_plots(report, output_dir: Path):
    """Generate accuracy/cost plots from iteration data."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print('[plots] matplotlib not available, skipping plots')
        return

    plots_dir = output_dir / 'plots'
    plots_dir.mkdir(exist_ok=True)

    iters = report.iterations
    xs = [r.iteration for r in iters]
    train_acc = [r.train_accuracy for r in iters]
    train_cost = [r.train_cost for r in iters]
    kept = [r.kept for r in iters]

    eval_acc = [r.eval_accuracy for r in iters]
    has_eval = any(e is not None for e in eval_acc)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(xs, train_acc, 'b-o', label='Train accuracy', markersize=4)

    if has_eval:
        eval_xs = [x for x, e in zip(xs, eval_acc) if e is not None]
        eval_ys = [e for e in eval_acc if e is not None]
        ax.plot(eval_xs, eval_ys, 'r-s', label='Eval accuracy', markersize=4)

    for x, acc, k in zip(xs, train_acc, kept):
        if k:
            ax.plot(x, acc, 'go', markersize=8, zorder=5)
        elif x > 0:
            ax.plot(x, acc, 'rx', markersize=8, zorder=5)

    best_acc = max(train_acc)
    ax.axhline(y=best_acc, color='green', linestyle='--', alpha=0.5,
               label=f'Best train: {best_acc:.1%}')

    ax.set_xlabel('Iteration')
    ax.set_ylabel('Accuracy')
    ax.set_title('Orchestration Learner: Train & Eval Accuracy over Iterations')
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(plots_dir / 'accuracy_over_iterations.png', dpi=150)
    plt.close(fig)
    print(f'[plots] saved {plots_dir / "accuracy_over_iterations.png"}')

    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(xs, train_cost, 'r-o', label='Avg cost/case', markersize=4)
    ax1.set_xlabel('Iteration')
    ax1.set_ylabel('Avg cost per case ($)')
    ax1.set_title('Orchestration Learner: Cost over Iterations')

    sup_costs = [r.supervisor_cost for r in iters]
    cum_sup = []
    total = 0.0
    for sc in sup_costs:
        total += sc
        cum_sup.append(total)
    ax2 = ax1.twinx()
    ax2.plot(xs, cum_sup, 'b--', label='Cumulative supervisor cost', alpha=0.7)
    ax2.set_ylabel('Cumulative supervisor cost ($)')

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2)
    ax1.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(plots_dir / 'cost_over_iterations.png', dpi=150)
    plt.close(fig)
    print(f'[plots] saved {plots_dir / "cost_over_iterations.png"}')

    fig, ax = plt.subplots(figsize=(8, 6))
    for r in iters:
        color = 'green' if r.kept else 'red'
        marker = 'o' if r.kept else 'x'
        ax.plot(r.train_cost, r.train_accuracy, marker=marker, color=color,
                markersize=8)
        ax.annotate(str(r.iteration), (r.train_cost, r.train_accuracy),
                    textcoords="offset points", xytext=(5, 5), fontsize=8)
    ax.set_xlabel('Avg cost per case ($)')
    ax.set_ylabel('Accuracy')
    ax.set_title('Orchestration Learner: Accuracy vs Cost')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(plots_dir / 'accuracy_vs_cost.png', dpi=150)
    plt.close(fig)
    print(f'[plots] saved {plots_dir / "accuracy_vs_cost.png"}')


# ---------------------------------------------------------------------------
# Helpers for dataset / evaluator setup (shared with the CLI)
# ---------------------------------------------------------------------------


def load_custom_instructions(value: str) -> str:
    """Load custom instructions from text or @filepath."""
    if not value:
        return ''
    if value.startswith('@'):
        path = Path(value[1:])
        if path.exists():
            return path.read_text()
        print(f'Warning: instruction file {path} not found, using as text')
    return value


def load_model_choices(path_str: str) -> str:
    """Load model choices from JSON and format as table."""
    if not path_str:
        return ''
    path = Path(path_str)
    if not path.exists():
        print(f'Warning: model file {path} not found')
        return ''
    models = json.loads(path.read_text())
    lines = ['| Model | Input $/1M | Output $/1M |',
             '|-------|-----------|------------|']
    for m in models:
        name = m.get('name', m.get('model', '?'))
        cin = m.get('input_cost', m.get('cost_in', '?'))
        cout = m.get('output_cost', m.get('cost_out', '?'))
        lines.append(f'| {name} | ${cin} | ${cout} |')
    return '\n'.join(lines)


def infer_ptools_module_name(
    benchmark_dir: Path,
    split: str,
    requested: str = '',
) -> str:
    """Infer the ptools module for benchmarks with per-task modules."""
    if requested:
        return requested
    if (benchmark_dir / 'ptools.py').exists():
        return 'ptools'
    if benchmark_dir.name == 'musr':
        if split.startswith('murder_mysteries'):
            return 'ptools_murder'
        if split.startswith('object_placements'):
            return 'ptools_object'
        if split.startswith('team_allocation'):
            return 'ptools_team'
    if benchmark_dir.name == 'natural_plan':
        for task in ('calendar', 'meeting', 'trip'):
            if split == task or split.startswith(f'{task}_'):
                return f'ptools_{task}'
    raise FileNotFoundError(
        f'Could not infer ptools module in {benchmark_dir}. '
        'Pass --ptools-module explicitly.'
    )


def _canonical_task_name(benchmark_dir: Path, split: str) -> str:
    if benchmark_dir.name == 'natural_plan':
        for task in ('calendar', 'meeting', 'trip'):
            if split == task or split.startswith(f'{task}_'):
                return task
    return split


def _copy_scratch_resources(benchmark_dir: Path, scratch_dir: Path) -> None:
    for dirname in ('prompt_templates',):
        src = benchmark_dir / dirname
        dst = scratch_dir / dirname
        if src.exists() and not dst.exists():
            shutil.copytree(src, dst)

    # RuleArena ptools resolves the tax prompt relative to __file__.
    # Scratch ptools live under .orchestration_learner, so copy only the
    # needed small prompt module instead of the full benchmark data directory.
    tax_prompt = benchmark_dir / 'data' / 'tax' / 'prompt.py'
    if tax_prompt.exists():
        dst = scratch_dir / 'data' / 'tax' / 'prompt.py'
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(tax_prompt, dst)


def _copy_benchmark_resources(benchmark_dir: Path, run_dir: Path) -> None:
    """Copy small resource dirs the evolved ptools may reference via __file__.

    Keeps the run dir self-contained so `fn: __learned__.<entry>` can
    import ptools_evolved.py without the original benchmark dir on disk.
    """
    for dirname in ('prompt_templates',):
        src = benchmark_dir / dirname
        dst = run_dir / dirname
        if src.exists() and not dst.exists():
            shutil.copytree(src, dst)


def _module_interfaces(module):
    from secretagent.core import Interface
    interfaces = []
    seen = set()
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, Interface) and id(obj) not in seen:
            interfaces.append(obj)
            seen.add(id(obj))
    return interfaces


def _dataset_from_cases(dataset, cases: list, suffix: str):
    return dataset.model_copy(update={
        'name': f'{dataset.name}{suffix}',
        'cases': list(cases),
    })


def _load_dataset_for_split(load_dataset, split: str):
    sig = inspect.signature(load_dataset)
    kwargs = {}
    actual_split = split
    cfg_map = {
        'prompt_mode': 'dataset.prompt_mode',
        'stratified': 'dataset.stratified',
        'sample_n': 'dataset.sample_n',
        'sample_seed': 'dataset.sample_seed',
        'partition': 'dataset.partition',
    }
    for param, cfg_key in cfg_map.items():
        if param in sig.parameters:
            value = config.get(cfg_key)
            if value is not None:
                kwargs[param] = value

    if 'partition' in sig.parameters:
        for task in ('calendar', 'meeting', 'trip'):
            prefix = f'{task}_'
            if split.startswith(prefix):
                actual_split = task
                kwargs['partition'] = split[len(prefix):]
                break

    return load_dataset(actual_split, **kwargs)


def _plain_sample(cases: list, n: int, seed: int | None) -> list:
    sampled = list(cases)
    if seed is not None:
        random.Random(seed).shuffle(sampled)
    return sampled[:min(n, len(sampled))]


def _case_stratified_sample_fn(evaluator_module):
    sampler = getattr(evaluator_module, 'stratified_sample', None)
    if sampler is None:
        return None
    params = list(inspect.signature(sampler).parameters)
    if len(params) >= 2 and params[1] == 'n':
        return sampler
    return None


def _resolve_train_eval_datasets(
    evaluator_module,
    load_dataset,
    train_split: str,
    eval_split: str,
    n_train: int,
    n_eval: int,
    seed: int | None,
):
    full_dataset = _load_dataset_for_split(load_dataset, train_split)
    case_stratified_sample = _case_stratified_sample_fn(evaluator_module)

    if n_eval > 0 and hasattr(evaluator_module, 'stratified_split'):
        from expt import stratified_split
        train_cases, eval_cases = stratified_split(
            full_dataset.cases, n_train, n_eval, seed=seed or 42)
        train_dataset = _dataset_from_cases(full_dataset, train_cases, '_train')
        eval_dataset = _dataset_from_cases(full_dataset, eval_cases, '_eval')
        return train_dataset, eval_dataset, f'disjoint stratified split from {train_split}'

    if n_eval > 0 and train_split == eval_split:
        cases = list(full_dataset.cases)
        if seed is not None:
            random.Random(seed).shuffle(cases)
        train_cases = cases[:min(n_train, len(cases))]
        eval_cases = cases[len(train_cases):len(train_cases) + n_eval]
        train_dataset = _dataset_from_cases(full_dataset, train_cases, '_train')
        eval_dataset = _dataset_from_cases(full_dataset, eval_cases, '_eval')
        return train_dataset, eval_dataset, f'disjoint plain split from {train_split}'

    if case_stratified_sample is not None:
        train_cases = case_stratified_sample(
            full_dataset.cases, n_train, seed=seed or 42)
        train_dataset = _dataset_from_cases(full_dataset, train_cases, '_train')
    else:
        train_dataset = _dataset_from_cases(
            full_dataset, _plain_sample(full_dataset.cases, n_train, seed), '_train')

    eval_dataset = None
    if n_eval > 0:
        eval_full = _load_dataset_for_split(load_dataset, eval_split)
        if case_stratified_sample is not None:
            eval_cases = case_stratified_sample(
                eval_full.cases, n_eval, seed=seed or 42)
        else:
            eval_cases = _plain_sample(eval_full.cases, n_eval, seed)
        eval_dataset = _dataset_from_cases(eval_full, eval_cases, '_eval')

    return train_dataset, eval_dataset, 'separate splits'


def _seed_task_description(tools_cfg, entry_point_name: str,
                           override: str, entry_interface) -> str:
    if override:
        return load_custom_instructions(override)
    entry_cfg = tools_cfg.get(entry_point_name) if hasattr(tools_cfg, 'get') else None
    if entry_cfg and entry_cfg.get('task_description'):
        return str(entry_cfg.get('task_description'))
    return (entry_interface.doc or '').strip()


def _rename_def_signature(signature: str, new_name: str) -> str:
    return 'def ' + new_name + '(' + signature.split('(', 1)[1]


def _seed_orchestrated_workflow(
    *,
    evolved_path: Path,
    ptools_module,
    ptools_module_name: str,
    tools_cfg,
    entry_point_name: str,
    task_description_override: str,
    model: str,
) -> str:
    from secretagent.core import implement_via_config
    from secretagent.orchestrate.catalog import PtoolCatalog
    from secretagent.orchestrate.composer import compose_with_retry
    from secretagent.orchestrate.pipeline import (
        Pipeline, _entry_signature_from_interface,
    )

    entry_interface = getattr(ptools_module, entry_point_name)
    tools_only_cfg = {
        name: cfg for name, cfg in tools_cfg.items()
        if name != entry_point_name
    }
    allowed_tool_names = set(tools_only_cfg)
    implement_via_config(ptools_module, tools_only_cfg)

    tool_interfaces = [
        iface for iface in _module_interfaces(ptools_module)
        if iface.name in allowed_tool_names and iface.implementation is not None
    ]
    catalog = PtoolCatalog.from_interfaces(tool_interfaces)
    if not catalog.ptools:
        raise ValueError(
            f'No implemented tools available to seed {entry_point_name}. '
            'Check the ptools config or pass a config with non-entry tools.'
        )

    entry_signature = _entry_signature_from_interface(entry_interface)
    task_description = _seed_task_description(
        tools_cfg, entry_point_name, task_description_override, entry_interface)

    print(f'[seed] composing initial workflow for {entry_point_name} '
          f'from {len(catalog)} tools with {model}')
    namespace = {iface.name: iface for iface in tool_interfaces}

    def _validate_seed_code(seed_code: str) -> None:
        Pipeline(seed_code, entry_signature, namespace)

    code, attempt = compose_with_retry(
        task_description,
        catalog,
        entry_signature,
        test_fn=_validate_seed_code,
        model=model,
    )
    if attempt > 1:
        print(f'[seed] accepted generated workflow on attempt {attempt}')

    seed_fn_name = f'{entry_point_name}_orchestrated_seed'
    seed_signature = _rename_def_signature(entry_signature, seed_fn_name)
    seed_pipeline = Pipeline(code, seed_signature, namespace)
    seed_source = (
        '\n\n# --- Auto-generated by orchestration_learner --seed-orchestrate ---\n'
        f'{seed_pipeline.source}\n'
    )
    evolved_path.write_text(evolved_path.read_text().rstrip() + seed_source)
    config.configure(dotlist=[
        f'ptools.{entry_point_name}.method=direct',
        f'ptools.{entry_point_name}.fn={ptools_module_name}.{seed_fn_name}',
    ])
    print(f'[seed] wrote {seed_fn_name} to {evolved_path}')
    return seed_fn_name


def _load_local_json_dataset(benchmark_dir: Path, split: str):
    from secretagent.dataset import Dataset
    dataset_path = benchmark_dir / 'data' / f'{split}.json'
    if not dataset_path.exists():
        raise FileNotFoundError(
            f'No load_dataset() in expt.py and no local dataset at {dataset_path}'
        )
    return Dataset.model_validate_json(dataset_path.read_text())


def _find_evaluator_cls(evaluator_module, benchmark_dir: Path):
    from secretagent.evaluate import Evaluator
    modules = [evaluator_module]
    try:
        modules.append(importlib.import_module('evaluator'))
    except ImportError:
        pass
    for module in modules:
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and issubclass(obj, Evaluator) and obj is not Evaluator:
                return obj
    from secretagent.evaluate import ExactMatchEvaluator
    return ExactMatchEvaluator


def _dotlist_value(dotlist: list[str], key: str):
    prefix = f'{key}='
    for arg in reversed(dotlist):
        if arg.startswith(prefix):
            raw = arg[len(prefix):]
            try:
                return yaml.safe_load(raw)
            except yaml.YAMLError:
                return raw
    return None


def _normalize_ptools_config(tools_cfg, ptools_module_name: str) -> dict[str, Any]:
    """Resolve benchmark sentinel methods into concrete implementations."""
    default_workflows = {
        'calendar_scheduling': 'calendar_workflow',
        'meeting_planning': 'meeting_workflow',
        'trip_planning': 'trip_workflow',
        'compute_rulearena_answer': 'l1_extract_workflow',
        'tabmwp_solve': 'tools_workflow',
        'are_sports_in_sentence_consistent': 'sports_understanding_workflow',
        'identify_shape': 'geometric_shapes_workflow',
        'answer_penguin_question': 'penguins_workflow',
    }
    normalized = {}
    for name, cfg in tools_cfg.items():
        cfg_dict = dict(cfg)
        if cfg_dict.get('method') == 'DEFAULT':
            workflow = default_workflows.get(name)
            if workflow is None:
                raise ValueError(
                    f'No DEFAULT ptools workflow mapping for {name!r}')
            cfg_dict = {
                'method': 'direct',
                'fn': f'{ptools_module_name}.{workflow}',
            }
        normalized[name] = cfg_dict
    return normalized


# ---------------------------------------------------------------------------
# The Learner
# ---------------------------------------------------------------------------


LEARNER_TAG = 'orch_learner'


class OrchestrationLearner(Learner):
    """Supervisor-driven pipeline hill climbing as a Learner.

    Output layout (train_dir is typically `<benchmark>/results/orchestration_learner`):

        {train_dir}/{TS}.orch_learner/
            config.yaml            (savefile snapshot)
            run_metadata.json
            ptools_evolved.py      (best pipeline source)
            report.json            (SupervisorReport)
            report.html            (viewable report)
            iterations/            (per-iteration artifacts)
            final_eval/            (optional held-out eval)
            plots/                 (accuracy/cost PNGs)
            implementation.yaml    (for eval-time binding via `direct` +
                                    `fn: __learned__.<entry>, learner: orch_learner`)

    Parameters mirror the CLI flags; see `secretagent.cli.orchestration_learner`.
    """

    def __init__(
        self,
        interface_name: str,
        train_dir: str,
        *,
        benchmark_name: str = '',
        config_file: str = '',
        n_train: int = 110,
        n_eval: int = 110,
        max_iterations: int = 10,
        target_accuracy: float | None = None,
        supervisor_model: str = 'gemini/gemini-3.1-pro-preview',
        custom_instructions: str = '',
        model_change: str = '',
        train_split: str = '',
        eval_split: str = '',
        ptools_module: str = '',
        seed_orchestrate: bool = False,
        scratch_evolved: bool = False,
        orchestrate_task_description: str = '',
        debug: bool = False,
        resume: Optional[Path] = None,
        dotlist_overrides: list[str] = (),
    ):
        self.interface_name = interface_name
        self.train_dir = str(train_dir)
        self.file_under = LEARNER_TAG
        self.only_correct = False

        # Orchestration args
        self.benchmark_name = benchmark_name
        self.config_file = config_file
        self.n_train = n_train
        self.n_eval = n_eval
        self.max_iterations = max_iterations
        self.target_accuracy = target_accuracy
        self.supervisor_model = supervisor_model
        self.custom_instructions = custom_instructions
        self.model_change = model_change
        self.train_split = train_split
        self.eval_split = eval_split
        self.ptools_module = ptools_module
        self.seed_orchestrate = seed_orchestrate
        self.scratch_evolved = scratch_evolved
        self.orchestrate_task_description = orchestrate_task_description
        self.debug = debug
        self.resume = Path(resume) if resume else None
        self.dotlist_overrides = list(dotlist_overrides)

        # The SupervisorReport produced by fit(), populated at run time.
        self.report_obj = None

        produced = ['ptools_evolved.py', 'report.json', 'report.html',
                    'run_metadata.json', 'implementation.yaml']

        if self.resume:
            # Reuse existing run directory: don't mint a fresh timestamp dir.
            self.out_dir = Path(self.resume)
            if not self.out_dir.exists():
                raise FileNotFoundError(
                    f'resume directory does not exist: {self.out_dir}')
            self.created_files = {
                name: self.out_dir / name for name in produced
            }
        else:
            # Mint a fresh {TS}.orch_learner dir via savefile.
            names = savefile.filename_list(self.train_dir, produced, self.file_under)
            self.out_dir = Path(names[0]).parent
            self.created_files = dict(zip(produced, names))

    # ------------------------------------------------------------------
    # fit()
    # ------------------------------------------------------------------

    def fit(self) -> 'OrchestrationLearner':
        """Run the supervisor-driven improvement loop.

        Mirrors the body of `cli.orchestration_learner.run()` but writes
        into `self.out_dir` (a savefile-managed dir). Populates
        `self.report_obj` and writes ptools_evolved.py, report.json,
        report.html, plots/, iterations/, and final_eval/ if eval is run.
        """
        from secretagent.core import implement_via_config
        from secretagent.orchestrate.module_reload import exec_ptools_module
        from secretagent.orchestrate.catalog import PtoolCatalog
        from secretagent.orchestrate.improve import (
            improve_with_supervisor, SupervisorReport,
        )

        benchmark_dir = Path.cwd()

        sys.path.insert(0, str(benchmark_dir))
        project_root = benchmark_dir
        while project_root != project_root.parent:
            if (project_root / 'src').exists():
                sys.path.insert(0, str(project_root / 'src'))
                break
            project_root = project_root.parent

        adapter = None
        adapter_train_split = None
        adapter_eval_split = None
        if self.benchmark_name:
            from secretagent.orchestrate.benchmark_adapter import BenchmarkAdapter
            adapter = BenchmarkAdapter(self.benchmark_name)
            adapter.setup_sys_path()
            benchmark_dir = adapter.benchmark_dir
            if str(benchmark_dir) not in sys.path:
                sys.path.insert(0, str(benchmark_dir))
            os.chdir(benchmark_dir)
            if not self.config_file:
                self.config_file = str(adapter.config_file)
            if not self.ptools_module:
                self.ptools_module = adapter.spec['ptools_module']

        if not self.config_file:
            raise ValueError(
                'config_file is required unless benchmark_name is provided')

        timestamp = datetime.now().strftime('%Y%m%d.%H%M%S')

        # --- Load config ---
        cfg_path = Path(self.config_file)
        if not cfg_path.is_absolute():
            cfg_path = benchmark_dir / cfg_path
        config.configure(yaml_file=str(cfg_path), dotlist=list(self.dotlist_overrides))
        config.set_root(benchmark_dir)

        if adapter is not None:
            adapter_overrides = []
            extra_keys = [arg.split('=', 1)[0] for arg in self.dotlist_overrides
                          if '=' in arg]
            if 'evaluate.entry_point' not in extra_keys:
                adapter_overrides.append(
                    f'evaluate.entry_point={adapter.entry_point_name}')
            if 'dataset.shuffle_seed' not in extra_keys:
                adapter_overrides.append(
                    f'dataset.shuffle_seed={adapter.shuffle_seed}')
            agent_model = adapter.spec.get('agent_model')
            if agent_model and 'llm.model' not in extra_keys:
                adapter_overrides.append(f'llm.model={agent_model}')
            if adapter_overrides:
                config.configure(dotlist=adapter_overrides)

            if self.train_split:
                adapter.spec.setdefault('train', {})['split'] = self.train_split
            if self.eval_split:
                adapter.spec.setdefault('eval', {})['split'] = self.eval_split

            explicit_shuffle_seed = _dotlist_value(
                self.dotlist_overrides, 'dataset.shuffle_seed')
            if explicit_shuffle_seed is not None:
                adapter.spec['shuffle_seed'] = int(explicit_shuffle_seed)

            adapter_train_split = adapter.spec.get('train', {}).get('split')
            adapter_eval_split = adapter.spec.get('eval', {}).get('split')

        if config.get('cachier.enable_caching') is None:
            config.configure(cachier=dict(enable_caching=True))

        if self.debug:
            config.configure(echo=dict(orchestrate_llm=True))

        configured_split = config.get('dataset.split')
        train_split = (self.train_split or adapter_train_split
                       or configured_split or 'train')
        eval_split = (self.eval_split or adapter_eval_split
                      or ('test' if train_split == 'train' else train_split))

        ptools_module_name = infer_ptools_module_name(
            benchmark_dir, train_split, self.ptools_module)
        ptools_cfg = _normalize_ptools_config(
            config.require('ptools'), ptools_module_name)
        config.configure(ptools=ptools_cfg)

        # --- Create/load evolved ptools module ---
        base_path = benchmark_dir / f'{ptools_module_name}.py'
        if not base_path.exists():
            raise FileNotFoundError(
                f'base ptools module not found: {base_path}')

        if self.scratch_evolved:
            scratch_dir = benchmark_dir / '.orchestration_learner'
            scratch_dir.mkdir(exist_ok=True)
            _copy_scratch_resources(benchmark_dir, scratch_dir)
            evolved_path = scratch_dir / f'{ptools_module_name}_{timestamp}_scratch.py'
            shutil.copy2(base_path, evolved_path)
            print(f'Created scratch module {evolved_path.relative_to(benchmark_dir)} '
                  f'from {base_path.name}')
        elif self.seed_orchestrate and not self.resume:
            scratch_dir = benchmark_dir / '.orchestration_learner'
            scratch_dir.mkdir(exist_ok=True)
            _copy_scratch_resources(benchmark_dir, scratch_dir)
            evolved_path = scratch_dir / f'{ptools_module_name}_{timestamp}_seed.py'
            shutil.copy2(base_path, evolved_path)
            print(f'Created seed module {evolved_path.relative_to(benchmark_dir)} '
                  f'from {base_path.name}')
        else:
            evolved_path = benchmark_dir / f'{ptools_module_name}_evolved.py'
            if not evolved_path.exists():
                shutil.copy2(base_path, evolved_path)
                print(f'Created {evolved_path.name} from {base_path.name}')
            else:
                print(f'Using existing {evolved_path.name}')

        spec = importlib.util.spec_from_file_location(
            ptools_module_name, str(evolved_path))
        ptools_module_obj = importlib.util.module_from_spec(spec)
        sys.modules[ptools_module_name] = ptools_module_obj
        exec_ptools_module(ptools_module_obj, evolved_path)

        if adapter is not None:
            evaluator_module = None
            load_dataset = None
            evaluator = adapter.get_evaluator()
        else:
            try:
                evaluator_module = __import__('expt')
            except ImportError as e:
                raise ImportError(
                    f'could not import expt module from {benchmark_dir}: {e}')
            load_dataset = getattr(evaluator_module, 'load_dataset', None)
            if load_dataset is None:
                def load_dataset(split, _bd=benchmark_dir):
                    return _load_local_json_dataset(_bd, split)
            evaluator_cls = _find_evaluator_cls(evaluator_module, benchmark_dir)
            evaluator_sig = inspect.signature(evaluator_cls)
            if 'task' in evaluator_sig.parameters:
                evaluator = evaluator_cls(
                    _canonical_task_name(benchmark_dir, train_split))
            else:
                evaluator = evaluator_cls()

        entry_point_name = config.get(
            'evaluate.entry_point', 'calculate_medical_value')
        if not hasattr(ptools_module_obj, entry_point_name):
            raise AttributeError(
                f'entry point {entry_point_name!r} not found in '
                f'{ptools_module_name}')

        if self.seed_orchestrate and not self.resume:
            seed_model = config.get('orchestrate.model') or self.supervisor_model
            _seed_orchestrated_workflow(
                evolved_path=evolved_path,
                ptools_module=ptools_module_obj,
                ptools_module_name=ptools_module_name,
                tools_cfg=config.require('ptools'),
                entry_point_name=entry_point_name,
                task_description_override=self.orchestrate_task_description,
                model=seed_model,
            )
            exec_ptools_module(ptools_module_obj, evolved_path)

        implement_via_config(ptools_module_obj, config.require('ptools'))
        if adapter is not None:
            adapter.run_setup_hook(ptools_module_obj)
        entry_interface = getattr(ptools_module_obj, entry_point_name)

        # --- Load datasets ---
        print('\n=== Loading datasets ===')
        seed = config.get('dataset.shuffle_seed', 42)
        if adapter is not None:
            train_dataset, eval_dataset = adapter.load_train_eval(
                self.n_train, self.n_eval)
            split_note = f'adapter:{self.benchmark_name}'
        else:
            train_dataset, eval_dataset, split_note = _resolve_train_eval_datasets(
                evaluator_module, load_dataset, train_split, eval_split,
                self.n_train, self.n_eval, seed,
            )
        print(f'Train: {len(train_dataset.cases)} cases')
        if eval_dataset:
            print(f'Eval: {len(eval_dataset.cases)} cases')
        print(f'Sampling: {split_note}')

        # --- Build catalog ---
        allowed_tool_names = set(config.require('ptools')) - {entry_point_name}
        tool_interfaces = [
            iface for iface in _module_interfaces(ptools_module_obj)
            if iface.name in allowed_tool_names and iface.implementation is not None
        ]
        catalog = PtoolCatalog.from_interfaces(tool_interfaces)

        instructions = load_custom_instructions(self.custom_instructions)
        model_choices_text = load_model_choices(self.model_change)

        # --- Resume state ---
        resume_iterations = None
        resume_best_accuracy = None
        resume_best_eval_accuracy = None
        resume_supervisor_cost = 0.0

        if self.resume:
            prev_report_path = self.resume / 'report.json'
            if not prev_report_path.exists():
                raise FileNotFoundError(f'{prev_report_path} not found')
            prev_report = SupervisorReport.model_validate_json(
                prev_report_path.read_text())
            resume_iterations = prev_report.iterations
            resume_best_accuracy = prev_report.best_train_accuracy
            resume_best_eval_accuracy = prev_report.final_eval_accuracy
            if resume_best_eval_accuracy is None:
                kept_evals = [r.eval_accuracy for r in prev_report.iterations
                              if r.kept and r.eval_accuracy is not None]
                if kept_evals:
                    resume_best_eval_accuracy = max(kept_evals)
            resume_supervisor_cost = prev_report.total_supervisor_cost

            prev_evolved = self.resume / 'ptools_evolved.py'
            if prev_evolved.exists():
                evolved_path.write_text(prev_evolved.read_text())
                exec_ptools_module(ptools_module_obj, evolved_path)
                implement_via_config(ptools_module_obj, config.require('ptools'))
                entry_interface = getattr(ptools_module_obj, entry_point_name)
                print(f'Loaded ptools_evolved.py from {self.resume.name}')

            last_iter = resume_iterations[-1].iteration if resume_iterations else 0
            print(f'Resuming from iteration {last_iter} '
                  f'(best train: {resume_best_accuracy:.1%}, '
                  f'supervisor cost: ${resume_supervisor_cost:.4f})')

        # --- Output directory housekeeping ---
        results_base = self.out_dir.parent
        # Per-iteration evals should land under the same results_base so
        # they're adjacent to (but not inside) the run dir.
        config.configure(evaluate=dict(result_dir=str(results_base)))
        config.save(self.out_dir / 'config.yaml')

        run_metadata = {
            'benchmark': benchmark_dir.name,
            'benchmark_dir': str(benchmark_dir),
            'config_file': str(cfg_path),
            'entry_point': entry_point_name,
            'ptools_module': ptools_module_name,
            'seed_orchestrate': self.seed_orchestrate,
            'scratch_evolved': self.scratch_evolved,
            'evolved_path': str(evolved_path),
            'results_base': str(results_base),
            'resume_from': str(self.resume) if self.resume else None,
            'train_split': train_split,
            'eval_split': eval_split,
            'n_train': len(train_dataset.cases),
            'n_eval': len(eval_dataset.cases) if eval_dataset else 0,
            'max_iterations': self.max_iterations,
            'target_accuracy': self.target_accuracy,
            'supervisor_model': self.supervisor_model,
        }
        (self.out_dir / 'run_metadata.json').write_text(
            json.dumps(run_metadata, indent=2)
        )

        # --- Print setup summary ---
        print('\n=== Orchestration Learner ===')
        print(f'Benchmark: {benchmark_dir.name}')
        print(f'Config: {cfg_path.name}')
        print(f'Ptools module: {ptools_module_name} ({evolved_path.name})')
        if self.scratch_evolved:
            print(f'Scratch evolved: {evolved_path}')
        print(f'Entry point: {entry_point_name}')
        print(f'Supervisor: {self.supervisor_model}')
        print(f'Train: {len(train_dataset.cases)} cases, '
              f'Eval: {len(eval_dataset.cases) if eval_dataset else 0} cases')
        print(f'Max iterations: {self.max_iterations}')
        if self.target_accuracy:
            print(f'Target accuracy: {self.target_accuracy:.1%}')
        if instructions:
            print(f'Custom instructions: {instructions[:100]}...')
        if model_choices_text:
            print('Model choices loaded')
        if self.resume:
            print(f'Resuming from: {self.resume}')
        print(f'Output: {self.out_dir}')

        # --- Run improvement loop ---
        def _on_iteration(output_dir: Path):
            report_path = output_dir / 'report.json'
            if report_path.exists():
                try:
                    r = SupervisorReport.model_validate_json(report_path.read_text())
                    generate_html_report(r, output_dir)
                except Exception:
                    pass

        report = improve_with_supervisor(
            entry_interface=entry_interface,
            tool_interfaces=tool_interfaces,
            catalog=catalog,
            evaluator=evaluator,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            supervisor_model=self.supervisor_model,
            max_iterations=self.max_iterations,
            target_accuracy=self.target_accuracy,
            custom_instructions=instructions,
            model_choices=model_choices_text,
            output_dir=self.out_dir,
            ptools_module=ptools_module_obj,
            resume_iterations=resume_iterations,
            resume_best_accuracy=resume_best_accuracy,
            resume_best_eval_accuracy=resume_best_eval_accuracy,
            resume_supervisor_cost=resume_supervisor_cost,
            on_iteration_complete=_on_iteration,
        )

        # --- Final eval ---
        entry_interface = getattr(ptools_module_obj, entry_point_name)
        if eval_dataset:
            print(f'\n=== Final Evaluation on Held-Out Set ({len(eval_dataset.cases)} cases) ===')
            final_dir = self.out_dir / 'final_eval'
            final_dir.mkdir(exist_ok=True)
            with config.configuration(evaluate=dict(
                expt_name='rc_final_eval',
                result_dir=str(final_dir),
                record_details=True,
            )):
                csv_path = evaluator.evaluate(eval_dataset, entry_interface)
            import pandas as pd
            df = pd.read_csv(csv_path)
            eval_acc = df['correct'].mean()
            eval_cost = df.get('cost', pd.Series([0])).mean()
            report.final_eval_accuracy = eval_acc
            print(f'Final eval accuracy: {eval_acc:.1%}')
            print(f'Final eval avg cost: ${eval_cost:.4f}')

            (self.out_dir / 'report.json').write_text(
                report.model_dump_json(indent=2)
            )

        # --- Plots + HTML ---
        print('\n=== Generating Plots & Report ===')
        generate_plots(report, self.out_dir)
        generate_html_report(report, self.out_dir)

        # --- Copy benchmark-local resource dirs adjacent to ptools_evolved.py ---
        # Some benchmarks' evolved ptools use `__file__` at import time to
        # reach local template directories. Copy prompt_templates/ into the
        # run dir so `fn: __learned__.<entry>` can import the evolved file
        # standalone, without needing the original benchmark dir on disk.
        _copy_benchmark_resources(benchmark_dir, self.out_dir)

        self.report_obj = report
        self._entry_point_name = entry_point_name
        return self

    # ------------------------------------------------------------------
    # save_implementation / report / learn
    # ------------------------------------------------------------------

    def save_implementation(self) -> Path:
        """Write implementation.yaml for binding via the `direct` factory.

        The yaml has one top-level key (the interface name) with:
            method: direct
            fn: __learned__.<implementing_fn_name>
            learner: orch_learner

        where <implementing_fn_name> is the bare name of the actual function
        that implements the entry point in `ptools_evolved.py` (not the
        interface stub).

        How <implementing_fn_name> is chosen:
          1. If the original config bound the entry_point via
             `ptools.<entry>.method=direct, fn=<module>.<fn_name>`, use
             `<fn_name>`. This is the common case (e.g. medcalc binds
             `calculate_medical_value` to `ptools.workflow`, so we emit
             `fn: __learned__.workflow`).
          2. Otherwise fall back to the entry_point name itself — works
             when the evolved module exposes the entry point as a regular
             function rather than an @interface stub.
        """
        entry_point = getattr(self, '_entry_point_name', None)
        if entry_point is None:
            entry_point = config.get('evaluate.entry_point') or self.interface_name

        fn_name = entry_point
        entry_cfg = config.get(f'ptools.{entry_point}')
        if entry_cfg:
            try:
                entry_cfg_dict = dict(entry_cfg)
            except (TypeError, ValueError):
                entry_cfg_dict = {}
            if entry_cfg_dict.get('method') == 'direct':
                fn_path = entry_cfg_dict.get('fn')
                if isinstance(fn_path, str) and fn_path:
                    fn_name = fn_path.rsplit('.', 1)[-1]

        impl = {
            self.interface_name: {
                'method': 'direct',
                'fn': f'__learned__.{fn_name}',
                'learner': LEARNER_TAG,
            }
        }
        impl_path = Path(self.created_files['implementation.yaml'])
        impl_path.write_text(yaml.dump(impl, sort_keys=False))
        return impl_path

    def report(self) -> str:
        """Short human-readable summary of the learned pipeline."""
        r = self.report_obj
        if r is None:
            return 'OrchestrationLearner: fit() has not been called'
        lines = [
            f'best train accuracy: {r.best_train_accuracy:.1%} '
            f'(iteration {r.best_iteration})',
            f'iterations: {len(r.iterations)}',
            f'supervisor cost: ${r.total_supervisor_cost:.4f}',
        ]
        if r.final_eval_accuracy is not None:
            lines.append(f'final eval accuracy: {r.final_eval_accuracy:.1%}')
        return '\n'.join(lines)

    def learn(
        self,
        dirs: list[Path] | None = None,
        latest: int = 1,
        check: Optional[list[str]] = None,
    ):
        """Top-level entry: skip distillation, fit, save, report.

        Orchestrate generates its own training data from the benchmark
        dataset each run, so there's no recorded-rollout distillation to do.
        """
        self.fit()
        output_file = self.save_implementation()
        print(self.report())
        print(f'saved output to {output_file}')
        return self
