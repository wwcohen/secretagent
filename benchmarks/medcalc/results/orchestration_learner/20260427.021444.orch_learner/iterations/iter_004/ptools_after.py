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
           (Formula Reference:
           - Free Water Deficit: TBW * ((Serum Na / Desired Na) - 1). TBW = Weight(kg) * factor (0.6 for men <65, 0.5 for men >=65 or women <65, 0.45 for women >=65).
           - Delta Gap: Anion Gap - 12. Where Anion Gap = Na - Cl - HCO3.
           - Albumin Corrected Anion Gap: Anion Gap + 2.5 * (4.4 - Albumin in g/dL). (If albumin is in g/L, divide by 10).
           - LDL Calculated (Friedewald): Total Cholesterol - HDL - (Triglycerides / 5). (Use mg/dL).
           - QTc Rautaharju: QT * (120 + HR) / 180.
           - MELD-Na: MELD + 1.32 * (137 - Na) - [0.033 * MELD * (137 - Na)].)
        4. Substitute the values into the formula explicitly.
        5. Show step-by-step arithmetic to ensure accuracy. Carefully perform multiplication and division before addition and subtraction. 
        6. Provide the final result with appropriate units.

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
           (Reference Guide:
           - HAS-BLED (Max 9): Hypertension (SBP>160) = 1, Abnormal Renal = 1, Abnormal Liver = 1, Stroke = 1, Bleeding = 1, Labile INR = 1, Age >65 = 1, Drugs (NSAID/antiplatelet) = 1, Alcohol = 1.
           - Child-Pugh: Bilirubin (<2=1, 2-3=2, >3=3), Albumin (>3.5=1, 2.8-3.5=2, <2.8=3), INR (<1.7=1, 1.7-2.2=2, >2.2=3), Ascites (None=1, Mild=2, Severe=3), Encephalopathy (None=1, Grade 1-2=2, Grade 3-4=3).
           - Wells PE: Clinical signs of DVT (3), Alt diag less likely (3), HR >100 (1.5), Immobilization/surgery (1.5), Prior DVT/PE (1.5), Hemoptysis (1), Malignancy (1).
           - Wells DVT: Active cancer (1), Paralysis/cast (1), Bedridden/surgery (1), Tenderness (1), Leg swollen (1), Calf >3cm larger (1), Pitting edema (1), Collateral veins (1), Prior DVT (1), Alt diag likely (-2).
           - HEART Score: History (0-2), ECG (0-2), Age (0-2), Risk factors (0-2), Troponin (0-2).
           - Caprini Score: Age 41-60 (1), 61-74 (2), >=75 (3). Minor surgery (1), Major surgery (2). Swollen legs (1), Varicose veins (1), BMI>25 (1), Oral contraceptives/HRT (1), Pregnancy (1). Hx of prior DVT/PE (3), Family hx DVT/PE (3). Elective arthroplasty (5), Hip/leg fracture (5), Stroke <1mo (5), Multiple trauma <1mo (5).
           - Centor Score (McIsaac): Age 3-14 (+1), 15-44 (0), >=45 (-1). Exudate/swelling on tonsils (+1). Tender/swollen anterior cervical lymph nodes (+1). Fever >38C (+1). Absence of cough (+1).
           - FeverPAIN: Fever in past 24h (+1), Purulence on tonsils (+1), Attend rapidly (<=3 days) (+1), Severely inflamed tonsils (+1), No cough/coryza (+1).
           - SIRS Criteria: Temp >38C or <36C (+1), HR >90 (+1), RR >20 or PaCO2 <32 (+1), WBC >12k or <4k or >10% bands (+1).
           - PERC Rule: Age >=50 (+1), HR >=100 (+1), O2 sat <95% (+1), Unilateral leg swelling (+1), Hemoptysis (+1), Recent surgery/trauma (+1), Prior DVT/PE (+1), Exogenous estrogen (+1).
           - RCRI: High-risk surgery (+1), Ischemic heart disease (+1), CHF (+1), Cerebrovascular disease (+1), Insulin therapy (+1), Creatinine >2.0 (+1).
           - Charlson Comorbidity Index (CCI): Age 50-59 (1), 60-69 (2), 70-79 (3), 80+ (4). MI (1), CHF (1), PVD (1), CVA/TIA (1), Dementia (1), COPD (1), Connective tissue disease (1), Peptic ulcer (1), Mild liver disease (1), Diabetes w/o complications (1). Hemiplegia (2), Moderate/severe renal (2), Diabetes w/ end-organ (2), Tumor w/o metastasis (2), Leukemia (2), Lymphoma (2). Moderate/severe liver (3). Metastatic tumor (6), AIDS (6).
           - GBS (Glasgow-Blatchford): BUN >=18.2 mg/dL (1-6 pts). Hb <12 g/dL (men) or <10 g/dL (women) (1-6 pts). SBP <110 (1-3 pts). HR >=100 (1). Melena (1), Syncope (2), Hepatic disease (2), Heart failure (2).
           - APACHE II: Age, Temp, MAP, HR, RR, Oxygenation, Arterial pH, Na, K, Cr, Hct, WBC, GCS, Chronic Health.
           - PSI/PORT: Age, Nursing home (10), Neoplasia (30), Liver (20), CHF (10), CVD (10), Renal (10), AMS (20), RR>=30 (20), SBP<90 (20), Temp<35 or >=40 (15), HR>=125 (10), pH<7.35 (30), BUN>=30 (20), Na<130 (20), Gluc>=250 (10), Hct<30 (10), pO2<60 (10), Pleural effusion (10).
           - CHA2DS2-VASc: CHF (1), HTN (1), Age>=75 (2), DM (1), Stroke/TIA (2), Vascular disease (1), Age 65-74 (1), Female (1).)
        2. Scan the patient note for values corresponding to each parameter.
        3. Assign points according to standard medical guidelines. Double-check assignments.
        4. Explicitly state the points for each criterion, and show the step-by-step arithmetic to sum them (e.g., 1 + 0 + 2 = 3) to prevent addition errors.

    Returns:
        A structured string summary:
        "Score Name: [Name]
    - [Criterion 1]: [Value] ([Points] pts)
    - [Criterion 2]: [Value] ([Points] pts)
    Steps: [Point] + [Point] + ...
    Total: [Sum]"
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
       - `apply_clinical_score`: For evaluating clinical scoring systems (e.g., HAS-BLED, APACHE II, Caprini, Centor, CCI, Wells, HEART, PSI, etc.).
       - `calculate_clinical_score`: For standard formulas (e.g., Delta Gap, Free Water Deficit, LDL Calculated, MELD Na).
       - `compute_clinical_value`: For diagnostic values, unit conversions, or dates.
    3. Pass the full patient note and a clear description of what needs to be calculated to the tool.
    4. You may use `compute_calculation_impl` to evaluate complex arithmetic or sum points if needed.
    5. You MUST output your final extracted answer enclosed in <answer> tags, e.g., <answer>15.0</answer> or <answer>11/24/2005</answer>.
    """


def _extract_number(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, tuple):
        return value
    s = str(value)
    if s.startswith('**exception'):
        return None

    # Safely prioritize extraction from explicit answer tags
    ans_str = None
    for pat in (r'<answer>\s*(.+?)\s*</answer>', r'ANSWER:\s*(.+)'):
        m = re.search(pat, s, re.DOTALL | re.IGNORECASE)
        if m:
            ans_str = m.group(1).strip()
            break

    if ans_str:
        # Check for dates/tuples specifically within the answer block
        import ast
        try:
            m_tuple = re.search(r"\(\s*'\d+\s+weeks?'\s*,\s*'\d+\s+days?'\s*\)", ans_str)
            if m_tuple:
                return ast.literal_eval(m_tuple.group(0))
        except Exception:
            pass

        m_text_gest = re.search(r"(\d+)\s+weeks?(?:,\s*|\s+and\s+|\s+)(\d+)\s+days?", ans_str, re.IGNORECASE)
        if m_text_gest:
            return (f"{m_text_gest.group(1)} weeks", f"{m_text_gest.group(2)} days")

        m_date = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", ans_str)
        if m_date:
            return m_date.group(1)

        nums_ans = re.findall(r'-?\d+\.?\d*', ans_str)
        if nums_ans:
            try:
                return float(nums_ans[-1])
            except ValueError:
                pass

    # Fallbacks in case the LLM forgot the tag entirely but output a date/tuple at the VERY END.
    try:
        m_tuple = re.search(r"\(\s*'\d+\s+weeks?'\s*,\s*'\d+\s+days?'\s*\)\s*$", s.strip())
        if m_tuple:
            return ast.literal_eval(m_tuple.group(0))
    except Exception:
        pass

    m_date = re.search(r"\b(\d{2}/\d{2}/\d{4})\b\s*(\.)?\s*$", s.strip())
    if m_date:
        return m_date.group(1)

    # Standard float fallback logic for the raw text
    nums = re.findall(r'-?\d+\.?\d*', s)
    if nums:
        try:
            return float(nums[-1])
        except ValueError:
            pass
            
    return None