"""No-API tests for the repo-root basics runner (secretagent.cli.basics).

Covers manifest discovery and subprocess command assembly -- the parts
that must stay faithful to each task's Makefile -- without spending any
API budget.
"""

from secretagent.cli import basics


def _task(task_id):
    (t,) = [t for t in basics._discover([task_id])]
    return t


def test_discovers_all_seven_tasks():
    ids = {t.id for t in basics._discover(None)}
    expected = {
        'bbh/date_understanding', 'bbh/geometric_shapes',
        'bbh/penguins_in_a_table', 'bbh/sports_understanding',
        'natural_plan/calendar', 'natural_plan/meeting', 'natural_plan/trip',
    }
    assert expected <= ids
    # every task exposes the five basic strategies
    for t in basics._discover(None):
        assert {'unstructured_baseline', 'structured_baseline',
                'workflow', 'pot', 'react'} <= set(t.strategies)


def test_filter_by_task_id():
    tasks = basics._discover(['bbh/penguins_in_a_table'])
    assert [t.id for t in tasks] == ['bbh/penguins_in_a_table']


def test_bbh_command_has_no_evaluator_and_routes_results(tmp_path):
    t = _task('bbh/penguins_in_a_table')
    out = tmp_path / 'structured_baseline'
    cmd = basics._build_command(
        t, 'structured_baseline', 'gemini/x', out, n=5, extra=[])
    assert '--evaluator' not in cmd  # bbh uses the default ExactMatch
    assert str(t.config) in cmd
    assert 'ptools.answer_penguin_question.method=simulate' in cmd
    assert 'evaluate.expt_name=structured_baseline' in cmd
    assert 'llm.model=gemini/x' in cmd
    assert f'evaluate.result_dir={out}' in cmd
    assert 'dataset.n=5' in cmd


def test_natural_plan_command_includes_evaluator_and_tools():
    t = _task('natural_plan/trip')
    cmd = basics._build_command(
        t, 'react', 'gemini/x', t.dir / 'react', n=None, extra=[])
    assert cmd[cmd.index('--evaluator') + 1] == 'evaluator.TripEvaluator'
    assert 'ptools.trip_planning.method=simulate_pydantic' in cmd
    assert any(c.startswith('ptools.trip_planning.tools=[') for c in cmd)
    assert not any(c.startswith('dataset.n=') for c in cmd)  # n=None -> omitted


def test_user_extra_overrides_come_last():
    t = _task('bbh/sports_understanding')
    extra = ['llm.model=override/me', 'dataset.split=test']
    cmd = basics._build_command(
        t, 'workflow', 'gemini/x', t.dir / 'workflow', n=2, extra=extra)
    # user args are appended after the driver's own, so they win
    assert cmd[-2:] == extra