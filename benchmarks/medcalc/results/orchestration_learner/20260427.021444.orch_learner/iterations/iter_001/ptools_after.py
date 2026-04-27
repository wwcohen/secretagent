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
        focus (str): The patient note and the formula to calculate (e.g., 'MAP', 'CKD-EPI GFR', 'Free Water Deficit', 'Delta Gap', 'MELD Na', 'LDL Calculated').

    Instructions:
        1. Identify all required clinical variables (e.g., SBP, DBP, Cr, Age, Na).
        2. Extract values from the provided patient note. Pay attention to units.
        3. State the precise standard formula being used.
        4. Show step-by-step arithmetic to ensure accuracy.
        5. Output the final numerical result inside <answer> tags.

    Returns:
        str: A structured summary of the calculation, e.g.:
        'Calculation: Mean Arterial Pressure (MAP)
        Variables: SBP=120 mmHg, DBP=80 mmHg
        Formula: (2 * DBP + SBP) / 3
        Steps: (2 * 80 + 120) / 3 = (160 + 120) / 3 = 280 / 3
        Result: 93.33 mmHg
        <answer>93.33</answer>'
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
        - Final numerical result inside <answer> tags.

    Example Output:
        "Variables: Weight=18kg. Formula: 4-2-1 rule. Calculation: (10kg*4) + (8kg*2) = 40+16 = 56. Result: 56 ml/hr.
        <answer>56</answer>"
    """


@implement_via('simulate')
def apply_clinical_score(focus: str) -> str:
    """
    Extracts clinical variables required by a specified scoring system and calculates the final score based on provided criteria.

    Args:
        focus (str): The patient note and the name of the scoring system (e.g., 'CHA2DS2-VASc', 'CURB-65', 'Wells Criteria', 'SIRS').

    Process:
        1. Identify the requested scoring system.
        2. Explicitly list all standard clinical criteria and their exact point values for the identified score before attempting to assign them.
        3. Scan the patient note for values corresponding to each criterion.
        4. Assign points strictly according to standard medical guidelines.
        5. Carefully sum the points to produce the final score. Double check the addition!
        6. Output the final numerical score inside <answer> tags.

    Returns:
        A structured string summary:
        "Score Name: [Name]
        - [Criterion 1]: [Value] ([Points] pts)
        - [Criterion 2]: [Value] ([Points] pts)
        Total: [Sum]
        <answer>[Sum]</answer>"
    """


@implement_via('simulate')
def verify_calculation(task_context: str, draft_reasoning: str) -> str:
    """
    You are an expert medical calculator checker.
    
    Review the 'task_context' and the 'draft_reasoning'.
    
    Instructions:
    1. Verify that the correct medical formula or standard clinical scoring criteria were used.
    2. Recalculate all math step-by-step. Summation errors are very common in scoring systems (e.g., APACHE II, HAS-BLED, Child-Pugh) - manually verify the point assignments and the final addition!
    3. Correct any formula, variable extraction, or arithmetic errors.
    4. Provide the final corrected numerical result inside <answer> tags, e.g., <answer>42.5</answer>.
    """


def compute_calculation_impl(expression: str) -> float:
    """
    Evaluates a mathematical expression safely.
    Useful for ensuring arithmetic is correct without relying on LLM math.
    """
    try:
        import ast
        import operator
        operators = {
            ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
            ast.Div: operator.truediv, ast.Pow: operator.pow, ast.BitXor: operator.xor,
            ast.USub: operator.neg
        }
        def eval_node(node):
            if isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.BinOp):
                return operators[type(node.op)](eval_node(node.left), eval_node(node.right))
            elif isinstance(node, ast.UnaryOp):
                return operators[type(node.op)](eval_node(node.operand))
            else:
                raise TypeError(node)
        return float(eval_node(ast.parse(expression, mode='eval').body))
    except Exception:
        return 0.0


# =============================================================================
# Public entry point — calculate_medical_value
# =============================================================================

@interface
def calculate_medical_value(patient_note: str, question: str) -> float:
    """Calculate a medical value from a patient note and question."""
    q_lower = question.lower()
    focus = f"Patient Note:\n{patient_note}\n\nTask: {question}"
    
    formula_kws = ["deficit", "gap", "ratio", "gfr", "bmi", "meld", "ldl", "qtc", "framingham", "fib-4", "fibrosis"]
    score_kws = ["score", "criteria", "index", "perc", "has-bled", "apache", "child-pugh", "sirs", "caprini", "feverpain", "heart", "charlson", "wells", "curb", "gbs", "glasgow-blatchford"]
    
    # 1. Deterministic Python-based routing to ensure the induced tools are ACTUALLY used
    if any(kw in q_lower for kw in formula_kws):
        draft = calculate_clinical_score(focus)
    elif any(kw in q_lower for kw in score_kws):
        draft = apply_clinical_score(focus)
    else:
        draft = compute_clinical_value(focus)
        
    # 2. Safety verification pass to catch arithmetic errors (especially summation in scoring)
    verified = verify_calculation(focus, draft)
    
    # 3. Robust extraction falling back safely
    ans = _extract_number(verified)
    if ans is not None:
        return float(ans)
        
    ans = _extract_number(draft)
    if ans is not None:
        return float(ans)
        
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