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
4. Provide your final numeric answer

Show your reasoning, then give the final answer as:
ANSWER: <number>"""

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

Return the final numeric answer.

Examples:
>>> calculate_medical_value("A 70-year-old male weighing 80 kg, height 175 cm.", "What is the patient's BMI?")
26.122
>>> calculate_medical_value("A 65-year-old female, BP 130/85 mmHg.", "What is the patient's Mean Arterial Pressure (MAP)?")
100.0
"""


def _build_medical_value_src(func_name: str, docstring: str,
                             return_type: str = 'float') -> str:
    """Build a synthetic source string with the docstring embedded."""
    # Indent the docstring for Python source
    doc_lines = docstring.strip().split('\n')
    indented = '\n'.join('    ' + line for line in doc_lines)
    return (
        f'def {func_name}(patient_note: str, question: str) -> {return_type}:\n'
        f'    """{doc_lines[0]}\n'
        f'\n{indented}\n'
        f'    """\n'
        f'    ...\n'
    )


def calculate_medical_value(patient_note: str, question: str) -> float:
    ...

calculate_medical_value.__doc__ = _CALCULATE_DOCSTRING
calculate_medical_value = interface(calculate_medical_value)
calculate_medical_value.src = _build_medical_value_src(
    'calculate_medical_value', _CALCULATE_DOCSTRING)


_CALCULATE_TEXT_DOCSTRING = """Calculate a medical value from a patient note.

Return the final answer as a string. Numeric answers should contain only the
number, while date, gestational-age, class, or percentage answers should be
returned in the natural format requested by the calculator question.
"""


# Optional non-legacy entry point; apples-to-apples benchmark configs keep using
# calculate_medical_value so they retain the historical float parsing behavior.
def calculate_medical_value_text(patient_note: str, question: str) -> str:
    ...

calculate_medical_value_text.__doc__ = _CALCULATE_TEXT_DOCSTRING
calculate_medical_value_text = interface(calculate_medical_value_text)
calculate_medical_value_text.src = _build_medical_value_src(
    'calculate_medical_value_text', _CALCULATE_TEXT_DOCSTRING, 'str')


# =============================================================================
# State-aware ReAct entry point (mirrors MUSR's _REACT_STATE pattern)
#
# Induced ptools default to `def f(focus: str) -> str` and so cannot see
# the patient note. We stash patient_note/question in a module-level dict
# and let induced helpers reach it via _REACT_STATE["patient_note"].
# react_calculate is a NEW interface (not a rebind of calculate_medical_value)
# to avoid the direct wrapper recursing into itself.
# =============================================================================

_REACT_STATE: dict = {'patient_note': '', 'question': ''}


def _reset_react_state(patient_note: str, question: str) -> None:
    _REACT_STATE['patient_note'] = patient_note
    _REACT_STATE['question'] = question


def react_calculate(patient_note: str, question: str) -> float:
    ...

react_calculate.__doc__ = _CALCULATE_DOCSTRING
react_calculate = interface(react_calculate)
react_calculate.src = _build_medical_value_src(
    'react_calculate', _CALCULATE_DOCSTRING)


def _extract_number_local(value) -> Optional[float]:
    """Local copy of expt._extract_number to avoid circular import."""
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
    m = re.search(r'<answer>\s*([\d.eE+-]+)\s*</answer>', s)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    m = re.search(r'ANSWER:\s*([\d.eE+-]+)', s)
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


def react_calculate_impl(patient_note: str, question: str) -> float:
    """Direct entry that resets state then runs the bound react_calculate."""
    _reset_react_state(patient_note, question)
    try:
        raw = react_calculate(patient_note, question)
    except Exception as ex:
        return float('nan')
    n = _extract_number_local(raw)
    return float('nan') if n is None else n


# =============================================================================
# L2 helper: simulate fallback for distilled workflow
# =============================================================================

def simulate_medical_value(patient_note: str, question: str) -> float:
    ...

simulate_medical_value.__doc__ = _CALCULATE_DOCSTRING
simulate_medical_value = interface(simulate_medical_value)
simulate_medical_value.src = _build_medical_value_src(
    'simulate_medical_value', _CALCULATE_DOCSTRING)


def simulate_medical_value_text(patient_note: str, question: str) -> str:
    ...

simulate_medical_value_text.__doc__ = _CALCULATE_DOCSTRING + """

Return the final answer in text form. For date questions, preserve the
requested date format. For weeks/days questions, preserve the requested
weeks/days format. Do not force date-like answers into numbers.
"""
simulate_medical_value_text = interface(simulate_medical_value_text)
simulate_medical_value_text.src = _build_medical_value_src(
    'simulate_medical_value_text', simulate_medical_value_text.__doc__)


# =============================================================================
# L3/L4 sub-interfaces
# =============================================================================

@interface
def identify_calculator(question: str, available_calculators: list[str]) -> dict:
    """Identify which medical calculator is needed based on the question.

    Analyze the question and match it to one of the available calculators.

    Return a dict with:
    - "calculator_name": exact name from the available list
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
def select_calculator_from_question(question: str, available_calculators: list[str]) -> dict:
    """Select the calculator named by the question.

    This is a deterministic selector in workflow v2. The question in
    MedCalc-Bench names the intended calculator, so selection should be based
    on explicit calculator-name phrases rather than clinical reasoning.

    Return a dict with:
    - "calculator_name": exact local calculator name to use for extraction/compute
    - "official_name": MedCalc-Bench calculator label when known
    - "selector_key": matched selector phrase
    - "supported_by_simple_registry": whether deterministic compute is available
    - "confidence": 1.0 for direct phrase matches, 0.0 otherwise
    """
    ...


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
    - Read field descriptions carefully for what each parameter means
    - For score/grade parameters (e.g. "temperature_score", "ascites_grade"):
      map clinical findings to the numeric score described in the field description
    - Extract numeric values with proper units (age in years, weight in kg, height in cm)
    - Convert units as needed (lbs→kg: ×0.453592, feet/inches→cm, g/L→g/dL: ÷10)
    - For sex: "man"/"male"/"he" → "male", "woman"/"female"/"she" → "female"
    - For boolean conditions: True if present, False if absent
    - If a condition is not mentioned, assume it is absent (False or 0)
    - Include ALL fields, even if the value is False/0/absent

    Return a dict with:
    - "extracted": {"param_name": value, ...} for each field
    - "missing": ["list of values truly not determinable from the note"]

    Examples:
    >>> extract_calculator_values("A 70yo male, 80kg, 175cm, Cr 1.2", "Creatinine Clearance (Cockcroft-Gault)", "age: years, sex: male/female, weight_kg: kg, creatinine_mg_dl: mg/dL", "")
    {'extracted': {'age': 70, 'sex': 'male', 'weight_kg': 80, 'creatinine_mg_dl': 1.2}, 'missing': []}
    """
    ...


@interface
def extract_calculator_values_v2(
    patient_note: str,
    question: str,
    calculator_name: str,
    field_descriptions: str,
    reasoning_context: str,
) -> dict:
    """Extract calculator inputs from a patient note and question.

    You are given:
    - A patient note with clinical information
    - The original question, which may contain calculator-specific rules,
      constants, output units, or values such as target BMI/desired sodium
    - The selected calculator name
    - Calculator-specific field descriptions and formula/schema context
    - Optional reasoning context from a prior analysis stage

    Instructions:
    - Extract inputs only; do not calculate the final answer.
    - Use the exact parameter names from the field descriptions as JSON keys.
    - Use the question when it specifies constants or rules for the calculator.
    - Convert units into the units requested by the field descriptions.
    - For sex: "man"/"male"/"he" -> "male", "woman"/"female"/"she" -> "female".
    - For boolean conditions: True if present, False if absent.
    - Include fields when they are determinable; list truly missing fields.

    Return a dict with:
    - "extracted": {"param_name": value, ...}
    - "missing": ["list of values not determinable from note/question"]

    Examples:
    >>> extract_calculator_values_v2("A 70yo male, 80kg, 175cm, Cr 1.2", "What is the patient's Creatinine Clearance using Cockcroft-Gault?", "Creatinine Clearance (Cockcroft-Gault)", "age: years, sex: male/female, weight_kg: kg, creatinine_mg_dl: mg/dL", "")
    {'extracted': {'age': 70, 'sex': 'male', 'weight_kg': 80, 'height_cm': 175, 'creatinine_mg_dl': 1.2}, 'missing': []}
    """
    ...


@interface
def refine_calculator_values_v2(
    patient_note: str,
    question: str,
    calculator_name: str,
    field_descriptions: str,
    current_values: str,
    missing_values: str,
    reasoning_context: str,
) -> dict:
    """Review and repair a draft calculator-input extraction.

    You are given the original note/question, calculator schema, and a draft
    extraction. Check whether each extracted value is supported by the note or
    question, correct extraction mistakes, and fill missing values if the
    evidence is present.

    Instructions:
    - Extract or repair inputs only; do not calculate the final answer.
    - Prefer values explicitly supported by the note/question.
    - Preserve correct existing values.
    - Correct unit mistakes and obvious type mistakes.
    - If a value is not determinable, leave it out and include it in "missing".

    Return a dict with:
    - "extracted": the full corrected extraction dict
    - "missing": values still not determinable
    - "changed": field names changed from current_values, if any
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

_SELECTOR_TO_OFFICIAL_CACHE: dict[str, str] | None = None


def _normalize_match_text(value: str) -> str:
    """Normalize calculator names/selector keys for phrase matching."""
    value = str(value).lower()
    value = re.sub(r"[’']", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _simple_to_official_name(simple_name: str) -> str:
    """Map a calculator_simple name to the official MedCalc-Bench name."""
    try:
        import official_calculators
        return official_calculators.NAME_MAPPING.get(simple_name, simple_name)
    except Exception:
        return simple_name


def _official_to_simple_name(official_name: str) -> str | None:
    """Map an official MedCalc-Bench name to calculator_simple if supported."""
    import calculator_simple

    signatures = calculator_simple.get_calculator_signatures()
    if official_name in signatures:
        return official_name

    for simple_name in signatures:
        if _simple_to_official_name(simple_name) == official_name:
            return simple_name
    return None


def _selector_to_official_names() -> dict[str, str]:
    """Build selector-key -> official-name mapping from bundled metadata."""
    global _SELECTOR_TO_OFFICIAL_CACHE
    if _SELECTOR_TO_OFFICIAL_CACHE is not None:
        return _SELECTOR_TO_OFFICIAL_CACHE

    from pathlib import Path
    from calculators import identify_calculator as python_identify

    metadata_path = (
        Path(__file__).parent
        / "calculator_implementations"
        / "name_to_python.json"
    )
    mapping: dict[str, str] = {}

    try:
        metadata = json.loads(metadata_path.read_text())
        for item in metadata.values():
            question = item.get("question")
            official_name = item.get("calculator name")
            if not question or not official_name:
                continue
            selector_key = python_identify(question)
            if selector_key and selector_key not in mapping:
                mapping[selector_key] = official_name
    except Exception:
        mapping = {}

    _SELECTOR_TO_OFFICIAL_CACHE = mapping
    return mapping


def _match_simple_name_from_selector(selector_key: str) -> str | None:
    """Fallback mapping from a selector phrase to a local calculator name."""
    import calculator_simple

    selector_norm = _normalize_match_text(selector_key)
    for simple_name, sig in calculator_simple.get_calculator_signatures().items():
        candidates = [simple_name, *sig.get("aliases", [])]
        for candidate in candidates:
            candidate_norm = _normalize_match_text(candidate)
            if not candidate_norm:
                continue
            if selector_norm == candidate_norm:
                return simple_name
            if selector_norm in candidate_norm or (
                len(candidate_norm) > 3 and candidate_norm in selector_norm
            ):
                return simple_name
    return None


def select_calculator_from_question_impl(
    question: str, available_calculators: list[str] | None = None
) -> dict:
    """Direct implementation for workflow v2 calculator selection."""
    from calculators import identify_calculator as python_identify

    selector_key = python_identify(question)
    if not selector_key:
        return {
            "calculator_name": None,
            "official_name": None,
            "selector_key": None,
            "supported_by_simple_registry": False,
            "confidence": 0.0,
        }

    official_name = _selector_to_official_names().get(selector_key)
    simple_name = (
        _official_to_simple_name(official_name) if official_name else None
    )
    if simple_name is None and official_name is None:
        simple_name = _match_simple_name_from_selector(selector_key)
    if official_name is None and simple_name is not None:
        official_name = _simple_to_official_name(simple_name)

    return {
        "calculator_name": simple_name or official_name or selector_key,
        "official_name": official_name,
        "selector_key": selector_key,
        "supported_by_simple_registry": simple_name is not None,
        "confidence": 1.0,
    }


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

def pot_medical_value(patient_note: str, question: str) -> float:
    ...

pot_medical_value.__doc__ = _CALCULATE_DOCSTRING
pot_medical_value = interface(pot_medical_value)
pot_medical_value.src = _build_medical_value_src(
    'pot_medical_value', _CALCULATE_DOCSTRING)


# =============================================================================
# L3 workflow: try PoT code generation, fallback to simulate
# =============================================================================

def pot_workflow(patient_note: str, question: str) -> float:
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

def distilled_workflow(patient_note: str, question: str) -> float:
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
    """Build descriptive field names from calculator docstring.

    Turns bare field names (e.g. 'ascites_grade') into descriptive
    strings (e.g. 'ascites_grade: 0=none, 1=mild/controlled, 2=moderate-severe')
    so that extract_clinical_values knows what to look for.
    """
    import calculator_simple
    doc = calculator_simple.get_calculator_docstring(calc_name) or ''
    sigs = calculator_simple.get_calculator_signatures()
    sig = sigs.get(calc_name, {})
    all_fields = sig.get('required', []) + sig.get('optional', [])

    # Parse "field_name: description" lines from docstring
    field_desc = {}
    for line in doc.split('\n'):
        line = line.strip()
        # Match lines like "    bilirubin: Total bilirubin in mg/dL (e.g., 2.5)"
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


def workflow(patient_note: str, question: str) -> float:
    """L4 workflow: Python-orchestrated with ptools interfaces + LLM extraction.

    Pipeline:
    1. identify_calculator (ptools) — LLM identifies which calculator
    2. _extract_values_two_stage   — LLM extraction with calculator-specific context
    3. compute_calculation (ptools) — Python computes result deterministically
    Fallback: chain-of-thought reasoning for scoring or failed extraction
    """
    import calculator_simple
    from calculators import identify_calculator as python_identify

    signatures = calculator_simple.get_calculator_signatures()
    available = list(signatures.keys())

    # ---- Stage 1: identify_calculator (ptools interface) ----
    calc_name = None
    try:
        result = identify_calculator(question, available)
        if isinstance(result, dict):
            calc_name = result.get("calculator_name")
            if calc_name and calc_name not in signatures:
                calc_lower = calc_name.lower()
                for sig_name in signatures:
                    if calc_lower in sig_name.lower() or sig_name.lower() in calc_lower:
                        calc_name = sig_name
                        break
                else:
                    calc_name = None
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
                return result['result']
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
    """Two-stage extraction: medical reasoning → structured extraction.

    All LLM calls go through @interface ptools.
    """
    # Check if scoring system (needs medical reasoning first)
    is_scoring = any(kw in calculator_name.lower() for kw in [
        'score', 'criteria', 'cha2ds2', 'heart', 'wells',
        'curb', 'sofa', 'apache', 'child-pugh', 'meld', 'centor', 'fever',
        'has-bled', 'rcri', 'charlson', 'caprini', 'blatchford', 'perc'
    ])

    # Stage 1 (scoring only): analyze conditions via interface
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

    # Build field descriptions for the extraction interface
    field_descriptions = '\n'.join(_build_descriptive_fields(calculator_name))

    # Stage 2: Structured extraction via interface
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
            val_lower = value.lower().strip()
            if val_lower in ("true", "yes", "1", "present", "positive"):
                cleaned[key] = True
            elif val_lower in ("false", "no", "0", "absent", "negative"):
                cleaned[key] = False
            else:
                try:
                    cleaned[key] = float(value)
                except ValueError:
                    cleaned[key] = value.strip()
        elif value is not None:
            cleaned[key] = value

    signatures = calculator_simple.get_calculator_signatures()
    sig = signatures.get(calculator_name, {})
    required = sig.get("required", [])
    optional = sig.get("optional", [])

    missing = [v for v in required if v not in cleaned or cleaned[v] is None]

    # Route scoring calculators to reasoning fallback when extraction is
    # unreliable: (a) >=4 optional boolean criteria where extraction
    # frequently gets conditions wrong, or (b) optional fields exist but
    # none were extracted (calculator runs entirely on defaults).
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


# =============================================================================
# L4 v2 workflow: deterministic calculator selection + extraction refinement
# =============================================================================

def _is_date_time_calculator(calculator_name: str | None, official_name: str | None = None) -> bool:
    """Return True for date/weeks-days calculators that should use LLM fallback."""
    names = " ".join(n for n in [calculator_name, official_name] if n)
    n = _normalize_match_text(names)
    return (
        "estimated due date" in n
        or "gestational age" in n
        or "conception" in n
    )


def _is_scoring_calculator_name(calculator_name: str) -> bool:
    """Heuristic used only to decide whether to call the scoring analysis ptool."""
    return any(kw in calculator_name.lower() for kw in [
        'score', 'criteria', 'cha2ds2', 'heart', 'wells',
        'curb', 'sofa', 'apache', 'child-pugh', 'meld', 'centor', 'fever',
        'has-bled', 'rcri', 'charlson', 'caprini', 'blatchford', 'perc'
    ])


def _build_calculator_schema_context(calc_name: str) -> str:
    """Build field descriptions plus lightweight formula/schema context."""
    import calculator_simple

    signatures = calculator_simple.get_calculator_signatures()
    sig = signatures.get(calc_name, {})
    required = sig.get("required", [])
    optional = sig.get("optional", [])
    formula = sig.get("formula", "")
    fields = _build_descriptive_fields(calc_name)

    lines = []
    if formula:
        lines.append(f"Formula: {formula}")
    if required:
        lines.append(f"Required fields: {', '.join(required)}")
    if optional:
        lines.append(f"Optional/defaultable fields: {', '.join(optional)}")
    if fields:
        lines.append("Field descriptions:")
        lines.extend(f"- {field}" for field in fields)
    return "\n".join(lines)


def _coerce_extraction_result(result: Any) -> tuple[dict, list[str]]:
    """Extract the useful dict payload from an LLM extraction response."""
    if not isinstance(result, dict):
        return {}, []

    extracted = result.get("extracted")
    if extracted is None:
        extracted = result.get("values")
    if extracted is None:
        extracted = result
    if not isinstance(extracted, dict):
        extracted = {}

    missing = result.get("missing", [])
    if isinstance(missing, str):
        missing = [m.strip() for m in missing.split(",") if m.strip()]
    if not isinstance(missing, list):
        missing = []
    return extracted, missing


def _extract_values_v2(patient_note: str, question: str, calc_name: str) -> dict:
    """Draft extraction followed by one generic extraction-refinement call."""
    reasoning_context = ""
    clinical_context = f"{patient_note}\n\nQuestion: {question}"

    if _is_scoring_calculator_name(calc_name):
        try:
            reasoning_result = analyze_scoring_conditions(clinical_context, calc_name)
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

    field_descriptions = _build_calculator_schema_context(calc_name)

    extracted: dict = {}
    missing: list[str] = []
    try:
        draft = extract_calculator_values_v2(
            patient_note, question, calc_name, field_descriptions, reasoning_context
        )
        extracted, missing = _coerce_extraction_result(draft)
    except Exception:
        extracted, missing = {}, []

    try:
        refined = refine_calculator_values_v2(
            patient_note,
            question,
            calc_name,
            field_descriptions,
            json.dumps(extracted, default=str),
            ", ".join(missing),
            reasoning_context,
        )
        refined_extracted, _ = _coerce_extraction_result(refined)
        if refined_extracted:
            extracted = refined_extracted
    except Exception:
        pass

    return extracted


def _extract_nested_value_v2(value: Any) -> Any:
    """Accept either plain values or lightweight typed-envelope values."""
    if isinstance(value, dict) and "value" in value:
        return value.get("value")
    return value


def _clean_scalar_v2(value: Any) -> Any:
    """Normalize common LLM scalar formats into calculator-ready values."""
    value = _extract_nested_value_v2(value)

    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, (list, tuple)):
        if not value:
            return None
        numeric_parts = [
            item for item in value
            if isinstance(item, (int, float))
            or (isinstance(item, str) and re.fullmatch(r"-?\d+(?:\.\d+)?", item.strip()))
        ]
        if len(numeric_parts) == 1:
            try:
                return float(numeric_parts[0])
            except (TypeError, ValueError):
                pass
        return value
    if not isinstance(value, str):
        return value

    text = value.strip().strip("\"'")
    text = re.sub(r"</?answer>", "", text, flags=re.IGNORECASE).strip()
    if not text:
        return None

    lowered = text.lower().strip(" .,:;")
    if lowered in {"unknown", "not mentioned", "not stated", "n/a", "na", "none", "null"}:
        return None
    if lowered in {"true", "yes", "y", "1", "present", "positive"}:
        return True
    if lowered in {"false", "no", "n", "0", "absent", "negative"}:
        return False
    if lowered in {"male", "man", "m"}:
        return "male"
    if lowered in {"female", "woman", "f"}:
        return "female"

    numeric_text = text.replace(",", "")
    try:
        return float(numeric_text)
    except ValueError:
        pass

    if "/" not in numeric_text:
        numbers = re.findall(r"-?\d+(?:\.\d+)?", numeric_text)
        if len(numbers) == 1:
            return float(numbers[0])

    return text


def _validate_extracted_values_v2(
    extracted: dict, calculator_name: str
) -> tuple[bool, list[str], dict]:
    """Validate required fields and normalize value types for workflow v2."""
    import calculator_simple

    flattened = {}
    for key, value in (extracted or {}).items():
        if isinstance(value, dict) and "value" in value:
            flattened[key] = value.get("value")
        elif isinstance(value, dict):
            for subkey, subvalue in value.items():
                flattened[subkey] = _extract_nested_value_v2(subvalue)
        else:
            flattened[key] = value

    cleaned = {}
    for key, value in flattened.items():
        clean_value = _clean_scalar_v2(value)
        if clean_value is not None:
            cleaned[key] = clean_value

    signatures = calculator_simple.get_calculator_signatures()
    sig = signatures.get(calculator_name, {})
    required = sig.get("required", [])
    missing = [v for v in required if v not in cleaned or cleaned[v] is None]
    return len(missing) == 0, missing, cleaned


def workflow_v2(patient_note: str, question: str) -> float:
    """Workflow v2: deterministic selector, question-aware extraction, refine, compute.

    This keeps all LLM calls behind interfaces. The LLM extracts/refines
    calculator inputs; deterministic Python still performs supported
    calculations. Date/time calculators and unsupported local calculators use
    the generic medical-value fallback because v1's extraction/compute path is
    structurally weak for those outputs.
    """
    import calculator_simple

    signatures = calculator_simple.get_calculator_signatures()
    available = list(signatures.keys())

    try:
        selected = select_calculator_from_question(question, available)
    except Exception:
        selected = {}

    calc_name = selected.get("calculator_name") if isinstance(selected, dict) else None
    official_name = selected.get("official_name") if isinstance(selected, dict) else None
    supported = bool(selected.get("supported_by_simple_registry")) if isinstance(selected, dict) else False

    if not calc_name:
        return simulate_medical_value_text(patient_note, question)

    if _is_date_time_calculator(calc_name, official_name):
        return simulate_medical_value_text(patient_note, question)

    if not supported or calc_name not in signatures:
        return simulate_medical_value_text(patient_note, question)

    extracted = _extract_values_v2(patient_note, question, calc_name)
    is_valid, _missing, cleaned = _validate_extracted_values_v2(extracted, calc_name)

    if is_valid:
        try:
            result = compute_calculation(calc_name, cleaned)
            if isinstance(result, dict) and result.get("result") is not None:
                return result["result"]
        except Exception:
            pass

    return simulate_medical_value_text(patient_note, question)
