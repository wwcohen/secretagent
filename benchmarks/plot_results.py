# /// script
# dependencies = ["pandas", "matplotlib", "pyyaml"]
# ///
"""Generate the 3 plots for code distillation results.

Reads val_results / recordings / learned_v2 directories and produces:
- plot1_class1_speed_vs_cost.png
- plot2_handvslearned_ptools.png
- plot3_5_conditions.png

Run with: uv run --script benchmarks/plot_results.py
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BENCHMARKS_DIR = ROOT / 'benchmarks'

# Map of benchmark name → (full path, label, color)
BENCHMARKS = {
    'natplan_calendar': BENCHMARKS_DIR / 'natural_plan',
    'natplan_meeting':  BENCHMARKS_DIR / 'natural_plan',
    'natplan_trip':     BENCHMARKS_DIR / 'natural_plan',
    'musr_murder':      BENCHMARKS_DIR / 'musr',
    'bbh_sports':       BENCHMARKS_DIR / 'bbh' / 'sports_understanding',
    'bbh_penguins':     BENCHMARKS_DIR / 'bbh' / 'penguins_in_a_table',
    'bbh_geometric':    BENCHMARKS_DIR / 'bbh' / 'geometric_shapes',
    'bbh_date':         BENCHMARKS_DIR / 'bbh' / 'date_understanding',
    'medcalc':          BENCHMARKS_DIR / 'medcalc',
    'finqa':            BENCHMARKS_DIR / 'finqa',
    'rulearena_nba':    BENCHMARKS_DIR / 'rulearena',
    'rulearena_tax':    BENCHMARKS_DIR / 'rulearena',
    'rulearena_airline': BENCHMARKS_DIR / 'rulearena',
}


def find_val_csv(benchdir: Path, expt_pat: str):
    """Find the most recent results.csv matching an expt name pattern."""
    cand = sorted(benchdir.glob(f'val_results/*.{expt_pat}/results.csv'))
    return cand[-1] if cand else None


def _norm_bbh(s):
    return str(s).strip().strip('()')


def _is_bbh(csv_path: Path) -> bool:
    return '/bbh/' in str(csv_path)


def csv_metrics(csv_path: Path, train_rollout_dir: Path = None):
    """Return (n, acc, total_cost, llm_calls_per_case).

    LLM-calls counted from the train recording's rollout (val recordings
    don't have rollout when record_details=false). When the val cost is
    near zero (= the distilled function ran without LLM), report 0 calls.
    """
    if csv_path is None or not csv_path.exists():
        return None
    df = pd.read_csv(csv_path)
    n = len(df)
    # For BBH benchmarks, the per-benchmark evaluator strips parens (e.g.
    # `(C)` vs `C`); my val runs used the default ExactMatchEvaluator and
    # so `correct` is undercounted. Re-compute using strip-parens for BBH.
    if _is_bbh(csv_path) and {'predicted_output', 'expected_output'} <= set(df.columns):
        df['real_correct'] = df.apply(
            lambda r: float(_norm_bbh(r['predicted_output']) == _norm_bbh(r['expected_output'])),
            axis=1)
        acc = df['real_correct'].mean() * 100
    else:
        acc = df['correct'].mean() * 100 if 'correct' in df.columns else 0
    cost = df['cost'].sum() if 'cost' in df.columns else 0
    cost_per_case = cost / max(n, 1)

    # If cost is near zero (distilled all LLM out), calls_per_case = 0
    calls_per_case = 0.0
    if cost_per_case < 0.001 and train_rollout_dir is None:
        return {'n': n, 'acc': acc, 'cost': cost,
                'cost_per_case': cost_per_case, 'calls_per_case': 0.0}

    # Count from train recording (records were taken with record_details=true)
    if train_rollout_dir and train_rollout_dir.exists():
        jsonl = train_rollout_dir / 'results.jsonl'
        if jsonl.exists():
            total_calls, n_rec = 0, 0
            for line in jsonl.open():
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                rollout = rec.get('rollout') or []
                count = 0
                for step in rollout:
                    stats = step.get('stats') or {}
                    if stats.get('cost', 0) > 0 or stats.get('input_tokens', 0) > 0:
                        count += 1
                    step_info = step.get('step_info') or []
                    for s in step_info:
                        if isinstance(s, dict) and s.get('tool_call'):
                            count += 1
                total_calls += count
                n_rec += 1
            calls_per_case = total_calls / max(n_rec, 1)

    return {'n': n, 'acc': acc, 'cost': cost,
            'cost_per_case': cost_per_case, 'calls_per_case': calls_per_case}


# Map benchmark -> latest train recording dir (used to count LLM calls/case
# for the BASELINE; distilled methods get 0 calls when cost is near zero)
TRAIN_REC_PATTERN = {
    'natplan_calendar': 'natural_plan/recordings/*calendar_train_record',
    'natplan_meeting':  'natural_plan/recordings/*meeting_train_record',
    'natplan_trip':     'natural_plan/recordings/*trip_train_record',
    'musr_murder':      'musr/recordings/*murder_train_record',
    'bbh_sports':       'bbh/sports_understanding/recordings/*sports_train_record',
    'bbh_penguins':     'bbh/penguins_in_a_table/recordings/*bbh_penguins_train_record_v2',
    'bbh_geometric':    'bbh/geometric_shapes/recordings/*bbh_geometric_train_record_v2',
    'bbh_date':         'bbh/date_understanding/recordings/*date_train_record_v4',
    'medcalc':          'medcalc/recordings/*medcalc_train_record',
    'finqa':            'finqa/recordings/*finqa_train_record',
    'rulearena_nba':    'rulearena/recordings/*nba_train_record',
    'rulearena_tax':    'rulearena/recordings/*tax_train_record',
    'rulearena_airline': 'rulearena/recordings/*airline_train_record',
}


def find_train_rec(bench):
    pat = TRAIN_REC_PATTERN.get(bench)
    if not pat:
        return None
    matches = sorted((BENCHMARKS_DIR).glob(pat))
    return matches[-1] if matches else None


def collect_all():
    """Collect all val eval metrics for each (benchmark, method) cell."""
    out = {}
    for bench, benchdir in BENCHMARKS.items():
        # For natplan/bbh: expt_name = <sub>_val_<method>; map varies
        natplan_sub = {
            'natplan_calendar': 'cal_val', 'natplan_meeting': 'meet_val',
            'natplan_trip': 'trip_val', 'natplan_calendar2': 'calendar_val',
        }
        bbh_sub = {
            'bbh_sports': 'sports_understanding_val',
            'bbh_penguins': 'penguins_in_a_table_val',
            'bbh_geometric': 'geometric_shapes_val',
            'bbh_date': 'date_understanding_val',
        }
        ru_sub = {'rulearena_nba': 'nba_val', 'rulearena_tax': 'tax_val',
                  'rulearena_airline': 'airline_val'}
        prefixes = []
        if bench in natplan_sub:
            prefixes.append(natplan_sub[bench])
            # Some benchmarks have alt prefixes — just try both
            if bench == 'natplan_calendar':
                prefixes.append('calendar_val')
            elif bench == 'natplan_meeting':
                prefixes.append('meeting_val')
            elif bench == 'natplan_trip':
                prefixes.append('trip_val')
        elif bench in bbh_sub:
            prefixes.append(bbh_sub[bench])
        elif bench in ru_sub:
            prefixes.append(ru_sub[bench])
        elif bench == 'musr_murder':
            prefixes.append('murder_val')
        elif bench == 'medcalc':
            prefixes.append('medcalc_val')
        elif bench == 'finqa':
            prefixes.append('finqa_val')

        cells = {'baseline': None, 'class1': None, 'class1v2': None,
                 'class2': None, 'class3': None}
        train_rec = find_train_rec(bench)
        for pref in prefixes:
            for method in cells:
                csv = find_val_csv(benchdir, f'{pref}_{method}')
                if csv:
                    # Only count calls/case for baseline (uses train rollout);
                    # for distilled methods, infer from cost: if near-zero cost,
                    # calls = 0; else count train rollout (over-estimate)
                    cells[method] = csv_metrics(csv, train_rec if method == 'baseline' else None)
                    # For distilled methods: if cost > 0, also use train rollout
                    if method != 'baseline' and cells[method]['cost_per_case'] > 0.001:
                        m2 = csv_metrics(csv, train_rec)
                        cells[method]['calls_per_case'] = m2['calls_per_case']
        out[bench] = cells
    return out


def plot1_cost_vs_acc(data, outpath):
    """Plot 1: cost vs accuracy per benchmark.

    X = cost per case ($, symlog), Y = val accuracy (%).
    Each benchmark contributes one point per method:
      red ●   baseline
      blue ■  Class 1 (ptool codedistill)
      green ▲ Class 2 (workflow codedistill)
      orange ◆ Class 3 (workflow on induced)
    Dashed line connects the same benchmark's points so the trajectory
    (cheaper / more accurate?) is visible. Up-and-left = better.
    """
    fig, ax = plt.subplots(figsize=(11, 7))
    methods = [
        ('baseline', 'red',     'o', 'baseline (hand workflow)'),
        ('class1v2', 'blue',    's', 'Class 1 (ptool codedistill)'),
        ('class1',   'blue',    's', None),
        ('class2',   'green',   '^', 'Class 2 (workflow codedistill)'),
        ('class3',   'orange',  'D', 'Class 3 (workflow on induced)'),
    ]
    legend_drawn = set()

    for bench, cells in data.items():
        path = []
        for mkey in ['baseline', 'class1v2', 'class1', 'class2', 'class3']:
            cell = cells.get(mkey)
            if cell:
                path.append((cell['cost_per_case'], cell['acc']))
        if len(path) >= 2:
            xs, ys = zip(*path)
            ax.plot(xs, ys, 'k--', alpha=0.2, lw=0.8, zorder=1)

        for mkey, color, marker, label in methods:
            cell = cells.get(mkey)
            if cell is None:
                continue
            lbl = label if label and mkey not in legend_drawn else None
            if lbl:
                legend_drawn.add(mkey)
            ax.scatter(cell['cost_per_case'], cell['acc'],
                       c=color, s=85, marker=marker, label=lbl, zorder=3,
                       edgecolors='black', linewidths=0.5)
            if mkey == 'baseline':
                ax.annotate(bench, (cell['cost_per_case'], cell['acc']),
                            fontsize=7, alpha=0.75,
                            xytext=(5, 3), textcoords='offset points')

    ax.set_xlabel('Cost per case ($)')
    ax.set_ylabel('Val accuracy (%)')
    ax.set_title('Cost vs accuracy per benchmark — baseline → distilled trajectory\n'
                 '(up-and-left = better: more accurate, cheaper)')
    ax.set_xscale('symlog', linthresh=0.001)
    ax.set_ylim(-5, 105)
    ax.legend(loc='lower right')
    ax.grid(alpha=0.3, which='both')
    fig.tight_layout()
    fig.savefig(outpath, dpi=120)
    print(f'wrote {outpath}')


def plot2a_handvs_learned_ptool(data, outpath):
    """Plot 2A — ptool replacement effect.
    Workflow held constant (hand-written). Vary ptool: hand vs learned (Class 1).
    Per benchmark = 1 point.
      X = baseline val acc (hand workflow + hand ptool)
      Y = Class 1 distilled val acc (hand workflow + learned ptool)
    Diagonal = parity. Above diagonal = ptool distillation helped.
    """
    fig, ax = plt.subplots(figsize=(8, 8))
    for bench, cells in data.items():
        b = cells.get('baseline')
        c = cells.get('class1v2') or cells.get('class1')
        if b is None or c is None:
            continue
        ax.scatter(b['acc'], c['acc'], s=100, zorder=3)
        ax.annotate(bench, (b['acc'], c['acc']), fontsize=9,
                    xytext=(6, 6), textcoords='offset points')
    ax.plot([0, 100], [0, 100], 'k--', alpha=0.4, label='parity (no distill effect)')
    ax.set_xlabel('Hand ptool acc (baseline workflow)  %')
    ax.set_ylabel('Learned ptool acc (Class 1 codedistill)  %')
    ax.set_title('Plot 2A: ptool replacement effect\n'
                 '(workflow held constant; hand-written ptool → distilled Python ptool)')
    ax.set_xlim(-5, 105); ax.set_ylim(-5, 105)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(outpath, dpi=120)
    print(f'wrote {outpath}')


def plot2b_handvs_learned_workflow(data, outpath):
    """Plot 2B — workflow replacement effect.
    Per benchmark = 1 point per learned-workflow variant.
      X = baseline val acc (hand workflow + hand ptool)
      Y = learned workflow val acc:
        blue = Class 2 (learned wf + hand ptool)
        red  = Class 3 v2 (learned wf + induced ptool) [where data exists]
    Diagonal = parity.
    """
    fig, ax = plt.subplots(figsize=(8, 8))
    drew_legend = {'class2': False, 'class3': False}
    for bench, cells in data.items():
        b = cells.get('baseline')
        if b is None:
            continue
        c2 = cells.get('class2')
        c3 = cells.get('class3') or cells.get('class3_v2')
        if c2 is not None:
            label = 'Class 2 (learned wf + hand ptool)' if not drew_legend['class2'] else None
            ax.scatter(b['acc'], c2['acc'], s=100, c='tab:blue', zorder=3, label=label)
            drew_legend['class2'] = True
            ax.annotate(bench, (b['acc'], c2['acc']), fontsize=8,
                        xytext=(6, 6), textcoords='offset points', alpha=0.8)
        if c3 is not None:
            label = 'Class 3 (learned wf + induced ptool)' if not drew_legend['class3'] else None
            ax.scatter(b['acc'], c3['acc'], s=120, c='tab:red', marker='^', zorder=3, label=label)
            drew_legend['class3'] = True
            ax.annotate(bench + ' (C3)', (b['acc'], c3['acc']), fontsize=8,
                        xytext=(6, -10), textcoords='offset points', alpha=0.8, color='tab:red')
    ax.plot([0, 100], [0, 100], 'k--', alpha=0.4, label='parity')
    ax.set_xlabel('Hand workflow acc (baseline)  %')
    ax.set_ylabel('Learned workflow acc  %')
    ax.set_title('Plot 2B: workflow replacement effect\n'
                 '(hand workflow → distilled Python workflow; ptool source as colour)')
    ax.set_xlim(-5, 105); ax.set_ylim(-5, 105)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(outpath, dpi=120)
    print(f'wrote {outpath}')


def plot3_5conditions(data, outpath):
    """Plot 3: 5-condition acc comparison per benchmark.

    Conditions:
      1. hand workflow (baseline) — current default
      2. hand ptool + react — NOT collected (would need ReAct conf per bench)
      3. induced ptool + react — collected via codedistill-induced-ptools
      4. learned workflow + hand ptool — Class 2
      5. learned workflow + induced ptool — Class 3 v2
    """
    benches = list(data.keys())
    n = len(benches)
    fig, ax = plt.subplots(figsize=(max(12, n * 1.0), 6))

    width = 0.16
    x = list(range(n))
    method_labels = ['1. hand workflow (baseline)',
                     '2. hand ptool + react',
                     '3. induced ptool + react',
                     '4. learned wf + hand ptool',
                     '5. learned wf + induced ptool']
    for j, key in enumerate(['baseline', 'react_handptool', 'class3', 'class2', 'class3_v2']):
        vals = []
        for bench in benches:
            c = data[bench].get(key) if key in data[bench] else None
            vals.append(c['acc'] if c else 0)
        offsets = [xi + (j - 2) * width for xi in x]
        ax.bar(offsets, vals, width=width, label=method_labels[j])

    ax.set_xticks(x)
    ax.set_xticklabels(benches, rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('Val accuracy %')
    ax.set_title('5-condition comparison: workflow source × ptool source')
    ax.legend(fontsize=8, loc='upper right')
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    fig.savefig(outpath, dpi=120)
    print(f'wrote {outpath}')


def main():
    out_dir = ROOT / 'docs' / 'plots'
    out_dir.mkdir(exist_ok=True)
    data = collect_all()

    # Print collected data for diagnostics
    print("=== Collected metrics ===")
    for bench, cells in data.items():
        line = f'{bench}: '
        for method, m in cells.items():
            if m is None: continue
            line += f' {method}=acc{m["acc"]:.0f}%/${m["cost"]:.3f}/{m["calls_per_case"]:.1f}calls'
        print(line)

    plot1_cost_vs_acc(data, out_dir / 'plot1_cost_vs_acc.png')
    plot2a_handvs_learned_ptool(data, out_dir / 'plot2a_ptool_replacement.png')
    plot2b_handvs_learned_workflow(data, out_dir / 'plot2b_workflow_replacement.png')
    plot3_5conditions(data, out_dir / 'plot3_5_conditions.png')


if __name__ == '__main__':
    main()
