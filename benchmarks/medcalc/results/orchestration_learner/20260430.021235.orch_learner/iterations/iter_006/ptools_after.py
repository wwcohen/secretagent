"""Self-contained ptools module wrapping induced helpers.

Hand-derived from the winning induction variant in learned/formula-4pc-pro-mp3.
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
# Induced ptools (inlined from learned/formula-4pc-pro-mp3)
# =============================================================================

@implement_via('simulate')
def perform_manual_calculation(focus: str) -> str:
    """
    Use this tool to evaluate a mathematical formula manually by plugging in extracted clinical values.

    Provide the tool with a `focus` detailing the specific calculation or score needed. The tool will:
    - State the correct formula to be used.
    - Identify the required variables and their values from the patient's note.
    - Perform unit conversions if needed (e.g., cm to inches).
    - Execute the math step-by-step to show the intermediate arithmetic operations.

    Pay close attention to operator precedence (order of operations), proper unit alignment between different lab values, and the standard rounding or precision requirements for the given clinical score.

    The response should be structured with the formula, the variables, the step-by-step arithmetic, and the final evaluated result.

    Returns:
    Formula: FENa = (UNa * SCr) / (SNa * UCr) * 100
    Variables: UNa = 64 mEq/L, SCr = 1.73 mg/dL, SNa = 98 mEq/L, UCr = 114 mg/dL
    Calculation:
    1. UNa * SCr = 64 * 1.73 = 110.72
    2. SNa * UCr = 98 * 114 = 11172
    3. 110.72 / 11172 = 0.00991048
    4. 0.00991048 * 100 = 0.991048
    Final Result: 0.99%
    """


@implement_via('simulate')
def perform_fallback_manual_calculation(focus: str) -> str:
    """
    Use this tool to structure a fallback manual calculation when an automated clinical calculator fails or is unavailable.

    In your `focus`, specify the clinical score or equation you need to calculate.

    You should extract and reason about:
    - The exact mathematical formula(s) required to compute the clinical score.
    - The specific clinical parameters and their values extracted from the patient note.

    Structure your response as follows:
    - Formula: [Mathematical equation]
    - Variables: [Extracted clinical parameters and their units]
    - Steps: [Step-by-step arithmetic substitution and resolution]
    - Final Result: [The manually calculated final value]

    Pay close attention to required unit conversions (e.g., height in cm to inches), mathematical constants, the correct order of operations, and any rounding rules specific to the clinical formula.

    Returns:
    Formula: Corrected Na = Na + 0.024 * (Glucose - 100)
    Variables: Na = 131 mEq/L, Glucose = 361 mg/dL
    Steps:
    1) Glucose - 100 = 361 - 100 = 261
    2) 0.024 * 261 = 6.264
    3) 131 + 6.264 = 137.264
    Final Result: 137.26
    """


@implement_via('simulate')
def report_final_calculation_result(focus: str) -> str:
    """
    Use this tool to report the final result of a medical calculation.

    What to reason about:
    - The specific clinical values extracted from the patient note (e.g., age, sex, creatinine level, blood pressure, etc.).
    - The specific medical calculator or equation being applied (e.g., CKD-EPI, MELD-Na, Framingham Risk Score).
    - The final computed numerical value.

    How the response should be structured:
    Write a short narrative summarizing the patient's relevant clinical inputs and the formula applied, concluding with the final calculated score or value.

    What the agent should pay attention to:
    - Ensure that all required variables for the specific formula are explicitly mentioned and correctly extracted.
    - Verify that the correct formula variation was chosen based on the patient's demographics (e.g., age, sex).
    - Ensure the final numerical result is presented in the correct units and with the appropriate decimal precision.

    Returns:
    A string containing the narrative summary of the clinical inputs and calculation, followed by the final numerical result.

    Example Return:
    The patient was 53 years old and had a serum creatinine of 2.0 mg/dL upon admission. Using these values in the MDRD GFR formula for a male patient, the calculated glomerular filtration rate is 35.125 mL/min/1.73 m2.

    <function_result>
    35.125
    </function_result>
    """


# =============================================================================
# Explicit High-Precision Math Tools
# =============================================================================

@implement_via('direct')
def use_rautaharju_formula(heart_rate_bpm: float, qt_interval_msec: float) -> float:
    """
    Use this tool ONLY to calculate the Corrected QT interval (QTc) using the Rautaharju Formula.
    Pass the heart rate in bpm and QT interval in msec exactly as found in the text.
    """
    hr = float(heart_rate_bpm)
    qt = float(qt_interval_msec)
    return float(qt * (120 + hr) / 180)

@implement_via('direct')
def use_framingham_qtc_formula(heart_rate_bpm: float, qt_interval_msec: float) -> float:
    """
    Use this tool ONLY to calculate the Corrected QT interval (QTc) using the Framingham Formula.
    Pass the heart rate in bpm and QT interval in msec exactly as found in the text.
    """
    hr = float(heart_rate_bpm)
    qt = float(qt_interval_msec)
    return float(qt + 154 * (1 - 60 / hr))

@implement_via('direct')
def use_maintenance_fluids_rule(weight_kg: float) -> float:
    """
    Use this tool ONLY to calculate the patient's maintenance fluid in mL/hr.
    Extract the patient's weight in kg and pass it to this tool.
    It automatically applies the 4-2-1 rule.
    """
    w = float(weight_kg)
    if w <= 10:
        return float(w * 4)
    elif w <= 20:
        return float(40 + (w - 10) * 2)
    else:
        return float(60 + (w - 20) * 1)

@implement_via('direct')
def calculate_albumin_corrected_delta_ratio(sodium: float, chloride: float, bicarbonate: float, albumin: float) -> float:
    """
    Use this tool ONLY to calculate the Albumin Corrected Delta Ratio.
    Provide serum sodium, chloride, bicarbonate, and albumin levels.
    """
    na = float(sodium)
    cl = float(chloride)
    hco3 = float(bicarbonate)
    alb = float(albumin)
    if alb > 10:
        alb = alb / 10.0
    ag = na - (cl + hco3)
    corrected_ag = ag + 2.5 * (4.0 - alb)
    return float((corrected_ag - 12.0) / (24.0 - hco3))

@implement_via('direct')
def calculate_steroid_conversion_exact(current_dose_mg: float, current_drug: str, target_drug: str) -> float:
    """
    Use this tool ONLY to calculate equivalent steroid dosages.
    Recognized drugs: 'Betamethasone', 'Dexamethasone', 'Hydrocortisone', 'Prednisolone', 'Prednisone', 'Methylprednisolone'
    """
    dose = float(current_dose_mg)
    equivalents = {
        'betamethasone': 0.75,
        'dexamethasone': 0.75,
        'hydrocortisone': 20.0,
        'prednisolone': 5.0,
        'prednisone': 5.0,
        'methylprednisolone': 4.0,
    }
    cur = str(current_drug).lower().strip()
    tgt = str(target_drug).lower().strip()
    
    cur_val = None
    tgt_val = None
    for k, v in equivalents.items():
        if k in cur: cur_val = v
        if k in tgt: tgt_val = v
        
    if cur_val and tgt_val:
        ratio = round(tgt_val / cur_val, 2)
        return float(dose * ratio)
    return 0.0

@implement_via('direct')
def calculate_cockcroft_gault(age: int, weight_kg: float, height_cm: float, serum_creatinine_mg_dl: float, is_female: bool) -> float:
    """
    Use this tool ONLY to calculate Creatinine Clearance using the Cockcroft-Gault Equation.
    It automatically calculates Ideal Body Weight (IBW) and Adjusted Body Weight based on BMI.
    """
    age_val = int(float(age))
    w = float(weight_kg)
    h = float(height_cm)
    scr = float(serum_creatinine_mg_dl)
    if isinstance(is_female, str):
        female_val = is_female.lower() in ['true', '1', 'yes', 't', 'female', 'f']
    else:
        female_val = bool(is_female)
        
    height_inches = h / 2.54
    if female_val:
        ibw = 45.5 + 2.3 * (height_inches - 60)
    else:
        ibw = 50.0 + 2.3 * (height_inches - 60)
    
    height_m = h / 100.0
    bmi = w / (height_m * height_m)
    
    if bmi >= 25.0:
        adj_w = ibw + 0.4 * (w - ibw)
    elif bmi < 18.5:
        adj_w = w
    else:
        adj_w = min(ibw, w)
        
    crcl = ((140 - age_val) * adj_w) / (72 * scr)
    if female_val:
        crcl *= 0.85
        
    return float(crcl)


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