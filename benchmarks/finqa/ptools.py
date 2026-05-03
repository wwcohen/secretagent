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
# Ptools called by the workflow
# ---------------------------------------------------------------

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

    Bound to ``direct``: arithmetic is exactly the kind of task where
    Python is precise and cheap, and an LLM call would only add cost
    and noise.  The function body below is what runs.
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


@implement_via('prompt_llm',
               prompt_template_file='prompt_templates/reasoning_plan.txt',
               answer_pattern=None)
def extract_reasoning_plan(problem: str) -> str:
    """Read the FinQA problem (context, table, and question) and produce a
    short plan for computing the answer.

    Your plan must include:
    1. What the question is asking for (the target quantity).
    2. Which specific rows/columns or text values are needed.
    3. The exact arithmetic formula using those values.

    Be precise: name the row labels and column headers exactly as they
    appear. Write the formula with actual numbers substituted in.

    Bound to ``prompt_llm`` with ``reasoning_plan.txt``, not to
    ``simulate``, because simulate's permissive framing ("propose a
    plausible output of this function") can't enforce the strict
    <plan>...</plan> output format that ``parse_plan_fields`` depends
    on.  Other experiments (e.g. react) override the binding to
    simulate, in which case this docstring is the spec the LLM sees.
    """
    ...


# Regexes and helper used by parse_plan_fields below.
_PLAN_TAG_RE   = re.compile(r'<plan>(.*?)</plan>', re.DOTALL | re.IGNORECASE)
_SCALE_RE      = re.compile(r'Scale:\s*(\w+)', re.IGNORECASE)
_DIRECT_RE     = re.compile(r'Direct[_\s]?answer:\s*(.+)', re.IGNORECASE)
_VALUE_LINE_RE = re.compile(r'^\s*-\s*([A-Za-z_]\w*)\s*=\s*(-?[\d.,]+)', re.MULTILINE)


def _extract_formula(plan: str) -> str | None:
    """Pull the arithmetic expression after 'Formula:' from a plan body.

    Permissive about contents: variable names are fine (substitute_values
    resolves them before compute() runs), and the formula doesn't need
    to contain literal digits.
    """
    m = re.search(r'[Ff]ormula:\s*(.+)', plan)
    if not m:
        return None
    expr = m.group(1).strip()
    expr = re.sub(r'[a-zA-Z_]+\s*=\s*', '', expr)
    expr = expr.rstrip('.')
    return expr or None


@implement_via('direct')
def parse_plan_fields(raw_plan: str) -> dict:
    """Strip <plan>...</plan> tags from the LLM output and parse out the
    Scale, Values, Formula, and Direct_answer fields.

    Returns a dict with keys:
        scale (str, lowercased; default "decimal")
        values (dict of short_name -> float)
        formula (str or None)
        direct_answer (str, possibly empty)

    Bound to ``direct``: this is pure regex over the LLM's structured
    output.  Routing it through an LLM would just add cost and a chance
    to garble the parse.
    """
    m = _PLAN_TAG_RE.search(raw_plan)
    body = m.group(1) if m else raw_plan
    out = {"scale": "decimal", "values": {}, "formula": None, "direct_answer": ""}
    m = _SCALE_RE.search(body)
    if m:
        out["scale"] = m.group(1).strip().lower()
    m = _DIRECT_RE.search(body)
    if m:
        out["direct_answer"] = m.group(1).strip()
    out["formula"] = _extract_formula(body)
    for vm in _VALUE_LINE_RE.finditer(body):
        try:
            out["values"][vm.group(1)] = float(vm.group(2).replace(",", ""))
        except ValueError:
            pass
    return out


@implement_via('direct')
def substitute_values(formula: str, values: dict) -> str:
    """Replace short_name tokens in a formula with their numeric values.

    Names are wrapped in parentheses to keep negatives parseable, and
    longest names are substituted first so e.g. ``rev_2018`` is replaced
    before ``rev`` (so the latter doesn't shadow the former).

    Bound to ``direct``: pure string substitution, deterministic by
    construction.
    """
    for name in sorted(values.keys(), key=len, reverse=True):
        formula = re.sub(rf'\b{re.escape(name)}\b', f'({values[name]})', formula)
    return formula


@implement_via('direct')
def format_for_scale(num: float, scale: str) -> str:
    """Format a numeric result according to the declared Scale.

    For scale="percent" we accept either convention (formula yielding the
    fraction 0.10, or the LLM's pct-magnitude 10.0) — pick by magnitude.
    For "integer", round and drop decimals; otherwise pretty-print.

    Bound to ``direct``: pure formatting; the rule set is small enough
    to encode in Python and large enough that we don't want an LLM
    making it up case by case.
    """
    if scale == "percent":
        pct = num if abs(num) >= 1.5 else num * 100
        return f"{pct:g}%"
    if scale == "integer":
        return str(int(round(num)))
    return f"{num:g}"


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

    Bound to ``simulate`` (in conf.yaml): the workflow only invokes
    this as a fallback for problems where the structured plan didn't
    yield a usable formula, so the input is unstructured prose and
    "extract a plausible final number" is exactly the kind of task
    simulate is good at.
    """
    ...


# ---------------------------------------------------------------
# Workflow implementation
# ---------------------------------------------------------------

def answer_finqa_workflow(problem: str) -> str:
    """Hand-coded workflow for answer_finqa.

    1. extract_reasoning_plan — LLM produces a <plan> with Target,
       Scale, Values, Formula, and Direct_answer fields.
    2. parse_plan_fields — pull those fields out of the plan body.
    3. yes/no/text scales → trust Direct_answer (or fall back to
       extract_final_number on empty).
    4. Numeric scales → substitute_values into the formula, evaluate
       with compute, then format_for_scale. Fall back to Direct_answer
       or extract_final_number on failure.

    See each ptool's docstring for the rationale behind its binding
    (direct vs. simulate vs. prompt_llm).
    """
    raw_plan = extract_reasoning_plan(problem)
    fields = parse_plan_fields(raw_plan)

    if fields["scale"] in ("yesno", "text"):
        return fields["direct_answer"] or extract_final_number(raw_plan)

    formula = fields["formula"]
    values = fields["values"]
    if formula and values:
        substituted = substitute_values(formula, values)
        result = compute(substituted)
        if not result.startswith("ERROR"):
            try:
                return format_for_scale(float(result), fields["scale"])
            except (ValueError, TypeError):
                pass

    if fields["direct_answer"]:
        return fields["direct_answer"]
    return extract_final_number(raw_plan)


# ---------------------------------------------------------------
# Workflow variant: lookup_cell for value extraction
# ---------------------------------------------------------------
#
# DOCUMENTED NEGATIVE RESULT — kept for reproducibility and writeup.
#
# Tests the question "would the workflow be better if it used the same
# primitives as the pot/react ablations?". Uses ONLY primitives from the
# pot/react toolset ({extract_reasoning_plan, lookup_cell, compute}) for
# value access and arithmetic — no new helpers. compute() is repurposed
# to parse raw cell strings (it strips $/, and evals as Python), falling
# back to the LLM-eyeballed value whenever the cell can't be parsed
# (FinQA cell formats like `$ -23158 ( 23158 )`, `1,234 million`, or
# empty / NOT FOUND will return ERROR from compute → fallback fires).
#
# Workflow-internal helpers (parse_plan_fields, substitute_values,
# format_for_scale, extract_final_number) are reused as-is; they're
# pre-existing string-handling glue, not new data-access tools. The
# (from row "...", column "...") cell references are parsed from the
# raw plan with a small regex local to this function so the main
# workflow's parser stays untouched.
#
# Result on N=300 valid (deepseek-v3.1, identical plan-extraction step):
#   workflow         : 75.67% (227/300)
#   workflow_lookup  : 73.00% (219/300)   -> -2.67pp, 0 wins / 8 losses
#
# Diagnosis: the LLM's dominant FinQA failure is citing wrong row/column
# references, not misreading values. A deterministic resolver faithfully
# follows the wrong reference; the LLM's eyeballed value usually comes
# from the correct cell even when its citation is off. So the lookup
# primitive amplifies citation errors rather than correcting them.
# An earlier draft used a richer Python helper for cell parsing instead
# of compute(); it produced the EXACT same 8 losses, ruling out parser
# choice as the cause.
#
# Decision: do NOT promote the workflow to use the pot/react primitives
# for value resolution. Reproduce the comparison with:
#   make workflow         SPLIT=valid N=300 RECORD=true SUFFIX=ab
#   make workflow-lookup  SPLIT=valid N=300 RECORD=true SUFFIX=ab

_LOOKUP_REF_RE = re.compile(
    r'-\s*(\w+)\s*=\s*[\d.,\-]+\s*\(\s*from\s+row\s*"([^"]+)"\s*,\s*column\s*"([^"]+)"\s*\)',
    re.IGNORECASE,
)


def answer_finqa_workflow_lookup(problem: str) -> str:
    """Workflow variant that uses only the pot/react primitives
    (lookup_cell + compute) for value extraction. Same prompt + plan
    extraction as the standard workflow; for each cell reference in
    the plan, runs lookup_cell + compute to resolve the cell to a
    number, falling back to the LLM-eyeballed value on parse failure.

    Documented negative result — see section header above for the
    full diagnosis. Performs ~2.7pp worse than the standard workflow
    on N=300 valid (0 wins / 8 losses among diverging cases).
    """
    raw_plan = extract_reasoning_plan(problem)
    fields = parse_plan_fields(raw_plan)

    if fields["scale"] in ("yesno", "text"):
        return fields["direct_answer"] or extract_final_number(raw_plan)

    values = dict(fields["values"])
    for m in _LOOKUP_REF_RE.finditer(raw_plan):
        name, row, col = m.group(1), m.group(2), m.group(3)
        cell = lookup_cell(problem, row, col)
        if cell.upper().startswith("NOT FOUND"):
            continue
        parsed = compute(cell)
        if parsed.startswith("ERROR"):
            continue
        try:
            values[name] = float(parsed)
        except ValueError:
            continue

    formula = fields["formula"]
    if formula and values:
        substituted = substitute_values(formula, values)
        result = compute(substituted)
        if not result.startswith("ERROR"):
            try:
                return format_for_scale(float(result), fields["scale"])
            except (ValueError, TypeError):
                pass

    if fields["direct_answer"]:
        return fields["direct_answer"]
    return extract_final_number(raw_plan)


# ---------------------------------------------------------------
# Tools used by the pot / react ablations (not called by the workflow)
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


# Plain-callable wrappers for the ReAct agent's tool list.
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
# React ablation: pydantic-ai agent + final-answer cleanup
# ---------------------------------------------------------------

# Bound to simulate_pydantic via the Makefile, with the call_* wrappers
# above as the tool list. The agent's final message is freeform prose;
# react_workflow pipes it through extract_final_number to clean it into
# a bare answer string, matching the standard cross-benchmark pattern
# (cf. bbh/penguins_in_a_table.penguins_react_workflow).
@interface
def react_solve_finqa(problem: str) -> str:
    """Solve a FinQA problem using a ReAct agent with the shared toolset.

    Returns the agent's freeform final answer (cleaned downstream by
    extract_final_number in react_workflow).
    """
    ...


def react_workflow(problem: str) -> str:
    """ReAct workflow for answer_finqa.

    Runs the pydantic-ai agent on `react_solve_finqa`, then cleans
    its freeform output into a bare numeric answer via
    extract_final_number — analogous to how the main workflow falls
    back on extract_final_number when the structured plan doesn't
    yield a usable formula.

    To run, bind via the Makefile (see the `react` target):
      ptools.answer_finqa.method=direct
      ptools.answer_finqa.fn=ptools.react_workflow
      ptools.react_solve_finqa.method=simulate_pydantic
      ptools.react_solve_finqa.tools=[ptools.call_parse_table, ...]
    """
    raw = react_solve_finqa(problem)
    return extract_final_number(raw)


# ---------------------------------------------------------------
# Unstructured baseline: zero-shot prompt + answer coercion
# ---------------------------------------------------------------

@implement_via('prompt_llm',
               prompt_template_file='prompt_templates/zeroshot.txt',
               answer_pattern=None)
def zeroshot_answer_finqa(problem: str) -> str:
    """Zero-shot unstructured prompt for FinQA (returns raw LLM string)."""
    ...


_NUM_RE = re.compile(r'[$€£]?\s*-?\s*[\d,]+\.?\d*\s*%?')


@implement_via('direct')
def coerce_to_answer(llm_output: str) -> str:
    """Extract the final answer from raw LLM text.

    Looks for ``<answer>`` tags first, then falls back to the last
    number-like token, then to the last non-empty line.
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
