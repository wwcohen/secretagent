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

    In your `focus`, specify the clinical score or formula you need to calculate.

    You should extract and reason about:
    - The exact mathematical formula(s) required to compute the clinical score.
    - The specific clinical parameters and their values extracted from the patient note.

    Structure your response as follows:
    - Formula: [Mathematical expression]
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
    - The specific medical calculator or formula being applied (e.g., CKD-EPI, MELD-Na, Framingham Risk Score).
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
# Public entry point — calculate_medical_value
# =============================================================================

@interface
def calculate_medical_value(patient_note: str, question: str) -> float:
    """
    Calculate a medical value from a patient note and question.

    CRITICAL FORMULAS AND RULES (Only apply if the question specifically asks for that metric):
    1. Maintenance Fluids (mL/hr): Use the 4-2-1 rule: 4 mL/kg/hr for the first 10 kg, 2 mL/kg/hr for the next 10 kg, and 1 mL/kg/hr for any remaining weight. (For patients > 20 kg, this simplifies exactly to: 40 + weight_in_kg).
    2. Albumin Corrected Delta Gap: First find Anion Gap = Na - Cl - HCO3. Then Corrected AG = Anion Gap + 2.5 * (4.0 - Albumin). Finally, Delta Gap = Corrected AG - 12. (Do NOT add HCO3 to the final result).
    3. Albumin Corrected Delta Ratio: Calculate Corrected AG as above. Then Delta Ratio = (Corrected AG - 12) / (24 - HCO3).
    4. Delta Gap (uncorrected): Anion Gap = Na - Cl - HCO3. Delta Gap = Anion Gap - 12.
    5. Free Water Deficit (kg or L): FWD = TBW * ((Serum Na / Desired Na) - 1). TBW = Weight_kg * factor. Factor: Male < 65 is 0.6, Male >= 65 is 0.5, Female < 65 is 0.5, Female >= 65 is 0.45.
    6. Steroid Conversion: Equivalents are: Cortisone=25, Hydrocortisone=20, Prednisone/Prednisolone=5, Methylprednisolone/Triamcinolone=4, Dexamethasone=0.75, Betamethasone=0.75. (Formula: Target_Dose = Current_Dose * Target_Eq / Current_Eq).
    7. LDL Calculated: You MUST calculate using the Friedewald formula. If values are in mg/dL: Total_Cholesterol - HDL - (Triglycerides / 5). Do NOT extract the measured LDL directly from the text.
    8. FIB-4 Index: Formula is (Age * AST) / (Platelets * sqrt(ALT)). CRITICAL: If Platelets are in the thousands (e.g. 294 x10^9/L), you MUST divide the platelet number by 1000 (e.g. use 0.294) to match the required system scale.
    9. Cockcroft-Gault CrCl: Extract the exact Serum Creatinine at the specific admission/event time requested. For normal BMI (<25), use min(Actual Weight, Ideal Body Weight). For obese (BMI >= 25), use Adjusted Body Weight = IBW + 0.4 * (Actual - IBW). IBW(men) = 50 + 2.3*(height_inches - 60). IBW(women) = 45.5 + 2.3*(height_inches - 60). Height in inches = height_cm / 2.54.
    10. MME Calculator: When calculating Morphine Milligram Equivalents for Methadone, use a multiplier of 4.7 (e.g., 20 mg/day * 4.7 = 94.0).
    11. MDRD GFR Formula: 175 * (Cr)^(-1.154) * (Age)^(-0.203) * (0.742 if female) * (1.212 if Black). Be sure to select the correct baseline Cr.
    12. MELD / MELD-Na: If the patient had dialysis at least twice in the past week, set Creatinine to 4.0. The minimum value for Cr, Bilirubin, and INR is 1.0. Maximum MELD score is 40.

    INSTRUCTIONS:
    - Identify the exact variables required from the text.
    - Apply the correct formula step-by-step.
    - Output your final evaluated numerical result enclosed in <answer> tags, like <answer>42.5</answer>.
    """




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