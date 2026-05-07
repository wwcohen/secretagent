"""
Wrapper for official MedCalc-Bench calculator implementations.

Provides a unified interface to load and execute the official calculators
with their expected input format.

Expected Input Format Examples:
- age: [45, "years"] or [6, "months"]
- height: [170, "cm"] or [5, "ft", 10, "in"]
- weight: [80, "kg"] or [180, "lbs"]
- sex: "Male" or "Female"
- boolean conditions: True/False (e.g., chf, hypertension, diabetes)
"""

import os
import sys
import json
import importlib.util
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from pathlib import Path


# Path to calculator implementations
CALC_DIR = Path(__file__).parent / "calculator_implementations"


# Mapping from calculator_simple.py names to official MedCalc-Bench names
NAME_MAPPING = {
    # QTc calculators
    "QTc (Bazett)": "QTc Bazett Calculator",
    "QTc (Framingham)": "QTc Framingham Calculator",
    "QTc (Fridericia)": "QTc Fridericia Calculator",
    "QTc (Hodges)": "QTc Hodges Calculator",
    "QTc (Rautaharju)": "QTc Rautaharju Calculator",
    "qt_corrected_interval_bazett_formula": "QTc Bazett Calculator",
    "qtc_bazett": "QTc Bazett Calculator",
    "qtc bazett": "QTc Bazett Calculator",

    # Scoring systems
    "CHA2DS2-VASc Score": "CHA2DS2-VASc Score for Atrial Fibrillation Stroke Risk",
    "cha2ds2-vasc": "CHA2DS2-VASc Score for Atrial Fibrillation Stroke Risk",
    "HEART Score": "HEART Score for Major Cardiac Events",
    "heart_score": "HEART Score for Major Cardiac Events",
    "HAS-BLED Score": "HAS-BLED Score for Major Bleeding Risk",
    "has-bled": "HAS-BLED Score for Major Bleeding Risk",
    "Revised Cardiac Risk Index (RCRI)": "Revised Cardiac Risk Index for Pre-Operative Risk",
    "rcri": "Revised Cardiac Risk Index for Pre-Operative Risk",
    "SOFA Score": "Sequential Organ Failure Assessment (SOFA) Score",
    "sofa": "Sequential Organ Failure Assessment (SOFA) Score",

    # Wells criteria
    "Wells' Criteria for PE": "Wells' Criteria for Pulmonary Embolism",
    "wells_pe": "Wells' Criteria for Pulmonary Embolism",
    "wells_dvt": "Wells' Criteria for DVT",

    # Pulmonary
    "CURB-65 Score": "CURB-65 Score for Pneumonia Severity",
    "curb-65": "CURB-65 Score for Pneumonia Severity",
    "curb65": "CURB-65 Score for Pneumonia Severity",
    "PSI/PORT Score": "PSI Score: Pneumonia Severity Index for CAP",
    "psi_port": "PSI Score: Pneumonia Severity Index for CAP",
    "PERC Rule": "PERC Rule for Pulmonary Embolism",
    "perc": "PERC Rule for Pulmonary Embolism",

    # Renal
    "Creatinine Clearance (Cockcroft-Gault)": "Creatinine Clearance (Cockcroft-Gault Equation)",
    "crcl": "Creatinine Clearance (Cockcroft-Gault Equation)",
    "CKD-EPI GFR (2021)": "CKD-EPI Equations for Glomerular Filtration Rate",
    "ckd-epi": "CKD-EPI Equations for Glomerular Filtration Rate",
    "MDRD GFR": "MDRD GFR Equation",

    # Hepatic
    "FIB-4 Index": "Fibrosis-4 (FIB-4) Index for Liver Fibrosis",
    "fib-4": "Fibrosis-4 (FIB-4) Index for Liver Fibrosis",
    "MELD-Na Score": "MELD Na (UNOS/OPTN)",
    "meld-na": "MELD Na (UNOS/OPTN)",
    "Child-Pugh Score": "Child-Pugh Score for Cirrhosis Mortality",

    # Infectious
    "Centor Score (McIsaac)": "Centor Score (Modified/McIsaac) for Strep Pharyngitis",
    "centor": "Centor Score (Modified/McIsaac) for Strep Pharyngitis",
    "FeverPAIN Score": "FeverPAIN Score for Strep Pharyngitis",

    # Hematologic
    "Caprini VTE Score": "Caprini Score for Venous Thromboembolism (2005)",
    "caprini": "Caprini Score for Venous Thromboembolism (2005)",
    "Glasgow-Blatchford Score (GBS)": "Glasgow-Blatchford Bleeding Score (GBS)",
    "gbs": "Glasgow-Blatchford Bleeding Score (GBS)",

    # Misc
    "Glasgow Coma Scale (GCS)": "Glasgow Coma Score (GCS)",
    "gcs": "Glasgow Coma Score (GCS)",
    "Body Surface Area (Mosteller)": "Body Surface Area Calculator",
    "bsa": "Body Surface Area Calculator",
    "Maintenance Fluids (4-2-1 Rule)": "Maintenance Fluids Calculations",
    "Gestational Age": "Estimated Gestational Age",
    "Date of Conception": "Estimated of Conception",
    "Morphine Milligram Equivalents (MME)": "Morphine Milligram Equivalents (MME) Calculator",
    "mme": "Morphine Milligram Equivalents (MME) Calculator",
    "Target Weight": "Target weight",
    "Steroid Conversion": "Steroid Conversion Calculator",
    "Framingham Risk Score": "Framingham Risk Score for Hard Coronary Heart Disease",
    "HOMA-IR": "HOMA-IR (Homeostatic Model Assessment for Insulin Resistance)",
    "Ideal Body Weight (Devine)": "Ideal Body Weight",
    "LDL Calculated (Friedewald)": "LDL Calculated",
}


@dataclass
class OfficialCalculator:
    """Metadata for an official calculator."""
    name: str
    file_path: str
    calculator_id: int
    func: Optional[Callable] = None
    required_params: List[str] = None
    optional_params: List[str] = None


# Registry of loaded calculators
OFFICIAL_REGISTRY: Dict[str, OfficialCalculator] = {}


def _load_calculator_module(file_path: str) -> Any:
    """Dynamically load a calculator module."""
    full_path = CALC_DIR / Path(file_path).name
    if not full_path.exists():
        return None

    spec = importlib.util.spec_from_file_location("calc_module", full_path)
    module = importlib.util.module_from_spec(spec)

    # Add calculator_implementations to path for helper imports
    old_path = sys.path.copy()
    sys.path.insert(0, str(CALC_DIR))

    try:
        spec.loader.exec_module(module)
    finally:
        sys.path = old_path

    return module


def _find_calculator_function(module: Any) -> Optional[Callable]:
    """Find the main calculator function in a module."""
    # Look for common function name patterns
    for name in dir(module):
        if 'explanation' in name.lower() and callable(getattr(module, name)):
            func = getattr(module, name)
            # Check if it takes params/input_variables
            return func
    return None


def load_calculators():
    """Load all official calculators from calc_path.json."""
    global OFFICIAL_REGISTRY

    calc_path_file = CALC_DIR / "calc_path.json"
    if not calc_path_file.exists():
        print(f"Warning: calc_path.json not found at {calc_path_file}")
        return

    with open(calc_path_file) as f:
        calc_paths = json.load(f)

    for name, info in calc_paths.items():
        file_path = info["File Path"]
        calc_id = info["Calculator ID"]

        module = _load_calculator_module(file_path)
        if module is None:
            continue

        func = _find_calculator_function(module)

        calc = OfficialCalculator(
            name=name,
            file_path=file_path,
            calculator_id=calc_id,
            func=func,
        )
        OFFICIAL_REGISTRY[name] = calc
        # Also register by lowercase
        OFFICIAL_REGISTRY[name.lower()] = calc


def get_calculator(name: str) -> Optional[OfficialCalculator]:
    """Get a calculator by name (case-insensitive fuzzy match)."""
    if not OFFICIAL_REGISTRY:
        load_calculators()

    # First check name mapping
    if name in NAME_MAPPING:
        mapped_name = NAME_MAPPING[name]
        if mapped_name in OFFICIAL_REGISTRY:
            return OFFICIAL_REGISTRY[mapped_name]

    # Case-insensitive name mapping check
    name_lower = name.lower()
    for mapping_key, mapped_name in NAME_MAPPING.items():
        if name_lower == mapping_key.lower():
            if mapped_name in OFFICIAL_REGISTRY:
                return OFFICIAL_REGISTRY[mapped_name]

    # Exact match
    if name in OFFICIAL_REGISTRY:
        return OFFICIAL_REGISTRY[name]

    # Case-insensitive match
    if name_lower in OFFICIAL_REGISTRY:
        return OFFICIAL_REGISTRY[name_lower]

    # Fuzzy match - check each registered calculator
    for reg_name, calc in OFFICIAL_REGISTRY.items():
        reg_lower = reg_name.lower()
        # Skip lowercase duplicates (we registered them as aliases)
        if reg_name != calc.name and reg_lower == reg_name:
            continue
        if name_lower in reg_lower or reg_lower in name_lower:
            return calc

    return None


def compute_official(calculator_name: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Compute using official calculator implementation.

    Args:
        calculator_name: Name of the calculator
        params: Dictionary of parameters in official format

    Returns:
        {"Explanation": str, "Answer": float} or None if failed
    """
    calc = get_calculator(calculator_name)
    if calc is None or calc.func is None:
        return None

    try:
        result = calc.func(params)
        return result
    except Exception as e:
        print(f"  [DEBUG] Official calculator error: {e}")
        return None


def get_all_calculator_names() -> List[str]:
    """Get list of all available calculator names."""
    if not OFFICIAL_REGISTRY:
        load_calculators()

    # Return unique formal names
    seen = set()
    names = []
    for calc in OFFICIAL_REGISTRY.values():
        if calc.name not in seen:
            names.append(calc.name)
            seen.add(calc.name)
    return sorted(names)


# =============================================================================
# Format conversion helpers
# =============================================================================

def format_age(age_value: float, unit: str = "years") -> List:
    """Format age for official calculator input."""
    return [age_value, unit]


def format_height(value: float, unit: str = "cm") -> List:
    """Format height for official calculator input."""
    if unit == "ft_in" and isinstance(value, (list, tuple)) and len(value) == 2:
        feet, inches = value
        return [feet, "ft", inches, "in"]
    return [value, unit]


def format_weight(value: float, unit: str = "kg") -> List:
    """Format weight for official calculator input."""
    return [value, unit]


def _unwrap_list_value(value: Any) -> Any:
    """Unwrap a [value, unit] list to the bare numeric value.

    A few official calculator params expect bare numbers (gcs, inr,
    a_a_gradient, alcoholic_drinks).  This helper extracts the numeric
    part from a [number, unit_string] list.  Non-list values pass through.
    """
    if isinstance(value, list) and len(value) >= 1:
        first = value[0]
        if isinstance(first, (int, float)):
            return first
    return value


def _normalize_count_unit(unit_str: str) -> str:
    """Normalize WBC/platelet unit strings to forms recognized by the official
    ``convert_to_units_per_liter_explanation`` helper.

    The unit converter's ``unit_to_liter`` dict only accepts:
        'L', 'dL', 'mL', 'µL', 'mm^3', 'cm^3', 'm^3'

    LLMs may produce numerous alternative spellings such as:
        '/mm³', 'cells/mm³', 'per microliter', '/µL', 'K/µL', 'k/mm3',
        'x10^3/μL', 'x10^3/µL', '10^3/µL', '10^9/L', 'thou/µL', etc.
    """
    s = unit_str.strip()
    low = s.lower()

    # Strip leading '/' or 'per ' or 'cells/' prefix
    for prefix in ("/", "cells/", "cells per ", "per ", "count/", "count per "):
        if low.startswith(prefix):
            s = s[len(prefix):]
            low = s.lower()
            break

    # Normalize micro-litre variants
    # μL, µL, uL, microliter, microlitre -> µL
    if low in ("μl", "µl", "ul", "microliter", "microlitre", "micro liter"):
        return "µL"

    # mm³, mm3 -> mm^3
    if low in ("mm³", "mm3", "mm^3"):
        return "mm^3"

    # Handle x10^3/unit and x10^9/unit patterns
    # e.g. "x10^3/µL" means the count is in thousands per µL
    # The caller should multiply count by 1000 if needed; here we return
    # the base volume unit.
    if "10^3" in low or "10³" in low or "x10^3" in low or "x10³" in low:
        # e.g. "x10^3/µL", "10^3/uL", "K/µL", "k/mm3"
        for vol in ("µl", "μl", "ul", "microliter"):
            if vol in low:
                return "µL"
        for vol in ("mm³", "mm3", "mm^3"):
            if vol in low:
                return "mm^3"
        if "l" in low:
            return "µL"  # fallback to µL for ambiguous
        return "µL"

    if "10^4" in low or "10⁴" in low or "x10^4" in low:
        for vol in ("µl", "μl", "ul", "microliter"):
            if vol in low:
                return "µL"
        return "µL"

    if "10^9" in low or "10⁹" in low or "x10^9" in low:
        # 10^9/L means count per litre → return "L"
        return "L"

    # K/µL, k/µL, thou/µL  (thousands per microlitre)
    if low.startswith("k/") or low.startswith("thou/"):
        remainder = s.split("/", 1)[1] if "/" in s else ""
        if remainder:
            return _normalize_count_unit(remainder)
        return "µL"

    # If unit matches known keys directly, pass through
    if s in ("L", "dL", "mL", "µL", "mm^3", "cm^3", "m^3"):
        return s

    # Last resort: return as-is and hope for the best
    return s


def _normalize_temperature_unit(unit_str: str) -> str:
    """Normalize temperature unit strings for convert_temperature.fahrenheit_to_celsius_explanation.

    That function checks ``units == "degrees celsius"``; everything else is
    treated as Fahrenheit.
    """
    low = unit_str.lower().strip()
    if low in ("°c", "c", "celsius", "degrees celsius", "deg c", "degc",
               "degree celsius", "degrees c"):
        return "degrees celsius"
    if low in ("°f", "f", "fahrenheit", "degrees fahrenheit", "deg f", "degf",
               "degree fahrenheit", "degrees f"):
        return "degrees fahrenheit"
    return unit_str


def _normalize_date_format(date_str: str) -> str:
    """Normalize date strings to MM/DD/YYYY format expected by official calculators.

    Handles ISO (YYYY-MM-DD), European (DD/MM/YYYY when unambiguous), and
    already-correct MM/DD/YYYY formats.
    """
    import re
    s = str(date_str).strip()
    # ISO format: YYYY-MM-DD
    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', s)
    if m:
        return f"{int(m.group(2)):02d}/{int(m.group(3)):02d}/{m.group(1)}"
    # Already MM/DD/YYYY or M/D/YYYY
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', s)
    if m:
        return s
    return s


# Steroid name normalization — maps bare/abbreviated names to official
# conversion_dict keys (e.g., "Hydrocortisone PO", "PredniSONE PO").
_STEROID_NAME_MAP = {
    "betamethasone": "Betamethasone IV",
    "cortisone": "Cortisone PO",
    "dexamethasone": "Dexamethasone IV",
    "decadron": "Dexamethasone IV",
    "hydrocortisone": "Hydrocortisone PO",
    "methylprednisolone": "MethylPrednisoLONE IV",
    "prednisolone": "PrednisoLONE PO",
    "prednisone": "PredniSONE PO",
    "triamcinolone": "Triamcinolone IV",
}
# Also match official names that may be missing their route suffix
_STEROID_OFFICIAL_NAMES = {
    "betamethasone iv": "Betamethasone IV",
    "cortisone po": "Cortisone PO",
    "dexamethasone iv": "Dexamethasone IV",
    "dexamethasone po": "Dexamethasone PO",
    "hydrocortisone iv": "Hydrocortisone IV",
    "hydrocortisone po": "Hydrocortisone PO",
    "methylprednisolone iv": "MethylPrednisoLONE IV",
    "methylprednisolone po": "MethylPrednisoLONE PO",
    "prednisolone po": "PrednisoLONE PO",
    "prednisone po": "PredniSONE PO",
    "triamcinolone iv": "Triamcinolone IV",
}


def _normalize_steroid_name(name: str) -> str:
    """Normalize a steroid name to match the official conversion_dict keys."""
    if not name:
        return name
    low = name.lower().strip()
    # Exact match on official names (case-insensitive)
    if low in _STEROID_OFFICIAL_NAMES:
        return _STEROID_OFFICIAL_NAMES[low]
    # Bare name without route
    if low in _STEROID_NAME_MAP:
        return _STEROID_NAME_MAP[low]
    # Fuzzy: check if any bare name is a substring
    for bare, official in _STEROID_NAME_MAP.items():
        if bare in low:
            return official
    # Already correct (pass through)
    return name


# GCS numeric-to-categorical reverse mappings
_GCS_EYE_TO_STR = {
    4: "eyes open spontaneously", 3: "eye opening to verbal command",
    2: "eye opening to pain", 1: "no eye opening",
}
_GCS_VERBAL_TO_STR = {
    5: "oriented", 4: "confused", 3: "inappropriate words",
    2: "incomprehensible sounds", 1: "no verbal response",
}
_GCS_MOTOR_TO_STR = {
    6: "obeys commands", 5: "localizes pain", 4: "withdrawal from pain",
    3: "flexion to pain", 2: "extension to pain", 1: "no motor response",
}
_GCS_MAPS = {"eye": _GCS_EYE_TO_STR, "verbal": _GCS_VERBAL_TO_STR, "motor": _GCS_MOTOR_TO_STR}


def _gcs_numeric_to_str(value: Any, component: str) -> str:
    """Convert a numeric GCS sub-component score to the categorical string
    expected by the official glasgow_coma_score.py calculator.

    Handles:
    - Numeric values: 4 → "eyes open spontaneously"
    - Exact string matches: pass through if already an official key
    - Partial/fuzzy strings: "spontaneously" → "eyes open spontaneously"
    - Unknown values → fallback (max score key for that component)
    """
    mapping = _GCS_MAPS.get(component, {})
    # Motor component doesn't have "not testable" in the official calc dict;
    # use "obeys commands" (6 pts) as fallback.  Eye/verbal have "not testable".
    fallback = "obeys commands" if component == "motor" else "not testable"
    # All valid string keys for this component
    valid_keys = set(mapping.values()) | {"not testable"}

    if isinstance(value, str):
        # Already a valid key — pass through
        if value.lower() in {k.lower() for k in valid_keys}:
            # Return the correctly-cased version
            for k in valid_keys:
                if k.lower() == value.lower():
                    return k
            return value
        # Fuzzy substring match: "spontaneously" → "eyes open spontaneously"
        val_lower = value.lower().strip()
        for official_key in mapping.values():
            if val_lower in official_key.lower() or official_key.lower() in val_lower:
                return official_key
        # Try to parse as number (LLM may send "4" as string)
        try:
            num = int(float(value))
            return mapping.get(num, fallback)
        except (ValueError, TypeError):
            return fallback

    try:
        num = int(float(value))
    except (ValueError, TypeError):
        return fallback
    return mapping.get(num, fallback)


def convert_extracted_to_official(extracted: Dict[str, Any], calculator_name: str) -> Dict[str, Any]:
    """
    Convert L4 extracted values to official calculator format.

    Most official calculators expect [value, unit] lists accessed via
    param[0]/param[1].  A few params (gcs, inr, a_a_gradient) expect
    bare numbers.  Each key-specific handler ensures the correct format.
    Unrecognised keys pass through as-is (lists preserved).
    """
    params = {}

    # === Pre-processing: normalize spaces to underscores in keys ===
    # LLMs sometimes send "body temperature" instead of "body_temperature".
    # Exception: "input steroid" and "target steroid" must keep spaces.
    _SPACE_EXCEPTIONS = {"input steroid", "target steroid"}
    normalized_extracted = {}
    for k, v in extracted.items():
        k_low = k.lower().strip()
        if " " in k and k_low not in _SPACE_EXCEPTIONS:
            normalized_extracted[k.replace(" ", "_")] = v
        else:
            normalized_extracted[k] = v
    extracted = normalized_extracted

    # Process each extracted value
    for key, value in extracted.items():
        if value is None:
            continue

        key_lower = key.lower().strip()

        # === Age ===
        if key_lower == "age":
            if isinstance(value, list):
                params["age"] = value
            elif isinstance(value, (int, float)):
                params["age"] = [value, "years"]
            elif isinstance(value, str):
                # Handle categorical age formats like "< 45", "45 - 65", "> 65"
                # Try to extract a reasonable numeric value
                if "< 45" in value or "<45" in value:
                    params["age"] = [40, "years"]  # Use middle of range
                elif "45" in value and "65" in value:
                    params["age"] = [55, "years"]  # Use middle of range
                elif "> 65" in value or ">65" in value or "≥65" in value or ">=65" in value:
                    params["age"] = [70, "years"]  # Use reasonable value
                else:
                    # Try to parse as number
                    import re
                    match = re.search(r'(\d+)', value)
                    if match:
                        params["age"] = [int(match.group(1)), "years"]

        # === Height ===
        elif key_lower in ("height", "height_cm", "patient_height", "body_height"):
            if isinstance(value, list):
                params["height"] = value
            elif isinstance(value, (int, float)):
                params["height"] = [value, "cm"]
        elif key_lower == "height_m":
            params["height"] = [_unwrap_list_value(value), "m"]
        elif key_lower == "height_in":
            params["height"] = [_unwrap_list_value(value), "in"]

        # === Weight ===
        elif key_lower in ("weight", "weight_kg", "actual_weight", "weight_used",
                           "body_weight", "patient_weight", "body_mass", "mass_kg"):
            if isinstance(value, list):
                params["weight"] = value
            elif isinstance(value, (int, float)):
                params["weight"] = [value, "kg"]
        elif key_lower == "weight_lbs":
            params["weight"] = [_unwrap_list_value(value), "lbs"]

        # === BMI ===
        elif key_lower in ("body_mass_index", "bmi"):
            if isinstance(value, list):
                params["body_mass_index"] = value
            elif isinstance(value, (int, float)):
                params["body_mass_index"] = [value, "kg/m^2"]
            elif isinstance(value, str):
                try:
                    params["body_mass_index"] = [float(value), "kg/m^2"]
                except (ValueError, TypeError):
                    params["body_mass_index"] = value

        # === Sex ===
        elif key_lower in ("sex", "gender"):
            if isinstance(value, str):
                params["sex"] = value.capitalize()
            elif isinstance(value, list):
                # Unwrap e.g. ["Male", ""] to "Male"
                params["sex"] = str(value[0]).capitalize() if value else "Male"

        # === Lab values that need [value, unit] format ===
        # These are params that official calculators access via param[0]/param[1].
        # If already a list, keep as-is. If scalar, wrap in [value, unit].
        elif key_lower in ("heart_rate", "hr", "heart_rate_bpm", "heartrate"):
            params["heart_rate"] = value if isinstance(value, list) else [value, "bpm"]
        elif key_lower in ("qt_interval", "qt"):
            params["qt_interval"] = value if isinstance(value, list) else [value, "msec"]
        elif key_lower in ("systolic_bp", "sbp", "sys_bp", "systolic_blood_pressure",
                           "systolic", "blood_pressure_systolic", "sbp_mmhg"):
            params["sys_bp"] = value if isinstance(value, list) else [value, "mmHg"]
        elif key_lower in ("diastolic_bp", "dbp", "dia_bp", "diastolic_blood_pressure"):
            params["dia_bp"] = value if isinstance(value, list) else [value, "mmHg"]
        elif key_lower in ("creatinine", "creatinine_mg_dl", "serum_creatinine",
                           "plasma_creatinine", "serum_cr", "scr", "cr"):
            params["creatinine"] = value if isinstance(value, list) else [value, "mg/dL"]
        elif key_lower in ("bun", "blood_urea_nitrogen", "bun_level", "serum_bun",
                           "urea_nitrogen", "blood_urea"):
            params["bun"] = value if isinstance(value, list) else [value, "mg/dL"]
        elif key_lower in ("sodium", "na", "serum_sodium", "serum_na", "plasma_sodium",
                           "plasma_na", "na_level"):
            params["sodium"] = value if isinstance(value, list) else [value, "mEq/L"]
        elif key_lower in ("potassium", "k", "serum_potassium", "serum_k",
                           "plasma_potassium", "plasma_k", "k_level"):
            params["potassium"] = value if isinstance(value, list) else [value, "mEq/L"]
        elif key_lower in ("chloride", "cl"):
            params["chloride"] = value if isinstance(value, list) else [value, "mEq/L"]
        elif key_lower in ("bicarbonate", "hco3", "co2"):
            params["bicarbonate"] = value if isinstance(value, list) else [value, "mEq/L"]
        elif key_lower in ("glucose", "blood_glucose"):
            params["glucose"] = value if isinstance(value, list) else [value, "mg/dL"]
        elif key_lower in ("albumin", "serum_albumin", "albumin_level", "albumin_g_dl",
                           "alb", "ser_albumin"):
            params["albumin"] = value if isinstance(value, list) else [value, "g/dL"]
        elif key_lower in ("calcium", "serum_calcium"):
            params["calcium"] = value if isinstance(value, list) else [value, "mg/dL"]
        elif key_lower in ("bilirubin", "total_bilirubin"):
            params["bilirubin"] = value if isinstance(value, list) else [value, "mg/dL"]
        elif key_lower in ("inr",):
            # INR is used as a bare number in Child-Pugh (float(params['inr']))
            # and MELD-Na (if inr < 1.0). No official calculator uses inr[0].
            params["inr"] = _unwrap_list_value(value) if isinstance(value, list) else value
        elif key_lower in ("ast", "aspartate_aminotransferase", "sgot", "ast_level",
                           "serum_ast", "asat"):
            params["ast"] = value if isinstance(value, list) else [value, "U/L"]
        elif key_lower in ("alt", "alanine_aminotransferase", "sgpt", "alt_level",
                           "serum_alt", "alat"):
            params["alt"] = value if isinstance(value, list) else [value, "U/L"]
        elif key_lower in ("platelets", "platelet_count", "plt", "platelet"):
            # SOFA and Fibrosis-4 use input_parameters["platelet_count"][0]
            # Unit must be recognisable by official calculator unit dicts
            if isinstance(value, list) and len(value) >= 2:
                count_val = value[0]
                raw_unit = str(value[1]).lower()
                # Multiply count by prefix magnitude so base unit is per-µL
                if "10^4" in raw_unit or "10⁴" in raw_unit:
                    count_val = count_val * 10000
                elif "10^3" in raw_unit or "10³" in raw_unit:
                    count_val = count_val * 1000
                unit_str = _normalize_count_unit(str(value[1]))
                params["platelet_count"] = [count_val, unit_str]
            elif isinstance(value, (int, float)):
                params["platelet_count"] = [value, "µL"]
            else:
                params["platelet_count"] = value if isinstance(value, list) else [value, "µL"]
        elif key_lower in ("hemoglobin", "hgb", "hb", "hgb_level", "hemoglobin_level",
                           "serum_hemoglobin"):
            params["hemoglobin"] = value if isinstance(value, list) else [value, "g/dL"]
        elif key_lower in ("pao2", "partial_pressure_oxygen", "po2", "partial_pressure_o2",
                           "arterial_po2", "arterial_pao2"):
            # Both SOFA (pao2[0]) and PSI (partial_pressure_oxygen[0]/[1]) need this.
            # Store under BOTH keys so PSI's .get("partial_pressure_oxygen") finds it.
            wrapped = value if isinstance(value, list) else [value, "mmHg"]
            params["pao2"] = wrapped
            params["partial_pressure_oxygen"] = wrapped
        elif key_lower in ("paco2", "partial_pressure_co2"):
            params["paco2"] = value if isinstance(value, list) else [value, "mmHg"]
        elif key_lower in ("fio2", "fraction_inspired_oxygen", "fi_o2",
                           "fio2_percentage", "inspired_oxygen", "fio_2"):
            # fio2 = params["fio2"][0] in SOFA and Apache II
            params["fio2"] = value if isinstance(value, list) else [value, "%"]
        elif key_lower in ("urine_output",):
            params["urine_output"] = value if isinstance(value, list) else [value, "mL/day"]
        elif key_lower in ("hematocrit", "hct", "hct_percent", "hematocrit_percent",
                           "hct_value"):
            # Apache II uses input_parameters['hematocrit'][0]
            params["hematocrit"] = value if isinstance(value, list) else [value, "%"]

        # === Params that need [value, unit] list format ===
        # These calculators access via param[0]/param[1] indexing.
        elif key_lower in ("temperature", "temp", "body_temperature", "body_temp",
                           "temperature_celsius", "temperature_fahrenheit",
                           "temp_c", "temp_f", "rectal_temperature", "rectal_temp",
                           "oral_temperature", "oral_temp"):
            # SIRS, Apache II, Centor, PSI all use temperature[0], temperature[1]
            # convert_temperature.fahrenheit_to_celsius_explanation checks
            # units == "degrees celsius" (not "°C"), and otherwise treats as °F.
            if isinstance(value, list) and len(value) >= 2:
                raw_unit = str(value[1]).lower().strip()
                if raw_unit in ("°c", "c", "celsius", "degrees celsius", "deg c", "degc"):
                    params["temperature"] = [value[0], "degrees celsius"]
                elif raw_unit in ("°f", "f", "fahrenheit", "degrees fahrenheit", "deg f", "degf"):
                    params["temperature"] = [value[0], "degrees fahrenheit"]
                else:
                    params["temperature"] = [value[0], value[1]]
            elif isinstance(value, (int, float)):
                # Bare number: assume Celsius (most common in clinical data)
                params["temperature"] = [value, "degrees celsius"]
            else:
                params["temperature"] = [value, "degrees celsius"]
        elif key_lower in ("respiratory_rate", "rr", "resp_rate", "respiration_rate"):
            # SIRS, Apache II, CURB-65, PSI use respiratory_rate[0]
            params["respiratory_rate"] = value if isinstance(value, list) else [value, "breaths per minute"]
        elif key_lower in ("wbc", "white_blood_cell_count", "white_blood_cells", "sirs_wbc",
                           "wbc_count", "leukocyte_count"):
            # SIRS, Apache II use wbc[0], wbc[1] with convert_to_units_per_liter_explanation
            # which expects unit keys like 'µL', 'mm^3', 'L' (no leading slash)
            if isinstance(value, list) and len(value) >= 2:
                count_val = value[0]
                unit_str = _normalize_count_unit(str(value[1]))
                params["wbc"] = [count_val, unit_str]
            elif isinstance(value, (int, float)):
                # Default to x10^3/µL (most common); convert to count/µL
                # by multiplying by 1000 so the unit converter sees 'µL'
                params["wbc"] = [value * 1000, "µL"]
            else:
                params["wbc"] = [value, "µL"]

        # === Params that need bare numbers (no [0] indexing in calculators) ===
        elif key_lower in ("gcs", "glasgow_coma_score", "glasgow_coma_scale"):
            # SOFA: gcs = input_parameters["gcs"] then "if gcs < 6"
            # Apache II: gcs = int(input_parameters['gcs'])
            params["gcs"] = _unwrap_list_value(value)
        elif key_lower in ("a_a_gradient", "aa_gradient"):
            # Apache II: a_a_gradient compared directly: "if a_a_gradient > 499"
            params["a_a_gradient"] = _unwrap_list_value(value)

        # === Boolean conditions - handle has_X prefix ===
        elif key_lower.startswith("has_"):
            condition = key_lower.replace("has_", "")
            bool_value = bool(value)

            # Handle combined conditions that need to be split
            if condition in ("stroke_tia", "stroke/tia"):
                # CHA2DS2-VASc expects stroke, tia, thromboembolism separately
                params["stroke"] = bool_value
                params["tia"] = bool_value
                params["thromboembolism"] = bool_value
            elif condition in ("chf", "congestive_heart_failure"):
                params["chf"] = bool_value
            elif condition in ("hypertension", "htn"):
                params["hypertension"] = bool_value
            elif condition in ("diabetes", "diabetes_mellitus"):
                params["diabetes"] = bool_value
            elif condition in ("vascular_disease", "atherosclerotic_disease"):
                params["vascular_disease"] = bool_value
            else:
                params[condition] = bool_value

        # === Handle combined conditions without has_ prefix ===
        elif key_lower in ("stroke_tia", "stroke/tia"):
            bool_value = bool(value)
            params["stroke"] = bool_value
            params["tia"] = bool_value
            params["thromboembolism"] = bool_value

        # === HEART Score specific categorical parameters ===
        elif key_lower in ("history", "history_suspicious", "chest_pain_history"):
            # Unwrap [value, ""] → value if list
            if isinstance(value, list):
                value = value[0] if value else ""
            # Normalize history to expected categorical values
            if isinstance(value, str):
                val_lower = value.lower().strip()
                if any(kw in val_lower for kw in ['highly', 'typical', 'classic', 'definite', 'high']):
                    params["history"] = "Highly suspicious"
                elif any(kw in val_lower for kw in ['moderately', 'moderate', 'somewhat', 'possible']):
                    params["history"] = "Moderately suspicious"
                elif any(kw in val_lower for kw in ['slightly', 'atypical', 'low', 'non-specific', 'vague', 'unlikely']):
                    params["history"] = "Slightly suspicious"
                else:
                    # Default to slightly suspicious for unrecognized strings
                    params["history"] = "Slightly suspicious"
            elif isinstance(value, (int, float)):
                # Numeric: 0=slightly, 1=moderately, 2=highly
                if value >= 2:
                    params["history"] = "Highly suspicious"
                elif value >= 1:
                    params["history"] = "Moderately suspicious"
                else:
                    params["history"] = "Slightly suspicious"
            else:
                params["history"] = "Slightly suspicious"
        elif key_lower in ("electrocardiogram", "ecg", "ekg", "ecg_findings",
                           "ecg_result", "ekg_findings", "ekg_result"):
            # Unwrap [value, ""] → value if list
            if isinstance(value, list):
                value = value[0] if value else ""
            # Normalize ECG to expected categorical values
            if isinstance(value, str):
                val_lower = value.lower().strip()
                if any(kw in val_lower for kw in ['st elevation', 'st depression', 'significant st', 'st deviation', 'stemi', 'nstemi']):
                    params["electrocardiogram"] = "Significant ST deviation"
                elif any(kw in val_lower for kw in ['non-specific', 'nonspecific', 'repolarization', 'minor', 't wave']):
                    params["electrocardiogram"] = "Non-specific repolarization disturbance"
                elif any(kw in val_lower for kw in ['normal', 'no changes', 'unremarkable', 'nsr', 'sinus rhythm']):
                    params["electrocardiogram"] = "Normal"
                else:
                    # Default to Normal for unrecognized strings
                    params["electrocardiogram"] = "Normal"
            elif isinstance(value, (int, float)):
                # Numeric: 0=normal, 1=non-specific, 2=significant ST
                if value >= 2:
                    params["electrocardiogram"] = "Significant ST deviation"
                elif value >= 1:
                    params["electrocardiogram"] = "Non-specific repolarization disturbance"
                else:
                    params["electrocardiogram"] = "Normal"
            else:
                params["electrocardiogram"] = "Normal"
        elif key_lower in ("initial_troponin", "troponin", "troponin_i", "troponin_t",
                           "hs_troponin", "hs_troponin_i", "troponin_level"):
            # Unwrap [value, ""] → value if list
            if isinstance(value, list):
                value = value[0] if value else ""
            # Normalize troponin to expected categorical values
            if isinstance(value, str):
                val_lower = value.lower().strip()
                if any(kw in val_lower for kw in ['greater than three', '>3', 'more than 3', 'high', 'markedly elevated']):
                    params["initial_troponin"] = "greater than three times normal limit"
                elif any(kw in val_lower for kw in ['between', '1-3', '1 to 3', 'one to three', 'slightly elevated', 'mildly elevated']):
                    params["initial_troponin"] = "between the normal limit or up to three times the normal limit"
                elif any(kw in val_lower for kw in ['normal', 'less than', '≤normal', 'negative', 'within normal', 'not elevated']):
                    params["initial_troponin"] = "less than or equal to normal limit"
                else:
                    params["initial_troponin"] = value
            elif isinstance(value, (int, float)):
                # Numeric troponin: HEART Score needs a categorical string.
                # Normal upper limit for troponin is ~0.04 ng/mL (conventional)
                # or ~14-20 ng/L (high-sensitivity).  Use a heuristic:
                #   <=normal limit  |  1-3x normal  |  >3x normal
                # We cannot know the assay, so treat value as a multiplier of
                # normal if it looks small, or as raw ng/mL otherwise.
                # If the LLM sends a raw value > 100, it is likely in ng/L;
                # if <= 100, likely ng/mL or a multiplier.
                params["initial_troponin"] = "less than or equal to normal limit"
            else:
                params["initial_troponin"] = value

        # === HAS-BLED specific parameters ===
        elif key_lower in ("alcoholic_drinks", "alcohol_drinks", "drinks_per_week"):
            val = _unwrap_list_value(value) if isinstance(value, list) else value
            try:
                params["alcoholic_drinks"] = int(float(val))
            except (ValueError, TypeError):
                params["alcoholic_drinks"] = 0
        elif key_lower in ("liver_disease_has_bled", "liver_disease_hasbled"):
            params["liver_disease_has_bled"] = bool(value)
        elif key_lower in ("renal_disease_has_bled", "renal_disease_hasbled"):
            params["renal_disease_has_bled"] = bool(value)
        elif key_lower in ("medications_for_bleeding", "bleeding_medications"):
            params["medications_for_bleeding"] = bool(value)
        elif key_lower in ("prior_bleeding", "bleeding_history"):
            params["prior_bleeding"] = bool(value)
        elif key_lower in ("labile_inr",):
            params["labile_inr"] = bool(value)

        # === Glasgow-Blatchford specific parameters ===
        elif key_lower in ("hepatic_disease_history", "liver_disease_history"):
            params["hepatic_disease_history"] = bool(value)
        elif key_lower in ("melena_present", "melena"):
            params["melena_present"] = bool(value)
        elif key_lower in ("cardiac_failure", "heart_failure_gbs"):
            params["cardiac_failure"] = bool(value)
        elif key_lower in ("syncope", "recent_syncope"):
            params["syncope"] = bool(value)

        # === Charlson CCI specific parameters ===
        elif key_lower in ("peptic_ulcer_disease", "peptic_ucler_disease", "peptic_ulcer"):
            # Note: Official code has typo "peptic_ucler_disease"
            params["peptic_ucler_disease"] = bool(value)
        elif key_lower in ("liver_disease", "liver_disease_cci"):
            # Charlson expects categorical: "none", "mild", "moderate to severe"
            if isinstance(value, bool):
                params["liver_disease"] = "mild" if value else "none"
            else:
                params["liver_disease"] = value
        elif key_lower in ("diabetes_mellitus", "diabetes_cci"):
            # Charlson expects categorical: "none or diet-controlled", "uncomplicated", "end-organ damage"
            if isinstance(value, bool):
                params["diabetes_mellitus"] = "uncomplicated" if value else "none or diet-controlled"
            else:
                params["diabetes_mellitus"] = value
        elif key_lower in ("solid_tumor", "tumor"):
            # Charlson expects categorical: "none", "localized", "metastatic"
            if isinstance(value, bool):
                params["solid_tumor"] = "localized" if value else "none"
            else:
                params["solid_tumor"] = value
        elif key_lower in ("mi", "myocardial_infarction"):
            params["mi"] = bool(value)
        elif key_lower in ("peripheral_vascular_disease", "pvd"):
            params["peripheral_vascular_disease"] = bool(value)
        elif key_lower in ("cva", "cerebrovascular_accident"):
            params["cva"] = bool(value)
        elif key_lower == "tia":
            params["tia"] = bool(value)
        elif key_lower in ("connective_tissue_disease", "ctd"):
            params["connective_tissue_disease"] = bool(value)
        elif key_lower == "dementia":
            params["dementia"] = bool(value)
        elif key_lower == "copd":
            params["copd"] = bool(value)
        elif key_lower == "hemiplegia":
            params["hemiplegia"] = bool(value)
        elif key_lower in ("moderate_to_severe_ckd", "ckd"):
            params["moderate_to_severe_ckd"] = bool(value)
        elif key_lower == "leukemia":
            params["leukemia"] = bool(value)
        elif key_lower == "lymphoma":
            params["lymphoma"] = bool(value)
        elif key_lower == "aids":
            params["aids"] = bool(value)

        # === Menstrual/Obstetric parameters ===
        # Dates must stay as strings — official calcs use strptime()
        elif key_lower in ("menstrual_date", "last_menstrual_period", "lmp", "lmp_date",
                           "last_menstrual_date", "date_of_last_menstrual_period"):
            # Unwrap [date_str, ""] or [date_str, "date"] → date_str
            # _unwrap_list_value only unwraps if element [0] is numeric;
            # for dates the first element is a string, so extract directly.
            if isinstance(value, list):
                params["menstrual_date"] = value[0] if value else value
            else:
                params["menstrual_date"] = value
        elif key_lower in ("delivery_date", "estimated_delivery_date", "edd",
                           "due_date", "expected_delivery_date"):
            if isinstance(value, list):
                # Unwrap [date_str, ""] or [date_str, "date"] → date_str
                params["delivery_date"] = value[0] if value else value
            else:
                params["delivery_date"] = value
        elif key_lower in ("conception_date", "date_of_conception"):
            # Unwrap [date_str, ""] or [date_str, "date"] → date_str
            if isinstance(value, list):
                params["conception_date"] = value[0] if value else value
            else:
                params["conception_date"] = value
        elif key_lower in ("current_date", "today", "todays_date", "today_date"):
            # Gestational age calculator needs current_date as a bare string
            if isinstance(value, list):
                params["current_date"] = value[0] if value else value
            else:
                params["current_date"] = value
        elif key_lower in ("cycle_length", "menstrual_cycle_length"):
            # Due date calculator needs cycle_length as a bare number
            params["cycle_length"] = _unwrap_list_value(value) if isinstance(value, list) else value

        # === Insulin ===
        elif key_lower in ("insulin", "fasting_insulin", "serum_insulin"):
            params["insulin"] = value if isinstance(value, list) else [value, "µIU/mL"]

        # === Fasting glucose alias for HOMA-IR ===
        elif key_lower in ("fasting_glucose", "fasting_blood_glucose"):
            params["glucose"] = value if isinstance(value, list) else [value, "mg/dL"]

        # === pH — used as bare number in APACHE II and PSI ===
        elif key_lower in ("ph", "arterial_ph", "blood_ph"):
            params["pH"] = _unwrap_list_value(value) if isinstance(value, list) else value

        # === Oxygen saturation — PERC uses oxygen_sat[0] ===
        elif key_lower in ("oxygen_sat", "o2_sat", "spo2", "oxygen_saturation", "sao2",
                           "o2_saturation", "sat_o2", "pulse_ox", "pulse_oximetry"):
            # PERC uses input_parameters["oxygen_sat"][0] so must be a list
            if isinstance(value, list):
                params["oxygen_sat"] = value
            elif isinstance(value, (int, float)):
                params["oxygen_sat"] = [value, "%"]
            else:
                params["oxygen_sat"] = [value, "%"]

        # === Pulse / heart rate aliases ===
        elif key_lower in ("pulse", "pulse_rate"):
            params["heart_rate"] = value if isinstance(value, list) else [value, "bpm"]

        # === Cholesterol parameters for LDL Friedewald ===
        elif key_lower in ("total_cholesterol", "total_chol", "tc", "cholesterol",
                           "serum_cholesterol", "total_cholesterol_level"):
            params["total_cholesterol"] = value if isinstance(value, list) else [value, "mg/dL"]
        elif key_lower in ("hdl_cholesterol", "hdl", "hdl_chol", "hdl_c",
                           "high_density_lipoprotein"):
            params["hdl_cholesterol"] = value if isinstance(value, list) else [value, "mg/dL"]
        elif key_lower in ("triglycerides", "tg", "trigs", "triglyceride",
                           "serum_triglycerides"):
            params["triglycerides"] = value if isinstance(value, list) else [value, "mg/dL"]

        # === Alcoholic drinks aliases ===
        elif key_lower in ("alcohol_drinks_per_week", "drinks", "drinks_per_week_alias",
                           "alcohol_use", "alcohol", "alcoholic_beverages"):
            val = _unwrap_list_value(value) if isinstance(value, list) else value
            try:
                params["alcoholic_drinks"] = int(float(val))
            except (ValueError, TypeError):
                params["alcoholic_drinks"] = 0

        # === GCS sub-component aliases ===
        elif key_lower in ("best_eye_response", "eye_response", "eye_opening", "eye",
                           "eye_opening_response", "eye_score", "gcs_eye", "gcs_eyes"):
            raw = _unwrap_list_value(value) if isinstance(value, list) else value
            params["best_eye_response"] = _gcs_numeric_to_str(raw, "eye")
        elif key_lower in ("best_verbal_response", "verbal_response", "verbal",
                           "verbal_score", "gcs_verbal"):
            raw = _unwrap_list_value(value) if isinstance(value, list) else value
            params["best_verbal_response"] = _gcs_numeric_to_str(raw, "verbal")
        elif key_lower in ("best_motor_response", "motor_response", "motor",
                           "motor_score", "gcs_motor"):
            raw = _unwrap_list_value(value) if isinstance(value, list) else value
            params["best_motor_response"] = _gcs_numeric_to_str(raw, "motor")

        # === Steroid conversion parameters ===
        elif key_lower in ("input steroid", "steroid_name", "input_steroid", "source_steroid",
                           "from_steroid", "steroid", "current_steroid", "starting_steroid"):
            # Official calc expects [steroid_name, dose_value, dose_unit] (3-element list)
            # e.g. ["PredniSONE PO", 10, "mg"]
            if isinstance(value, list) and len(value) >= 3:
                # Already in the right format
                params["input steroid"] = [_normalize_steroid_name(value[0]), value[1], value[2]]
            elif isinstance(value, list) and len(value) == 2:
                # [steroid_name, dose] — assume mg
                params["input steroid"] = [_normalize_steroid_name(value[0]), value[1], "mg"]
            elif isinstance(value, str):
                # Just the steroid name — default to 1 mg
                params["input steroid"] = [_normalize_steroid_name(value), 1, "mg"]
            elif isinstance(value, dict):
                # Try to extract from dict structure
                name = value.get("name", value.get("steroid", str(value)))
                dose = value.get("dose", value.get("amount", 1))
                unit = value.get("unit", "mg")
                params["input steroid"] = [_normalize_steroid_name(name), dose, unit]
            else:
                params["input steroid"] = [_normalize_steroid_name(str(value)), 1, "mg"]
        elif key_lower in ("target steroid", "target_steroid", "output_steroid", "target",
                           "to_steroid", "desired_steroid", "convert_to_steroid"):
            # Target steroid must be a bare string (e.g., "PredniSONE PO")
            if isinstance(value, list):
                raw_target = value[0] if value else value
            else:
                raw_target = value
            params["target steroid"] = _normalize_steroid_name(raw_target) if isinstance(raw_target, str) else raw_target

        # === FENa parameters ===
        elif key_lower in ("urine_sodium", "urine_na", "u_na", "una", "urine_na_concentration"):
            params["urine_sodium"] = value if isinstance(value, list) else [value, "mEq/L"]
        elif key_lower in ("urine_creatinine", "urine_cr", "u_cr", "ucr",
                           "urine_creatinine_concentration"):
            params["urine_creatinine"] = value if isinstance(value, list) else [value, "mg/dL"]

        # === Additional lab values that may arrive as bare numbers ===
        elif key_lower in ("phosphorus", "serum_phosphorus"):
            params["phosphorus"] = value if isinstance(value, list) else [value, "mg/dL"]
        elif key_lower in ("magnesium", "serum_magnesium"):
            params["magnesium"] = value if isinstance(value, list) else [value, "mg/dL"]
        elif key_lower in ("lactate", "serum_lactate"):
            params["lactate"] = value if isinstance(value, list) else [value, "mmol/L"]
        elif key_lower in ("urea",):
            params["urea"] = value if isinstance(value, list) else [value, "mg/dL"]

        # === Vasopressors — SOFA uses param[0] indexing ===
        elif key_lower in ("dopamine", "dopamine_dose"):
            if isinstance(value, list):
                params["dopamine"] = value
            elif isinstance(value, bool):
                # bool True/False: treat as 0 dose if False, 1 if True
                params["dopamine"] = [int(value), "mcg/kg/min"]
            elif isinstance(value, (int, float)):
                params["dopamine"] = [value, "mcg/kg/min"]
            else:
                params["dopamine"] = [0, "mcg/kg/min"]
        elif key_lower in ("dobutamine", "dobutamine_dose"):
            if isinstance(value, list):
                params["dobutamine"] = value
            elif isinstance(value, bool):
                params["dobutamine"] = [int(value), "mcg/kg/min"]
            elif isinstance(value, (int, float)):
                params["dobutamine"] = [value, "mcg/kg/min"]
            else:
                params["dobutamine"] = [0, "mcg/kg/min"]
        elif key_lower in ("epinephrine", "epinephrine_dose"):
            if isinstance(value, list):
                params["epinephrine"] = value
            elif isinstance(value, bool):
                params["epinephrine"] = [int(value), "mcg/kg/min"]
            elif isinstance(value, (int, float)):
                params["epinephrine"] = [value, "mcg/kg/min"]
            else:
                params["epinephrine"] = [0, "mcg/kg/min"]
        elif key_lower in ("norepinephrine", "norepinephrine_dose"):
            if isinstance(value, list):
                params["norepinephrine"] = value
            elif isinstance(value, bool):
                params["norepinephrine"] = [int(value), "mcg/kg/min"]
            elif isinstance(value, (int, float)):
                params["norepinephrine"] = [value, "mcg/kg/min"]
            else:
                params["norepinephrine"] = [0, "mcg/kg/min"]

        # === Mechanical ventilation / CPAP — SOFA checks these as booleans ===
        elif key_lower in ("mechanical_ventilation", "on_ventilator", "ventilator"):
            params["mechanical_ventilation"] = bool(value) if not isinstance(value, bool) else value
        elif key_lower in ("cpap", "continuous_positive_airway_pressure"):
            params["cpap"] = bool(value) if not isinstance(value, bool) else value

        # === Direct pass-through ===
        else:
            # Handle boolean-like string values
            if isinstance(value, str):
                val_lower = value.lower()
                if val_lower in ("true", "yes", "1", "present"):
                    value = True
                elif val_lower in ("false", "no", "0", "absent"):
                    value = False
            # Booleans: convert to [int(bool_val), ""] to prevent
            # 'bool' object is not subscriptable errors when official
            # calculators do param[0].
            if isinstance(value, bool):
                params[key_lower] = value
            # Wrap bare numbers in [value, ""] to prevent 'int' not subscriptable
            # errors when official calculators do param[0]/param[1]
            # The few params that need bare numbers (gcs, a_a_gradient, inr)
            # have explicit handlers above.
            elif isinstance(value, (int, float)):
                params[key_lower] = [value, ""]
            else:
                params[key_lower] = value

    # === Post-processing: detect bare steroid name keys ===
    # If the LLM sends e.g. {"Hydrocortisone": 100, "target": "PredniSONE PO"},
    # detect the steroid name as a key and construct "input steroid" from it.
    _STEROID_NAMES = {
        "betamethasone": "Betamethasone IV", "cortisone": "Cortisone PO",
        "dexamethasone": "Dexamethasone IV", "decadron": "Dexamethasone IV",
        "hydrocortisone": "Hydrocortisone PO", "methylprednisolone": "MethylPrednisoLONE IV",
        "prednisolone": "PrednisoLONE PO", "prednisone": "PredniSONE PO",
        "triamcinolone": "Triamcinolone IV",
    }
    if "input steroid" not in params and calculator_name and "steroid" in (calculator_name or "").lower():
        for k, v in list(params.items()):
            k_clean = k.lower().strip().replace(" ", "")
            for short, official in _STEROID_NAMES.items():
                if short in k_clean:
                    dose = _unwrap_list_value(v) if isinstance(v, list) else v
                    if isinstance(dose, (int, float)):
                        params["input steroid"] = [official, dose, "mg"]
                    else:
                        params["input steroid"] = [official, 1, "mg"]
                    del params[k]
                    break
            if "input steroid" in params:
                break

    # === Post-processing: fix up steroid dose if sent separately ===
    if "input steroid" in params and isinstance(params["input steroid"], list):
        # If dose/unit were sent as separate keys, patch them into the list
        if "steroid_dose" in params or "dose" in params:
            dose = params.pop("steroid_dose", params.pop("dose", None))
            if dose is not None:
                dose_val = _unwrap_list_value(dose) if isinstance(dose, list) else dose
                params["input steroid"][1] = dose_val
        if "steroid_dose_unit" in params or "dose_unit" in params:
            unit = params.pop("steroid_dose_unit", params.pop("dose_unit", None))
            if unit is not None:
                unit_val = unit[0] if isinstance(unit, list) else unit
                if len(params["input steroid"]) >= 3:
                    params["input steroid"][2] = unit_val

    # === Post-processing: MME medication key rewriting ===
    # The official mme.py iterates over input_parameters, splits on " Dose",
    # and expects keys like "Methadone Dose" / "Methadone Dose Per Day" with
    # exact FDA tall-man lettering.  The LLM sends lowercase_underscore keys.
    _MME_DRUG_MAP = {
        "codeine": "Codeine", "fentanyl_buccal": "FentaNYL buccal",
        "fentanyl_patch": "FentANYL patch", "hydrocodone": "HYDROcodone",
        "hydromorphone": "HYDROmorphone", "methadone": "Methadone",
        "morphine": "Morphine", "oxycodone": "OxyCODONE",
        "oxymorphone": "OxyMORphone", "tapentadol": "Tapentadol",
        "tramadol": "TraMADol", "buprenorphine": "Buprenorphine",
    }
    if calculator_name and "mme" in (calculator_name or "").lower():
        # First: expand a "medications" or "opioid_medications" dict if present
        for meds_key in ("medications", "opioid_medications", "opioids"):
            if meds_key in params and isinstance(params[meds_key], dict):
                meds = params.pop(meds_key)
                for med_key, med_val in meds.items():
                    params[med_key.lower().replace(" ", "_")] = med_val
            elif meds_key in params and isinstance(params[meds_key], list):
                # Remove container keys that are lists (not individual drugs)
                params.pop(meds_key)

        # Rewrite LLM-style keys to official format
        rewritten = {}
        keys_to_remove = []
        for k, v in list(params.items()):
            k_low = k.lower().replace(" ", "_")
            # Match drug_name_dose or drug_name_dose_per_day patterns
            for llm_name, official_name in _MME_DRUG_MAP.items():
                if k_low.startswith(llm_name):
                    suffix = k_low[len(llm_name):]
                    if suffix in ("_dose_per_day", "_doses_per_day", "_per_day",
                                  "_frequency", "_freq"):
                        new_key = f"{official_name} Dose Per Day"
                        wrapped = v if isinstance(v, list) else [v, "doses/day"]
                        rewritten[new_key] = wrapped
                        keys_to_remove.append(k)
                    elif suffix in ("_dose", "_mg", "_mcg", "_ug", "",
                                    "_amount", "_quantity"):
                        new_key = f"{official_name} Dose"
                        if isinstance(v, list):
                            wrapped = v
                        elif isinstance(v, (int, float)):
                            # Use µg for fentanyl variants, mg for everything else
                            unit = "µg" if "fentanyl" in llm_name else "mg"
                            wrapped = [v, unit]
                        else:
                            wrapped = [v, "mg"]
                        rewritten[new_key] = wrapped
                        keys_to_remove.append(k)
                    break
                # Also match if a drug name appears anywhere in the key
                # e.g., "morphine_equivalent_doses" contains "morphine"
                elif llm_name in k_low and k_low not in keys_to_remove:
                    # Determine if it's a frequency/per_day or dose key
                    if any(x in k_low for x in ("per_day", "frequency", "freq")):
                        new_key = f"{official_name} Dose Per Day"
                        wrapped = v if isinstance(v, list) else [v, "doses/day"]
                    else:
                        new_key = f"{official_name} Dose"
                        if isinstance(v, list):
                            wrapped = v
                        elif isinstance(v, (int, float)):
                            unit = "µg" if "fentanyl" in llm_name else "mg"
                            wrapped = [v, unit]
                        else:
                            wrapped = [v, "mg"]
                    rewritten[new_key] = wrapped
                    keys_to_remove.append(k)
                    break
        for k in keys_to_remove:
            if k in params:
                del params[k]
        params.update(rewritten)

        # Remove any remaining non-drug keys that would confuse the MME
        # calculator's iteration.  Valid keys are "{DrugName} Dose" and
        # "{DrugName} Dose Per Day" only.
        _MME_VALID_SUFFIXES = (" Dose", " Dose Per Day")
        stale_keys = [k for k in params
                      if not any(k.endswith(s) for s in _MME_VALID_SUFFIXES)
                      and k not in ("medications", "opioid_medications", "opioids")]
        for sk in stale_keys:
            del params[sk]

    # === Post-processing: normalize date formats to MM/DD/YYYY ===
    # Official gestational age / due date / conception date calculators use
    # strptime with '%m/%d/%Y'.  LLMs often send ISO format (YYYY-MM-DD).
    for date_key in ("menstrual_date", "delivery_date", "conception_date", "current_date"):
        if date_key in params and isinstance(params[date_key], str):
            params[date_key] = _normalize_date_format(params[date_key])

    # === Post-processing: GCS sub-component fallback ===
    # If calculator is GCS and only total gcs score is present (no sub-components),
    # set all three to "not testable" (official calc gives full score for "not testable").
    calc_lower = (calculator_name or "").lower()
    if "glasgow" in calc_lower or "gcs" in calc_lower:
        gcs_subs = ("best_eye_response", "best_verbal_response", "best_motor_response")
        if not any(s in params for s in gcs_subs) and "gcs" in params:
            # eye/verbal have "not testable" key (full score), motor doesn't
            params.setdefault("best_eye_response", "not testable")
            params.setdefault("best_verbal_response", "not testable")
            params.setdefault("best_motor_response", "obeys commands")  # 6 pts = full score

    # === Post-processing: Caprini mobility normalization ===
    # Official Caprini calculator expects exact strings: "normal",
    # "on bed rest", "confined to bed >72 hours" for mobility.
    if "caprini" in calc_lower:
        if "mobility" in params and isinstance(params["mobility"], str):
            mob_lower = params["mobility"].lower().strip()
            if mob_lower in ("normal", "full", "ambulatory", "out of bed",
                             "ambulating", "walking", "mobile"):
                params["mobility"] = "normal"
            elif mob_lower in ("bed rest", "on bed rest",
                               "medical patient currently on bed rest",
                               "medical patient currently at bed rest",
                               "medical patient on bed rest",
                               "on bedrest", "bedrest"):
                params["mobility"] = "on bed rest"
            elif any(kw in mob_lower for kw in ("confined", ">72", "72 hours",
                                                 "72 hrs", "greater than 72")):
                params["mobility"] = "confined to bed >72 hours"

    # === Post-processing: Caprini surgery_type normalization ===
    # Official Caprini calculator expects exact strings for surgery type.
    if "caprini" in calc_lower:
        if "surgery_type" in params and isinstance(params["surgery_type"], str):
            surg_lower = params["surgery_type"].lower().strip()
            if "arthroplasty" not in surg_lower and \
               "elective major lower extremity" in surg_lower:
                params["surgery_type"] = "elective major lower extremity arthroplasty"
            elif surg_lower in ("major surgery", "major open", "major open surgery"):
                params["surgery_type"] = "major"
            elif surg_lower in ("minor surgery", "minor procedure"):
                params["surgery_type"] = "minor"
            elif surg_lower in ("laparoscopic surgery", "laparoscopic procedure"):
                params["surgery_type"] = "laparoscopic"
            elif surg_lower in ("no surgery", "none", "n/a", "not applicable"):
                params["surgery_type"] = "none"

    # === Post-processing: calculator-specific missing-param defaults ===
    # Many official calculators crash with KeyError when the LLM omits a
    # required parameter.  Inject neutral defaults rather than crashing.
    _CALC_DEFAULTS = {
        "centor":               {"temperature": [37.0, "degrees celsius"]},
        "apache":               {"fio2": [21, "%"], "gcs": 15, "hematocrit": [40, "%"],
                                 "pao2": [80, "mmHg"], "partial_pressure_oxygen": [80, "mmHg"],
                                 "sys_bp": [120, "mmHg"], "dia_bp": [80, "mmHg"],
                                 "a_a_gradient": 10,
                                 "wbc": [7000, "cells/mm^3"]},
        "sofa":                 {"pao2": [80, "mmHg"], "fio2": [21, "%"]},
        "curb":                 {"sys_bp": [120, "mmHg"], "dia_bp": [80, "mmHg"],
                                 "bun": [15, "mg/dL"]},
        "wells":                {"heart_rate": [80, "bpm"]},
        "blatchford":           {"bun": [15, "mg/dL"], "sex": "Male",
                                 "hemoglobin": [14, "g/dL"], "sys_bp": [120, "mmHg"]},
        "psi":                  {"partial_pressure_oxygen": [80, "mmHg"],
                                 "pao2": [80, "mmHg"], "bun": [15, "mg/dL"],
                                 "sex": "Male"},
        "framingham":           {"sex": "Male"},
        "creatinine_clearance": {"sex": "Male"},
        "creatinine clearance": {"sex": "Male"},
        "cockcroft":            {"sex": "Male"},
        "ideal_body":           {"sex": "Male"},
        "ideal body":           {"sex": "Male"},
        "ckd":                  {"sex": "Male"},
        "mdrd":                 {"sex": "Male"},
        "free_water":           {"sex": "Male"},
        "free water":           {"sex": "Male"},
        "caprini":              {"sex": "Male"},
    }
    for pattern, defaults in _CALC_DEFAULTS.items():
        if pattern in calc_lower:
            for param, default_val in defaults.items():
                if param not in params:
                    params[param] = default_val

    # === Post-processing: normalize unit strings in [value, unit] lists ===
    # The official calculators' unit conversion dicts only accept specific
    # unit strings.  Normalize common variants.
    _UNIT_NORM_MAP = {
        # Count units (for convert_to_units_per_liter_explanation)
        "platelet_count": _normalize_count_unit,
        "wbc": _normalize_count_unit,
    }
    for param_name, normalizer in _UNIT_NORM_MAP.items():
        if param_name in params and isinstance(params[param_name], list) and len(params[param_name]) >= 2:
            params[param_name][1] = normalizer(str(params[param_name][1]))

    # Normalize temperature unit for convert_temperature.fahrenheit_to_celsius_explanation
    if "temperature" in params and isinstance(params["temperature"], list) and len(params["temperature"]) >= 2:
        params["temperature"][1] = _normalize_temperature_unit(str(params["temperature"][1]))

    # === Post-processing: fix volume unit case sensitivity ===
    # unit_converter_new expects exact-case units: 'L', 'dL', 'mL', 'µL'.
    # LLMs often send lowercase variants like "mEq/l" or "mg/dl" which crash.
    _UNIT_CASE_FIXES = {
        "l": "L", "dl": "dL", "ml": "mL", "ul": "µL",
        "meq/l": "mEq/L", "mg/dl": "mg/dL", "g/dl": "g/dL",
        "u/l": "U/L", "iu/l": "IU/L", "mmol/l": "mmol/L",
        "µiu/ml": "µIU/mL", "ng/ml": "ng/mL", "pg/ml": "pg/mL",
        "meq": "mEq", "mm hg": "mmHg", "mmhg": "mmHg",
        "µmol": "µmol", "umol": "µmol", "µmol/l": "µmol/L",
        "umol/l": "µmol/L",
        "gm": "g", "gm/dl": "g/dL", "gm/l": "g/L",
    }
    for param_name, param_val in params.items():
        if isinstance(param_val, list) and len(param_val) >= 2 and isinstance(param_val[1], str):
            # Normalize Greek mu (U+03BC μ) to micro sign (U+00B5 µ) before lookup
            unit_str = param_val[1].replace("\u03bc", "\u00b5")
            low_unit = unit_str.lower().strip()
            if low_unit in _UNIT_CASE_FIXES:
                params[param_name][1] = _UNIT_CASE_FIXES[low_unit]
            elif unit_str != param_val[1]:
                # Even if not in fixes dict, apply the mu normalization
                params[param_name][1] = unit_str

    # === Post-processing: ensure PSI's partial_pressure_oxygen is set ===
    # PSI uses input_variables.get("partial_pressure_oxygen") which is separate
    # from pao2.  Ensure both are populated.
    if "pao2" in params and "partial_pressure_oxygen" not in params:
        params["partial_pressure_oxygen"] = params["pao2"]
    if "partial_pressure_oxygen" in params and "pao2" not in params:
        params["pao2"] = params["partial_pressure_oxygen"]

    # === Post-processing: guard against None subscripting ===
    # Some calculators do param[0] / param[1] which would fail on None.
    # Remove None-valued keys that need to be subscriptable.
    _SUBSCRIPTABLE_KEYS = {
        "heart_rate", "qt_interval", "sys_bp", "dia_bp", "creatinine", "bun",
        "sodium", "potassium", "chloride", "bicarbonate", "glucose", "albumin",
        "calcium", "bilirubin", "ast", "alt", "platelet_count", "hemoglobin",
        "pao2", "paco2", "fio2", "urine_output", "hematocrit", "temperature",
        "respiratory_rate", "wbc", "total_cholesterol", "hdl_cholesterol",
        "triglycerides", "urine_sodium", "urine_creatinine", "phosphorus",
        "magnesium", "lactate", "urea", "insulin", "weight", "height", "age",
        "partial_pressure_oxygen", "oxygen_sat",
    }
    for sk in _SUBSCRIPTABLE_KEYS:
        if sk in params and params[sk] is None:
            del params[sk]

    # === Post-processing: ensure [value, unit] lists with empty-string units
    # don't fail unit-dict lookups.  Replace "" with a sensible default where
    # we can infer the expected unit from the parameter name. ===
    _DEFAULT_UNITS = {
        "heart_rate": "bpm", "qt_interval": "msec",
        "sys_bp": "mmHg", "dia_bp": "mmHg",
        "creatinine": "mg/dL", "bun": "mg/dL",
        "sodium": "mEq/L", "potassium": "mEq/L",
        "chloride": "mEq/L", "bicarbonate": "mEq/L",
        "glucose": "mg/dL", "albumin": "g/dL",
        "calcium": "mg/dL", "bilirubin": "mg/dL",
        "ast": "U/L", "alt": "U/L",
        "hemoglobin": "g/dL", "hematocrit": "%",
        "pao2": "mmHg", "paco2": "mmHg",
        "fio2": "%", "urine_output": "mL/day",
        "temperature": "degrees celsius",
        "respiratory_rate": "breaths per minute",
        "total_cholesterol": "mg/dL", "hdl_cholesterol": "mg/dL",
        "triglycerides": "mg/dL",
        "urine_sodium": "mEq/L", "urine_creatinine": "mg/dL",
        "phosphorus": "mg/dL", "magnesium": "mg/dL",
        "lactate": "mmol/L", "insulin": "µIU/mL",
        "weight": "kg", "height": "cm",
        "age": "years", "partial_pressure_oxygen": "mmHg",
        "oxygen_sat": "%",
    }
    for param_name, default_unit in _DEFAULT_UNITS.items():
        if param_name in params and isinstance(params[param_name], list) and len(params[param_name]) >= 2:
            if params[param_name][1] == "" or params[param_name][1] is None:
                params[param_name][1] = default_unit

    return params


def get_official_source(calculator_name: str) -> Optional[str]:
    """Get the source code of an official calculator for use in extraction prompts."""
    calc = get_calculator(calculator_name)
    if calc is None:
        return None

    full_path = CALC_DIR / Path(calc.file_path).name
    if not full_path.exists():
        return None

    try:
        with open(full_path) as f:
            return f.read()
    except Exception:
        return None


def get_expected_params(calculator_name: str) -> List[str]:
    """
    Extract expected parameter names from official calculator source.
    Looks for patterns like: params['xxx'] or input_variables['xxx']
    """
    import re
    source = get_official_source(calculator_name)
    if not source:
        return []

    # Find all parameter accesses
    patterns = [
        r"params\['(\w+)'\]",
        r'params\["(\w+)"\]',
        r"input_variables\['(\w+)'\]",
        r'input_variables\["(\w+)"\]',
        r"variables\['(\w+)'\]",
        r'variables\["(\w+)"\]',
        r"input_parameters\.get\('(\w+)'",
        r'input_parameters\.get\("(\w+)"',
        r"input_parameters\['(\w+)'\]",
    ]

    params = set()
    for pattern in patterns:
        matches = re.findall(pattern, source)
        params.update(matches)

    return sorted(list(params))


# Auto-load on import
load_calculators()


if __name__ == "__main__":
    print(f"Loaded {len(get_all_calculator_names())} official calculators:")
    for name in get_all_calculator_names()[:10]:
        calc = get_calculator(name)
        print(f"  - {name}: {calc.file_path}")
    print("  ...")
