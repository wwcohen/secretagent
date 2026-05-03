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

    CRITICAL EXTRACTION RULES:
    1. Initial Table Only: The extracted `table` must ONLY contain the initial rows described at the beginning. Do NOT include items that are added later via actions.
    2. Distractor Tables: Often, a second table (e.g., giraffes) is introduced. If the question specifically asks about the original entities (e.g., penguins), this second table is a DISTRACTOR — completely ignore it and do not add any action for it. ONLY if the question specifically asks about the new entities should you add an action to "replace the current table with the new table: ...".

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
    """Take a table (provided as a list of lists where the first list is the header) and a question about information in that table, and return the answer as a plain string.
    
    IMPORTANT: 
    - If the question asks for a count (e.g. "how many animals"), count the number of data rows (exclude the header row) and return just the number.
    - If asked for an average, median, or sum, compute it accurately based on the data rows.
    """
    ...

@interface
def choose_response(answer: str, options: List[Tuple[str, str]]) -> Tuple[str, str]:
    """Take an answer to a question and a list of multiple-choice options and
    return the multiple-choice option best matching the answer.

    IMPORTANT: If the answer does not match any of the options even partially, return ('None', 'None'). Do not guess randomly.

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
    try:
        table, actions, question, options = analyze_input(input_str)
        for action in actions:
            table = table_operation(table, action)
        answer = answer_question(table, question)
        res = choose_response(answer, options)
        
        valid_letters = {str(opt[0]).strip().strip('()').upper() for opt in options}
        
        # Verify choose_response gave a valid, structured response
        if res is not None and isinstance(res, (list, tuple)) and len(res) == 2:
            letter = str(res[0]).strip().strip('()').upper()
            if letter in valid_letters and letter != 'NONE':
                return f'({letter})'
                
        # Fallback if choose_response returns None or 'None' but we have a valid answer
        if answer is not None and str(answer).strip().lower() != 'none':
            ans_str = str(answer).strip().lower()
            for opt_letter, text in options:
                if str(text).strip().lower() == ans_str:
                    return f'({opt_letter})'
                    
        return zeroshot_unstructured_workflow(input_str)
    except Exception:
        # Final fallback for any other exceptions (like unpack errors or extraction failures)
        return zeroshot_unstructured_workflow(input_str)

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