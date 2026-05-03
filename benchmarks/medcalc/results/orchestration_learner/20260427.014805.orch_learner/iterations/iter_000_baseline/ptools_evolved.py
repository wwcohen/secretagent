"""Self-contained ptools module wrapping induced helpers.

Hand-derived from the winning induction variant in learned/stateless-oc0-mp3.
Designed to be ingested by OrchestrationLearner via inspect.getsource:
the file MUST have no indirection — every symbol the supervisor sees
lives here.
"""

import re
from typing import Optional

from secretagent.core import interface, implement_via

# Reuse the existing medcalc machinery (formulas + calculator engine).
# Only computational helpers are imported; nothing that wires interfaces.
import calculator_simple
import calculators


# =============================================================================
# Induced ptools (inlined from learned/stateless-oc0-mp3)
# =============================================================================

@implement_via('simulate')
def calculate_clinical_score(focus: str) -> str:
    """
    Extracts relevant clinical variables from a patient note and applies standard medical formulas to derive a result.

    Args:
        focus (str): The name of the formula or score to calculate (e.g., 'MAP', 'CKD-EPI GFR', 'Serum Osmolality').

    Instructions:
        1. Identify all required clinical variables (e.g., SBP, DBP, Cr, Age, Na).
        2. Extract values from the provided patient note.
        3. State the formula being used.
        4. Show step-by-step arithmetic to ensure accuracy.
        5. Provide the final result with appropriate units.

    Returns:
        str: A structured summary of the calculation, e.g.:
        'Calculation: Mean Arterial Pressure (MAP)
        Variables: SBP=120 mmHg, DBP=80 mmHg
        Formula: (2 * DBP + SBP) / 3
        Steps: (2 * 80 + 120) / 3 = (160 + 120) / 3 = 280 / 3
        Result: 93.33 mmHg'
    """


@implement_via('simulate')
def compute_clinical_value(focus: str) -> str:
    """
    Extracts clinical parameters from patient notes and applies specific medical formulas or unit conversions to derive a diagnostic or therapeutic value.

    Args:
        focus (str): A description of the clinical calculation to perform, including extracted variables (e.g., 'Calculate BMI for a 65kg, 155cm patient' or 'Perform 4-2-1 maintenance fluid calculation for 18kg child').

    Returns:
        str: A structured summary of the calculation, including: 
        - Extracted variables used.
        - The formula applied.
        - Step-by-step arithmetic.
        - Final result with appropriate units.

    Example Output:
        "Variables: Weight=18kg. Formula: 4-2-1 rule. Calculation: (10kg*4) + (8kg*2) = 40+16 = 56. Result: 56 ml/hr."
    """


@implement_via('simulate')
def apply_clinical_score(focus: str) -> str:
    """
    Extracts clinical variables required by a specified scoring system and calculates the final score based on provided criteria.

    Args:
        focus (str): The name of the scoring system (e.g., 'CHA2DS2-VASc', 'CURB-65', 'Wells Criteria', 'SIRS') and the context/values to be evaluated.

    Process:
        1. Define the parameters/criteria for the requested score.
        2. Scan the patient note for values corresponding to each parameter.
        3. Assign points according to standard medical guidelines.
        4. Sum the points to produce the final score.

    Returns:
        A structured string summary:
        "Score Name: [Name]
    - [Criterion 1]: [Value] ([Points] pts)
    - [Criterion 2]: [Value] ([Points] pts)
    Total: [Sum]"

    Example Return:
        "CHA2DS2-VASc Score Calculation:
    - Age (65-74): 68 (1 pt)
    - Stroke/TIA: Yes (2 pts)
    - Vascular disease: Yes (1 pt)
    - CHF/HTN/DM: No (0 pts)
    Total: 4"
    """

# =============================================================================
# Public entry point — calculate_medical_value
# =============================================================================

@interface
def calculate_medical_value(patient_note: str, question: str) -> float:
    """Calculate a medical value from a patient note and question."""




def _extract_number(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value)
    if s.startswith('**exception'):
        return None
    try:
        return float(s)
    except ValueError:
        pass
    for pat in (r'<answer>\s*([\d.eE+-]+)\s*</answer>', r'ANSWER:\s*([\d.eE+-]+)'):
        m = re.search(pat, s)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    nums = re.findall(r'-?\d+\.?\d*', s)
    if nums:
        try:
            return float(nums[-1])
        except ValueError:
            pass
    return None
