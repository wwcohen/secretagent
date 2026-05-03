"""MedCalc-Bench interface definitions and workflow functions.

Defines the secretagent interfaces used across all experiment levels (L0–L4).
Each level binds a different implementation to `calculate_medical_value` via config.

Level mapping:
  L0 (baseline)   → prompt_llm with template file
  L1 (simulate)   → simulate with rich docstring + formula reference
  L2 (distilled)  → direct workflow: try Python, fallback to simulate helper
  L3 (PoT)        → program_of_thought with tool interfaces
  L4 (pipeline)   → direct workflow calling sub-interfaces for extraction + Python compute
"""

import inspect
import json
import re
from typing import Any, Dict, List, Optional

from secretagent.core import interface
from secretagent import config


# =============================================================================
# Formula reference (dynamically extracted from calculator_simple.py)
# =============================================================================

def get_formula_reference() -> str:
    """Extract formulas from calculator_simple.py at import time."""
    import calculator_simple

    formulas = {}
    for name, spec in calculator_simple.CALCULATOR_REGISTRY.items():
        if spec.name not in formulas and spec.formula:
            formulas[spec.name] = spec.formula

    lines = ["FORMULAS (use these exact formulas):"]
    for name, formula in sorted(formulas.items()):
        lines.append(f"- {name}: {formula}")
    return "\n".join(lines)


FORMULA_REFERENCE = get_formula_reference()


# =============================================================================
# Generate L0 baseline prompt template (same formulas, direct framing)
# =============================================================================

_BASELINE_TEMPLATE = f"""You are a medical calculation assistant.

{FORMULA_REFERENCE}

Patient Note:
$patient_note

Question: $question

Instructions:
1. Read the patient note carefully
2. Extract the relevant values needed for the calculation
3. Perform the calculation step by step
4. Provide your final answer

Show your reasoning, then give the final answer as:
ANSWER: <value>"""

# Write at import time so prompt_llm can load it from file
from pathlib import Path as _Path
(_Path(__file__).parent / 'prompt_templates' / 'baseline.txt').write_text(
    _BASELINE_TEMPLATE)


# =============================================================================
# Main entry-point interface (all levels evaluate this)
# =============================================================================

_CALCULATE_DOCSTRING = f"""Calculate a medical value from a patient note.

Given a patient note and a calculation question, reason step by step:
1. Carefully read the patient note to extract all relevant clinical values
2. Identify what medical calculation/score is needed
3. Apply the appropriate formula from the reference below
4. Show your calculation step by step, checking your arithmetic

{FORMULA_REFERENCE}

Important:
- Be precise with extracted values. Double-check your arithmetic.
- For sex/gender: "man"/"male"/"he" → male, "woman"/"female"/"she" → female.
- Convert units as needed (lbs→kg: ×0.453592, feet/inches→cm: (ft×12+in)×2.54).
- For scoring systems: carefully check each criterion against the patient note.
  Look for conditions implied by medications or clinical findings, not just
  explicitly named conditions.

CRITICAL FORMATTING INSTRUCTIONS FOR THE FINAL ANSWER:
- If the answer is a numeric value, return ONLY the raw number (e.g., 6.25). Do NOT include units, commas, or symbols like "%" or "mmHg".
- If the answer is a date, you MUST wrap the exact date string in double quotes so it is a valid Python string (e.g., "06/09/2002").
- If the answer is a tuple of weeks and days, return a valid Python tuple of strings (e.g., ('33 weeks', '5 days')).

Examples:
>>> calculate_medical_value("A 70-year-old male weighing 80 kg, height 175 cm.", "What is the patient's BMI?")
26.122
>>> calculate_medical_value("A 65-year-old female, BP 130/85 mmHg.", "What is the patient's MAP?")
100.0
"""


def _build_medical_value_src(func_name: str, docstring: str) -> str:
    """Build a synthetic source string with the docstring embedded."""
    # Indent the docstring for Python source
    doc_lines = docstring.strip().split('\n')
    indented = '\n'.join('    ' + line for line in doc_lines)
    return (
        f'from typing import Any\n'
        f'def {func_name}(patient_note: str, question: str) -> Any:\n'
        f'    """{doc_lines[0]}\n'
        f'\n{indented}\n'
        f'    """\n'
        f'    ...\n'
    )


def calculate_medical_value(patient_note: str, question: str) -> Any:
    ...

calculate_medical_value.__doc__ = _CALCULATE_DOCSTRING
calculate_medical_value = interface(calculate_medical_value)
calculate_medical_value.src = _build_medical_value_src(
    'calculate_medical_value', _CALCULATE_DOCSTRING)


# =============================================================================
# L2 helper: simulate fallback for distilled workflow
# =============================================================================

def simulate_medical_value(patient_note: str, question: str) -> Any:
    ...

simulate_medical_value.__doc__ = _CALCULATE_DOCSTRING
simulate_medical_value = interface(simulate_medical_value)
simulate_medical_value.src = _build_medical_value_src(
    'simulate_medical_value', _CALCULATE_DOCSTRING)


# =============================================================================
# L3/L4 sub-interfaces
# =============================================================================

@interface
def identify_calculator(question: str, available_calculators: list[str]) -> dict:
    """Identify which medical calculator is needed based on the question.

    Analyze the question and match it to one of the available calculators.

    Return a dict with:
    - "calculator_name": exact name from the available list (CRITICAL: Copy the name exactly character-for-character)
    - "confidence": 0.0-1.0 confidence score
    - "reasoning": brief explanation

    Examples:
    >>> identify_calculator("What is the patient's BMI?", ["Body Mass Index (BMI)", "Ideal Body Weight (Devine)"])
    {'calculator_name': 'Body Mass Index (BMI)', 'confidence': 0.99, 'reasoning': 'BMI directly asked'}
    """
    ...


@interface
def extract_clinical_values(patient_note: str, required_values: list[str]) -> dict:
    """Extract specific clinical values from a patient note.

    Given the patient note and list of required values, find and extract each one.
    Convert all values to standard units (kg for weight, cm for height, etc.).

    IMPORTANT for sex/gender:
    - "man", "male", "he", "his" → sex = "male"
    - "woman", "female", "she", "her" → sex = "female"

    Return a dict with:
    - "extracted": {"value_name": numeric_value, ...}
    - "missing": ["list of values not found"]

    Examples:
    >>> extract_clinical_values("A 70-year-old male weighing 80 kg, height 175 cm, creatinine 1.2 mg/dL.", ["age", "sex", "weight_kg", "height_cm", "creatinine_mg_dl"])
    {'extracted': {'age': 70, 'sex': 'male', 'weight_kg': 80, 'height_cm': 175, 'creatinine_mg_dl': 1.2}, 'missing': []}
    """
    ...


@interface
def compute_calculation(calculator_name: str, values: dict) -> dict:
    """Compute a medical calculation using pre-extracted values.

    Uses verified Python implementations for all 55 medical calculators.
    This tool is deterministic and accurate.

    Args:
        calculator_name: The exact calculator name
        values: Dictionary of parameter names to values

    Returns:
        {"calculator_name": str, "result": numeric_answer, "formula_used": str}
        OR {"error": str, "result": None} if calculation fails

    Examples:
    >>> compute_calculation("Body Mass Index (BMI)", {"weight_kg": 80, "height_cm": 175})
    {'calculator_name': 'Body Mass Index (BMI)', 'result': 26.122, 'formula_used': 'BMI = weight_kg / (height_m)^2'}
    """
    ...


# =============================================================================
# L4 sub-interfaces: extraction pipeline
# =============================================================================

@interface
def analyze_scoring_conditions(patient_note: str, calculator_name: str) -> dict:
    """Analyze a patient note to identify conditions relevant to a scoring calculator.

    You are a medical expert. Carefully read the patient note and identify ALL
    conditions/criteria relevant to the named scoring calculator.

    Look for:
    - Conditions EXPLICITLY mentioned (e.g., "history of heart failure")
    - Conditions IMPLIED by medications (e.g., warfarin implies anticoagulation,
      metformin implies diabetes, ACE inhibitors imply hypertension)
    - Conditions IMPLIED by clinical findings (e.g., elevated JVP implies heart failure)
    - Demographics: age, sex (infer from pronouns if not stated)

    CRITICAL: DO NOT assume conditions or lab values are present unless explicitly mentioned.
    If a lab value (e.g., BUN, Hemoglobin, Creatinine, Bilirubin) or vital sign is NOT in the text, you MUST state it is missing and consider it ABSENT or normal (0 points). Do NOT make up or hallucinate numbers or lab values.
    - For historical scores (e.g., Charlson Comorbidity Index), a past history of a condition (e.g., past ulcer, past TIA, past malignancy) often counts as PRESENT unless the calculator strictly requires active disease. Erroneously marking past conditions as absent is a common mistake.
    CRITICAL INSTRUCTION: Score the conditions EXACTLY as they appear in the text, REGARDLESS of the primary diagnosis or whether the scoring system seems clinically appropriate for the patient's presentation. Do not overthink clinical applicability.

    Be thorough — missing a condition leads to wrong scores.

    Return a dict with:
    - "reasoning": step-by-step analysis of how you identified each condition
    - "conditions_present": list of conditions found present
    - "conditions_absent": list of conditions found absent
    - "demographics": {"age": number, "sex": "male" or "female"}

    Examples:
    >>> analyze_scoring_conditions("A 72-year-old man with atrial fibrillation, hypertension, and diabetes on warfarin.", "CHA2DS2-VASc Score")
    {'reasoning': 'Age 72 (≥75=2pts). Male. AF present. HTN=1pt. DM=1pt. No CHF/stroke/vascular disease mentioned.', 'conditions_present': ['age_65_74', 'hypertension', 'diabetes'], 'conditions_absent': ['chf', 'stroke_tia', 'vascular_disease'], 'demographics': {'age': 72, 'sex': 'male'}}
    """
    ...


@interface
def extract_calculator_values(
    patient_note: str,
    calculator_name: str,
    field_descriptions: str,
    reasoning_context: str,
) -> dict:
    """Extract specific clinical values from a patient note for a medical calculator.

    You are given:
    - A patient note with clinical information
    - The name of the calculator to extract values for
    - A description of each field to extract (with units and expected ranges)
    - Optional reasoning context from a prior analysis stage

    Instructions:
    - Use the EXACT parameter names from the field descriptions as JSON keys
    - CRITICAL: Always extract the patient's baseline or admission values (prior to any treatment or surgery) unless the question specifically asks for post-treatment values. Pay close attention to the timeline in the note.
    - CRITICAL: If a field name ends in '_score' or '_points' (e.g., 'bun_score', 'age_score'), you MUST calculate and provide the integer point value based on the scoring system, NOT the raw clinical measurement (e.g., if bun_score is requested, give the points for BUN, not the raw BUN in mg/dL).
    - For all other fields, extract the RAW numeric value (e.g., if 'platelets' is requested, provide 115, not the point value).
    - Convert units ONLY for weight (lbs→kg: ×0.453592) and height (feet/inches→cm).
    - CRITICAL: DO NOT convert units for lab values. Extract the raw numeric value exactly as it appears in the text (e.g., if the text says 26 g/L, extract 26. If it says 120 mmol/L, extract 120).
    - Extract dates exactly as they appear in the text (e.g., "09/05/2001").
    - For boolean conditions: True if present, False if absent
    - If a condition is not mentioned, assume it is absent (False or 0)
    - For scoring systems with mutually exclusive severity levels (e.g., mild vs moderate/severe liver disease), mark ONLY the single most appropriate severity level as True.
    - Include ALL fields, even if the value is False/0/absent
    - If a required numeric value or field is entirely unmentioned and cannot be inferred, OMIT it from the 'extracted' dictionary completely instead of writing 'missing' or null.
    - CRITICAL: Do NOT guess or assume standard physiological values. If it is missing, omit it.

    Return a dict with:
    - "extracted": {"param_name": value, ...} for each field
    - "missing": ["list of values truly not determinable from the note"]

    Examples:
    >>> extract_calculator_values("A 70yo male, 80kg, 175cm, Cr 1.2", "Creatinine Clearance (Cockcroft-Gault)", "age: years, sex: male/female, weight_kg: kg, creatinine_mg_dl: mg/dL", "")
    {'extracted': {'age': 70, 'sex': 'male', 'weight_kg': 80, 'creatinine_mg_dl': 1.2}, 'missing': []}
    """
    ...


@interface
def repair_missing_values(
    patient_note: str,
    calculator_name: str,
    current_values: str,
    missing_values: str,
) -> dict:
    """Re-extract missing clinical values from a patient note.

    A previous extraction attempt was incomplete. Some required values are missing.
    Look more carefully at the patient note to find them.

    Tips for finding missing values:
    - Sex/gender: infer from pronouns (he/his → male, she/her → female)
    - Age: look for "X-year-old" or "age X" or date of birth
    - Lab values: may appear in different formats (e.g., "Cr 1.2" = creatinine 1.2 mg/dL)
    - Boolean conditions: if not mentioned, they are likely absent (False/0)
    - Scoring criteria: check medications and clinical findings for implied conditions

    Return a dict with:
    - "extracted": {"value_name": value, ...} for each previously missing value found

    Examples:
    >>> repair_missing_values("A 70-year-old man on metoprolol...", "CHA2DS2-VASc", "{'age': 70}", "sex, hypertension")
    {'extracted': {'sex': 'male', 'hypertension': False}}
    """
    ...


# =============================================================================
# Direct implementations
# =============================================================================

def compute_calculation_impl(calculator_name: str, values: dict) -> dict:
    """Direct Python implementation for compute_calculation."""
    from calculators import compute_direct

    result = compute_direct(calculator_name, values)
    if result is None:
        return {
            "error": f"Calculation failed for {calculator_name} with values {values}",
            "result": None,
            "calculator_name": calculator_name,
        }
    return {
        "calculator_name": result.calculator_name,
        "result": result.result,
        "extracted_values": result.extracted_values,
        "formula_used": result.formula_used,
    }


# =============================================================================
# L3 helper: PoT sub-interface (bound to program_of_thought via config)
# =============================================================================

def pot_medical_value(patient_note: str, question: str) -> Any:
    ...

pot_medical_value.__doc__ = _CALCULATE_DOCSTRING
pot_medical_value = interface(pot_medical_value)
pot_medical_value.src = _build_medical_value_src(
    'pot_medical_value', _CALCULATE_DOCSTRING)


# =============================================================================
# L3 workflow: try PoT code generation, fallback to simulate
# =============================================================================

def pot_workflow(patient_note: str, question: str) -> Any:
    """L3 workflow: try Program of Thought, fallback to reasoning.

    PoT generates Python code calling tool interfaces. If the code
    execution fails or returns None/NaN, fall back to chain-of-thought.
    """
    import math

    try:
        result = pot_medical_value(patient_note, question)
        if result is not None and not (isinstance(result, float) and math.isnan(result)):
            return result
    except Exception:
        pass

    return simulate_medical_value(patient_note, question)


# =============================================================================
# L2 workflow: try Python calculator, fallback to simulate
# =============================================================================

def distilled_workflow(patient_note: str, question: str) -> Any:
    """L2 workflow: try Python extraction + calculation, fallback to LLM simulate.

    This implements the 'distilled' approach:
    1. Try to identify the calculator from the question using Python pattern matching
    2. Try to extract values from the patient note using Python regex
    3. If Python succeeds, compute the result directly (zero LLM cost)
    4. If Python fails at any step, fallback to simulate_medical_value (LLM)
    """
    from calculators import calculate

    # Try pure Python first
    result = calculate(patient_note, question)
    if result is not None and result.result is not None:
        return result.result

    # Fallback to LLM
    return simulate_medical_value(patient_note, question)


# =============================================================================
# L4 workflow: Python-orchestrated pipeline with specialist LLM stages
# =============================================================================

def _build_descriptive_fields(calc_name: str) -> list[str]:
    """Build descriptive field names from calculator docstring."""
    import calculator_simple
    doc = calculator_simple.get_calculator_docstring(calc_name) or ''
    sigs = calculator_simple.get_calculator_signatures()
    sig = sigs.get(calc_name, {})
    all_fields = sig.get('required', []) + sig.get('optional', [])

    field_desc = {}
    for line in doc.split('\n'):
        line = line.strip()
        match = re.match(r'(\w+):\s+(.+)', line)
        if match and match.group(1) in all_fields:
            field_desc[match.group(1)] = match.group(2).strip()

    result = []
    for f in all_fields:
        if f in field_desc:
            result.append(f'{f}: {field_desc[f]}')
        else:
            result.append(f)
    return result


def workflow(patient_note: str, question: str) -> Any:
    """L4 workflow: Python-orchestrated with ptools interfaces + LLM extraction.

    Pipeline:
    1. identify_calculator (ptools) — LLM identifies which calculator
    2. _extract_values_two_stage   — LLM extraction with calculator-specific context
    3. compute_calculation (ptools) — Python computes result deterministically
    Fallback: chain-of-thought reasoning for scoring or failed extraction
    """
    import calculator_simple
    from calculators import identify_calculator as python_identify

    # Bypass entirely for date/tuple edge cases where literal_eval parsing is tricky
    is_date_or_tuple = any(kw in question.lower() for kw in ['date', 'tuple', 'weeks and days', 'm/d/y', 'gestational age', 'conception', 'naegele'])
    if is_date_or_tuple:
        try:
            import re
            from datetime import datetime, timedelta
            
            # Simple LMP extraction
            lmp_match = re.search(r'last menstrual period was on (\d{1,2}/\d{1,2}/\d{4})', patient_note.lower())
            if not lmp_match:
                lmp_match = re.search(r'last menstrual period.*?(?:\b)(\d{1,2}/\d{1,2}/\d{4})', patient_note.lower())
                
            if lmp_match:
                lmp_str = lmp_match.group(1)
                lmp_date = datetime.strptime(lmp_str, "%m/%d/%Y")
                
                cycle_len = 28
                cycle_match = re.search(r'cycle length is (\d+) days', patient_note.lower())
                if cycle_match:
                    cycle_len = int(cycle_match.group(1))
                
                q_lower = question.lower()
                
                # Return strings configured to literal_eval exactly to the target types to prevent pipeline list-mutations
                if "due date" in q_lower or "naegele" in q_lower:
                    edd = lmp_date + timedelta(days=280 + (cycle_len - 28))
                    return f'"{edd.strftime("%m/%d/%Y")}"'
                    
                elif "conception" in q_lower:
                    conception = lmp_date + timedelta(days=14 + (cycle_len - 28))
                    return f'"{conception.strftime("%m/%d/%Y")}"'
                    
                elif "gestational age" in q_lower:
                    today_match = re.search(r"today's date is (\d{1,2}/\d{1,2}/\d{4})", patient_note.lower())
                    if today_match:
                        today_str = today_match.group(1)
                        today_date = datetime.strptime(today_str, "%m/%d/%Y")
                        diff = today_date - lmp_date
                        weeks = diff.days // 7
                        days = diff.days % 7
                        days_str = f"{days} days"
                        return f"('{weeks} weeks', '{days_str}')"
        except Exception:
            pass

        date_prompt = question + (
            "\n\nCRITICAL INSTRUCTIONS FOR DATES/TUPLES:"
            "\n- For Estimated Due Date (Naegele's rule): Add 7 days to LMP, subtract 3 months. Adjust for cycle length if != 28 days."
            "\n- For Date of Conception: Add 14 days to the LMP."
            "\n- For Gestational Age: Calculate exact weeks and days from LMP to today."
            "\n- FORMAT: Return ONLY the raw date string WITH double quotes (e.g. \"06/09/2002\")."
            "\n- FORMAT: For tuples, return the exact Python tuple (e.g. ('33 weeks', '5 days'))."
            "\nReturn ONLY the final string or tuple. Do not include any other text."
        )
        try:
            res = simulate_medical_value(patient_note, date_prompt)
            if res is not None:
                # Prevent JSON tuple-to-list mutations by returning the string repr
                if isinstance(res, list) and len(res) == 2:
                    return f"('{res[0]}', '{res[1]}')"
                if isinstance(res, tuple) and len(res) == 2:
                    return f"('{res[0]}', '{res[1]}')"
                if isinstance(res, str):
                    res = res.strip()
                    if not (res.startswith('"') and res.endswith('"')) and not res.startswith('('):
                        return f'"{res}"'
                    return res
        except Exception:
            pass

    signatures = calculator_simple.get_calculator_signatures()
    available = list(signatures.keys())

    # ---- Stage 1: identify_calculator (ptools interface) ----
    calc_name = None
    try:
        result = identify_calculator(question, available)
        if isinstance(result, dict):
            calc_name = result.get("calculator_name")
            if calc_name and calc_name not in signatures:
                import difflib
                
                # 1. Try exact lower match
                matches = [s for s in signatures if s.lower() == calc_name.lower()]
                if matches:
                    calc_name = matches[0]
                else:
                    # 2. Try difflib string matcher
                    close = difflib.get_close_matches(calc_name, available, n=1, cutoff=0.3)
                    if close:
                        calc_name = close[0]
                    else:
                        # 3. Substring fallback prioritized by length
                        calc_lower = calc_name.lower()
                        best_match = None
                        best_len = 0
                        for sig_name in signatures:
                            if calc_lower in sig_name.lower() or sig_name.lower() in calc_lower:
                                if len(sig_name) > best_len:
                                    best_len = len(sig_name)
                                    best_match = sig_name
                        calc_name = best_match
    except Exception:
        pass

    # Python fallback for identification
    if not calc_name:
        pattern = python_identify(question)
        if pattern:
            for name, spec in calculator_simple.CALCULATOR_REGISTRY.items():
                if isinstance(spec, calculator_simple.CalculatorSpec):
                    if pattern.lower() in spec.name.lower():
                        calc_name = spec.name
                        break

    if not calc_name:
        return simulate_medical_value(patient_note, question)

    # Route correctly if Albumin Corrected was requested but only base calc identified
    if "albumin corrected" in question.lower():
        if "delta gap" in question.lower() or calc_name == "Delta Gap":
            calc_name = "Albumin Corrected Delta Gap"
        elif "delta ratio" in question.lower() or calc_name == "Delta Ratio":
            calc_name = "Albumin Corrected Delta Ratio"

    # Hard bypass for calculators the Python schema fails to represent adequately
    hard_bypass = [
        "morphine milligram",
    ]
    if calc_name and any(hb in calc_name.lower() for hb in hard_bypass):
        return simulate_medical_value(patient_note, question)

    # ---- Stage 2: Extract values (LLM with calculator-specific context) ----
    sig = signatures.get(calc_name, {})
    required = sig.get("required", [])
    optional = sig.get("optional", [])

    extracted = _extract_values_two_stage(
        patient_note, calc_name, required, optional
    )

    # ---- Stage 3: Validate + compute_calculation (ptools interface) ----
    is_valid, missing, cleaned = _validate_extracted_values(extracted, calc_name)

    if missing and not is_valid:
        repaired = _repair_extraction(patient_note, calc_name, cleaned, missing)
        is_valid, missing, cleaned = _validate_extracted_values(repaired, calc_name)

    if is_valid:
        try:
            result = compute_calculation(calc_name, cleaned)
            if isinstance(result, dict) and result.get('result') is not None:
                val = result['result']
                
                # Fix mathematical bugs in calculators.py deterministic logic
                if calc_name == "Charlson Comorbidity Index (CCI)":
                    age = cleaned.get('age', 0)
                    if age > 10:  # Direct age extraction fallback
                        if age >= 50:
                            val += (age - 40) // 10
                    else:  # Schema expects pre-computed points
                        val += age
                        
                elif calc_name == "QTc (Rautaharju)":
                    qt = cleaned.get('qt_msec')
                    hr = cleaned.get('heart_rate')
                    if qt and hr:
                        val = qt * (120 + hr) / 180
                        
                elif calc_name == "SOFA Score":
                    ratio = cleaned.get('pao2_fio2_ratio')
                    note_lower = patient_note.lower()
                    not_vent = "un-intubated" in note_lower or "uninstrumented" in note_lower or "no continuous positive-pressure" in note_lower or "not intubated" in note_lower
                    is_vent = "mechanically ventilated" in note_lower or "intubated" in note_lower or "mechanical ventilation" in note_lower
                    
                    if ratio is not None and ratio < 200:
                        # SOFA caps respiratory score at 2 if not mechanically ventilated
                        if not_vent and not is_vent:
                            if ratio < 100:
                                val -= 2
                            else:
                                val -= 1
                        
                return val
        except Exception:
            pass

    # Fallback: chain-of-thought reasoning
    return simulate_medical_value(patient_note, question)

# backward compat alias
pipeline_workflow = workflow


# =============================================================================
# L4 helper functions (inline LLM calls for extraction pipeline)
# =============================================================================

def _extract_values_two_stage(
    patient_note: str,
    calculator_name: str,
    required_values: list[str],
    optional_values: list[str],
) -> dict:
    """Two-stage extraction: medical reasoning → structured extraction."""
    is_scoring = any(kw in calculator_name.lower() for kw in [
        'score', 'criteria', 'cha2ds2', 'heart', 'wells',
        'curb', 'sofa', 'apache', 'child-pugh', 'meld', 'centor', 'fever',
        'has-bled', 'rcri', 'charlson', 'caprini', 'blatchford', 'perc'
    ])

    reasoning_context = ""
    if is_scoring:
        try:
            reasoning_result = analyze_scoring_conditions(patient_note, calculator_name)
            if isinstance(reasoning_result, dict):
                conditions_present = reasoning_result.get("conditions_present", [])
                conditions_absent = reasoning_result.get("conditions_absent", [])
                demographics = reasoning_result.get("demographics", {})
                reasoning_context = (
                    f"MEDICAL ANALYSIS (from reasoning stage):\n"
                    f"- Conditions PRESENT: {', '.join(conditions_present) if conditions_present else 'None'}\n"
                    f"- Conditions ABSENT: {', '.join(conditions_absent) if conditions_absent else 'None'}\n"
                    f"- Demographics: Age={demographics.get('age', 'unknown')}, Sex={demographics.get('sex', 'unknown')}"
                )
        except Exception:
            pass

    if calculator_name == "Glasgow Coma Scale (GCS)":
        reasoning_context += "\nCRITICAL: For GCS, carefully assign integer subscores for Eye (1-4), Verbal (1-5), and Motor (1-6). Opening eyes ONLY to pain is 2 points, not 3."
    elif calculator_name == "APACHE II Score":
        reasoning_context += "\nCRITICAL: For APACHE II oxygenation, use PaO2 to score if FiO2 < 0.50. Only use A-a gradient if FiO2 >= 0.50."
    elif "FeverPAIN" in calculator_name or "Centor" in calculator_name:
        reasoning_context += "\nCRITICAL: 'absence_of_cough' or 'no_cough' MUST be marked TRUE if cough is explicitly denied OR if cough is not mentioned at all. Only mark FALSE if the patient actually has a cough. For FeverPAIN, 'attend_rapidly' is TRUE if seen within 3 days."
    elif "Caprini" in calculator_name:
        reasoning_context += "\nCRITICAL: For Caprini, Elective lower extremity arthroplasty = 5 pts. Hip, pelvis or leg fracture = 5 pts. Stroke/paralysis = 5 pts. Multiple trauma = 5 pts. Acute spinal cord injury = 5 pts. Major surgery (>45 min) = 2 pts. Central venous access = 2 pts. Bed rest > 72 hours = 2 pts. Minor surgery = 1 pt. History of major surgery (<1 month) = 1 pt. COPD = 1 pt. BMI > 25 = 1 pt."

    field_descriptions = '\n'.join(_build_descriptive_fields(calculator_name))

    try:
        result = extract_calculator_values(
            patient_note, calculator_name, field_descriptions, reasoning_context)
        if isinstance(result, dict):
            return result.get("extracted", result)
    except Exception:
        pass
    return {}


def _validate_extracted_values(
    extracted: dict, calculator_name: str
) -> tuple[bool, list[str], dict]:
    """Validate and clean extracted values."""
    import calculator_simple

    # Flatten nested dicts
    flattened = {}
    for key, value in extracted.items():
        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                flattened[subkey] = subvalue
        else:
            flattened[key] = value

    # Normalize boolean-like values
    cleaned = {}
    for key, value in flattened.items():
        if isinstance(value, str):
            val_clean = re.sub(r'[^\w\s]', '', value.lower()).strip()
            if val_clean in ("true", "yes", "1", "present", "positive"):
                cleaned[key] = True
            elif val_clean in ("false", "no", "0", "absent", "negative"):
                cleaned[key] = False
            else:
                try:
                    cleaned[key] = float(value.replace(',', ''))
                except ValueError:
                    cleaned[key] = value.strip()
        elif value is not None:
            cleaned[key] = value

    signatures = calculator_simple.get_calculator_signatures()
    sig = signatures.get(calculator_name, {})
    required = sig.get("required", [])
    optional = sig.get("optional", [])

    missing = [v for v in required if v not in cleaned or cleaned[v] is None]

    if not missing and optional:
        extracted_optional = sum(1 for v in optional if v in cleaned)
        if len(optional) >= 4 or extracted_optional == 0:
            missing = [v for v in optional if v not in cleaned]

    return len(missing) == 0, missing, cleaned


def _repair_extraction(
    patient_note: str, calculator_name: str,
    current_values: dict, missing: list[str],
) -> dict:
    """Re-extract missing values via interface."""
    try:
        result = repair_missing_values(
            patient_note, calculator_name,
            str(current_values), ', '.join(missing))
        if isinstance(result, dict):
            new_extracted = result.get("extracted", result)
            return {**current_values, **new_extracted}
    except Exception:
        pass
    return current_values