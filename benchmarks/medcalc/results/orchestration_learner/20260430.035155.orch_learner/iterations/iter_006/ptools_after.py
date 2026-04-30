"""Self-contained ptools module wrapping induced helpers.

Hand-derived from the winning induction variant in learned/rule-4pc-pro-mp3.
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
# Induced ptools (inlined from learned/rule-4pc-pro-mp3)
# =============================================================================

@implement_via('simulate')
def map_patient_data_to_score(focus: str) -> str:
    """
    Maps extracted patient data to the criteria of a specific medical score or formula to calculate the total.

    Provide the name of the score and the relevant extracted clinical values in the `focus`. The response will break down each criterion, evaluate the patient's data against it, assign the corresponding points, and calculate the final total.

    Pay attention to the exact thresholds, units, and point values defined by the medical score (e.g., Age >= 65, HR > 100, specific biomarker ranges). Make sure to explicitly note criteria that receive 0 points due to lack of evidence, falling outside the risk thresholds, or normal findings.

    Returns:
    Score Name: [Name of the Score]
    - [Criterion 1]: [Patient Data / Observation] -> [Points]
    - [Criterion 2]: [Patient Data / Observation] -> [Points]
    ...
    Total Score: [Calculated Sum]
    """


@implement_via('simulate')
def compute_score_step_by_step(focus: str) -> str:
    """
    Computes a medical score manually step-by-step. Provide the name of the medical score to calculate in the `focus` parameter (e.g., 'CURB-65', 'Caprini VTE').

    The response will structure the calculation by:
    1. Listing all the criteria evaluated for the score.
    2. Stating the patient's specific extracted data or status for each criterion.
    3. Assigning the exact point value (including 0 points for absent symptoms or normal findings) for each criterion.
    4. Providing the explicit mathematical sum of the points to reach the final total score.

    Pay attention to the specific definitions, thresholds, and exclusions for each scoring criterion to ensure accurate point assignment.

    Returns:
    - **[Criterion 1]**: [Patient's status/value] ([X] points)
    - **[Criterion 2]**: [Patient's status/value] ([Y] points)
    ...
    Calculation: [X] + [Y] + ... = [Total Score]
    """


@implement_via('simulate')
def calculate_clinical_score(focus: str) -> str:
    """
    Calculates a specified medical score by extracting relevant clinical criteria and applying the appropriate scoring formula.

    Information to extract/reason about:
    - Identify the required parameters for the specific score indicated in the `focus` (e.g., 'SOFA score', 'Child-Pugh score', 'Charlson Comorbidity Index').
    - Extract the corresponding clinical values (lab results, vitals, comorbidities, age) from the patient note.

    How the response should be structured:
    - Provide a step-by-step list of each parameter evaluated.
    - Note the extracted patient value for each parameter.
    - State the points assigned based on the specific scoring criteria.
    - Provide a final summation equation yielding the total score.

    What the agent should pay attention to:
    - Accurately apply clinical thresholds, age brackets, and unit conversions.
    - Account for missing information properly (e.g., defaulting to normal/0 points if the score guidelines permit, or noting the missing data).
    - Ensure strict arithmetic correctness when summing the assigned points.

    Returns:
    A structured string detailing the score calculation step-by-step.

    Example:
    Score Calculation: SOFA score
    1. Respiration: PaO2/FiO2 = 160 -> Score = 3
    2. Coagulation: Platelets = 110,000/uL -> Score = 1
    3. Liver: Bilirubin = 1.4 mg/dL -> Score = 1
    4. Cardiovascular: MAP = 57.3 mmHg -> Score = 1
    5. Neurological: GCS = 5 -> Score = 4
    6. Renal: Creatinine = 2.2 mg/dL -> Score = 2
    Total SOFA Score = 3 + 1 + 1 + 1 + 4 + 2 = 12
    """

# =============================================================================
# Unified CoT Engine
# =============================================================================

@implement_via('simulate')
def _solve_medical_value_cot(patient_note: str, question: str) -> str:
    """
    You are an expert clinical AI. Your task is to calculate a medical score or extract a clinical value.
    
    1. Read the patient note carefully.
    2. Identify what the question is asking (e.g., APACHE II, Wells, Caprini, HEART, HAS-BLED, GBS, SOFA, PERC, Age, Heart Rate, etc.).
    3. If calculating a clinical score, think step-by-step:
       - List each specific criterion for the score based on standard medical guidelines.
       - Extract the patient's value for that criterion from the note.
       - Assign points based on strictly defined medical thresholds.
       - Note: Missing data or normal findings usually receive 0 points unless specified otherwise.
       - Explicitly sum the assigned points to find the total.
    4. If extracting a simple value, just state it.
    5. CRITICAL: You MUST output your final numerical answer inside <answer> tags at the very end of your response.
       Do not include units or extra text inside the tags.
       
    Example for a score:
    ... reasoning ...
    Total Score: 12
    <answer>12</answer>
    
    Example for a simple value:
    The patient's age is 65.
    <answer>65</answer>
    """


# =============================================================================
# Public entry point — calculate_medical_value
# =============================================================================

@implement_via('direct')
def calculate_medical_value(patient_note: str, question: str) -> float:
    """Calculate a medical value from a patient note and question."""
    text_result = _solve_medical_value_cot(patient_note, question)
    val = _extract_number(text_result)
    if val is not None:
        return val
    return 0.0


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
        
    # 1. <answer> tags (Most reliable, ignores reasoning numbers)
    m = re.search(r'<answer>(.*?)</answer>', s, re.IGNORECASE | re.DOTALL)
    if m:
        nums = re.findall(r'-?\d+\.?\d*', m.group(1))
        if nums:
            return float(nums[-1])
            
    # 2. ANSWER: 
    m = re.search(r'(?i)answer:\s*(.*?)(?:\n|$)', s)
    if m:
        nums = re.findall(r'-?\d+\.?\d*', m.group(1))
        if nums:
            return float(nums[-1])
            
    # 3. Explicit total equations
    for pat in (
        r'(?i)total score[\s:=]+([-\d.]+)', 
        r'(?i)total points[\s:=]+([-\d.]+)', 
        r'(?i)final score[\s:=]+([-\d.]+)'
    ):
        matches = re.findall(pat, s)
        if matches:
            try:
                return float(matches[-1])
            except ValueError:
                pass

    # 4. Fallback to the very last number
    nums = re.findall(r'-?\d+\.?\d*', s)
    if nums:
        try:
            return float(nums[-1])
        except ValueError:
            pass
    return None