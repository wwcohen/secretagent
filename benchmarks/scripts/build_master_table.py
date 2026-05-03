"""Cleaner master comparison.

Columns kept (drop empty / sparse):
  baseline_full   : my fresh DS-V3.1 baseline (val_full)
  archived_workflow: 1 archived workflow per bench (filtered to DS-V3*)
  v1_baseline     : from v1 doc text
  v1_ptool        : from v1 doc text (ptool codedistill)
  v1_e2e          : from v1 doc text (e2e codedistill)
  v1_oracle       : from v1 doc text (only rulearena_airline)
  c1_v2           : my class 1 v2 (mostly mini n=30)
  c1_v4           : my class 1 v4 (full n=full)
  c2_v2           : my class 2 v2 (mostly mini)
  c2_v4           : my class 2 v4 (full)
  c3_v4           : my class 3 v4 (full)

Empty cells:
  RUN  : currently being produced by a running master (musr_obj/team or tabmwp)
  —    : not run, not planned
"""
import re
import pandas as pd

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
    name = (str(row.get('expt_name') or row.get('name') or '')).lower()
    scope = row['scope']
    if 'baseline' in name and scope == 'val_full': return 'baseline_full'
    # Class 1
    if 'class1v4' in name or 'class1_v4' in name: return 'c1_v4'
    if 'class1v2' in name: return 'c1_v2'
    # Class 2
    if 'class2v4' in name: return 'c2_v4'
    if re.search(r'class2(?!v\d)', name) and scope.startswith('val'): return 'c2_v2'
    # Class 3
    if 'class3v4' in name: return 'c3_v4'
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
             'medcalc','finqa',
             'rulearena_nba','rulearena_tax','rulearena_airline',
             'tabmwp']
COL_ORDER = ['baseline_full','archived_workflow',
             'v1_baseline','v1_ptool','v1_e2e',
             'c1_v2','c1_v4','c2_v2','c2_v4','c3_v4']

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

# Mark RUN cells (active masters' planned outputs)
RUN_MAP = {
    'musr_object':  ['c1_v4','c2_v4','c3_v4'],     # musr master 7010
    'musr_team':    ['c1_v4','c2_v4','c3_v4'],     # musr master 7010
    'tabmwp':       ['baseline_full','c1_v4','c2_v4','c3_v4'],  # tabmwp master 8536
    'medcalc':      ['c2_v4'],   # manually kicked off
    'finqa':        ['c2_v4','c3_v4'],  # fill_v2 master
    'rulearena_nba': ['c2_v4'],
    'rulearena_tax': ['c2_v4'],
    'natplan_calendar': ['c3_v4'],   # fill_v2
    # c1_v4 holes: medcalc/geometric/date/rulearena had 0 ENABLED → leave as — (= baseline)
}

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
print("=== N (val size) ===")
print(n_fmt.to_string())

with open('/tmp/master_table.md','w') as f:
    f.write('# Master comparison — all classes × all versions × all benchmarks\n\n')
    f.write('## What each `vN` means\n\n')
    f.write('All versions are MY own runs, not someone else\'s. They are snapshots of the codedistill pipeline as it evolved over April 2026.\n\n')
    f.write('| Version | Date | Key behaviors |\n')
    f.write('|---|---|---|\n')
    f.write('| **v1** | early April | Original. `only_correct=False` (learned from wrong rollouts too). Gate: `train_wrong_rate <= 10%`, no held-out val split. `_format_traces` showed only the local ptool i/o (no top-level task context). `Learner.validate()` re-ran `fit()` 3× per ptool. Numbers preserved in [v1 doc](code_distillation_results.md). |\n')
    f.write('| **v2** | 2026-04-28 (1st rerun) | First val gate. 80/20 case split inside the learner, `val_wrong_rate <= 5%` gate, `only_correct=True`. Top-level task i/o injected into `_format_traces`. Single-fit (skip Learner.validate re-fit). Round-1 early stop at <10%. Case-output truncation (`_truncate_repr`). Mostly run at mini sizes (n=30 train, n=30 val) so numbers are sample-noisy. |\n')
    f.write('| **v3** | 2026-04-28 (2nd) | Mid-iteration snapshot — mostly mirrored v2 with bug fixes (e.g. `\'backoff\': \'true\'`→`True`, pydantic-ai recursion fix). Many cells stayed empty because the rerun was abandoned in favor of v4. Effectively deprecated. |\n')
    f.write('| **v4** | 2026-04-29 (full-size) | Full-size rerun. `max_wrong_rate=0.20` (relaxed from v2\'s 0.05). Train/val recordings at full benchmark sizes (n=43-100 instead of 30-50). Class 2 with `backoff=simulate` (LLM fallback when generated code returns None). Class 3 uses `_REACT_STATE` for musr induced-ptool state injection. Same fit-time 80/20 holdout as v2. **This is the headline version for the v2 doc.** |\n\n')
    f.write('Legend for table cells:\n')
    f.write('- **baseline_full**: my fresh DS-V3.1 baseline (full-size val)\n')
    f.write('- **archived_workflow**: archived workflow run from `benchmarks/<bench>/results/` or `benchmarks/results/<bench>/`, filtered to DS-V3* model only\n')
    f.write('- **v1_baseline / v1_ptool / v1_e2e**: numbers from [v1 doc](code_distillation_results.md)\n')
    f.write('- **c1_vN**: Class 1 (ptool codedistill) version N — replaces individual simulate ptools with Python\n')
    f.write('- **c2_vN**: Class 2 (workflow distill on hand-written tools) version N — replaces top-level workflow with Python that calls existing ptools\n')
    f.write('- **c3_v4**: Class 3 (workflow distill on LLM-induced ptools) v4\n\n')
    f.write('Cells marked `🏃` are currently being produced by a running master:\n')
    f.write('  - musr_object / musr_team class 1/2/3 v4 → `/tmp/musr_obj_team_full.sh` (PID 7010)\n')
    f.write('  - tabmwp class 1/2/3 v4 → `/tmp/tabmwp_full.sh` (PID 8536)\n')
    f.write('  - musr_murder class 2 v4 was queued in fill master (now killed), needs explicit re-launch\n\n')
    f.write('Cells marked `—` are not planned. Empty class 1/3 columns (v1, v3) and class 2 v3 dropped entirely.\n\n')
    f.write('## Accuracy (%)\n\n')
    f.write(acc_fmt.to_markdown())
    f.write('\n\n## Cost (total USD over val set)\n\n')
    f.write(cost_fmt.to_markdown())
    f.write('\n\n## N (val size)\n\n')
    f.write(n_fmt.to_markdown())
print('\nWrote /tmp/master_table.md')
