"""Tools for the penguins_in_a_table benchmark.

The task: given a question about a table of penguins (with possible
table modifications), answer a multiple-choice question about the
resulting table.

Derived from the program trace mock in penguins_in_a_table.py
(doctest-prompting project).
"""

from typing import Any, List, Tuple

from secretagent.core import interface, implement_via
from secretagent.evaluate import Evaluator


class PenguinsEvaluator(Evaluator):
    def compare_predictions(self, predicted_output, expected_output) -> dict[str, Any]:
        def normalize(s):
            return str(s).strip().strip('()')
        return dict(correct=float(normalize(predicted_output) == normalize(expected_output)))

# ── sub-tools ────────────────────────────────────────────────────────────────

@interface
def analyze_input(input_str: str) -> Tuple[List[List[str]], List[str], str, List[Tuple[str, str]]]:
    """Accept an input and extract an information table, one or more actions
    being performed on the table, a question being asked about the table,
    and the possible answers to the question.

    Returns (table, actions, question, options) where:
      - table is a list of rows, each row a list of string cell values
        (first row is the header)
      - actions is a list of natural-language action descriptions to apply
        to the table (may be empty)
      - question is the question string
      - options is a list of (letter, answer_text) pairs,
        e.g. [('A', '1'), ('B', '2'), ...]
    """
    ...

@interface
def table_operation(table: List[List[str]], action: str) -> List[List[str]]:
    """Take a table and an action to perform on that table, and return a copy
    of the table after performing the action.

    Examples of actions: 'delete the penguin named Bernard',
    'sort by age', 'add a penguin named Dave, age 3, height 55, weight 10'.
    """
    ...

@interface
def answer_question(table: List[List[str]], question: str) -> str:
    """Take a table and a question about information in that table, and return
    the answer to that question as a plain string.
    """
    ...

@interface
def choose_response(answer: str, options: List[Tuple[str, str]]) -> Tuple[str, str]:
    """Take an answer to a question and a list of multiple-choice options and
    return the multiple-choice option best matching the answer.

    Returns the (letter, answer_text) pair, e.g. ('A', '1').
    """
    ...

# ── top-level interface ───────────────────────────────────────────────────────

@interface
def answer_penguin_question(question: str) -> str:
    """Given a penguins-in-a-table multiple-choice question, return the correct
    option label, e.g. '(A)'.

    The input includes the table, any modifications to apply, the question
    text, and labeled answer options.
    """
    ...

@interface
def answer_penguin_question_orchestrated(input_str: str) -> str:
    """Given a penguins-in-a-table multiple-choice question, return the correct
    option label, e.g. '(A)'.
    """
    ...

@interface
def react_answer_penguin_question(question: str) -> str:
    """Given a penguins-in-a-table multiple-choice question, return a freeform
    answer string. Intended to be bound via simulate_pydantic with the sub-tools
    as the tool list (ReAct); its output is post-processed by
    extract_option_letter in penguins_react_workflow.
    """
    ...


# ── hand-coded workflow ───────────────────────────────────────────────────────

def penguins_workflow(input_str: str) -> str:
    """Hand-coded workflow implementing answer_penguin_question.

    To use:
        ptools.answer_penguin_question.method=direct
        ptools.answer_penguin_question.fn=ptools.penguins_workflow
    """
    table, actions, question, options = analyze_input(input_str)
    for action in actions:
        table = table_operation(table, action)
    answer = answer_question(table, question)
    letter, _ = choose_response(answer, options)
    return f'({letter})'

# ── zero-shot unstructured workflow ──────────────────────────────────────────

@implement_via('prompt_llm', prompt_template_file='prompt_templates/zeroshot.txt')
def zeroshot_answer_penguin_question(question: str) -> str:
    ...

@implement_via('simulate')
def extract_option_letter(llm_output: str) -> str:
    """Given raw LLM output, extract and return the multiple-choice letter
    in parentheses, e.g. '(A)'.
    """
    ...

def zeroshot_unstructured_workflow(input_str: str) -> str:
    """Workflow for zero-shot prompt with letter extraction.

    To use:
        ptools.answer_penguin_question.method=direct
        ptools.answer_penguin_question.fn=ptools.zeroshot_unstructured_workflow
    """
    llm_output = zeroshot_answer_penguin_question(input_str)
    return extract_option_letter(llm_output)


def penguins_react_workflow(input_str: str) -> str:
    """Workflow that runs ReAct over the sub-tools and extracts the option
    letter from its freeform final answer.

    To use:
        ptools.answer_penguin_question.method=direct
        ptools.answer_penguin_question.fn=ptools.penguins_react_workflow
        ptools.react_answer_penguin_question.method=simulate_pydantic
        ptools.react_answer_penguin_question.tools=[...]
    """
    react_answer = react_answer_penguin_question(input_str)
    return extract_option_letter(react_answer)
