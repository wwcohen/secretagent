"""Self-contained ptools module wrapping induced helpers.

Hand-derived from the winning induction variant in learned/stateless-oc0-mp3.
Designed to be ingested by OrchestrationLearner via inspect.getsource:
the file MUST have no indirection — every symbol the supervisor sees
lives here.
"""

import re
import ast
import operator
from typing import Optional, Any

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
        focus (str): The name of the formula or score to calculate (e.g., 'MAP', 'CKD-EPI GFR', 'Serum Osmolality', 'Delta Gap', 'Free Water Deficit').

    Instructions:
        1. Identify all required clinical variables (e.g., SBP, DBP, Cr, Age, Na, Cl, HCO3, Weight).
        2. Extract values from the provided patient note.
        3. State the exact formula being used. 
           (Reference Guide for formulas:
           - Delta Gap: (Na - Cl - HCO3) - 12
           - Corrected Anion Gap: (Na - Cl - HCO3) + 2.5 * (4.0 - Albumin)
           - Albumin Corrected Delta Ratio: (Corrected Anion Gap - 12) / (24 - HCO3)
           - Free Water Deficit: Male: 0.6 * Weight_kg * ((Na/140) - 1). Female: 0.5 * Weight_kg * ((Na/140) - 1)
           - MDRD GFR: 175 * (Cr)^(-1.154) * (Age)^(-0.203) * (0.742 if female) * (1.212 if Black)
           - CKD-EPI 2021: 142 * min(Cr/k, 1)^a * max(Cr/k, 1)^(-1.200) * 0.9938^Age * (1.012 if female). k=0.7(F)/0.9(M), a=-0.241(F)/-0.302(M)
           - QTc Rautaharju: QT * (120 + HR) / 180
           - Friedewald LDL: Total Chol - HDL - (Triglycerides / 5) for mg/dL. If mmol/L, use Triglycerides / 2.2. Convert mmol/L to mg/dL by multiplying by 38.67
           - MME (Morphine Eq): Hydrocodone x1, Oxycodone x1.5, Hydromorphone x4, Tramadol x0.1
           - Steroid Equivalents: Hydrocortisone 20 = Prednisone 5 = Methylprednisolone 4 = Betamethasone 0.6 = Dexamethasone 0.75
           - MELD Na: MELD = 10 * (0.957*ln(Cr) + 0.378*ln(Bili) + 1.120*ln(INR) + 0.643). If MELD>11, MELD-Na = MELD + 1.32*(137-Na) - [0.033*MELD*(137-Na)])
        4. Substitute the values into the formula explicitly.
        5. Show step-by-step arithmetic to ensure accuracy. Carefully perform multiplication and division before addition and subtraction. 
        6. Provide the final result with appropriate units.

    Returns:
        str: A structured summary of the calculation.
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
    """


@implement_via('simulate')
def apply_clinical_score(focus: str) -> str:
    """
    Extracts clinical variables required by a specified scoring system and calculates the final score based on provided criteria.

    Args:
        focus (str): The name of the scoring system (e.g., 'CHA2DS2-VASc', 'CURB-65', 'Wells Criteria', 'SIRS') and the context/values to be evaluated.

    Process:
        1. Define the parameters/criteria for the requested score. 
           (Reference Guide:
           - HAS-BLED (Max 9): Hypertension (SBP>160)=1, Abnormal Renal=1, Abnormal Liver=1, Stroke=1, Bleeding=1, Labile INR=1, Age >65=1, Drugs (NSAID/antiplatelet)=1, Alcohol=1.
           - Child-Pugh: Bilirubin (<2=1, 2-3=2, >3=3), Albumin (>3.5=1, 2.8-3.5=2, <2.8=3), INR (<1.7=1, 1.7-2.2=2, >2.2=3), Ascites (None=1, Mild=2, Severe=3), Encephalopathy (None=1, Grade 1-2=2, Grade 3-4=3).
           - Wells PE: Clinical signs of DVT=3, Alt diag less likely=3, HR >100=1.5, Immobilization/surgery=1.5, Prior DVT/PE=1.5, Hemoptysis=1, Malignancy=1.
           - Wells DVT: Active cancer=1, Paralysis/cast=1, Bedridden/surgery=1, Tenderness=1, Leg swollen=1, Calf >3cm larger=1, Pitting edema=1, Collateral veins=1, Prior DVT=1, Alt diag likely=-2.
           - HEART Score: History (slight=0, mod=1, high=2), ECG (normal=0, non-spec=1, ST-dep=2), Age (<45=0, 45-64=1, >=65=2), Risk factors (0=0, 1-2=1, >=3=2), Troponin (<=1x=0, 1-3x=1, >3x=2).
           - GBS (Glasgow-Blatchford): BUN mg/dL 50-64=2, 65-79=3, >=80=4. Hb Men: 12-13=1, 10-12=3, <10=6. Hb Women: 10-12=1, <10=6. SBP: 100-109=1, 90-99=2, <90=3. HR >=100=1. Melena=1, Syncope=2, Hepatic disease=2, Heart failure=2.
           - APACHE II: Age >=45=2, 55=3, 65=5, 75=6. Chronic health: non-op/emergency=5, elective=2. Assign points for Temp, MAP, HR, RR, Oxygen, pH, Na, K, Cr, Hct, WBC, GCS.
           - PSI/PORT: Age (M=age, F=age-10). Nursing home=10, Neoplasia=30, Liver=20, CHF=10, CVD=10, Renal=10. AMS=20, RR>=30=20, SBP<90=20, Temp<35 or >=40=15, HR>=125=10, pH<7.35=30, BUN>=30=20, Na<130=20, Gluc>=250=10, Hct<30=10, pO2<60=10, Pleural effusion=10.
           - CHA2DS2-VASc: CHF=1, HTN=1, Age>=75=2, DM=1, Stroke/TIA=2, Vascular disease=1, Age 65-74=1, Female=1.
           - Caprini VTE: Age 41-60=1, 61-74=2, >=75=3. Minor surg=1, Major surg=2. Swollen legs=1, Varicose veins=1, BMI>25=1. Hx DVT/PE=3, Family hx=3, Procoagulant=3. Immobilization=2, Central venous access=2, Malignancy=2. CHF=1, Acute MI=1, COPD=1.
           - Centor: Temp >38C=1, No cough=1, Tender cervical adenopathy=1, Tonsillar exudate/swelling=1, Age 3-14=1, Age 15-44=0, Age >=45=-1.
           - FeverPAIN: Fever in 24h=1, Purulence=1, Attend rapidly <=3 days=1, Severe inflamed tonsils=1, No cough=1.
           - SIRS: Temp >38 or <36=1, HR >90=1, RR >20 or PaCO2 <32=1, WBC >12k or <4k or >10% bands=1.
           - PERC Rule: Positives (Age >=50, HR >=100, O2 <95%, Hemoptysis, Estrogen, Prior DVT/PE, Unilateral leg swelling, Surgery/trauma in 4 wks) = 1 point each.
           - RCRI: High-risk surgery=1, Ischemic heart disease=1, CHF=1, Cerebrovascular disease=1, Insulin=1, Pre-op Cr >2.0=1.
           - Charlson (CCI): MI=1, CHF=1, PVD=1, Cerebrovascular=1, Dementia=1, COPD=1, Rheumatologic=1, Peptic ulcer=1, Mild liver=1, Diabetes w/o complication=1, Diabetes w/ complication=2, Hemiplegia=2, Mod/severe renal=2, Localized tumor=2, Leukemia/Lymphoma=2, Mod/severe liver=3, Metastatic tumor=6, AIDS=6. Age 50-59=1, 60-69=2, 70-79=3, 80-89=4.)
        2. Scan the patient note for values corresponding to each parameter.
        3. Assign points according to standard medical guidelines. Double-check assignments.
        4. Explicitly state the points for each criterion, and show the step-by-step arithmetic to sum them (e.g., 1 + 0 + 2 = 3) to prevent addition errors.

    Returns:
        A structured string summary.
    """


@implement_via('direct')
def compute_calculation_impl(expression: str) -> float:
    """
    Evaluates a mathematical expression securely using Python.
    Use this tool to perform arithmetic securely when calculating scores or formulas to avoid LLM math errors.
    
    Args:
        expression (str): A string containing a mathematical expression, e.g., "1 + 2 + 0 + 1" or "(140 - 130) * 0.6 * 65".
        
    Returns:
        float: The exact computed result.
    """
    def eval_expr(node):
        ops = {
            ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
            ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
            ast.Pow: operator.pow, ast.Mod: operator.mod,
            ast.USub: operator.neg, ast.UAdd: operator.pos
        }
        if hasattr(ast, 'Constant') and isinstance(node, ast.Constant):
            return node.value
        elif hasattr(ast, 'Num') and isinstance(node, getattr(ast, 'Num', type(None))):
            return node.n
        elif isinstance(node, ast.BinOp):
            return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
        elif isinstance(node, ast.UnaryOp):
            return ops[type(node.op)](eval_expr(node.operand))
        else:
            raise TypeError("Unsupported node")
            
    try:
        return float(eval_expr(ast.parse(expression, mode='eval').body))
    except Exception:
        return float('nan')


# =============================================================================
# Public entry point — calculate_medical_value
# =============================================================================

@interface
def calculate_medical_value(patient_note: str, question: str) -> float:
    """Calculate a medical value from a patient note and question.

    CRITICAL INSTRUCTIONS:
    You are an expert clinical orchestration agent. To ensure absolute accuracy, you MUST NOT calculate the final answer directly in a single step.
    Instead, you MUST delegate the step-by-step extraction and calculation to the specialized tools provided.
    
    1. Analyze the question to determine the required calculation.
    2. Call ONE of the following tools:
       - `apply_clinical_score`: For clinical scoring systems (HAS-BLED, APACHE II, Child-Pugh, Wells, HEART, GBS, PSI, Caprini, PERC, SIRS, Centor, FeverPAIN, RCRI, Charlson).
       - `calculate_clinical_score`: For formulas (Delta Gap, Free Water Deficit, MELD Na, Framingham, CKD-EPI, MDRD, QTc, LDL, Albumin Corrected Delta Ratio).
       - `compute_clinical_value`: For diagnostic values or unit conversions (MME, Steroid Conversion, Dates).
    3. Pass the full patient note and a clear description of what needs to be calculated to the tool.
    4. You may use `compute_calculation_impl` to evaluate complex arithmetic or sum points if needed.
    5. VERY IMPORTANT: For clinical scores, double-check your addition step-by-step.
    6. Return the final numerical result. If the question asks for a date, output it EXACTLY as MM/DD/YYYY. If it asks for a tuple, output it EXACTLY as (X weeks, Y days).
    """


def _extract_number(value) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value)
    if s.startswith('**exception'):
        return None

    # First try explicit answer tags
    for pat in (r'<answer>\s*(.*?)\s*</answer>', r'ANSWER:\s*(.*)'):
        m = re.search(pat, s, re.IGNORECASE | re.DOTALL)
        if m:
            ans = m.group(1).strip()
            # Try date
            date_m = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', ans)
            if date_m:
                return date_m.group(1)
            # Try tuple
            gest_m = re.search(r"(\d+)\s*weeks?.*?(\d+)\s*days?", ans, re.IGNORECASE)
            if gest_m:
                return (f"{gest_m.group(1)} weeks", f"{gest_m.group(2)} days")
            # Try float
            nums = re.findall(r'-?\d+\.?\d*', ans)
            if nums:
                try:
                    return float(nums[-1])
                except ValueError:
                    pass

    # If no explicit tag, find the positions of the last date, tuple, and float
    date_matches = list(re.finditer(r'\b(\d{2}/\d{2}/\d{4})\b', s))
    tuple_matches = list(re.finditer(r"(\d+)\s*weeks?.*?(\d+)\s*days?", s, re.IGNORECASE))
    float_matches = list(re.finditer(r'-?\d+\.?\d*', s))

    last_date_pos = date_matches[-1].end() if date_matches else -1
    last_tuple_pos = tuple_matches[-1].end() if tuple_matches else -1
    last_float_pos = float_matches[-1].end() if float_matches else -1

    # Safely extract Date or Tuple only if it appears after (or is part of) the final float
    if last_date_pos >= last_float_pos and date_matches:
        return date_matches[-1].group(1)
    
    if last_tuple_pos >= last_float_pos and tuple_matches:
        return (f"{tuple_matches[-1].group(1).lower()} weeks", f"{tuple_matches[-1].group(2).lower()} days")

    # Otherwise fallback to standard float extraction
    if float_matches:
        try:
            return float(float_matches[-1].group())
        except ValueError:
            pass

    return None