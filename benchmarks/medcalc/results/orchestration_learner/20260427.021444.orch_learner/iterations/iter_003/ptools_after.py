"""Self-contained ptools module wrapping induced helpers.

Hand-derived from the winning induction variant in learned/stateless-oc0-mp3.
Designed to be ingested by OrchestrationLearner via inspect.getsource:
the file MUST have no indirection — every symbol the supervisor sees
lives here.
"""

import re
import ast
import operator
import math
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
        focus (str): The name of the formula or score to calculate (e.g., 'MAP', 'CKD-EPI GFR', 'Serum Osmolality', 'Delta Gap', 'Free Water Deficit').

    Instructions:
        1. Identify all required clinical variables (e.g., SBP, DBP, Cr, Age, Na, Cl, HCO3, Weight).
        2. Extract values from the provided patient note.
        3. State the exact formula being used. 
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
           - GBS (Glasgow-Blatchford): BUN, Hb, SBP, Pulse, Melena (1), Syncope (2), Hepatic disease (2), Heart failure (2).
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
    You are an expert clinical orchestration agent. To ensure absolute accuracy, extract variables carefully and compute step-by-step.
    
    1. Identify the calculation required (formula, score, or date).
    2. Extract all necessary variables from the patient note.
    3. For numerical calculations (scores, formulas, diagnostic values):
       - State the formula and substitute the variables with their numerical values.
       - You MUST wrap the final purely mathematical expression in <math>...</math> tags so the system can evaluate it safely.
       - Do not include variable names or units inside <math>.
       - Example: <math>1 + 2 + 0 + 1</math>
       - Example: <math>141 * min(1.2/0.9, 1)^-1.209 * 0.993^65</math>
    4. For Date calculations (Due Date, Conception, Gestational Age):
       - Do NOT use <math> tags.
       - Calculate the date format exactly as requested.
       - Wrap your final answer in <date>...</date> tags. 
       - Examples: <date>11/24/2005</date> or <date>6 weeks, 0 days</date>
    5. For simple lookups, wrap the number in <answer>...</answer>.

    REFERENCE GUIDE FOR SCORING SYSTEMS:
    - HAS-BLED (Max 9): HTN (SBP>160)=1, Abn Renal=1, Abn Liver=1, Stroke=1, Bleeding=1, Labile INR=1, Age>65=1, Drugs=1, Alcohol=1.
    - Child-Pugh: Bili (<2=1, 2-3=2, >3=3), Albumin (>3.5=1, 2.8-3.5=2, <2.8=3), INR (<1.7=1, 1.7-2.2=2, >2.2=3), Ascites (None=1, Mild=2, Severe=3), Enceph (None=1, Gr1-2=2, Gr3-4=3).
    - Wells PE: DVT signs=3, Alt diag less likely=3, HR>100=1.5, Immobilization/surgery=1.5, Prior DVT/PE=1.5, Hemoptysis=1, Malignancy=1.
    - Wells DVT: Cancer=1, Paralysis/cast=1, Bedridden/surgery=1, Tenderness=1, Leg swollen=1, Calf >3cm larger=1, Pitting edema=1, Collateral veins=1, Prior DVT=1, Alt diag likely=-2.
    - HEART: History (0-2), ECG (0-2), Age (0-2), Risk factors (0-2), Troponin (0-2).
    - GBS (Glasgow-Blatchford): BUN, Hb, SBP, Pulse>=100=1, Melena=1, Syncope=2, Hepatic disease=2, Heart failure=2.
    - PSI/PORT: Age, Nursing home=10, Neoplasia=30, Liver=20, CHF=10, CVD=10, Renal=10, AMS=20, RR>=30=20, SBP<90=20, Temp<35 or >=40=15, HR>=125=10, pH<7.35=30, BUN>=30=20, Na<130=20, Gluc>=250=10, Hct<30=10, pO2<60=10, Pleural effusion=10.
    - APACHE II: Sum points for Age, Temp, MAP, HR, RR, Oxygenation, pH, Na, K, Cr, Hct, WBC, GCS, Chronic Health.
    - Caprini VTE (2005): Sum all risk factors based on assigned point values (1, 2, 3, or 5).
    - Centor (Modified/McIsaac): Age 3-14 (+1), 15-44 (0), >=45 (-1); Exudate/swelling tonsils (+1); Tender/swollen anterior cervical nodes (+1); Temp > 38C (+1); No cough (+1).
    - FeverPAIN: Fever in past 24h (+1), Purulence/exudate (+1), Attend rapidly <=3 days (+1), Severely Inflamed tonsils (+1), No cough/coryza (+1).
    - SIRS: Temp <36 or >38, HR >90, RR >20 or PaCO2 <32, WBC <4000 or >12000 or >10% bands. (1 point each).
    - PERC PE: Age>=50, HR>=100, O2<95%, Hemoptysis, Estrogen use, Prior DVT/PE, Unilateral leg swelling, Surgery/trauma in prior 4 weeks. (1 point each if present).
    - Revised Cardiac Risk Index: High-risk surgery (1), Ischemic heart disease (1), CHF (1), Cerebrovascular disease (1), Insulin-treated diabetes (1), Preop Creatinine >2.0 (1).
    """


def _extract_number(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value)
    if s.startswith('**exception'):
        return None
        
    # 1. Look for <date> tags (allows correct formatting bypass for dates)
    date_match = re.search(r'<date>\s*(.*?)\s*</date>', s, re.IGNORECASE)
    if date_match:
        date_str = date_match.group(1).strip()
        # Ensure exact tuple representation if weeks/days format is utilized
        m = re.search(r'(\d+)\s*weeks?,\s*(\d+)\s*days?', date_str, re.IGNORECASE)
        if m:
            w, d = m.group(1), m.group(2)
            w_str = f"{w} week" if w == "1" else f"{w} weeks"
            d_str = f"{d} day" if d == "1" else f"{d} days"
            return (w_str, d_str)
        return date_str

    # 2. Look for <math> tags to definitively prevent addition/multiplication hallucinations
    math_match = re.search(r'<math>\s*(.*?)\s*</math>', s, re.IGNORECASE | re.DOTALL)
    if math_match:
        raw_expr = math_match.group(1)
        # Handle cases where LLM might provide 'Score = X + Y' or 'X + Y = Z'
        exprs_to_try = raw_expr.split('=')
        for part in exprs_to_try:
            expr = part.replace('[', '(').replace(']', ')').replace('{', '(').replace('}', ')').strip()
            if not expr: 
                continue
            try:
                def eval_expr(node):
                    ops = {
                        ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
                        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
                        ast.Pow: operator.pow, ast.BitXor: operator.pow, ast.Mod: operator.mod,
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
                    elif isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            func_name = node.func.id
                        elif isinstance(node.func, ast.Attribute):
                            func_name = node.func.attr
                        else:
                            raise TypeError("Unsupported func")
                        
                        args = [eval_expr(arg) for arg in node.args]
                        if func_name in ('min', 'max'): return min(*args) if func_name == 'min' else max(*args)
                        if func_name == 'log': return math.log(*args)
                        if func_name == 'exp': return math.exp(*args)
                        if func_name == 'abs': return abs(*args)
                        if func_name == 'sqrt': return math.sqrt(*args)
                    elif isinstance(node, ast.Name):
                        if node.id == 'e': return math.e
                        if node.id == 'pi': return math.pi
                    raise TypeError("Unsupported node")
                
                return float(eval_expr(ast.parse(expr, mode='eval').body))
            except Exception:
                continue

    # 3. Standard fallback extraction
    for pat in (r'<answer>\s*([\d.eE+-]+)\s*</answer>', r'ANSWER:\s*([\d.eE+-]+)'):
        m = re.search(pat, s, re.IGNORECASE)
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