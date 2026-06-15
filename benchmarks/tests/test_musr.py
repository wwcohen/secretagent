"""Lightweight pytest suite for benchmarks/musr/.

Modeled on tests/test_natural_plan.py: import a subtask's ptools, bind the
decomposed-workflow sub-tools to 'simulate', run the hand-designed
``answer_question_workflow`` on a real dataset example, and check it produces
a 0-based answer index. One parametrized case per subtask (murder, object,
team).

MuSR has no per-subtask evaluator module — ``expected_output`` is simply the
0-based index of the correct choice — so the no-API test guards dataset
integrity (the narrative/question/choices/index contract the workflow relies
on) instead of feeding a golden answer through an evaluator.

The workflows take the narrative as an explicit argument, so they do not
depend on the module-global ``_REACT_STATE`` (that is only used by the
alternative ReAct entry points) and can be called directly.
"""

import json
from pathlib import Path

import pytest

from conftest import CI_TEST_MODEL, load_benchmark_modules, needs_api_key
from secretagent import config

MUSR_DIR = Path(__file__).resolve().parent.parent / "musr"

# Per subtask: the @interface sub-tools that ``answer_question_workflow``
# calls and that must be bound before it runs.
TASKS = {
    "murder": [
        "extract_suspects_and_evidence",
        "verify_alibis",
        "deduce_murderer",
        "extract_index",
    ],
    "object": [
        "extract_movements",
        "extract_discoveries",
        "infer_belief",
        "extract_index",
    ],
    "team": [
        "extract_team_requirements",
        "score_team_assignments",
        "extract_index",
    ],
}


def _valid_cases(task):
    """Parse the subtask's valid split into a list of cases."""
    path = MUSR_DIR / task / "data" / "valid.json"
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("task", ["murder", "object", "team"])
def test_dataset_wellformed(task):
    """Each subtask's valid split has well-formed multiple-choice cases.

    No API key needed. MuSR has no evaluator to score a golden through, so
    this pins the data contract the workflow relies on: input_args is
    (narrative, question, choices) and expected_output is a valid 0-based
    index into choices.
    """
    cases = _valid_cases(task)
    assert cases, f"{task}/data/valid.json has no cases"
    for case in cases[:5]:
        narrative, question, choices = case["input_args"]
        assert isinstance(narrative, str) and narrative.strip()
        assert isinstance(question, str) and question.strip()
        assert isinstance(choices, list) and len(choices) >= 2
        idx = case["expected_output"]
        assert isinstance(idx, int) and 0 <= idx < len(choices)


@needs_api_key
@pytest.mark.parametrize("task", ["murder", "object", "team"])
def test_workflow(task, tmp_path):
    """Bind the sub-tools to 'simulate', run the workflow, get an answer index."""
    (ptools,) = load_benchmark_modules(MUSR_DIR / task, "ptools")
    for tool in TASKS[task]:
        getattr(ptools, tool).implement_via("simulate")

    narrative, question, choices = _valid_cases(task)[0]["input_args"]
    with config.configuration(
        llm={"model": CI_TEST_MODEL},
        cachier={"cache_dir": str(tmp_path / "llm_cache")},  # keep cache out of cwd
    ):
        result = ptools.answer_question_workflow(narrative, question, choices)

    assert isinstance(result, int)