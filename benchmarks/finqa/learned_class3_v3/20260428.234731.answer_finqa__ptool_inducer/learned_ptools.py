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


