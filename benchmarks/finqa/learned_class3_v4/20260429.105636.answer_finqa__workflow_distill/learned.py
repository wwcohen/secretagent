"""Auto-generated workflow-distilled implementation for answer_finqa.

Tools from benchmarks/finqa/learned_class3_v3/20260428.234731.answer_finqa__ptool_inducer/learned_ptools.py are inlined below.
"""

"""Induced ptools for answer_finqa."""

from secretagent.core import implement_via


@implement_via('simulate')
def analyze_problem_and_requirements(focus: str) -> str:
    """
    Analyzes the financial QA problem to determine what specific numerical information needs to be extracted and calculated.
    The function should parse the question focus to identify:
    - The target value(s) to find
    - Relevant table columns/rows
    - Any constraints or exclusions mentioned
    - Required operations (sum, difference, percentage, etc.)

    Pay attention to:
    - Key phrases indicating mathematical operations
    - Time periods or category filters
    - Comparative language (vs, compared to, relative to)
    - Exclusion terms (excluding, except, not including)

    Returns:
    A structured string outlining the analysis including:
    - Target value description
    - Required data sources
    - Necessary calculations
    - Any constraints to apply

    Example return:
    "Target: Percentage of owned US facilities
    Data needed: Total US facilities count, Owned US facilities count
    Calculation: (Owned US facilities / Total US facilities) * 100
    Constraints: None"
    """


@implement_via('simulate')
def provide_final_answer(focus: str) -> str:
    """
    This function provides the final numerical answer to the financial QA problem.

    It should be used when the agent has completed all reasoning steps and determined
    the final numerical result. The function formats the answer appropriately for
    financial contexts, preserving percentages, decimal precision, and currency
    formatting as needed.

    Parameters:
        focus (str): The final calculated numerical value that answers the question.
                     This should be a string representation of the number exactly as
                     it should be presented in the final answer.

    Returns:
        str: The final answer formatted as a string. The output should be ready for
             direct use without additional processing.

    Example:
        >>> provide_final_answer("40.5%")
        "40.5%"

    Note:
        - The agent should ensure the value is properly rounded and formatted
        - Percentages should include the % symbol
        - Large numbers should not include commas (e.g., 858774.286825054)
        - The function does not perform calculations; it only formats the final result
    """


@implement_via('simulate')
def perform_numerical_calculation(focus: str) -> str:
    """
    Performs mathematical operations (addition, subtraction, multiplication, division,
    percentage calculation, min/max comparison, etc.) on numerical values identified from
    the financial context. The function receives a focus string describing the specific
    calculation needed (e.g., 'percentage of owned facilities', 'net change from 2012 to 2013',
    'lowest operating income').

    The response should be a structured string containing only the final calculated numerical
    value, formatted appropriately for the requested calculation (e.g., percentage with %
    symbol, negative values with minus sign).

    Attention: Ensure all input values are properly validated as numerical before calculation.
    Handle division by zero errors and ensure proper rounding/precision based on financial
    context. Return the value in the exact format requested by the question.

    Returns:
        str: The calculated numerical result (e.g., '92.86%', '-16', '846', '198')
    """


@implement_via('simulate')
def extract_relevant_information(focus: str) -> str:
    """
    Extracts relevant numerical values, text snippets, or data points from the provided context (table and surrounding text) based on the specified focus.
    The response should be a structured string that clearly presents the extracted information, often listing values or describing the found data.
    The agent should pay close attention to:
    - Identifying the exact information requested by the focus parameter
    - Locating this information in both tabular data and surrounding narrative text
    - Extracting numerical values with their proper units and signs
    - Noting any contextual details needed for interpretation (e.g., 'exclusive of X', 'through Y date')

    Returns:
    A string containing the extracted information, formatted for clarity. For example:
    "- Class b-1 shareholders elect: 3 directors
    - Class b-2 shareholders elect: 2 directors
    - Total: 5 directors"
    """


@implement_via('simulate')
def plan_calculation_approach(focus: str) -> str:
    """
    Determines the appropriate calculation method for solving a numerical financial problem.

    This function outlines the reasoning approach for performing calculations based on
    tabular data and surrounding text. It focuses on identifying what needs to be
    calculated, which data points to use, and the mathematical operations required.
    The agent should pay attention to:
    - The specific financial metric or ratio being requested
    - Relevant columns/rows in the table data
    - Any necessary conversions or aggregations
    - Whether the calculation requires multiple steps
    - How to handle potential missing or ambiguous data

    Returns:
        str: A structured plan outlining the calculation approach

    Example output:
        "Plan to calculate [specific metric] by [method description].
        Will use [data points] from [table location] and perform [mathematical operations].
        Need to consider [any special factors]."
    """




import re

def answer_finqa(narrative_and_question):
    """
    Solve a FinQA numerical reasoning question over a financial report excerpt.
    
    Args:
        narrative_and_question: A tuple containing a single string with the full problem
                               (context, table, question)
    
    Returns:
        A numerical answer (float or int) or None if unable to confidently answer.
    """
    # Handle input - it comes as a tuple with a single string
    if isinstance(narrative_and_question, tuple):
        full_text = narrative_and_question[0]
    else:
        full_text = narrative_and_question
    
    # Initialize the react state so tools can read the narrative
    try:
        from ptools_common import _REACT_STATE
        _REACT_STATE['narrative'] = full_text
    except Exception:
        pass
    
    # Extract the question from the full text
    # The question is typically after "## Question\n" or at the end
    question = ""
    question_match = re.search(r'##\s*Question\s*\n(.+?)(?:\n##|\Z)', full_text, re.DOTALL)
    if question_match:
        question = question_match.group(1).strip()
    else:
        # Try to find the last line as the question
        lines = full_text.strip().split('\n')
        for line in reversed(lines):
            line = line.strip()
            if line and '|' not in line and not line.startswith('#'):
                question = line
                break
    
    if not question:
        return None
    
    try:
        # Step 1: Analyze the problem
        analysis = analyze_problem_and_requirements(question)
        
        # Step 2: Extract relevant information
        info = extract_relevant_information(question)
        
        # Step 3: Plan the calculation
        plan = plan_calculation_approach(f"Given context: {full_text[-2000:]}\nQuestion: {question}\nExtracted info: {info}\nAnalysis: {analysis}")
        
        # Step 4: Try to extract numbers directly from the context and do calculation
        # First, let's try a more targeted extraction
        info2 = extract_relevant_information(f"Extract exact numbers needed from the table and text to answer: {question}")
        
        # Step 5: Perform the calculation
        calc_input = f"Based on the financial report context, answer this question with a numerical calculation.\nQuestion: {question}\nAnalysis: {analysis}\nExtracted data: {info}\nAdditional data: {info2}\nPlan: {plan}"
        result = perform_numerical_calculation(calc_input)
        
        # Step 6: Get the final answer
        final = provide_final_answer(f"The calculation result is: {result}. Provide just the numerical answer for: {question}")
        
        # Parse the numerical result
        answer = parse_number(final)
        if answer is not None:
            return answer
        
        # Try parsing from the calculation result
        answer = parse_number(result)
        if answer is not None:
            return answer
        
        return None
        
    except Exception:
        return None


def parse_number(text):
    """Extract a numerical value from text, returning float or None."""
    if text is None:
        return None
    
    text = str(text).strip()
    
    # Remove common formatting
    text = text.replace(',', '').replace('$', '').replace('€', '').replace('£', '')
    
    # Try to find a percentage value and convert
    pct_match = re.search(r'(-?\d+\.?\d*)\s*%', text)
    if pct_match:
        try:
            val = float(pct_match.group(1))
            # The expected outputs show percentages as decimals (e.g., 0.4 for 40%)
            # Check if the value looks like it should be divided by 100
            return round(val / 100, 5)
        except (ValueError, OverflowError):
            pass
    
    # Try to find a plain number
    num_match = re.search(r'(-?\d+\.?\d*)', text)
    if num_match:
        try:
            val = float(num_match.group(1))
            # Round to 5 decimal places
            if val == int(val) and '.' not in num_match.group(1):
                return int(val) * 1.0 if abs(val) > 1 else val
            return round(val, 5)
        except (ValueError, OverflowError):
            return None
    
    return None
