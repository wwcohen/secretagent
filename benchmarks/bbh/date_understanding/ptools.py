"""Tools for the date_understanding benchmark.

The task: given a date understanding multiple-choice question, determine
the correct date by reasoning about calendars, date arithmetic, and
temporal relationships.

Derived from the BIG-Bench Hard date_understanding task.
"""

from typing import Any, List, Tuple

from secretagent.core import interface, implement_via
from secretagent.evaluate import Evaluator


class DateUnderstandingEvaluator(Evaluator):
    def compare_predictions(self, predicted_output, expected_output) -> dict[str, Any]:
        def normalize(s):
            return str(s).strip().strip('()')
        return dict(correct=float(normalize(predicted_output) == normalize(expected_output)))


# An option is a possible multiple-choice answer, encoded as (letter, date),
# where letter is a short string like A,B,C,D,E,F and date is a string in
# MM/DD/YYYY format, i.e. Tuple[str, str].


# ── sub-tools ────────────────────────────────────────────────────────────────

@interface
def extract_options(input_str: str) -> List[Tuple[str, str]]:
    """Extract the possible multiple-choice answers from the input string.

    Returns a list of (letter, date_str) pairs, e.g. [('A', '12/14/2026'), ...].

    Examples:
    >>> extract_options("Q: Today is Christmas Eve of 1937. What is the date 10 days ago in MM/DD/YYYY?\\nOptions:\\n(A) 12/14/2026\\n(B) 12/14/1950\\n(C) 12/14/2007\\n(D) 12/14/1937\\n")
    [('A', '12/14/2026'), ('B', '12/14/1950'), ('C', '12/14/2007'), ('D', '12/14/1937')]
    """
    ...

@interface
def extract_date_facts(input_str: str) -> List[str]:
    """Extract the background facts about dates needed to answer the question
    from the input string.

    Examples:
    >>> extract_date_facts("Q: Today is Christmas Eve of 1937. What is the date 10 days ago in MM/DD/YYYY?")
    ['Today is Christmas Eve of 1937.']
    >>> extract_date_facts("Q: Jane and John married on Jan 2, 1958. It is their 5-year anniversary today. What is the date tomorrow in MM/DD/YYYY?")
    ['Jane and John married on Jan 2, 1958.', 'It is their 5-year anniversary today.']
    """
    ...

@interface
def extract_question(input_str: str) -> str:
    """Extract the question to answer from the input string.

    Examples:
    >>> extract_question("Q: Today is Christmas Eve of 1937. What is the date 10 days ago in MM/DD/YYYY?")
    'What is the date 10 days ago in MM/DD/YYYY?'
    """
    ...

@interface
def make_inference(date_fact: str, context: List[str]) -> str:
    """Given a background fact about dates, and a list of previously
    stated facts, make a relevant inference.

    The inference is a natural language string.

    Examples:
    >>> make_inference('Today is Christmas Eve of 1937.', [])
    "If today is Christmas Eve of 1937, then today's date is 12/24/1937."
    >>> make_inference('It is their 5-year anniversary today.', ['Jane and John married on Jan 2, 1958.'])
    "If it is their 5-year anniversary today, then today's date is 01/02/1963."
    """
    ...

@interface
def answer_question(question: str, inferences: List[str]) -> str:
    """Given a question and a list of inferences about dates, construct a
    natural language answer to the question.

    Examples:
    >>> answer_question('What is the date 10 days ago in MM/DD/YYYY?', ["If today is Christmas Eve of 1937, then today's date is 12/24/1937."])
    '10 days before 12/24/1937 is 12/14/1937.'
    """
    ...

@interface
def match_option(answer: str, options: List[Tuple[str, str]]) -> Tuple[str, str]:
    """Find the multiple-choice option that best matches an answer string.

    Returns the matching (letter, date) pair.

    Examples:
    >>> match_option('10 days before 12/24/1937 is 12/14/1937.', [('A', '12/14/2026'), ('B', '12/14/1950'), ('C', '12/14/2007'), ('D', '12/14/1937')])
    ('D', '12/14/1937')
    """
    ...

# ── top-level interface ───────────────────────────────────────────────────────

@interface
def answer_date_question(question: str) -> str:
    """Given a date understanding multiple-choice question, return the correct
    option label, e.g. '(A)'.

    The input includes a scenario involving dates, a question about the
    resulting date, and labeled answer options in MM/DD/YYYY format.
    """
    ...

@interface
def answer_date_question_orchestrated(question: str) -> str:
    """Given a date understanding multiple-choice question, return the correct
    option label in parentheses, e.g. '(A)'.
    """
    ...

@interface
def react_answer_date_question(question: str) -> str:
    """Given a date understanding multiple-choice question, return a freeform
    answer string. Intended to be bound via simulate_pydantic with the sub-tools
    as the tool list (ReAct); its output is post-processed by
    extract_option_letter in date_understanding_react_workflow.
    """
    ...


# ── hand-coded workflow ───────────────────────────────────────────────────────

def date_understanding_workflow(input_str: str) -> str:
    """Hand-coded workflow implementing answer_date_question.

    Mirrors the mock's date_understanding pipeline: extract options, extract
    date facts, make inferences (each fact sees prior facts as context),
    answer the question from the inferences, then match the answer to an
    option.

    To use:
        ptools.answer_date_question.method=direct
        ptools.answer_date_question.fn=ptools.date_understanding_workflow
    """
    options = extract_options(input_str)
    date_facts = extract_date_facts(input_str)
    inferences = [make_inference(fact, date_facts[:i])
                  for i, fact in enumerate(date_facts)]
    question = extract_question(input_str)
    answer = answer_question(question, inferences)
    letter, _ = match_option(answer, options)
    return f'({letter})'


#
# zeroshot unstructured model is a workflow - first get a string
# answer, then use a second tool to extract the option letter
#

@implement_via('prompt_llm', prompt_template_file='prompt_templates/zeroshot.txt')
def zeroshot_answer_date_question(question: str) -> str:
    ...

@implement_via('simulate')
def extract_option_letter(llm_output: str) -> str:
    """Given raw LLM output, extract and return the multiple-choice letter
    in parentheses, e.g. '(A)'.
    """
    ...

def date_understanding_react_workflow(input_str: str) -> str:
    """Workflow that runs ReAct over the sub-tools and extracts the option
    letter from its freeform final answer.

    To use:
        ptools.answer_date_question.method=direct
        ptools.answer_date_question.fn=ptools.date_understanding_react_workflow
        ptools.react_answer_date_question.method=simulate_pydantic
        ptools.react_answer_date_question.tools=[...]
    """
    react_answer = react_answer_date_question(input_str)
    return extract_option_letter(react_answer)


def zeroshot_unstructured_workflow(question: str) -> str:
    """Workflow for using a zero-shot prompt and coercing the answer to a letter.

    To run the zeroshot unstructured model, bind this to the
    implementation of 'answer_date_question'.
    """
    llm_output = zeroshot_answer_date_question(question)
    return extract_option_letter(llm_output)
