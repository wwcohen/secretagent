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
from secretagent.llm_util import llm


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

Given a patient note and a calculation question:
1. Carefully read the patient note to extract all relevant clinical values
2. Identify what medical calculation/score is needed
3. Apply the appropriate formula from the reference below
4. Show your calculation step by step

{FORMULA_REFERENCE}

Important: Be precise with extracted values. Double-check your arithmetic.
For sex/gender: "man"/"male"/"he" → male, "woman"/"female"/"she" → female.
Convert units as needed (lbs→kg: ×0.453592, feet/inches→cm: (ft×12+in)×2.54).

Return ONLY the final numeric answer.

Examples:
>>> calculate_medical_value("A 70-year-old male weighing 80 kg, height 175 cm.", "What is the patient's BMI?")
26.122
>>> calculate_medical_value("A 65-year-old female, BP 130/85 mmHg.", "What is the patient's Mean Arterial Pressure (MAP)?")
100.0
"""


def _build_medical_value_src(func_name: str, docstring: str) -> str:
    """Build a synthetic source string with the docstring embedded."""
    # Indent the docstring for Python source
    doc_lines = docstring.strip().split('\n')
    indented = '\n'.join('    ' + line for line in doc_lines)
    return (
        f'def {func_name}(patient_note: str, question: str) -> float:\n'
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


# =============================================================================
# L2 helper: simulate fallback for distilled workflow
# =============================================================================

def simulate_medical_value(patient_note: str, question: str) -> float:
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
# Chain-of-thought reasoning fallback (reusable by any workflow)
# =============================================================================

def _reasoning_fallback(patient_note: str, question: str) -> float:
    """Ask the LLM to reason step-by-step, then extract the numeric answer.

    Uses the same formula-rich prompt as the L0 baseline.  Unlike
    ``simulate`` (which predicts a bare number), this lets the LLM show
    its work — critical for complex scoring systems where holistic
    reasoning outperforms structured extraction.
    """
    from string import Template

    model = config.require("llm.model")
    prompt = Template(_BASELINE_TEMPLATE).safe_substitute(
        patient_note=patient_note, question=question)
    response, _ = llm(prompt, model)

    # Extract number: try ANSWER: pattern first, then last number
    match = re.search(r'(?:ANSWER|answer|Answer)[:\s]*([-\d.eE+]+)', response)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    numbers = re.findall(r'-?\d+\.?\d*', response)
    if numbers:
        try:
            return float(numbers[-1])
        except ValueError:
            pass
    # Final fallback to simulate
    return simulate_medical_value(patient_note, question)


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

    return _reasoning_fallback(patient_note, question)


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
        return _reasoning_fallback(patient_note, question)

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
    return _reasoning_fallback(patient_note, question)

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
    import calculator_simple

    docstring = calculator_simple.get_calculator_docstring(calculator_name)
    model = config.require("llm.model")

    # Check if scoring system (needs medical reasoning first)
    is_scoring = any(kw in calculator_name.lower() for kw in [
        'score', 'criteria', 'index', 'risk', 'cha2ds2', 'heart', 'wells',
        'curb', 'sofa', 'apache', 'child-pugh', 'meld', 'centor', 'fever',
        'has-bled', 'rcri', 'charlson', 'caprini', 'blatchford', 'perc'
    ])

    reasoning_context = ""
    if is_scoring:
        reasoning_prompt = f"""You are a medical expert analyzing a patient note for the {calculator_name}.

PATIENT NOTE:
{patient_note}

TASK: Identify ALL conditions/criteria relevant to this calculator.
Look for both explicit mentions AND clinical findings that imply conditions.

Return JSON:
{{"reasoning": "step-by-step analysis", "conditions_present": ["list"], "conditions_absent": ["list"], "demographics": {{"age": number, "sex": "male/female"}}}}
"""
        try:
            reasoning_response, _ = llm(reasoning_prompt, model)
            try:
                reasoning_result = json.loads(reasoning_response)
            except json.JSONDecodeError:
                match = re.search(r'\{[\s\S]*\}', reasoning_response, re.DOTALL)
                reasoning_result = json.loads(match.group()) if match else {}

            conditions_present = reasoning_result.get("conditions_present", [])
            conditions_absent = reasoning_result.get("conditions_absent", [])
            demographics = reasoning_result.get("demographics", {})

            reasoning_context = f"""
MEDICAL ANALYSIS (from reasoning stage):
- Conditions PRESENT: {', '.join(conditions_present) if conditions_present else 'None'}
- Conditions ABSENT: {', '.join(conditions_absent) if conditions_absent else 'None'}
- Demographics: Age={demographics.get('age', 'unknown')}, Sex={demographics.get('sex', 'unknown')}
"""
        except Exception:
            pass

    # Build explicit field list so the LLM knows exactly what to return
    all_fields = required_values + optional_values
    field_list = ', '.join(f'"{f}"' for f in all_fields) if all_fields else '(see calculator description)'

    # Stage 2: Structured extraction
    extraction_prompt = f"""Extract values from the patient note for the {calculator_name} calculator.
{reasoning_context}
CALCULATOR DESCRIPTION:
{docstring or 'No description available.'}

PATIENT NOTE:
{patient_note}

You MUST return values for these exact parameter names: [{field_list}]

INSTRUCTIONS:
- Use the EXACT parameter names listed above as JSON keys
- Read the calculator description carefully for what each parameter means
- For score/grade parameters (e.g. "temperature_score", "ascites_grade"):
  map clinical findings to the numeric score described in the calculator description
- Extract numeric values with proper units (age in years, weight in kg, height in cm)
- Convert units as needed (lbs→kg: ×0.453592, feet/inches→cm)
- For sex: "man"/"male"/"he" → "male", "woman"/"female"/"she" → "female"
- For boolean conditions: True if present, False if absent
- If a condition is not mentioned, assume it is absent (False or 0)

Return ONLY valid JSON:
{{"extracted": {{"param_name": value, ...}}, "missing": ["values truly not determinable from note"]}}
"""
    try:
        response, _ = llm(extraction_prompt, model)
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            match = re.search(r'\{[\s\S]*\}', response, re.DOTALL)
            result = json.loads(match.group()) if match else {"extracted": {}, "missing": required_values}
        return result.get("extracted", {})
    except Exception:
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
                    cleaned[key] = value.lower().strip()
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
    """Re-prompt LLM for missing values."""
    import calculator_simple
    model = config.require("llm.model")
    docstring = calculator_simple.get_calculator_docstring(calculator_name)

    repair_prompt = f"""Previous extraction was incomplete for {calculator_name}.

MISSING REQUIRED VALUES: {', '.join(missing)}
ALREADY EXTRACTED: {current_values}

CALCULATOR DESCRIPTION:
{docstring or 'No description available.'}

PATIENT NOTE:
{patient_note}

Find the missing values. For sex: infer from pronouns (he→male, she→female).
Return ONLY JSON: {{"extracted": {{"value_name": value, ...}}}}
"""
    try:
        response, _ = llm(repair_prompt, model)
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            match = re.search(r'\{[\s\S]*\}', response, re.DOTALL)
            parsed = json.loads(match.group()) if match else {"extracted": {}}
        new_extracted = parsed.get("extracted", {})
        return {**current_values, **new_extracted}
    except Exception:
        return current_values
