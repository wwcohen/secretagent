"""Master comparison table builder.

Columns:
  baseline_full   : fresh DS-V3.1 baseline (val_full), no distill
  archived_workflow: 1 archived workflow per bench (filtered to DS-V3*)
  v1_baseline / v1_ptool / v1_e2e: legacy v1 numbers from doc
  c1_v2           : legacy mini Class 1
  c1_opus / c1_gemini : Class 1 (ptool codedistill); suffix = learner LLM
  c2_v2           : legacy mini Class 2
  c2_opus / c2_gemini : Class 2 (workflow distill on hand-written ptools)
  c3_opus / c3_gemini : Class 3 (workflow distill on **induced** ptools)
  orch_existing_workflow / orch_seed_from_ptools:
      held-out test-set orchestrator_learner runs
  orch_induced_seed_ptools:
      held-out test-set orchestrator_learner run with induced seed ptools

Empty cell — = no run for that combination.
Test/cache results are excluded except the explicitly labeled orchestrator
test columns.
"""
import re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_csv('/tmp/all_vals_scan.csv')

# v1 numbers (extracted from docs/code_distillation_results.md, lines 150-161)
V1 = {
    'natplan_calendar':   {'baseline':0.54,'ptool':0.84,'e2e':0.90,'baseline_cost':0.19,'ptool_cost':0.09,'e2e_cost':0.0},
    'natplan_meeting':    {'baseline':0.0, 'ptool':None,'e2e':0.0, 'baseline_cost':0.17,'ptool_cost':None,'e2e_cost':0.0},
    'natplan_trip':       {'baseline':None,'ptool':None,'e2e':None,'baseline_cost':None,'ptool_cost':None,'e2e_cost':None},
    'musr_murder':        {'baseline':0.70,'ptool':0.70,'e2e':0.0, 'baseline_cost':0.81,'ptool_cost':0.79,'e2e_cost':0.0},
    'musr_object':        {'baseline':None,'ptool':None,'e2e':None,'baseline_cost':None,'ptool_cost':None,'e2e_cost':None},
    'musr_team':          {'baseline':None,'ptool':None,'e2e':None,'baseline_cost':None,'ptool_cost':None,'e2e_cost':None},
    'bbh_sports_understanding': {'baseline':0.97,'ptool':0.97,'e2e':0.63,'baseline_cost':0.10,'ptool_cost':0.09,'e2e_cost':0.0},
    'bbh_penguins_in_a_table':  {'baseline':0.70,'ptool':0.53,'e2e':0.58,'baseline_cost':0.04,'ptool_cost':0.03,'e2e_cost':0.0},
    'bbh_geometric_shapes':     {'baseline':0.75,'ptool':0.73,'e2e':None,'baseline_cost':1.64,'ptool_cost':0.87,'e2e_cost':None},
    'bbh_date_understanding':   {'baseline':0.39,'ptool':None,'e2e':0.59,'baseline_cost':0.29,'ptool_cost':None,'e2e_cost':0.0},
    'medcalc':            {'baseline':0.38,'ptool':0.44,'e2e':0.42,'baseline_cost':0.13,'ptool_cost':0.01,'e2e_cost':0.0},
    'finqa':              {'baseline':0.62,'ptool':0.61,'e2e':0.35,'baseline_cost':0.12,'ptool_cost':0.10,'e2e_cost':0.0},
    'rulearena_nba':      {'baseline':None,'ptool':None,'e2e':None,'baseline_cost':None,'ptool_cost':None,'e2e_cost':None},
    'rulearena_tax':      {'baseline':None,'ptool':None,'e2e':None,'baseline_cost':None,'ptool_cost':None,'e2e_cost':None},
    'rulearena_airline':  {'baseline':0.90,'ptool':None,'e2e':None,'baseline_cost':0.46,'ptool_cost':None,'e2e_cost':None,'oracle':1.0,'oracle_cost':0.0},
    'tabmwp':             {'baseline':None,'ptool':None,'e2e':None,'baseline_cost':None,'ptool_cost':None,'e2e_cost':None},
}

def sub_bench(row):
    explicit = row.get('sub_bench')
    if pd.notna(explicit) and str(explicit).strip():
        return str(explicit).strip()
    bench = row['bench']
    name = (str(row.get('expt_name') or row.get('name') or '')).lower()
    path = str(row.get('path') or '').lower()
    split = str(row.get('split') or '').lower()
    if bench == 'natural_plan':
        for sub in ('calendar','meeting','trip'):
            if sub in name or sub in path or sub in split: return f'natplan_{sub}'
    if bench == 'rulearena':
        for sub in ('airline','nba','tax'):
            if sub in name or sub in path: return f'rulearena_{sub}'
    if bench == 'musr':
        for sub in ('object','team','murder'):
            if sub in name or sub in path or sub in split: return f'musr_{sub}'
    return bench.replace('bbh/','bbh_')

df['sub_bench'] = df.apply(sub_bench, axis=1)

def categorize(row):
    scope = row['scope']
    dir_name = str(row.get('name') or '').lower()
    name = (str(row.get('expt_name') or '') or dir_name).lower()
    # Orchestrator rows are held-out test-set results and are explicitly
    # included as test-labeled columns. Other test/cache rows remain excluded.
    if scope == 'orchestrator_test':
        if 'orch_existing_workflow' in dir_name:
            return 'orch_existing_workflow'
        if 'orch_seed_from_ptools' in dir_name:
            return 'orch_seed_from_ptools'
        return None
    if scope == 'orchestrator_induced_test':
        if 'orch_induced_seed_ptools' in dir_name:
            return 'orch_induced_seed_ptools'
        return None
    if 'test' in scope: return None
    if name.endswith('_cache'): return None  # extra guard
    if 'baseline' in name and scope == 'val_full': return 'baseline_full'
    # Class 1 (ptool codedistill)
    if 'class1_gemini' in name: return 'c1_gemini'
    if 'class1_opus' in name: return 'c1_opus'
    if 'class1v2' in name: return 'c1_v2'
    # Class 2 (workflow distill on hand-written ptools)
    if 'class2_gemini' in name: return 'c2_gemini'
    if 'class2_opus' in name: return 'c2_opus'
    if re.search(r'class2(?!v\d|_(opus|gemini))', name) and scope.startswith('val'): return 'c2_v2'
    # Class 3 (workflow distill on induced ptools)
    if 'class3_gemini' in name: return 'c3_gemini'
    if 'class3_opus' in name: return 'c3_opus'
    # archived: pick workflow only (DS-V3 model). Accept "workflow" or "<sub>_workflow"
    if scope == 'archived_inproject':
        is_wf = name == 'workflow' or re.fullmatch(r'(murder|object|team|calendar|meeting|trip)_workflow', name)
        if is_wf:
            m = str(row.get('model') or '')
            if 'deepseek-ai/DeepSeek-V3' in m: return 'archived_workflow'
    return None

df['cat'] = df.apply(categorize, axis=1)
df = df[df['cat'].notna()]
df_best = (df.sort_values(['sub_bench','cat','n'], ascending=[True,True,False])
             .drop_duplicates(['sub_bench','cat'], keep='first'))

ROW_ORDER = ['natplan_calendar','natplan_meeting','natplan_trip',
             'musr_murder','musr_object','musr_team',
             'bbh_sports_understanding','bbh_penguins_in_a_table','bbh_geometric_shapes','bbh_date_understanding',
             'medcalc_formulas','medcalc_rules','finqa',
             'rulearena_nba','rulearena_tax','rulearena_airline',
             'tabmwp']
COL_ORDER = ['baseline_full','archived_workflow',
             'v1_baseline','v1_ptool','v1_e2e',
             'c1_v2','c1_opus','c1_gemini','c2_v2','c2_opus','c2_gemini','c3_opus','c3_gemini',
             'orch_existing_workflow','orch_seed_from_ptools','orch_induced_seed_ptools']

acc = df_best.pivot(index='sub_bench', columns='cat', values='acc').reindex(index=ROW_ORDER)
cost = df_best.pivot(index='sub_bench', columns='cat', values='cost').reindex(index=ROW_ORDER)
n = df_best.pivot(index='sub_bench', columns='cat', values='n').reindex(index=ROW_ORDER)

# inject v1_*
for sub in ROW_ORDER:
    v = V1.get(sub, {})
    if v.get('baseline') is not None:
        acc.loc[sub,'v1_baseline'] = v['baseline']; cost.loc[sub,'v1_baseline'] = v.get('baseline_cost')
    if v.get('ptool') is not None:
        acc.loc[sub,'v1_ptool'] = v['ptool']; cost.loc[sub,'v1_ptool'] = v.get('ptool_cost')
    if v.get('e2e') is not None:
        acc.loc[sub,'v1_e2e'] = v['e2e']; cost.loc[sub,'v1_e2e'] = v.get('e2e_cost')
    # v1_oracle dropped (only rulearena_airline had it; user requested removal)

acc = acc.reindex(columns=COL_ORDER)
cost = cost.reindex(columns=COL_ORDER)
n = n.reindex(columns=COL_ORDER)

# Drop columns that are entirely NaN
keep_cols = [c for c in COL_ORDER if not acc[c].isna().all()]
acc = acc[keep_cols]; cost = cost[keep_cols]; n = n[keep_cols]

# Mark RUN cells (active masters' planned outputs).
# All opus/gemini masters have completed; left empty.
RUN_MAP = {}

def fmt_acc(sub, col, v):
    if pd.notna(v):
        return f'{int(round(v*100)):3d}'
    if col in RUN_MAP.get(sub, []):
        return ' 🏃'
    return '  —'

def fmt_cost(sub, col, v):
    if pd.notna(v):
        if v < 0.005: return '$0   '
        if v < 0.10: return f'${v:.2f}'
        return f'${v:.1f} '
    if col in RUN_MAP.get(sub, []):
        return ' 🏃  '
    return '  —  '

def fmt_n(sub, col, v):
    if pd.notna(v): return str(int(v))
    if col in RUN_MAP.get(sub, []): return '🏃'
    return '—'

acc_fmt = pd.DataFrame({c: [fmt_acc(r,c,acc.loc[r,c]) for r in acc.index] for c in acc.columns}, index=acc.index)
cost_fmt = pd.DataFrame({c: [fmt_cost(r,c,cost.loc[r,c]) for r in cost.index] for c in cost.columns}, index=cost.index)
n_fmt = pd.DataFrame({c: [fmt_n(r,c,n.loc[r,c]) for r in n.index] for c in n.columns}, index=n.index)

print("=== ACCURACY (%) ===")
print(acc_fmt.to_string())
print()
print("=== COST_TOTAL (USD) ===")
print(cost_fmt.to_string())
print()
print("=== N ===")
print(n_fmt.to_string())

out_text = []
out_text.append('# Master comparison — all classes × learners × all benchmarks\n\n')
out_text.append('There is one version of the codedistill pipeline. Cells are\n')
out_text.append('distinguished by **which class of distillation** and **which LLM\n')
out_text.append('was the learner** (Opus 4.6 vs Gemini 3.1 Pro Preview).\n\n')
out_text.append('Legend for table cells:\n')
out_text.append('- **baseline_full**: fresh DS-V3.1 baseline (full-size val), no distillation\n')
out_text.append('- **archived_workflow**: archived hand-written workflow run filtered to DS-V3*\n')
out_text.append('- **v1_baseline / v1_ptool / v1_e2e**: legacy numbers from [v1 doc](code_distillation_results.md)\n')
out_text.append('- **c1_v2**: legacy Class 1 (mini sizes); kept for traceability\n')
out_text.append('- **c1_opus / c1_gemini**: Class 1 = ptool codedistill (replace each simulate ptool with Python). Suffix is the learner LLM.\n')
out_text.append('- **c2_opus / c2_gemini**: Class 2 = distill workflow (rewrite the top-level workflow to call hand-written ptools). Suffix is the learner LLM.\n')
out_text.append("- **c3_opus / c3_gemini**: Class 3 = distill workflow with **induced** ptools (same as Class 2 but the ptool toolbox comes from the prof's LLM-discovered induced_ptools seed=42 modules). Suffix is the learner LLM.\n")
out_text.append('- **orch_existing_workflow**: held-out **test** result for hand workflow + orchestrator-improved ptools.\n')
out_text.append('- **orch_seed_from_ptools**: held-out **test** result for orchestrator-generated workflow + orchestrator-improved ptools.\n')
out_text.append('- **orch_induced_seed_ptools**: held-out **test** result for orchestrator-generated workflow + induced seed ptools.\n\n')
out_text.append('`medcalc` is always split into `medcalc_formulas` and `medcalc_rules`; overall medcalc rows are not used when category-level extraction is available.\n\n')
out_text.append('Cells marked `—` had no run for that combination (no distill or 0 ENABLED ptools).\n\n')
out_text.append('## Accuracy (%)\n\n')
out_text.append(acc_fmt.to_markdown())
out_text.append('\n\n## Cost (total USD over split)\n\n')
out_text.append(cost_fmt.to_markdown())
out_text.append('\n\n## N\n\n')
out_text.append(n_fmt.to_markdown())
rendered = ''.join(out_text)

for out_path in [Path('/tmp/master_table.md'), ROOT.parent / 'paper' / 'results' / 'master_table.md']:
    out_path.write_text(rendered)
print('\nWrote /tmp/master_table.md')
print(f'Wrote {ROOT.parent / "paper" / "results" / "master_table.md"}')
