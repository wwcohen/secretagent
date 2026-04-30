"""Induced ptools for calculate_medical_value."""

from secretagent.core import implement_via


@implement_via('simulate')
def define_calculation_task(focus: str) -> str:
    """
    Use this tool to formalize the clinical calculation task before performing any math. 

    This function helps you: 
    1. Specify the clinical score or formula required based on the patient note. 
    2. Extract the specific variables (e.g., sodium levels, weight, heart rate) needed for the calculation. 
    3. Map these variables to their corresponding values found in the clinical text. 

    Returns: 
    A structured string summarizing the task: 
    'TASK: [Calculation Name] 
    REQUIRED_VARIABLES: [list of parameters] 
    EXTRACTED_VALUES: [mapping of parameters to note values] 
    STATUS: Ready for computation'
    """


@implement_via('simulate')
def extract_clinical_data(focus: str) -> str:
    """
    Identifies and retrieves clinical data points from the patient note relevant to a specific medical formula or decision rule.

    Args:
        focus: A string describing the medical tool or criteria (e.g., 'Wells' Criteria for PE', 'BMI', 'MELD score').

    Instructions:
        - Scan the note for all required parameters defined by the medical formula.
        - If a parameter is missing or ambiguous, state that it is 'not found' or 'unclear'.
        - Be precise with units and temporal context provided in the note.

    Returns:
        A structured string summarizing the extracted values:
        'Extracted data for [focus]:
        - [Parameter 1]: [Value]
        - [Parameter 2]: [Value]
        ...'
    """


