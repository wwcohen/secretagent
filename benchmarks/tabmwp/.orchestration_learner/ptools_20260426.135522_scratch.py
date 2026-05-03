"""Interfaces for the TabMWP (Tabular Math Word Problems) benchmark.

Two modes of table access:
  - Option A (in-context): table text is passed directly in arguments.
  - Option B (tool-based): table is accessed via direct-implemented tool
    interfaces that query a table store.

The top-level interface is `tabmwp_solve`. Hand-coded workflows are
defined at the bottom of this file.
"""

import pandas as pd

from secretagent.core import interface

# ---------------------------------------------------------------
# Table store — populated at experiment startup by expt.py
# Maps example id -> {"table": str, "table_for_pd": dict,
#                      "table_title": str | None}
# ---------------------------------------------------------------

_TABLE_STORE: dict[str, dict] = {}


def load_table_store(dataset_dict: dict) -> None:
    """Populate the table store from the raw dataset dict.

    Called by expt.py before running experiments.
    """
    _TABLE_STORE.clear()
    for ex_id, ex in dataset_dict.items():
        _TABLE_STORE[ex_id] = {
            "table": ex["table"],
            "table_for_pd": ex["table_for_pd"],
            "table_title": ex.get("table_title"),
        }


# ---------------------------------------------------------------
# Top-level interface
# ---------------------------------------------------------------

@interface
def tabmwp_solve(question: str, table: str, table_id: str, choices: list | None) -> str:
    """Solve a TabMWP problem. Return the answer as a string.

    Arguments:
      question: the math word problem text
      table: the table as pipe-delimited text (header row + data rows)
      table_id: identifier for looking up the table via tool interfaces
      choices: list of answer options for multi-choice, or None for free-text
    """


# ---------------------------------------------------------------
# Shared reasoning interfaces (used by both Option A and Option B)
# ---------------------------------------------------------------

@interface
def identify_operation(question: str, table_description: str) -> str:
    """Determine what math operation is needed to answer the question.

    Given the question and a description of the table (column names,
    row count, title), identify the operation: lookup, sum, difference,
    average, count, comparison, min, max, range, or other.

    Return a short string naming the operation.
    """


@interface
def compute_answer(operation: str, values: list[str]) -> str:
    """Perform the arithmetic or logical operation on the given values.

    Arguments:
      operation: the operation to perform (e.g. "sum", "average", "difference")
      values: the numeric or text values extracted from the table

    Return the computed result as a string.
    """


@interface
def format_answer(result: str, choices: list | None) -> str:
    """Format the computed result into the final answer.

    If choices is a list (multi-choice question), select the choice
    that best matches the result. If choices is None (free-text),
    return the result directly as a clean string (no units, no extra text).
    """


# ---------------------------------------------------------------
# Option A: in-context table interfaces
# ---------------------------------------------------------------

@interface
def extract_relevant_values(question: str, table: str) -> list[str]:
    """Given the full table in context, extract the specific values
    needed to answer the question.

    Read the table carefully, identify which rows and columns are
    relevant to the question, and return their values as a list
    of strings.
    """


# ---------------------------------------------------------------
# Option B: tool-based table access interfaces (direct implementations)
# ---------------------------------------------------------------

@interface
def get_table_schema(table_id: str) -> str:
    """Return the table schema: column names, row count, and table title.

    Does NOT return actual data values. Use lookup_value or query_column
    to retrieve data.
    """
    info = _TABLE_STORE[table_id]
    df = pd.DataFrame(info["table_for_pd"])
    title = info["table_title"] or "(no title)"
    columns = ", ".join(df.columns.tolist())
    return f"Title: {title}\nColumns: {columns}\nRows: {len(df)}"


@interface
def lookup_value(table_id: str, row_label: str, column: str) -> str:
    """Look up a specific cell value by row label and column name.

    The row_label is matched against the first column of the table.
    Returns the cell value as a string, or 'NOT FOUND' if no match.
    """
    info = _TABLE_STORE[table_id]
    df = pd.DataFrame(info["table_for_pd"])
    first_col = df.columns[0]
    mask = df[first_col].str.strip().str.lower() == row_label.strip().lower()
    if mask.any() and column in df.columns:
        return str(df.loc[mask, column].iloc[0])
    return "NOT FOUND"


@interface
def query_column(table_id: str, column: str) -> list[str]:
    """Return all values in a given column as a list of strings.

    Returns an empty list if the column name is not found.
    """
    info = _TABLE_STORE[table_id]
    df = pd.DataFrame(info["table_for_pd"])
    if column in df.columns:
        return df[column].tolist()
    return []


@interface
def query_table(table_id: str) -> str:
    """Return the full table as pipe-delimited text.

    Fallback tool when targeted lookups are insufficient.
    """
    return _TABLE_STORE[table_id]["table"]


# ---------------------------------------------------------------
# Answer extraction (for post-processing verbose agent output)
# ---------------------------------------------------------------

@interface
def extract_answer(llm_output: str, choices: list | None) -> str:
    """Extract a clean, concise answer from verbose LLM output.

    The llm_output may contain reasoning, explanation, or prose around
    the actual answer. Extract just the final answer value.

    If choices is a list, return the matching choice exactly.
    If choices is None, return the numeric or short text answer only,
    with no extra words, units, or explanation.
    """


# ---------------------------------------------------------------
# PoT-specific interface (receives table as pandas-ready dict)
# ---------------------------------------------------------------

@interface
def tabmwp_solve_pot(question: str, table_for_pd: dict, choices: list | None) -> str:
    """Solve a TabMWP problem using generated Python code.

    Arguments:
      question: the math word problem text
      table_for_pd: a dictionary where keys are column names and values
        are lists of cell values as strings.
        Example: {"Name": ["Alice", "Bob"], "Score": ["90", "85"]}
      choices: list of answer options for multi-choice, or None for free-text

    The table_for_pd dict can be accessed directly:
      columns = list(table_for_pd.keys())
      values = table_for_pd[column_name]  # list of strings

    To do arithmetic, convert strings to numbers manually:
      nums = [statistics.mean([int(v) for v in table_for_pd["Score"]])]

    Call final_answer(result) with the answer as a string.
    """


def pot_workflow(question: str, table: str, table_id: str, choices: list | None) -> str:
    """Wrapper that converts inputs for the PoT interface.

    Looks up table_for_pd from the table store and delegates to
    tabmwp_solve_pot which receives a pandas-ready dict.
    """
    info = _TABLE_STORE[table_id]
    return tabmwp_solve_pot(question, info["table_for_pd"], choices)


@interface
def tabmwp_react(question: str, table: str, table_id: str, choices: list | None) -> str:
    """Solve a TabMWP problem using a ReAct agent with tools, then
    extract a clean answer from the agent's verbose output.
    """
    raw_output = tabmwp_solve(question, table, table_id, choices)
    return extract_answer(raw_output, choices)


# ---------------------------------------------------------------
# Hand-coded workflows
# ---------------------------------------------------------------

def incontext_workflow(question: str, table: str, table_id: str, choices: list | None) -> str:
    """Option A workflow: table passed in-context through ptool arguments.

    table_id is unused here but included to match the top-level signature.
    """
    lines = table.strip().split("\n")
    header = lines[0] if lines else ""
    table_description = f"Columns: {header} | Rows: {len(lines) - 1}"

    operation = identify_operation(question, table_description)
    values = extract_relevant_values(question, table)
    result = compute_answer(operation, values)
    return format_answer(result, choices)


def tools_workflow(question: str, table: str, table_id: str, choices: list | None) -> str:
    """Option B workflow: table accessed via tool-calling interfaces.

    The table argument is available as fallback but the workflow uses
    tool calls to query the table store via table_id.
    """
    schema = get_table_schema(table_id)
    operation = identify_operation(question, schema)

    # Use extract_relevant_values with the full table text to determine
    # which values are needed, then compute
    values = extract_relevant_values(question, query_table(table_id))
    result = compute_answer(operation, values)
    return format_answer(result, choices)


# ---------------------------------------------------------------
# Workflow improvement experiments
# ---------------------------------------------------------------

# --- Experiment: workflow_broad (fewer, broader ptools) ---

@interface
def extract_and_compute(question: str, table: str) -> str:
    """Given a question and a table, extract the relevant values and
    compute the answer in a single step.

    Read the table carefully, determine what operation is needed
    (lookup, sum, difference, average, count, comparison, etc.),
    extract the relevant values, perform the calculation, and return
    the result as a string.

    Return ONLY the computed value, no units or explanation.
    """


def broad_workflow(question: str, table: str, table_id: str, choices: list | None) -> str:
    """2-step workflow: extract_and_compute -> format_answer."""
    result = extract_and_compute(question, table)
    return format_answer(result, choices)


# --- Experiment: workflow_rich (full context at every step) ---

@interface
def identify_operation_rich(question: str, table: str) -> str:
    """Given the full question and table, determine what math operation
    is needed to answer the question.

    Read both the question and the table data carefully.
    Identify the operation: lookup, sum, difference, average, count,
    comparison, min, max, range, or other.

    Return a short string naming the operation.
    """


@interface
def compute_answer_rich(question: str, table: str, operation: str, values: list[str]) -> str:
    """Perform the arithmetic or logical operation on the given values.

    You also receive the original question and table for full context.

    Arguments:
      question: the original math word problem
      table: the full table as pipe-delimited text
      operation: the operation to perform (e.g. "sum", "average", "difference")
      values: the numeric or text values extracted from the table

    Return the computed result as a string.
    """


@interface
def format_answer_rich(question: str, table: str, result: str, choices: list | None) -> str:
    """Format the computed result into the final answer.

    You also receive the original question and table for full context.

    If choices is a list (multi-choice question), select the choice
    that best matches the result. If choices is None (free-text),
    return the result directly as a clean string (no units, no extra text).
    """


def rich_workflow(question: str, table: str, table_id: str, choices: list | None) -> str:
    """4-step workflow where every ptool receives full question + table context."""
    operation = identify_operation_rich(question, table)
    values = extract_relevant_values(question, table)
    result = compute_answer_rich(question, table, operation, values)
    return format_answer_rich(question, table, result, choices)
