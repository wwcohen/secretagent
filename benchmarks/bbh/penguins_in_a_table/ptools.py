"""Tools for the penguins_in_a_table benchmark.

The task: given a question about a table of penguins (with possible
table modifications), answer a multiple-choice question about the
resulting table.

Derived from the program trace mock in penguins_in_a_table.py
(doctest-prompting project).
"""

from pydantic import BaseModel, Field

from secretagent.core import interface, implement_via


class Option(BaseModel):
    """A single labeled multiple-choice answer."""
    letter: str = Field(..., description="Single-letter label, e.g. 'A'.")
    answer_text: str = Field(..., description="The choice text, e.g. 'Vincent'.")


class TableQuery(BaseModel):
    """A penguins-in-a-table question parsed into its components."""
    table: list[list[str]] = Field(
        ..., description="Header row plus data rows, each row a list of cell strings.")
    actions: list[str] = Field(
        ..., description="Natural-language modifications to apply to the table; may be empty.")
    question: str = Field(..., description="The question text to answer about the table.")
    options: list[Option] = Field(..., description="Labeled answer options.")


# ── sub-tools ────────────────────────────────────────────────────────────────

@interface
def analyze_input(input_str: str) -> TableQuery:
    """Accept an input string and extract the table, modifications, question,
    and labeled answer options as a structured TableQuery.
    """
    ...

@interface
def table_operation(table: list[list[str]], action: str) -> list[list[str]]:
    """Take a table and an action to perform on that table, and return a copy
    of the table after performing the action.

    Examples of actions: 'delete the penguin named Bernard',
    'sort by age', 'add a penguin named Dave, age 3, height 55, weight 10'.
    """
    ...

@interface
def answer_question(table: list[list[str]], question: str) -> str:
    """Take a table and a question about information in that table, and return
    the answer to that question as a plain string.
    """
    ...

@interface
def choose_response(answer: str, options: list[Option]) -> Option:
    """Pick the multiple-choice Option whose answer_text best matches the
    given free-form answer string.
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
    q = analyze_input(input_str)
    table = q.table
    for action in q.actions:
        table = table_operation(table, action)
    answer = answer_question(table, q.question)
    chosen = choose_response(answer, q.options)
    return f'({chosen.letter})'

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
