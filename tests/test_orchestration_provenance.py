"""Tests for orchestration learner provenance helpers."""

import json

from secretagent import config
from secretagent.orchestrate.improve import IterationRecord, _save_running_report


def test_save_running_report_writes_config_snapshot(tmp_path):
    output_dir = tmp_path / 'orch_run'
    output_dir.mkdir()

    with config.configuration(
        llm={'model': 'test-model'},
        evaluate={'result_dir': str(tmp_path), 'expt_name': 'demo'},
    ):
        iterations = [
            IterationRecord(
                iteration=0,
                train_accuracy=0.5,
                train_cost=0.01,
                kept=True,
                train_result_dir='/tmp/train_run',
                eval_result_dir='/tmp/eval_run',
            )
        ]
        _save_running_report(
            output_dir=output_dir,
            iterations=iterations,
            best_accuracy=0.5,
            best_source='def f() -> int:\n    return 1',
            best_config_overrides=['llm.model=test-model'],
            total_supervisor_cost=0.12,
        )

    report = json.loads((output_dir / 'report.json').read_text())
    assert report['config_snapshot_path'] == 'config.yaml'
    assert report['iterations'][0]['train_result_dir'] == '/tmp/train_run'
    assert report['iterations'][0]['eval_result_dir'] == '/tmp/eval_run'

    saved_cfg = (output_dir / 'config.yaml').read_text()
    assert 'llm:' in saved_cfg
    assert 'test-model' in saved_cfg
