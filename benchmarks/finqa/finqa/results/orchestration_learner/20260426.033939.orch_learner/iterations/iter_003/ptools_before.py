"""FinQA: numerical reasoning over financial text + tables.

Top-level task: ``answer_finqa(problem)`` — one string built by
``data/build_datasets.py``.

Experiment mapping (see Makefile):
  workflow              — hand-coded workflow + engineered ptools
  pot                   — drop workflow, keep ptools (program of thought)
  react                 — drop workflow, keep ptools (ReAct agent)
  structured_baseline   — drop workflow and ptools (simulate)
  unstructured_baseline — drop workflow, ptools, and structured prompt
"""

import re

from secretagent.core import interface, implement_via


# ---------------------------------------------------------------
# Top-level interface
# ---------------------------------------------------------------

@interface
def answer_finqa(problem: str) -> str:
    """Answer a FinQA instance.

    The problem string contains report context, a markdown table, and a question.
    Return only the final answer (number, percent, or brief text), with no explanation.
    """
    ...


# ---------------------------------------------------------------
# Ptools: direct-implemented Python tools
# ---------------------------------------------------------------

@interface
def parse_table(problem: str) -> str:
    """Extract the markdown table from a FinQA problem and return it
    as clean tab-separated text with column headers on the first line.
    """
    lines = problem.split('\n')
    table_lines = [l for l in lines if l.strip().startswith('|') and '|' in l[1:]]
    if not table_lines:
        return "(no table found)"
    rows = []
    for line in table_lines:
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        rows.append('\t'.join(cells))
    return '\n'.join(rows)


@interface
def lookup_cell(problem: str, row_label: str, column: str) -> str:
    """Look up a cell value by row label and column name from the table
    embedded in a FinQA problem.

    The row_label is matched (case-insensitive substring) against the first
    column. The column is matched (case-insensitive substring) against the
    header row. Returns the cell value as a string, or 'NOT FOUND'.
    """
    lines = problem.split('\n')
    table_lines = [l for l in lines if l.strip().startswith('|') and '|' in l[1:]]
    if not table_lines:
        return "NOT FOUND"
    parsed = []
    for line in table_lines:
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        parsed.append(cells)
    if len(parsed) < 2:
        return "NOT FOUND"
    headers = [h.lower() for h in parsed[0]]
    col_idx = None
    col_lower = column.lower()
    for i, h in enumerate(headers):
        if not h:
            continue
        if col_lower in h or h in col_lower:
            col_idx = i
            break
    if col_idx is None:
        return f"NOT FOUND (no column matching '{column}')"
    row_lower = row_label.lower()
    for row in parsed[1:]:
        if row and row_lower in row[0].lower():
            if col_idx < len(row):
                return row[col_idx]
    return f"NOT FOUND (no row matching '{row_label}')"


@interface
def compute(expression: str) -> str:
    """Evaluate a mathematical expression and return the numeric result as a string.

    Supports standard arithmetic (+, -, *, /, **, %), abs(), round(),
    min(), max(), and sum(). Input values may include dollar signs and
    commas which are stripped before evaluation.

    Examples:
      compute("(637 / 5.0)")           → "127.4"
      compute("(193.5 - 100) / 100")   → "0.935"
      compute("60 / 243 * 100")        → "24.691358..."
    """
    cleaned = expression.replace('$', '').replace(',', '')
    safe_globals = {
        "__builtins__": {},
        "abs": abs, "round": round, "min": min, "max": max, "sum": sum,
    }
    try:
        result = eval(cleaned, safe_globals)  # noqa: S307
        if isinstance(result, float):
            if result == int(result) and abs(result) < 1e15:
                return str(int(result))
            return f"{result:.10g}"
        return str(result)
    except Exception as e:
        return f"ERROR: {e}"


# ---------------------------------------------------------------
# Ptools: LLM-implemented interfaces (bound to simulate via config)
# ---------------------------------------------------------------

@interface
def extract_reasoning_plan(problem: str) -> str:
    """Read the FinQA problem (context, table, and question) and produce a
    short plan for computing the answer.

    Your plan must include:
    1. What the question is asking for (the target quantity).
    2. Which specific rows/columns or text values are needed.
    3. The exact arithmetic formula using those values.

    Be precise: name the row labels and column headers exactly as they
    appear. Write the formula with actual numbers substituted in.

    Example output:
      Target: percentage change in revenue from 2016 to 2017
      Values: revenue_2016 = $10,815 from row "2016", col "operating income";
              revenue_2017 = $11,503 from row "2017", col "operating income"
      Formula: (11503 - 10815) / 10815
    """
    ...


@interface
def extract_final_number(verbose_output: str) -> str:
    """Extract only the final numeric answer from verbose LLM output.

    The input may contain reasoning, explanation, or prose around
    the actual answer. Return ONLY the final numeric value as a clean
    string — a plain number, optionally with a percent sign.

    Examples:
      "The answer is 127.4 million dollars." → "127.4"
      "93.5%" → "93.5%"
      "Calculated: (193.5 - 100)/100 = 0.935 = 93.5%" → "93.5%"
    """
    ...


# ---------------------------------------------------------------
# Workflow implementation
# ---------------------------------------------------------------

def answer_finqa_workflow(problem: str) -> str:
    """Hand-coded workflow for answer_finqa.

    LLM extracts a reasoning plan with target, values, and formula.
    Python evaluates the formula. Falls back to LLM extraction when
    no clean formula is found.
    """
    plan = extract_reasoning_plan(problem)
    formula = _extract_formula(plan)
    if formula:
        result = compute(formula)
        if not result.startswith("ERROR"):
            return result
    return extract_final_number(plan)


def _extract_formula(plan: str) -> str | None:
    """Pull the arithmetic expression after 'Formula:' from a plan."""
    m = re.search(r'[Ff]ormula:\s*(.+)', plan)
    if not m:
        return None
    expr = m.group(1).strip()
    expr = re.sub(r'[a-zA-Z_]+\s*=\s*', '', expr)
    expr = expr.rstrip('.')
    if not re.search(r'\d', expr):
        return None
    return expr


# ---------------------------------------------------------------
# Tool callables for ReAct (wrappers around interfaces)
# ---------------------------------------------------------------

def call_parse_table(problem: str) -> str:
    """Parse the markdown table from a FinQA problem into clean text."""
    return parse_table(problem)


def call_lookup_cell(problem: str, row_label: str, column: str) -> str:
    """Look up a specific cell value by row and column name."""
    return lookup_cell(problem, row_label, column)


def call_compute(expression: str) -> str:
    """Evaluate an arithmetic expression and return the result."""
    return compute(expression)


def call_extract_reasoning_plan(problem: str) -> str:
    """Produce a reasoning plan with target, values, and formula."""
    return extract_reasoning_plan(problem)


# ---------------------------------------------------------------
# Unstructured baseline: zero-shot prompt + answer coercion
# ---------------------------------------------------------------

@implement_via('prompt_llm', prompt_template_file='prompt_templates/zeroshot.txt', answer_pattern=None)
def zeroshot_answer_finqa(problem: str) -> str:
    """Zero-shot unstructured prompt for FinQA (returns raw LLM string)."""
    ...


_NUM_RE = re.compile(r'[$€£]?\s*-?\s*[\d,]+\.?\d*\s*%?')


@implement_via('direct')
def coerce_to_answer(llm_output: str) -> str:
    """Extract the final numeric answer from raw LLM text.

    Looks for ``<answer>`` tags first, then falls back to the last
    number-like token in the text.
    """
    s = llm_output.strip()
    m = re.search(r'<answer[^>]*>(.*?)</answer>', s, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    matches = _NUM_RE.findall(s)
    if matches:
        return matches[-1].strip()
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    return lines[-1] if lines else s


def unstructured_baseline_workflow(problem: str) -> str:
    """Workflow for the unstructured baseline: zero-shot prompt then cleanup.

    To run, bind answer_finqa to this function via:
      ptools.answer_finqa.method=direct
      ptools.answer_finqa.fn=ptools.unstructured_baseline_workflow
    """
    raw = zeroshot_answer_finqa(problem)
    return coerce_to_answer(raw)
