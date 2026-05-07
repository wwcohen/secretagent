"""
MedCalc-Bench Calculator Implementations (ALL 55 CALCULATORS).

Pure Python implementations of all 55 calculators from MedCalc-Bench v1.2.
Formulas derived from training data ground truth explanations.

Categories:
- Physical/Anthropometric (7): BMI, IBW, ABW, BSA, MAP, Target Weight, Maintenance Fluids
- Renal Function (3): Creatinine Clearance, CKD-EPI GFR, MDRD GFR
- Electrolytes/Metabolic (10): Anion Gap, Delta Gap/Ratio, Osmolality, Corrections, LDL, FENa
- Cardiac (9): QTc (5 formulas), CHA2DS2-VASc, HEART Score, RCRI, Wells PE
- Hepatic (4): FIB-4, MELD-Na, Child-Pugh, Steroid Conversion
- Pulmonary (4): CURB-65, PSI, PERC, SOFA
- Infectious/Inflammatory (4): Centor, FeverPAIN, SIRS, GBS
- Hematologic/Coagulation (4): HAS-BLED, Wells DVT, Caprini, MME
- ICU Scoring (2): APACHE II, Charlson Comorbidity Index
- Obstetric (3): Gestational Age, Due Date, Conception Date
- Other (5): GCS, HOMA-IR, Framingham Risk
"""

import re
import math
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from dataclasses import dataclass


# =============================================================================
# Result container
# =============================================================================

@dataclass
class CalcResult:
    """Result from a calculator."""
    calculator_name: str
    result: float
    extracted_values: Dict[str, Any]
    method: str = "python"
    formula_used: str = ""
    confidence: float = 1.0  # Extraction confidence (0.0-1.0)


# =============================================================================
# Value extraction utilities
# =============================================================================

def extract_number(text: str, patterns: List[str], default: Optional[float] = None) -> Optional[float]:
    """Extract a numeric value using regex patterns."""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, IndexError):
                continue
    return default


def extract_age(text: str) -> Optional[float]:
    """Extract age from text.

    Handles various formats:
    - "87-year-old man"
    - "An 87-year-old"
    - "age 65"
    - "aged 65"
    - "at age 45"
    - "45-year-old, 58 kg, 156 cm woman"
    """
    patterns = [
        # Article prefix: "An 87-year-old" or "A 45-year-old"
        r'(?:an?\s+)?(\d+)\s*[-–]?\s*year\s*[-–]?\s*old',
        # Standard patterns
        r'(\d+)\s*[-–]?\s*(?:year|yr|y/?o|years?\s*old)',
        r'age[:\s]+(\d+)',
        r'(\d+)\s*yo\b',
        r'(\d+)\s*(?:year|yr)s?\s*(?:of\s+age|old)',
        r'(?:is|was)\s+(\d+)\s*(?:years?\s*old)?',
        # "aged 65" or "at age 45"
        r'aged\s+(\d+)',
        r'at\s+age\s+(\d+)',
        # Comma-separated at start: "45-year-old, 58 kg"
        r'^(\d+)\s*[-–]?\s*year',
    ]
    age = extract_number(text, patterns)
    # Validate age is reasonable
    if age is not None and 0 < age <= 120:
        return age
    return None


def extract_race(text: str) -> Optional[str]:
    """Extract race from clinical text."""
    text_lower = text.lower()
    # Remove instructional text like "If the patient is black, please use the MDRD..."
    # to avoid false positive race extraction from question instructions
    text_lower = re.sub(r'if the patient is black[^.]*\.?', '', text_lower)
    black_patterns = [
        'african american', 'african-american', 'black race', 'black male',
        'black female', 'black patient', 'black man', 'black woman',
        r'\bblack\b'
    ]
    for pattern in black_patterns:
        if re.search(pattern, text_lower):
            return 'black'
    return None


def extract_sex(text: str) -> Optional[str]:
    """Extract sex from text. Returns 'male' or 'female'."""
    text_lower = text.lower()
    # Check for explicit gender
    if re.search(r'\b(male|man|boy|gentleman|mr\.)\b', text_lower):
        if 'female' not in text_lower and 'woman' not in text_lower:
            return 'male'
    if re.search(r'\b(female|woman|girl|lady|mrs\.|ms\.)\b', text_lower):
        return 'female'
    return None


def extract_weight_kg(text: str) -> Optional[float]:
    """Extract weight in kg.

    Handles various formats:
    - "weight: 75 kg"
    - "weighs 75 kg" / "weighed 67.2 kg" / "weighing 70 kg"
    - "75 kg"
    - "body weight 80 kg"
    - "231 lb" (converts to kg)
    """
    # Try kg first (various verb forms)
    patterns_kg = [
        r'weigh(?:s|ed|ing)?\s+(\d+\.?\d*)\s*kg',  # weigh/weighed/weighing
        r'weight[:\s,]+(\d+\.?\d*)\s*kg',
        r'body\s*weight[:\s,]+(\d+\.?\d*)',
        r'(\d+\.?\d*)\s*kg\b(?!\s*/)',  # avoid "kg/m2"
        r'(\d+\.?\d*)\s*kilograms?',
    ]
    kg = extract_number(text, patterns_kg)
    if kg and 10 < kg < 400:  # Reasonable weight range
        return kg

    # Try lbs
    patterns_lb = [
        r'weigh(?:s|ed|ing)?\s+(\d+\.?\d*)\s*(?:lbs?|pounds?)',
        r'weight[:\s,]+(\d+\.?\d*)\s*(?:lbs?|pounds?)',
        r'(\d+\.?\d*)\s*(?:lbs?|pounds?)\b',
    ]
    lb = extract_number(text, patterns_lb)
    if lb and 20 < lb < 800:  # Reasonable weight range
        return lb * 0.453592

    return None


def extract_height_cm(text: str) -> Optional[float]:
    """Extract height in cm.

    Handles various formats:
    - "height: 173 cm"
    - "was 173 cm tall"
    - "163 cm (5 ft 3 in)" - parenthetical
    - "1.73 m" or "1.73 meters"
    - "5'10\"" or "5 ft 10 in"
    """
    # Try cm patterns FIRST (most common in medical notes)
    # Order matters: try patterns that match height-specific context first,
    # then general patterns. Validate each match against height range.
    patterns_cm = [
        r'(?:was|is)\s+(\d+)\s*cm\s*tall',  # "was 173 cm tall"
        r'height[:\s,]+(\d+\.?\d*)\s*cm',   # "height: 173 cm"
        r'(\d+\.?\d*)\s*centimeters?',      # "173 centimeters"
    ]

    # Try height-specific patterns first
    for pattern in patterns_cm:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                cm = float(match.group(1))
                if 50 < cm < 250:  # Reasonable height in cm
                    return cm
            except (ValueError, IndexError):
                continue

    # Fallback: try general "X cm" pattern, but avoid matching small values
    # like "7.0 cm (inside diameter)" by requiring value in height range
    general_pattern = r'(\d+\.?\d*)\s*cm\b'
    for match in re.finditer(general_pattern, text, re.IGNORECASE):
        try:
            cm = float(match.group(1))
            if 50 < cm < 250:  # Reasonable height in cm
                return cm
        except (ValueError, IndexError):
            continue

    # Try meters (but avoid matching years like "1.5 m" in other contexts)
    patterns_m = [
        r'height[:\s,]+(\d+\.?\d*)\s*m(?:eters?)?\b',
        r'(\d+\.\d+)\s*m(?:eters?)?\b',  # Require decimal for meters
    ]
    m = extract_number(text, patterns_m)
    if m:
        if m > 3:  # Likely already cm
            if 50 < m < 250:
                return m
        elif 1 < m < 2.5:  # Valid meter range
            return m * 100

    # Try feet-inches patterns - REQUIRE explicit indicator to avoid matching ages/times
    # Pattern 1: With explicit feet marker: 5'10", 5 ft 10 in, 5 feet 10 inches
    ft_in_pattern = r"(\d+)\s*(?:['\u2032]|ft|feet|foot)\s*(\d+)?\s*[\"'\u2033]?\s*(?:in|inches?)?"
    match = re.search(ft_in_pattern, text, re.IGNORECASE)
    if match:
        feet = int(match.group(1))
        inches = int(match.group(2)) if match.group(2) else 0
        if 3 <= feet <= 8:  # Reasonable feet value for height
            total_inches = feet * 12 + inches
            return total_inches * 2.54

    # Try plain inches with explicit indicator
    patterns_in = [
        r'height[:\s,]+(\d+\.?\d*)\s*(?:in|inches?)',
        r'(\d+\.?\d*)\s*(?:in|inches?)\s*tall',
    ]
    inches = extract_number(text, patterns_in)
    if inches and 40 < inches < 100:  # Reasonable height in inches
        return inches * 2.54

    return None


def extract_creatinine(text: str) -> Optional[float]:
    """Extract creatinine in mg/dL. STRICT: requires explicit units.

    Only returns a value when units are clearly specified:
    - Explicit mg/dL: returns value as-is
    - Explicit µmol/L: converts to mg/dL
    - No units: returns None (triggers LLM fallback)
    """
    # ROBUST mg/dL patterns - various formats
    patterns_mgdl = [
        # "creatinine: 1.2 mg/dL" or "creatinine 1.2 mg/dL"
        r'(?:serum\s+)?creatinine[:\s,]+(\d+\.?\d*)\s*mg\s*/\s*d[Ll]',
        r'(?:serum\s+)?creatinine[:\s,]+(\d+\.?\d*)\s*mg/d[Ll]',
        # "Cr: 1.2 mg/dL"
        r'\bcr[:\s]+(\d+\.?\d*)\s*mg\s*/\s*d[Ll]',
        r'\bcr[:\s]+(\d+\.?\d*)\s*mg/d[Ll]',
        # "1.2 mg/dL creatinine" or just "1.2 mg/dL" nearby creatinine
        r'(\d+\.?\d*)\s*mg\s*/\s*d[Ll]\s*(?:creatinine)?',
        r'(\d+\.?\d*)\s*mg/d[Ll]\s*(?:creatinine)?',
        # Parenthetical: "creatinine (1.2 mg/dL)"
        r'creatinine\s*\(\s*(\d+\.?\d*)\s*mg\s*/\s*d[Ll]\s*\)',
        r'creatinine\s*\(\s*(\d+\.?\d*)\s*mg/d[Ll]\s*\)',
    ]
    val = extract_number(text, patterns_mgdl)
    if val is not None and 0.1 <= val <= 30:
        return val

    # ROBUST µmol/L patterns - convert to mg/dL
    patterns_umol = [
        # Various spellings of µmol/L
        r'creatinine[:\s,]+(\d+\.?\d*)\s*[µμu]mol\s*/\s*[Ll]',
        r'creatinine[:\s,]+(\d+\.?\d*)\s*[µμu]mol/[Ll]',
        r'creatinine[:\s,]+(\d+\.?\d*)\s*umol\s*/\s*[Ll]',
        r'creatinine[:\s,]+(\d+\.?\d*)\s*umol/[Ll]',
        r'\bcr[:\s]+(\d+\.?\d*)\s*[µμu]mol\s*/\s*[Ll]',
        r'\bcr[:\s]+(\d+\.?\d*)\s*[µμu]mol/[Ll]',
        # Value with unit nearby
        r'(\d+\.?\d*)\s*[µμu]mol\s*/\s*[Ll]\s*(?:creatinine)?',
        r'(\d+\.?\d*)\s*[µμu]mol/[Ll]\s*(?:creatinine)?',
        r'(\d+\.?\d*)\s*umol\s*/\s*[Ll]\s*(?:creatinine)?',
        r'(\d+\.?\d*)\s*umol/[Ll]\s*(?:creatinine)?',
        # Parenthetical
        r'creatinine\s*\(\s*(\d+\.?\d*)\s*[µμu]mol\s*/\s*[Ll]\s*\)',
    ]
    val_umol = extract_number(text, patterns_umol)
    if val_umol is not None:
        converted = val_umol / 88.4
        if 0.1 <= converted <= 30:
            return converted

    # STRICT: No explicit units found - return None to trigger LLM fallback
    # Don't guess between mg/dL and µmol/L
    return None


def extract_blood_pressure(text: str) -> Tuple[Optional[float], Optional[float]]:
    """Extract systolic and diastolic blood pressure."""
    # Try pattern like "120/80 mmHg" or "BP: 120/80"
    pattern = r'(?:blood\s*pressure|bp)[:\s]+(\d+)/(\d+)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return float(match.group(1)), float(match.group(2))

    # Try pattern like "120/80"
    pattern2 = r'(\d{2,3})/(\d{2,3})\s*(?:mm\s*Hg)?'
    match2 = re.search(pattern2, text, re.IGNORECASE)
    if match2:
        return float(match2.group(1)), float(match2.group(2))

    return None, None


def extract_heart_rate(text: str) -> Optional[float]:
    """Extract heart rate in bpm."""
    patterns = [
        r'heart\s*rate[:\s,]+(\d+\.?\d*)',
        r'hr[:\s]+(\d+)',
        r'pulse[:\s]+(\d+)',
        r'(\d+)\s*(?:bpm|beats?\s*per\s*minute)',
    ]
    return extract_number(text, patterns)


def extract_temperature_celsius(text: str) -> Optional[float]:
    """Extract temperature in Celsius."""
    # Try Celsius first
    patterns_c = [
        r'temperature[:\s,]+(\d+\.?\d*)\s*°?\s*C',
        r'temp[:\s]+(\d+\.?\d*)\s*°?\s*C',
        r'(\d+\.?\d*)\s*°?\s*C\b',
    ]
    c = extract_number(text, patterns_c)
    if c and 30 < c < 45:
        return c

    # Try Fahrenheit
    patterns_f = [
        r'temperature[:\s,]+(\d+\.?\d*)\s*°?\s*F',
        r'temp[:\s]+(\d+\.?\d*)\s*°?\s*F',
        r'(\d+\.?\d*)\s*°?\s*F\b',
    ]
    f = extract_number(text, patterns_f)
    if f and 90 < f < 110:
        return (f - 32) * 5 / 9

    return None


def extract_lab_value(text: str, names: List[str], unit: str = "") -> Optional[float]:
    """Extract a lab value by name."""
    for name in names:
        patterns = [
            rf'{name}[:\s,]+(\d+\.?\d*)\s*{unit}',
            rf'{name}\s+(?:is|was|of|level)[:\s]+(\d+\.?\d*)',
            rf'(\d+\.?\d*)\s*{unit}\s*{name}',
        ]
        val = extract_number(text, patterns)
        if val is not None:
            return val
    return None


def extract_sodium(text: str) -> Optional[float]:
    """Extract sodium in mEq/L (or mmol/L, same value)."""
    return extract_lab_value(text, ['sodium', 'na'], '(?:mEq/L|mmol/L)?')


def extract_potassium(text: str) -> Optional[float]:
    """Extract potassium."""
    return extract_lab_value(text, ['potassium', 'k'], '(?:mEq/L|mmol/L)?')


def extract_chloride(text: str) -> Optional[float]:
    """Extract chloride in mEq/L."""
    # First try full name
    val = extract_lab_value(text, ['chloride'], '(?:mEq/L|mmol/L)?')
    if val is not None and 70 <= val <= 130:
        return val
    # Try abbreviation with word boundary (avoid matching 'clinical', 'class', etc.)
    patterns = [
        r'\bcl\b[:\s,]+(\d+\.?\d*)\s*(?:mEq/L|mmol/L)?',
        r'\bcl\b\s+(?:is|was|of|level)[:\s]+(\d+\.?\d*)',
        r'(\d+\.?\d*)\s*(?:mEq/L|mmol/L)\s*\(?\bcl\b',
    ]
    val = extract_number(text, patterns)
    if val is not None and 70 <= val <= 130:
        return val
    return None


def extract_bicarbonate(text: str) -> Optional[float]:
    """Extract bicarbonate/CO2.

    Tries HCO3/HCO3- first (BMP standard), then 'bicarbonate'/'bicarb'.
    Avoids bare 'co2' alias which falsely matches pCO2 (partial pressure).
    """
    unit = '(?:mEq/L|mmol/L)?'
    # Try HCO3 formats first -- this is the standard BMP abbreviation
    # 'hco3-' handles "HCO3- 18mEq/L" format (dash after abbreviation)
    val = extract_lab_value(text, ['hco3-', 'hco3'], unit)
    if val is not None:
        return val
    # Then try full names
    val = extract_lab_value(text, ['bicarbonate', 'bicarb'], unit)
    if val is not None:
        return val
    # Only match explicit total CO2, not pCO2 (partial pressure)
    return extract_lab_value(text, ['total co2', 'tco2'], unit)


def extract_bun(text: str) -> Optional[float]:
    """Extract BUN in mg/dL."""
    val = extract_lab_value(text, ['bun', 'blood urea nitrogen', 'urea nitrogen'], '(?:mg/dL)?')
    if val is None:
        # Try mmol/L and convert
        val_mmol = extract_lab_value(text, ['bun', 'urea'], 'mmol/L')
        if val_mmol:
            val = val_mmol * 2.8  # Convert mmol/L to mg/dL
    return val


def extract_glucose(text: str) -> Optional[float]:
    """Extract glucose in mg/dL."""
    return extract_lab_value(text, ['glucose', 'blood sugar', 'serum glucose'], '(?:mg/dL)?')


def extract_albumin(text: str) -> Optional[float]:
    """Extract albumin in g/dL."""
    val = extract_lab_value(text, ['albumin', 'alb'], '(?:g/[dD][lL]|g/[lL])?')
    if val is not None:
        # Sanity: albumin in g/dL is typically 1.0-6.0
        # Values > 6 are likely in g/L (normal range 35-55 g/L) — convert
        if val > 6.0:
            val = val / 10.0
        # Final sanity: reject values outside 0.5-6.0 g/dL
        if 0.5 <= val <= 6.0:
            return val
    return None


def extract_calcium(text: str) -> Optional[float]:
    """Extract calcium in mg/dL."""
    return extract_lab_value(text, ['calcium', 'ca'], '(?:mg/dL)?')


def extract_ast(text: str) -> Optional[float]:
    """Extract AST."""
    return extract_lab_value(text, ['ast', 'aspartate aminotransferase', 'sgot'], '(?:U/L|IU/L)?')


def extract_alt(text: str) -> Optional[float]:
    """Extract ALT."""
    return extract_lab_value(text, ['alt', 'alanine aminotransferase', 'sgpt'], '(?:U/L|IU/L)?')


def extract_platelets(text: str) -> Optional[float]:
    """Extract platelet count (in 10^9/L or thousands)."""
    patterns = [
        r'platelet[s]?[:\s,]+(\d+\.?\d*)\s*[×x]?\s*10\^?9',
        r'platelet[s]?[:\s,]+(\d+\.?\d*)\s*(?:k|K|thousand)',
        r'platelet[s]?[:\s,]+(\d+\.?\d*)',
        r'plt[:\s]+(\d+\.?\d*)',
    ]
    val = extract_number(text, patterns)
    if val:
        # Normalize to 10^9/L
        if val > 1000:  # Likely in raw count
            val = val / 1000
    return val


def extract_qt_interval(text: str) -> Optional[float]:
    """Extract QT interval in msec."""
    patterns = [
        r'qt\s*(?:interval)?[:\s]+(\d+\.?\d*)\s*(?:ms|msec)?',
        r'(\d+\.?\d*)\s*(?:ms|msec)\s*qt',
    ]
    return extract_number(text, patterns)


def extract_cholesterol(text: str, type_: str = 'total') -> Optional[float]:
    """Extract cholesterol values in mg/dL."""
    if type_ == 'total':
        return extract_lab_value(text, ['total cholesterol', 'cholesterol'], '(?:mg/dL)?')
    elif type_ == 'hdl':
        return extract_lab_value(text, ['hdl', 'hdl cholesterol', 'hdl-c'], '(?:mg/dL)?')
    elif type_ == 'triglycerides':
        return extract_lab_value(text, ['triglycerides', 'tg', 'trigs'], '(?:mg/dL)?')
    return None


# =============================================================================
# Physical Calculators
# =============================================================================

def calculate_bmi(text: str) -> Optional[CalcResult]:
    """Calculate Body Mass Index."""
    weight = extract_weight_kg(text)
    height_cm = extract_height_cm(text)

    if weight is None or height_cm is None:
        return None

    height_m = height_cm / 100
    bmi = weight / (height_m ** 2)

    return CalcResult(
        calculator_name="Body Mass Index (BMI)",
        result=round(bmi, 3),
        extracted_values={"weight_kg": weight, "height_cm": height_cm},
        formula_used="BMI = weight / height^2"
    )


def calculate_map(text: str) -> Optional[CalcResult]:
    """Calculate Mean Arterial Pressure."""
    systolic, diastolic = extract_blood_pressure(text)

    if systolic is None or diastolic is None:
        return None

    # MAP = (2 * DBP + SBP) / 3 = 2/3 * DBP + 1/3 * SBP
    map_value = (2 * diastolic + systolic) / 3

    return CalcResult(
        calculator_name="Mean Arterial Pressure (MAP)",
        result=round(map_value, 3),
        extracted_values={"systolic": systolic, "diastolic": diastolic},
        formula_used="MAP = (2*DBP + SBP) / 3"
    )


def calculate_ideal_body_weight(text: str) -> Optional[CalcResult]:
    """Calculate Ideal Body Weight using Devine formula."""
    sex = extract_sex(text)
    height_cm = extract_height_cm(text)

    if sex is None or height_cm is None:
        return None

    height_in = height_cm / 2.54

    if sex == 'male':
        ibw = 50 + 2.3 * (height_in - 60)
    else:
        ibw = 45.5 + 2.3 * (height_in - 60)

    return CalcResult(
        calculator_name="Ideal Body Weight",
        result=round(ibw, 3),
        extracted_values={"sex": sex, "height_cm": height_cm, "height_in": height_in},
        formula_used="IBW = 50/45.5 + 2.3*(height_in - 60)"
    )


def calculate_adjusted_body_weight(text: str) -> Optional[CalcResult]:
    """Calculate Adjusted Body Weight."""
    ibw_result = calculate_ideal_body_weight(text)
    weight = extract_weight_kg(text)

    if ibw_result is None or weight is None:
        return None

    ibw = ibw_result.result
    # ABW = IBW + 0.4 * (actual - IBW)
    abw = ibw + 0.4 * (weight - ibw)

    return CalcResult(
        calculator_name="Adjusted Body Weight",
        result=round(abw, 3),
        extracted_values={"ibw": ibw, "actual_weight": weight},
        formula_used="ABW = IBW + 0.4*(weight - IBW)"
    )


def calculate_body_surface_area(text: str) -> Optional[CalcResult]:
    """Calculate Body Surface Area using Mosteller formula."""
    weight = extract_weight_kg(text)
    height_cm = extract_height_cm(text)

    if weight is None or height_cm is None:
        return None

    # BSA = sqrt((weight * height) / 3600)
    bsa = math.sqrt((weight * height_cm) / 3600)

    return CalcResult(
        calculator_name="Body Surface Area Calculator",
        result=round(bsa, 3),
        extracted_values={"weight_kg": weight, "height_cm": height_cm},
        formula_used="BSA = sqrt((weight * height) / 3600)"
    )


def calculate_target_weight(text: str) -> Optional[CalcResult]:
    """Calculate Target Weight from target BMI."""
    # Extract target BMI from question
    patterns = [
        r'target\s*bmi[:\s]+(\d+\.?\d*)',
        r'bmi\s*(?:of|is|should\s*be)[:\s]+(\d+\.?\d*)',
    ]
    target_bmi = extract_number(text, patterns)
    height_cm = extract_height_cm(text)

    if target_bmi is None or height_cm is None:
        return None

    height_m = height_cm / 100
    target_weight = target_bmi * (height_m ** 2)

    return CalcResult(
        calculator_name="Target weight",
        result=round(target_weight, 3),
        extracted_values={"target_bmi": target_bmi, "height_cm": height_cm},
        formula_used="weight = BMI * height^2"
    )


def calculate_maintenance_fluids(text: str) -> Optional[CalcResult]:
    """Calculate Maintenance Fluids using 4-2-1 rule."""
    weight = extract_weight_kg(text)

    if weight is None:
        return None

    # 4-2-1 rule: 4 mL/kg/hr for first 10 kg, 2 mL/kg/hr for next 10 kg, 1 mL/kg/hr thereafter
    if weight <= 10:
        fluids = 4 * weight
    elif weight <= 20:
        fluids = 40 + 2 * (weight - 10)
    else:
        fluids = 60 + 1 * (weight - 20)

    return CalcResult(
        calculator_name="Maintenance Fluids Calculations",
        result=round(fluids, 3),
        extracted_values={"weight_kg": weight},
        formula_used="4-2-1 rule"
    )


# =============================================================================
# QTc Calculators
# =============================================================================

def calculate_qtc_bazett(text: str) -> Optional[CalcResult]:
    """Calculate QTc using Bazett formula."""
    qt = extract_qt_interval(text)
    hr = extract_heart_rate(text)

    if qt is None or hr is None:
        return None

    rr = 60 / hr
    qtc = qt / math.sqrt(rr)

    return CalcResult(
        calculator_name="QTc Bazett Calculator",
        result=round(qtc, 3),
        extracted_values={"qt_msec": qt, "heart_rate": hr, "rr_sec": rr},
        formula_used="QTc = QT / sqrt(RR)"
    )


def calculate_qtc_fridericia(text: str) -> Optional[CalcResult]:
    """Calculate QTc using Fridericia formula."""
    qt = extract_qt_interval(text)
    hr = extract_heart_rate(text)

    if qt is None or hr is None:
        return None

    rr = 60 / hr
    qtc = qt / (rr ** (1/3))

    return CalcResult(
        calculator_name="QTc Fridericia Calculator",
        result=round(qtc, 3),
        extracted_values={"qt_msec": qt, "heart_rate": hr, "rr_sec": rr},
        formula_used="QTc = QT / RR^(1/3)"
    )


def calculate_qtc_framingham(text: str) -> Optional[CalcResult]:
    """Calculate QTc using Framingham formula."""
    qt = extract_qt_interval(text)
    hr = extract_heart_rate(text)

    if qt is None or hr is None:
        return None

    rr = 60 / hr
    qtc = qt + 154 * (1 - rr)

    return CalcResult(
        calculator_name="QTc Framingham Calculator",
        result=round(qtc, 3),
        extracted_values={"qt_msec": qt, "heart_rate": hr, "rr_sec": rr},
        formula_used="QTc = QT + 154*(1 - RR)"
    )


def calculate_qtc_hodges(text: str) -> Optional[CalcResult]:
    """Calculate QTc using Hodges formula."""
    qt = extract_qt_interval(text)
    hr = extract_heart_rate(text)

    if qt is None or hr is None:
        return None

    rr = round(60 / hr, 5)
    qtc = qt + 1.75 * ((60 / rr) - 60)

    return CalcResult(
        calculator_name="QTc Hodges Calculator",
        result=round(qtc, 3),
        extracted_values={"qt_msec": qt, "heart_rate": hr, "rr_interval": rr},
        formula_used="QTc = QT + 1.75*(60/RR - 60)"
    )


# =============================================================================
# Lab Calculators
# =============================================================================

def calculate_creatinine_clearance(text: str) -> Optional[CalcResult]:
    """
    Calculate Creatinine Clearance using Cockcroft-Gault.

    This implements the adjusted body weight logic:
    - If BMI > 30 (obese): use Adjusted Body Weight = IBW + 0.4*(actual - IBW)
    - If BMI 25-30 (overweight): use Adjusted Body Weight
    - If BMI < 18.5 (underweight): use actual weight
    - If BMI normal: use min(IBW, actual weight)

    STRICT parsing: returns None if any required value is missing or uncertain.
    """
    age = extract_age(text)
    actual_weight = extract_weight_kg(text)
    height_cm = extract_height_cm(text)
    creatinine = extract_creatinine(text)  # STRICT: requires explicit units
    sex = extract_sex(text)

    # STRICT: all required values must be present
    if age is None or actual_weight is None or creatinine is None or sex is None:
        return None

    # STRICT: validate physiologically reasonable values
    if not (18 <= age <= 120):
        return None
    if not (20 <= actual_weight <= 300):
        return None
    if not (0.1 <= creatinine <= 30):
        return None

    # Calculate weight to use based on BMI
    if height_cm is not None:
        height_m = height_cm / 100
        bmi = actual_weight / (height_m ** 2)
        height_in = height_cm / 2.54

        # Calculate Ideal Body Weight
        if sex == 'male':
            ibw = 50 + 2.3 * (height_in - 60)
        else:
            ibw = 45.5 + 2.3 * (height_in - 60)

        # Determine which weight to use
        if bmi >= 30:  # Obese
            weight_to_use = ibw + 0.4 * (actual_weight - ibw)
            weight_type = "adjusted (obese)"
        elif bmi >= 25:  # Overweight
            weight_to_use = ibw + 0.4 * (actual_weight - ibw)
            weight_type = "adjusted (overweight)"
        elif bmi < 18.5:  # Underweight
            weight_to_use = actual_weight
            weight_type = "actual (underweight)"
        else:  # Normal BMI
            weight_to_use = min(ibw, actual_weight)
            weight_type = "min(IBW, actual)"
    else:
        # No height available - use actual weight
        weight_to_use = actual_weight
        bmi = None
        ibw = None
        weight_type = "actual (no height)"

    # CrCl = ((140 - age) * weight * gender_coef) / (creatinine * 72)
    gender_coef = 1.0 if sex == 'male' else 0.85
    crcl = ((140 - age) * weight_to_use * gender_coef) / (creatinine * 72)

    # STRICT: validate result is reasonable
    if not (0 < crcl < 300):
        return None

    return CalcResult(
        calculator_name="Creatinine Clearance (Cockcroft-Gault Equation)",
        result=round(crcl, 3),
        extracted_values={
            "age": age,
            "actual_weight": actual_weight,
            "weight_used": weight_to_use,
            "weight_type": weight_type,
            "bmi": round(bmi, 2) if bmi else None,
            "ibw": round(ibw, 2) if ibw else None,
            "creatinine": creatinine,
            "sex": sex,
            "gender_coef": gender_coef
        },
        formula_used="CrCl = ((140-age) * weight * gender_coef) / (Cr * 72); gender: male=1.0, female=0.85; weight: BMI>=25 use ABW=IBW+0.4*(actual-IBW), BMI<18.5 use actual, normal use min(IBW,actual)"
    )


def calculate_ckd_epi_gfr(text: str) -> Optional[CalcResult]:
    """Calculate GFR using CKD-EPI 2021 equation.

    STRICT parsing: returns None if any required value is missing or uncertain.
    """
    age = extract_age(text)
    creatinine = extract_creatinine(text)  # STRICT: requires explicit units
    sex = extract_sex(text)

    # STRICT: all required values must be present
    if age is None or creatinine is None or sex is None:
        return None

    # STRICT: validate extracted values
    if not (18 <= age <= 120):
        return None
    if not (0.1 <= creatinine <= 30):
        return None

    # CKD-EPI 2021 (race-free):
    # GFR = 142 × (Scr/A)^B × 0.9938^age × (1.012 if female)
    if sex == 'female':
        a = 0.7
        if creatinine <= 0.7:
            b = -0.241
        else:
            b = -1.200
        gender_coef = 1.012
    else:
        a = 0.9
        if creatinine <= 0.9:
            b = -0.302
        else:
            b = -1.200
        gender_coef = 1.0

    gfr = 142 * ((creatinine / a) ** b) * (0.9938 ** age) * gender_coef

    # STRICT: validate result is reasonable
    if not (0 < gfr < 200):
        return None

    return CalcResult(
        calculator_name="CKD-EPI Equations for Glomerular Filtration Rate",
        result=round(gfr, 3),
        extracted_values={"age": age, "creatinine": creatinine, "sex": sex},
        formula_used="GFR = 142 × (Scr/A)^B × 0.9938^age × gender_coef"
    )


def calculate_mdrd_gfr(text: str) -> Optional[CalcResult]:
    """Calculate GFR using MDRD equation."""
    age = extract_age(text)
    creatinine = extract_creatinine(text)
    sex = extract_sex(text)

    if age is None or creatinine is None or sex is None:
        return None

    # MDRD: GFR = 175 × Scr^-1.154 × age^-0.203 × (0.742 if female) × (1.212 if Black)
    race = extract_race(text)
    gender_coef = 0.742 if sex == 'female' else 1.0
    race_coef = 1.212 if race == 'black' else 1.0
    gfr = 175 * (creatinine ** -1.154) * (age ** -0.203) * gender_coef * race_coef

    return CalcResult(
        calculator_name="MDRD GFR Equation",
        result=round(gfr, 3),
        extracted_values={"age": age, "creatinine": creatinine, "sex": sex, "race": race},
        formula_used="GFR = 175 × Scr^-1.154 × age^-0.203 × gender_coef × race_coef"
    )


def calculate_anion_gap(text: str) -> Optional[CalcResult]:
    """Calculate Anion Gap."""
    sodium = extract_sodium(text)
    chloride = extract_chloride(text)
    bicarb = extract_bicarbonate(text)

    if sodium is None or chloride is None or bicarb is None:
        return None

    ag = sodium - (chloride + bicarb)

    return CalcResult(
        calculator_name="Anion Gap",
        result=round(ag, 3),
        extracted_values={"sodium": sodium, "chloride": chloride, "bicarbonate": bicarb},
        formula_used="AG = Na - (Cl + HCO3)"
    )


def calculate_delta_gap(text: str) -> Optional[CalcResult]:
    """Calculate Delta Gap."""
    ag_result = calculate_anion_gap(text)

    if ag_result is None:
        return None

    delta_gap = ag_result.result - 12

    return CalcResult(
        calculator_name="Delta Gap",
        result=round(delta_gap, 3),
        extracted_values=ag_result.extracted_values,
        formula_used="Delta Gap = AG - 12"
    )


def calculate_delta_ratio(text: str) -> Optional[CalcResult]:
    """Calculate Delta Ratio."""
    delta_gap_result = calculate_delta_gap(text)
    bicarb = extract_bicarbonate(text)

    if delta_gap_result is None or bicarb is None:
        return None

    if bicarb == 24:  # Avoid division by zero
        return None

    delta_ratio = delta_gap_result.result / (24 - bicarb)

    return CalcResult(
        calculator_name="Delta Ratio",
        result=round(delta_ratio, 3),
        extracted_values={**delta_gap_result.extracted_values, "bicarbonate": bicarb},
        formula_used="Delta Ratio = Delta Gap / (24 - HCO3)"
    )


def calculate_albumin_corrected_anion_gap(text: str) -> Optional[CalcResult]:
    """Calculate Albumin-Corrected Anion Gap."""
    ag_result = calculate_anion_gap(text)
    albumin = extract_albumin(text)

    if ag_result is None or albumin is None:
        return None

    corrected_ag = ag_result.result + 2.5 * (4 - albumin)

    return CalcResult(
        calculator_name="Albumin Corrected Anion Gap",
        result=round(corrected_ag, 3),
        extracted_values={**ag_result.extracted_values, "albumin": albumin},
        formula_used="Corrected AG = AG + 2.5*(4 - albumin)"
    )


def calculate_albumin_corrected_delta_gap(text: str) -> Optional[CalcResult]:
    """Calculate Albumin-Corrected Delta Gap."""
    corrected_ag_result = calculate_albumin_corrected_anion_gap(text)
    if corrected_ag_result is None:
        return None
    corrected_delta_gap = corrected_ag_result.result - 12
    return CalcResult(
        calculator_name="Albumin Corrected Delta Gap",
        result=round(corrected_delta_gap, 3),
        extracted_values=corrected_ag_result.extracted_values,
        formula_used="Albumin Corrected Delta Gap = Albumin Corrected AG - 12"
    )


def calculate_albumin_corrected_delta_ratio(text: str) -> Optional[CalcResult]:
    """Calculate Albumin-Corrected Delta Ratio."""
    corrected_dg_result = calculate_albumin_corrected_delta_gap(text)
    bicarb = extract_bicarbonate(text)
    if corrected_dg_result is None or bicarb is None:
        return None
    if bicarb == 24:  # Avoid division by zero
        return None
    corrected_delta_ratio = corrected_dg_result.result / (24 - bicarb)
    return CalcResult(
        calculator_name="Albumin Corrected Delta Ratio",
        result=round(corrected_delta_ratio, 5),
        extracted_values={**corrected_dg_result.extracted_values, "bicarbonate": bicarb},
        formula_used="Albumin Corrected Delta Ratio = Albumin Corrected Delta Gap / (24 - HCO3)"
    )


def calculate_serum_osmolality(text: str) -> Optional[CalcResult]:
    """Calculate Serum Osmolality."""
    sodium = extract_sodium(text)
    bun = extract_bun(text)
    glucose = extract_glucose(text)

    if sodium is None or bun is None or glucose is None:
        return None

    osm = 2 * sodium + (bun / 2.8) + (glucose / 18)

    return CalcResult(
        calculator_name="Serum Osmolality",
        result=round(osm, 3),
        extracted_values={"sodium": sodium, "bun": bun, "glucose": glucose},
        formula_used="Osm = 2*Na + BUN/2.8 + Glucose/18"
    )


def calculate_free_water_deficit(text: str) -> Optional[CalcResult]:
    """Calculate Free Water Deficit."""
    weight = extract_weight_kg(text)
    sodium = extract_sodium(text)
    age = extract_age(text)
    sex = extract_sex(text)

    if weight is None or sodium is None or age is None or sex is None:
        return None

    # Total body water percentage
    if age < 18:
        tbw_pct = 0.6  # Children
    elif sex == 'male':
        if age >= 65:
            tbw_pct = 0.5
        else:
            tbw_pct = 0.6
    else:  # female
        if age >= 65:
            tbw_pct = 0.45
        else:
            tbw_pct = 0.5

    deficit = tbw_pct * weight * (sodium / 140 - 1)

    return CalcResult(
        calculator_name="Free Water Deficit",
        result=round(deficit, 3),
        extracted_values={"weight": weight, "sodium": sodium, "tbw_pct": tbw_pct},
        formula_used="FWD = TBW% × weight × (Na/140 - 1); TBW%: child=0.6, male<65=0.6, male>=65=0.5, female<65=0.5, female>=65=0.45"
    )


def calculate_sodium_correction(text: str) -> Optional[CalcResult]:
    """Calculate Sodium Correction for Hyperglycemia."""
    sodium = extract_sodium(text)
    glucose = extract_glucose(text)

    if sodium is None or glucose is None:
        return None

    corrected = sodium + 0.024 * (glucose - 100)

    return CalcResult(
        calculator_name="Sodium Correction for Hyperglycemia",
        result=round(corrected, 3),
        extracted_values={"sodium": sodium, "glucose": glucose},
        formula_used="Corrected Na = Na + 0.024*(glucose - 100)"
    )


def calculate_calcium_correction(text: str) -> Optional[CalcResult]:
    """Calculate Calcium Correction for Hypoalbuminemia."""
    calcium = extract_calcium(text)
    albumin = extract_albumin(text)

    if calcium is None or albumin is None:
        return None

    corrected = calcium + 0.8 * (4 - albumin)

    return CalcResult(
        calculator_name="Calcium Correction for Hypoalbuminemia",
        result=round(corrected, 3),
        extracted_values={"calcium": calcium, "albumin": albumin},
        formula_used="Corrected Ca = Ca + 0.8*(4 - albumin)"
    )


def calculate_ldl(text: str) -> Optional[CalcResult]:
    """Calculate LDL using Friedewald equation."""
    total_chol = extract_cholesterol(text, 'total')
    hdl = extract_cholesterol(text, 'hdl')
    tg = extract_cholesterol(text, 'triglycerides')

    if total_chol is None or hdl is None or tg is None:
        return None

    ldl = total_chol - hdl - (tg / 5)

    return CalcResult(
        calculator_name="LDL Calculated",
        result=round(ldl, 3),
        extracted_values={"total_cholesterol": total_chol, "hdl": hdl, "triglycerides": tg},
        formula_used="LDL = Total - HDL - TG/5"
    )


def calculate_fib4(text: str) -> Optional[CalcResult]:
    """Calculate FIB-4 Index for Liver Fibrosis."""
    age = extract_age(text)
    ast = extract_ast(text)
    alt = extract_alt(text)
    platelets = extract_platelets(text)

    if age is None or ast is None or alt is None or platelets is None:
        return None

    fib4 = (age * ast) / (platelets * math.sqrt(alt))

    return CalcResult(
        calculator_name="Fibrosis-4 (FIB-4) Index for Liver Fibrosis",
        result=round(fib4, 3),
        extracted_values={"age": age, "ast": ast, "alt": alt, "platelets": platelets},
        formula_used="FIB-4 = (Age × AST) / (Platelets × √ALT)"
    )


# =============================================================================
# Additional Extraction Functions for Test-Only Calculators
# =============================================================================

def extract_bilirubin(text: str) -> Optional[float]:
    """Extract total bilirubin in mg/dL."""
    return extract_lab_value(text, ['bilirubin', 'total bilirubin', 'tbili'], '(?:mg/dL)?')


def extract_inr(text: str) -> Optional[float]:
    """Extract INR."""
    patterns = [
        r'inr[:\s,]+(\d+\.?\d*)',
        r'(?:international\s*normalized\s*ratio)[:\s,]+(\d+\.?\d*)',
    ]
    return extract_number(text, patterns)


def extract_hemoglobin(text: str) -> Optional[float]:
    """Extract hemoglobin in g/dL."""
    return extract_lab_value(text, ['hemoglobin', 'hgb', 'hb'], '(?:g/dL)?')


def extract_hematocrit(text: str) -> Optional[float]:
    """Extract hematocrit as percentage."""
    return extract_lab_value(text, ['hematocrit', 'hct'], '%?')


def extract_wbc(text: str) -> Optional[float]:
    """Extract WBC count (in 10^9/L or thousands)."""
    patterns = [
        r'wbc[:\s,]+(\d+\.?\d*)',
        r'white\s*blood\s*cells?[:\s,]+(\d+\.?\d*)',
        r'leukocytes?[:\s,]+(\d+\.?\d*)',
    ]
    return extract_number(text, patterns)


def extract_respiratory_rate(text: str) -> Optional[float]:
    """Extract respiratory rate in breaths/min."""
    patterns = [
        r'respiratory\s*rate[:\s,]+(\d+)',
        r'rr[:\s]+(\d+)',
        r'(\d+)\s*breaths?\s*(?:per\s*min|/min)',
    ]
    return extract_number(text, patterns)


def extract_pao2(text: str) -> Optional[float]:
    """Extract PaO2 in mmHg."""
    patterns = [
        r'pao2[:\s,]+(\d+\.?\d*)',
        r'arterial\s*oxygen[:\s,]+(\d+\.?\d*)',
        r'po2[:\s,]+(\d+\.?\d*)',
    ]
    return extract_number(text, patterns)


def extract_fio2(text: str) -> Optional[float]:
    """Extract FiO2 as fraction (0-1) or percentage."""
    patterns = [
        r'fio2[:\s,]+(\d+\.?\d*)\s*%',
        r'fio2[:\s,]+(\d+\.?\d*)',
    ]
    val = extract_number(text, patterns)
    if val is not None and val > 1:
        val = val / 100  # Convert percentage to fraction
    return val


def extract_ph(text: str) -> Optional[float]:
    """Extract arterial pH."""
    patterns = [
        r'ph[:\s,]+(\d+\.?\d+)',
        r'arterial\s*ph[:\s,]+(\d+\.?\d+)',
    ]
    val = extract_number(text, patterns)
    if val and 7.0 <= val <= 8.0:
        return val
    return None


def extract_gcs_components(text: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """Extract GCS components (eye, verbal, motor)."""
    eye = None
    verbal = None
    motor = None

    # Try to extract individual components
    eye_patterns = [r'eye[:\s]+(\d+)', r'e[:\s]*(\d+)(?:\s*v|\s*m|$)']
    verbal_patterns = [r'verbal[:\s]+(\d+)', r'v[:\s]*(\d+)(?:\s*m|$)']
    motor_patterns = [r'motor[:\s]+(\d+)', r'm[:\s]*(\d+)']

    for p in eye_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            eye = int(m.group(1))
            break

    for p in verbal_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            verbal = int(m.group(1))
            break

    for p in motor_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            motor = int(m.group(1))
            break

    # Try combined pattern like "GCS 15" or "E4V5M6"
    combined = re.search(r'gcs[:\s]+(\d+)', text, re.IGNORECASE)
    if combined and eye is None and verbal is None and motor is None:
        total = int(combined.group(1))
        if total == 15:
            return 4, 5, 6
        elif total == 3:
            return 1, 1, 1

    evm = re.search(r'e(\d)v(\d)m(\d)', text, re.IGNORECASE)
    if evm:
        return int(evm.group(1)), int(evm.group(2)), int(evm.group(3))

    return eye, verbal, motor


def extract_urine_sodium(text: str) -> Optional[float]:
    """Extract urine sodium in mEq/L."""
    patterns = [
        r'urine\s*(?:sodium|na)[:\s,]+(\d+\.?\d*)',
        r'(?:una|u\s*na)[:\s,]+(\d+\.?\d*)',
    ]
    return extract_number(text, patterns)


def extract_urine_creatinine(text: str) -> Optional[float]:
    """Extract urine creatinine in mg/dL."""
    patterns = [
        r'urine\s*creatinine[:\s,]+(\d+\.?\d*)',
        r'(?:ucr|u\s*cr)[:\s,]+(\d+\.?\d*)',
    ]
    return extract_number(text, patterns)


def check_condition(text: str, patterns: List[str]) -> bool:
    """Check if condition is PRESENT (not negated) in text.

    Handles negation phrases like "no diabetes", "denies hypertension", etc.
    Returns True only if the condition is mentioned without negation.
    """
    text_lower = text.lower()

    # Negation patterns that negate conditions (look for these before the match)
    negation_prefixes = [
        r'no\s+(?:history\s+of\s+)?',
        r'denies\s+(?:any\s+)?',
        r'negative\s+for\s+',
        r'without\s+(?:any\s+)?',
        r'ruled\s+out\s+',
        r'no\s+evidence\s+of\s+',
        r'absence\s+of\s+',
        r'not\s+have\s+',
        r'does\s+not\s+have\s+',
    ]

    for pattern in patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            # Check if preceded by negation (look back up to 40 chars)
            start = match.start()
            preceding_text = text_lower[max(0, start-40):start]

            # Check if any negation pattern ends right before our match
            is_negated = any(
                re.search(neg + r'\s*$', preceding_text, re.IGNORECASE)
                for neg in negation_prefixes
            )

            if not is_negated:
                return True
    return False


# =============================================================================
# Test-Only Calculators (14 additional)
# =============================================================================

def calculate_fena(text: str) -> Optional[CalcResult]:
    """Calculate Fractional Excretion of Sodium (FENa)."""
    urine_na = extract_urine_sodium(text)
    serum_na = extract_sodium(text)
    urine_cr = extract_urine_creatinine(text)
    serum_cr = extract_creatinine(text)

    if None in (urine_na, serum_na, urine_cr, serum_cr):
        return None

    # FENa = (UNa × SCr) / (SNa × UCr) × 100
    fena = (urine_na * serum_cr) / (serum_na * urine_cr) * 100

    return CalcResult(
        calculator_name="Fractional Excretion of Sodium (FENa)",
        result=round(fena, 3),
        extracted_values={
            "urine_sodium": urine_na,
            "serum_sodium": serum_na,
            "urine_creatinine": urine_cr,
            "serum_creatinine": serum_cr
        },
        formula_used="FENa = (UNa × SCr) / (SNa × UCr) × 100"
    )


def calculate_gcs(text: str) -> Optional[CalcResult]:
    """Calculate Glasgow Coma Scale."""
    eye, verbal, motor = extract_gcs_components(text)

    # If we got a total GCS directly
    gcs_match = re.search(r'gcs[:\s]+(\d+)', text, re.IGNORECASE)
    if gcs_match and eye is None:
        total = int(gcs_match.group(1))
        return CalcResult(
            calculator_name="Glasgow Coma Score (GCS)",
            result=total,
            extracted_values={"gcs_total": total},
            formula_used="GCS = Eye + Verbal + Motor"
        )

    if eye is None or verbal is None or motor is None:
        return None

    total = eye + verbal + motor

    return CalcResult(
        calculator_name="Glasgow Coma Score (GCS)",
        result=total,
        extracted_values={"eye": eye, "verbal": verbal, "motor": motor},
        formula_used="GCS = Eye + Verbal + Motor"
    )


def calculate_meld_na(text: str) -> Optional[CalcResult]:
    """Calculate MELD-Na Score (UNOS/OPTN)."""
    bilirubin = extract_bilirubin(text)
    inr = extract_inr(text)
    creatinine = extract_creatinine(text)
    sodium = extract_sodium(text)

    if None in (bilirubin, inr, creatinine, sodium):
        return None

    # Apply minimum/maximum bounds
    bilirubin = max(1.0, bilirubin)
    creatinine = max(1.0, min(4.0, creatinine))
    sodium = max(125, min(137, sodium))
    inr = max(1.0, inr)

    # MELD(i) = 0.957 × ln(Cr) + 0.378 × ln(Bili) + 1.120 × ln(INR) + 0.643
    meld_i = 0.957 * math.log(creatinine) + 0.378 * math.log(bilirubin) + \
             1.120 * math.log(inr) + 0.643
    meld_i_rounded = round(meld_i, 1)
    meld = round(meld_i_rounded * 10)

    # Only apply sodium correction if MELD > 11
    if meld > 11:
        meld_na = meld + 1.32 * (137 - sodium) - 0.033 * meld * (137 - sodium)
    else:
        meld_na = meld
    meld_na = max(6, min(40, round(meld_na)))

    return CalcResult(
        calculator_name="MELD Na (UNOS/OPTN)",
        result=meld_na,
        extracted_values={
            "bilirubin": bilirubin,
            "inr": inr,
            "creatinine": creatinine,
            "sodium": sodium,
            "meld_base": meld
        },
        formula_used="Clamp inputs: Cr=[1,4], Bili>=1, INR>=1, Na=[125,137]. MELD(i) = 0.957×ln(Cr) + 0.378×ln(Bili) + 1.120×ln(INR) + 0.643; MELD = round(round(MELD(i),1)×10); if MELD>11: MELD-Na = MELD + 1.32×(137-Na) - 0.033×MELD×(137-Na), else MELD-Na = MELD; clamp result [6,40]"
    )


def calculate_child_pugh(text: str) -> Optional[CalcResult]:
    """Calculate Child-Pugh Score for Cirrhosis Mortality."""
    bilirubin = extract_bilirubin(text)
    albumin = extract_albumin(text)
    inr = extract_inr(text)

    if None in (bilirubin, albumin, inr):
        return None

    score = 0

    # Bilirubin points
    if bilirubin < 2:
        score += 1
    elif bilirubin <= 3:
        score += 2
    else:
        score += 3

    # Albumin points
    if albumin > 3.5:
        score += 1
    elif albumin >= 2.8:
        score += 2
    else:
        score += 3

    # INR points
    if inr < 1.7:
        score += 1
    elif inr <= 2.3:
        score += 2
    else:
        score += 3

    # Ascites (check text)
    text_lower = text.lower()
    if 'severe ascites' in text_lower or 'tense ascites' in text_lower:
        score += 3
    elif 'ascites' in text_lower and ('mild' in text_lower or 'moderate' in text_lower or 'slight' in text_lower):
        score += 2
    elif 'no ascites' in text_lower or 'ascites: none' in text_lower:
        score += 1
    else:
        score += 1  # Assume none if not mentioned

    # Encephalopathy
    if 'grade 3' in text_lower or 'grade 4' in text_lower or 'severe encephalopathy' in text_lower:
        score += 3
    elif 'grade 1' in text_lower or 'grade 2' in text_lower or 'mild encephalopathy' in text_lower:
        score += 2
    elif 'no encephalopathy' in text_lower or 'encephalopathy: none' in text_lower:
        score += 1
    else:
        score += 1  # Assume none if not mentioned

    return CalcResult(
        calculator_name="Child-Pugh Score for Cirrhosis Mortality",
        result=score,
        extracted_values={"bilirubin": bilirubin, "albumin": albumin, "inr": inr},
        formula_used="Sum of points for bilirubin, albumin, INR, ascites, encephalopathy"
    )


def calculate_cci(text: str) -> Optional[CalcResult]:
    """Calculate Charlson Comorbidity Index."""
    age = extract_age(text)
    if age is None:
        return None

    score = 0
    conditions = {}
    text_lower = text.lower()

    # Age points (1 point per decade over 40)
    if age >= 50:
        age_points = min(4, (age - 40) // 10)
        score += age_points
        conditions["age_points"] = age_points

    # 1 point conditions
    one_point = [
        ('mi', ['myocardial infarction', 'heart attack', ' mi ', 'mi,']),
        ('chf', ['congestive heart failure', 'chf', 'heart failure']),
        ('pvd', ['peripheral vascular', 'pvd', 'claudication']),
        ('cva', ['cerebrovascular', 'stroke', 'cva', 'tia']),
        ('dementia', ['dementia', 'alzheimer']),
        ('copd', ['copd', 'chronic pulmonary', 'emphysema', 'chronic bronchitis']),
        ('ctd', ['connective tissue', 'lupus', 'rheumatoid arthritis', 'scleroderma']),
        ('pud', ['peptic ulcer', 'gastric ulcer', 'duodenal ulcer']),
        ('mild_liver', ['mild liver', 'chronic hepatitis']),
        ('diabetes', ['diabetes(?! with)', 'dm(?! with)']),
    ]

    for name, patterns in one_point:
        if check_condition(text_lower, patterns):
            score += 1
            conditions[name] = 1

    # 2 point conditions
    two_point = [
        ('hemiplegia', ['hemiplegia', 'paraplegia']),
        ('moderate_renal', ['moderate renal', 'renal disease', 'dialysis', 'creatinine >3']),
        ('diabetes_complications', ['diabetes with', 'diabetic nephropathy', 'diabetic retinopathy']),
        ('malignancy', ['cancer', 'malignancy', 'tumor', 'carcinoma', 'lymphoma', 'leukemia']),
    ]

    for name, patterns in two_point:
        if check_condition(text_lower, patterns):
            score += 2
            conditions[name] = 2

    # 3 point conditions
    if check_condition(text_lower, ['moderate liver', 'severe liver', 'cirrhosis', 'portal hypertension']):
        score += 3
        conditions['severe_liver'] = 3

    # 6 point conditions
    if check_condition(text_lower, ['metastatic', 'metastases', 'stage iv cancer', 'aids', ' hiv ']):
        score += 6
        conditions['metastatic_or_aids'] = 6

    return CalcResult(
        calculator_name="Charlson Comorbidity Index (CCI)",
        result=score,
        extracted_values={"age": age, "conditions": conditions},
        formula_used="Sum of weighted comorbidity points + age points"
    )


def calculate_wells_dvt(text: str) -> Optional[CalcResult]:
    """Calculate Wells' Criteria for DVT."""
    score = 0
    findings = {}
    text_lower = text.lower()

    # Active cancer (+1)
    if check_condition(text_lower, ['active cancer', 'malignancy', 'cancer treatment']):
        score += 1
        findings['active_cancer'] = 1

    # Paralysis/paresis/immobilization (+1)
    if check_condition(text_lower, ['paralysis', 'paresis', 'immobiliz', 'bedridden', 'plaster cast']):
        score += 1
        findings['paralysis_immobilization'] = 1

    # Bedridden >3 days or major surgery within 12 weeks (+1)
    if check_condition(text_lower, ['bedridden', 'recent surgery', 'major surgery', 'post-op']):
        score += 1
        findings['bedridden_surgery'] = 1

    # Localized tenderness along deep venous system (+1)
    if check_condition(text_lower, ['tenderness along', 'localized tenderness', 'calf tenderness']):
        score += 1
        findings['localized_tenderness'] = 1

    # Entire leg swollen (+1)
    if check_condition(text_lower, ['entire leg swollen', 'whole leg swell', 'leg edema']):
        score += 1
        findings['entire_leg_swollen'] = 1

    # Calf swelling >3 cm compared to other leg (+1)
    if check_condition(text_lower, ['calf swell', 'asymmetric swell', '>3 cm', 'calf circumference']):
        score += 1
        findings['calf_swelling_3cm'] = 1

    # Pitting edema confined to symptomatic leg (+1)
    if check_condition(text_lower, ['pitting edema', 'unilateral edema']):
        score += 1
        findings['pitting_edema'] = 1

    # Collateral superficial veins (+1)
    if check_condition(text_lower, ['collateral vein', 'superficial vein', 'varicose']):
        score += 1
        findings['collateral_veins'] = 1

    # Previously documented DVT (+1)
    if check_condition(text_lower, ['previous dvt', 'prior dvt', 'history of dvt', 'recurrent dvt']):
        score += 1
        findings['previous_dvt'] = 1

    # Alternative diagnosis at least as likely (-2)
    if check_condition(text_lower, ['alternative diagnosis', 'cellulitis', 'baker.s cyst', 'superficial thrombophlebitis']):
        score -= 2
        findings['alternative_diagnosis'] = -2

    return CalcResult(
        calculator_name="Wells' Criteria for DVT",
        result=score,
        extracted_values=findings,
        formula_used="Sum of clinical criteria points"
    )


def calculate_rcri(text: str) -> Optional[CalcResult]:
    """Calculate Revised Cardiac Risk Index for Pre-Operative Risk."""
    score = 0
    findings = {}
    text_lower = text.lower()

    # High-risk surgery (intraperitoneal, intrathoracic, suprainguinal vascular)
    if check_condition(text_lower, ['high.risk surgery', 'intraperitoneal', 'intrathoracic',
                                     'vascular surgery', 'aortic', 'major surgery']):
        score += 1
        findings['high_risk_surgery'] = 1

    # History of ischemic heart disease
    if check_condition(text_lower, ['ischemic heart', 'coronary artery disease', 'cad',
                                     'myocardial infarction', 'angina', 'positive stress test']):
        score += 1
        findings['ischemic_heart_disease'] = 1

    # History of congestive heart failure
    if check_condition(text_lower, ['heart failure', 'chf', 'pulmonary edema', 'lvef',
                                     's3 gallop', 'paroxysmal nocturnal dyspnea']):
        score += 1
        findings['congestive_heart_failure'] = 1

    # History of cerebrovascular disease
    if check_condition(text_lower, ['stroke', 'tia', 'cerebrovascular', 'cva']):
        score += 1
        findings['cerebrovascular_disease'] = 1

    # Insulin-dependent diabetes
    if check_condition(text_lower, ['insulin.dependent', 'type 1 diabetes', 'iddm',
                                     'diabetes.*insulin', 'insulin therapy']):
        score += 1
        findings['insulin_diabetes'] = 1

    # Preoperative creatinine >2.0 mg/dL
    creatinine = extract_creatinine(text)
    if creatinine and creatinine > 2.0:
        score += 1
        findings['elevated_creatinine'] = creatinine

    return CalcResult(
        calculator_name="Revised Cardiac Risk Index for Pre-Operative Risk",
        result=score,
        extracted_values=findings,
        formula_used="Sum of 6 risk factors (0-6 points)"
    )


def calculate_sofa(text: str) -> Optional[CalcResult]:
    """Calculate Sequential Organ Failure Assessment (SOFA) Score."""
    score = 0
    components = {}

    # Respiration: PaO2/FiO2 ratio
    pao2 = extract_pao2(text)
    fio2 = extract_fio2(text)
    if pao2 and fio2 and fio2 > 0:
        ratio = pao2 / fio2
        if ratio >= 400:
            resp_score = 0
        elif ratio >= 300:
            resp_score = 1
        elif ratio >= 200:
            resp_score = 2
        elif ratio >= 100:
            resp_score = 3
        else:
            resp_score = 4
        score += resp_score
        components['respiration'] = resp_score

    # Coagulation: Platelets
    platelets = extract_platelets(text)
    if platelets:
        if platelets >= 150:
            coag_score = 0
        elif platelets >= 100:
            coag_score = 1
        elif platelets >= 50:
            coag_score = 2
        elif platelets >= 20:
            coag_score = 3
        else:
            coag_score = 4
        score += coag_score
        components['coagulation'] = coag_score

    # Liver: Bilirubin
    bilirubin = extract_bilirubin(text)
    if bilirubin:
        if bilirubin < 1.2:
            liver_score = 0
        elif bilirubin < 2.0:
            liver_score = 1
        elif bilirubin < 6.0:
            liver_score = 2
        elif bilirubin < 12.0:
            liver_score = 3
        else:
            liver_score = 4
        score += liver_score
        components['liver'] = liver_score

    # Cardiovascular: MAP or vasopressors
    systolic, diastolic = extract_blood_pressure(text)
    if systolic and diastolic:
        map_val = (2 * diastolic + systolic) / 3
        text_lower = text.lower()
        if 'dopamine' in text_lower or 'dobutamine' in text_lower:
            if 'high dose' in text_lower or '>15' in text_lower:
                cv_score = 4
            elif '>5' in text_lower:
                cv_score = 3
            else:
                cv_score = 2
        elif 'norepinephrine' in text_lower or 'epinephrine' in text_lower:
            cv_score = 4
        elif map_val < 70:
            cv_score = 1
        else:
            cv_score = 0
        score += cv_score
        components['cardiovascular'] = cv_score

    # CNS: GCS
    eye, verbal, motor = extract_gcs_components(text)
    if eye and verbal and motor:
        gcs = eye + verbal + motor
        if gcs >= 15:
            cns_score = 0
        elif gcs >= 13:
            cns_score = 1
        elif gcs >= 10:
            cns_score = 2
        elif gcs >= 6:
            cns_score = 3
        else:
            cns_score = 4
        score += cns_score
        components['cns'] = cns_score

    # Renal: Creatinine
    creatinine = extract_creatinine(text)
    if creatinine:
        if creatinine < 1.2:
            renal_score = 0
        elif creatinine < 2.0:
            renal_score = 1
        elif creatinine < 3.5:
            renal_score = 2
        elif creatinine < 5.0:
            renal_score = 3
        else:
            renal_score = 4
        score += renal_score
        components['renal'] = renal_score

    if not components:
        return None

    return CalcResult(
        calculator_name="Sequential Organ Failure Assessment (SOFA) Score",
        result=score,
        extracted_values=components,
        formula_used="Sum of 6 organ system scores (0-24)"
    )


def calculate_has_bled(text: str) -> Optional[CalcResult]:
    """Calculate HAS-BLED Score for Major Bleeding Risk."""
    score = 0
    findings = {}
    text_lower = text.lower()

    # H - Hypertension (uncontrolled, >160 mmHg systolic)
    systolic, _ = extract_blood_pressure(text)
    if systolic and systolic > 160:
        score += 1
        findings['hypertension'] = 1
    elif check_condition(text_lower, ['uncontrolled hypertension', 'hypertension']):
        score += 1
        findings['hypertension'] = 1

    # A - Abnormal renal function (dialysis, transplant, Cr >2.26)
    creatinine = extract_creatinine(text)
    if creatinine and creatinine > 2.26:
        score += 1
        findings['abnormal_renal'] = 1
    elif check_condition(text_lower, ['dialysis', 'renal transplant', 'renal failure']):
        score += 1
        findings['abnormal_renal'] = 1

    # A - Abnormal liver function
    if check_condition(text_lower, ['cirrhosis', 'liver disease', 'hepatic', 'bilirubin >2']):
        score += 1
        findings['abnormal_liver'] = 1

    # S - Stroke history
    if check_condition(text_lower, ['stroke', 'cva', 'cerebrovascular accident']):
        score += 1
        findings['stroke'] = 1

    # B - Bleeding history or predisposition
    if check_condition(text_lower, ['bleeding', 'hemorrhage', 'anemia', 'thrombocytopenia']):
        score += 1
        findings['bleeding'] = 1

    # L - Labile INR (unstable/high INRs, TTR <60%)
    if check_condition(text_lower, ['labile inr', 'unstable inr', 'ttr <60', 'supratherapeutic']):
        score += 1
        findings['labile_inr'] = 1

    # E - Elderly (>65)
    age = extract_age(text)
    if age and age > 65:
        score += 1
        findings['elderly'] = 1

    # D - Drugs (antiplatelet, NSAIDs)
    if check_condition(text_lower, ['aspirin', 'nsaid', 'ibuprofen', 'naproxen', 'antiplatelet', 'clopidogrel']):
        score += 1
        findings['drugs_antiplatelet'] = 1

    # D - Alcohol excess
    if check_condition(text_lower, ['alcohol', 'etoh', 'drinking', 'alcoholic']):
        score += 1
        findings['alcohol'] = 1

    return CalcResult(
        calculator_name="HAS-BLED Score for Major Bleeding Risk",
        result=score,
        extracted_values=findings,
        formula_used="H-A-S-B-L-E-D criteria (0-9 points)"
    )


def calculate_gbs(text: str) -> Optional[CalcResult]:
    """Calculate Glasgow-Blatchford Bleeding Score."""
    score = 0
    components = {}

    # BUN
    bun = extract_bun(text)
    if bun:
        if bun >= 25:
            score += 6
            components['bun'] = 6
        elif bun >= 18.2:
            score += 4
            components['bun'] = 4
        elif bun >= 14:
            score += 3
            components['bun'] = 3
        elif bun >= 6.5:
            score += 2
            components['bun'] = 2

    # Hemoglobin
    hgb = extract_hemoglobin(text)
    sex = extract_sex(text)
    if hgb:
        if sex == 'male':
            if hgb < 10:
                score += 6
                components['hemoglobin'] = 6
            elif hgb < 12:
                score += 3
                components['hemoglobin'] = 3
            elif hgb < 13:
                score += 1
                components['hemoglobin'] = 1
        else:  # female
            if hgb < 10:
                score += 6
                components['hemoglobin'] = 6
            elif hgb < 12:
                score += 1
                components['hemoglobin'] = 1

    # Systolic BP
    systolic, _ = extract_blood_pressure(text)
    if systolic:
        if systolic < 90:
            score += 3
            components['systolic_bp'] = 3
        elif systolic < 100:
            score += 2
            components['systolic_bp'] = 2
        elif systolic < 110:
            score += 1
            components['systolic_bp'] = 1

    # Pulse
    hr = extract_heart_rate(text)
    if hr and hr >= 100:
        score += 1
        components['tachycardia'] = 1

    text_lower = text.lower()

    # Melena
    if check_condition(text_lower, ['melena', 'black stool', 'tarry stool']):
        score += 1
        components['melena'] = 1

    # Syncope
    if check_condition(text_lower, ['syncope', 'fainting', 'passed out', 'loss of consciousness']):
        score += 2
        components['syncope'] = 2

    # Hepatic disease
    if check_condition(text_lower, ['liver disease', 'cirrhosis', 'hepatic', 'chronic liver']):
        score += 2
        components['hepatic_disease'] = 2

    # Cardiac failure
    if check_condition(text_lower, ['heart failure', 'cardiac failure', 'chf']):
        score += 2
        components['cardiac_failure'] = 2

    if not components:
        return None

    return CalcResult(
        calculator_name="Glasgow-Blatchford Bleeding Score (GBS)",
        result=score,
        extracted_values=components,
        formula_used="Sum of clinical and lab criteria (0-23)"
    )


def calculate_apache_ii(text: str) -> Optional[CalcResult]:
    """Calculate APACHE II Score."""
    score = 0
    components = {}

    # Temperature
    temp = extract_temperature_celsius(text)
    if temp:
        if temp >= 41 or temp < 30:
            score += 4
        elif temp >= 39 or temp < 32:
            score += 3
        elif temp >= 38.5 or temp < 34:
            score += 2
        elif temp >= 36 and temp < 38.5:
            score += 0
        else:
            score += 1
        components['temperature'] = temp

    # MAP
    systolic, diastolic = extract_blood_pressure(text)
    if systolic and diastolic:
        map_val = (2 * diastolic + systolic) / 3
        if map_val >= 160 or map_val < 50:
            score += 4
        elif map_val >= 130 or map_val < 70:
            score += 2
        elif map_val >= 110:
            score += 1
        components['map'] = map_val

    # Heart rate
    hr = extract_heart_rate(text)
    if hr:
        if hr >= 180 or hr < 40:
            score += 4
        elif hr >= 140 or hr < 55:
            score += 3
        elif hr >= 110 or hr < 70:
            score += 2
        components['heart_rate'] = hr

    # Respiratory rate
    rr = extract_respiratory_rate(text)
    if rr:
        if rr >= 50 or rr < 6:
            score += 4
        elif rr >= 35:
            score += 3
        elif rr >= 25 or rr < 10:
            score += 1
        components['respiratory_rate'] = rr

    # pH
    ph = extract_ph(text)
    if ph:
        if ph >= 7.7 or ph < 7.15:
            score += 4
        elif ph >= 7.6 or ph < 7.25:
            score += 3
        elif ph < 7.33:
            score += 2
        elif ph >= 7.5:
            score += 1
        components['ph'] = ph

    # Sodium
    na = extract_sodium(text)
    if na:
        if na >= 180 or na < 111:
            score += 4
        elif na >= 160 or na < 120:
            score += 3
        elif na >= 155 or na < 130:
            score += 2
        elif na >= 150:
            score += 1
        components['sodium'] = na

    # Potassium
    k = extract_potassium(text)
    if k:
        if k >= 7 or k < 2.5:
            score += 4
        elif k >= 6:
            score += 3
        elif k >= 5.5 or k < 3:
            score += 1
        components['potassium'] = k

    # Creatinine
    cr = extract_creatinine(text)
    if cr:
        if cr >= 3.5:
            score += 4
        elif cr >= 2:
            score += 3
        elif cr >= 1.5:
            score += 2
        components['creatinine'] = cr

    # Hematocrit
    hct = extract_hematocrit(text)
    if hct:
        if hct >= 60 or hct < 20:
            score += 4
        elif hct >= 50 or hct < 30:
            score += 2
        elif hct >= 46:
            score += 1
        components['hematocrit'] = hct

    # WBC
    wbc = extract_wbc(text)
    if wbc:
        if wbc >= 40 or wbc < 1:
            score += 4
        elif wbc >= 20 or wbc < 3:
            score += 2
        elif wbc >= 15:
            score += 1
        components['wbc'] = wbc

    # GCS (15 - GCS)
    eye, verbal, motor = extract_gcs_components(text)
    if eye and verbal and motor:
        gcs = eye + verbal + motor
        score += (15 - gcs)
        components['gcs'] = gcs

    # Age points
    age = extract_age(text)
    if age:
        if age >= 75:
            score += 6
        elif age >= 65:
            score += 5
        elif age >= 55:
            score += 3
        elif age >= 45:
            score += 2
        components['age'] = age

    # Chronic health points (check for conditions)
    text_lower = text.lower()
    if check_condition(text_lower, ['immunocompromised', 'chronic organ failure',
                                     'cirrhosis', 'nyha class iv', 'dialysis dependent']):
        if check_condition(text_lower, ['emergency', 'non-operative']):
            score += 5
        else:
            score += 2
        components['chronic_health'] = True

    if not components:
        return None

    return CalcResult(
        calculator_name="APACHE II Score",
        result=score,
        extracted_values=components,
        formula_used="Acute Physiology + Age + Chronic Health points"
    )


def calculate_caprini(text: str) -> Optional[CalcResult]:
    """Calculate Caprini Score for Venous Thromboembolism (2005)."""
    score = 0
    findings = {}
    text_lower = text.lower()

    # Age points
    age = extract_age(text)
    if age:
        if age >= 75:
            score += 3
            findings['age'] = 3
        elif age >= 61:
            score += 2
            findings['age'] = 2
        elif age >= 41:
            score += 1
            findings['age'] = 1

    # 1 point factors
    one_point = [
        ('minor_surgery', ['minor surgery']),
        ('obesity', ['obese', 'bmi >25', 'bmi>25']),
        ('leg_swelling', ['leg swell', 'edema']),
        ('varicose_veins', ['varicose']),
        ('pregnancy', ['pregnant', 'pregnancy']),
        ('recent_mi', ['myocardial infarction', 'mi', 'heart attack']),
        ('chf', ['heart failure', 'chf']),
        ('sepsis', ['sepsis', 'septic']),
        ('pneumonia', ['pneumonia']),
        ('copd', ['copd']),
        ('immobility', ['bed rest', 'immobile', 'bedridden']),
    ]

    for name, patterns in one_point:
        if check_condition(text_lower, patterns):
            score += 1
            findings[name] = 1

    # 2 point factors
    two_point = [
        ('major_surgery', ['major surgery', 'laparoscop']),
        ('malignancy', ['cancer', 'malignancy']),
        ('central_line', ['central line', 'central venous', 'picc']),
        ('cast', ['plaster cast', 'cast', 'immobilization']),
    ]

    for name, patterns in two_point:
        if check_condition(text_lower, patterns):
            score += 2
            findings[name] = 2

    # 3 point factors
    if check_condition(text_lower, ['prior vte', 'previous dvt', 'previous pe', 'history of dvt']):
        score += 3
        findings['prior_vte'] = 3

    # 5 point factors
    if check_condition(text_lower, ['stroke', 'hip fracture', 'major trauma', 'spinal cord injury']):
        score += 5
        findings['high_risk_factor'] = 5

    return CalcResult(
        calculator_name="Caprini Score for Venous Thromboembolism (2005)",
        result=score,
        extracted_values=findings,
        formula_used="Sum of weighted risk factors"
    )


def calculate_psi(text: str) -> Optional[CalcResult]:
    """Calculate Pneumonia Severity Index (PSI/PORT Score)."""
    score = 0
    components = {}
    text_lower = text.lower()

    # Demographics
    age = extract_age(text)
    sex = extract_sex(text)
    if age:
        if sex == 'male':
            score += age
        else:
            score += age - 10
        components['age'] = age

    # Nursing home resident
    if check_condition(text_lower, ['nursing home', 'long-term care', 'skilled nursing']):
        score += 10
        components['nursing_home'] = 10

    # Coexisting conditions
    if check_condition(text_lower, ['neoplastic', 'cancer', 'malignancy']):
        score += 30
        components['neoplastic'] = 30

    if check_condition(text_lower, ['liver disease', 'cirrhosis', 'hepatic']):
        score += 20
        components['liver_disease'] = 20

    if check_condition(text_lower, ['heart failure', 'chf', 'congestive']):
        score += 10
        components['chf'] = 10

    if check_condition(text_lower, ['cerebrovascular', 'stroke', 'cva']):
        score += 10
        components['cerebrovascular'] = 10

    if check_condition(text_lower, ['renal disease', 'kidney disease', 'chronic kidney']):
        score += 10
        components['renal_disease'] = 10

    # Physical exam findings
    if check_condition(text_lower, ['altered mental', 'confusion', 'disoriented']):
        score += 20
        components['altered_mental'] = 20

    rr = extract_respiratory_rate(text)
    if rr and rr >= 30:
        score += 20
        components['tachypnea'] = 20

    systolic, _ = extract_blood_pressure(text)
    if systolic and systolic < 90:
        score += 20
        components['hypotension'] = 20

    temp = extract_temperature_celsius(text)
    if temp and (temp < 35 or temp >= 40):
        score += 15
        components['temperature_abnormal'] = 15

    hr = extract_heart_rate(text)
    if hr and hr >= 125:
        score += 10
        components['tachycardia'] = 10

    # Lab findings
    ph = extract_ph(text)
    if ph and ph < 7.35:
        score += 30
        components['acidosis'] = 30

    bun = extract_bun(text)
    if bun and bun >= 30:
        score += 20
        components['elevated_bun'] = 20

    na = extract_sodium(text)
    if na and na < 130:
        score += 20
        components['hyponatremia'] = 20

    glucose = extract_glucose(text)
    if glucose and glucose >= 250:
        score += 10
        components['hyperglycemia'] = 10

    hct = extract_hematocrit(text)
    if hct and hct < 30:
        score += 10
        components['anemia'] = 10

    pao2 = extract_pao2(text)
    if pao2 and pao2 < 60:
        score += 10
        components['hypoxemia'] = 10

    # Pleural effusion
    if check_condition(text_lower, ['pleural effusion']):
        score += 10
        components['pleural_effusion'] = 10

    if not components:
        return None

    return CalcResult(
        calculator_name="PSI Score: Pneumonia Severity Index for CAP",
        result=score,
        extracted_values=components,
        formula_used="Demographics + Comorbidities + Physical Exam + Labs"
    )


def calculate_framingham_risk(text: str) -> Optional[CalcResult]:
    """Calculate Framingham Risk Score for Hard Coronary Heart Disease."""
    age = extract_age(text)
    sex = extract_sex(text)
    total_chol = extract_cholesterol(text, 'total')
    hdl = extract_cholesterol(text, 'hdl')
    systolic, _ = extract_blood_pressure(text)

    if None in (age, sex, total_chol, hdl, systolic):
        return None

    text_lower = text.lower()
    smoker = check_condition(text_lower, ['smok', 'tobacco', 'cigarette'])
    treated_bp = check_condition(text_lower, ['antihypertensive', 'bp medication', 'blood pressure medication', 'treated hypertension'])

    # Simplified Framingham calculation (10-year risk)
    # This is an approximation of the full model

    if sex == 'male':
        # Male coefficients (simplified)
        ln_age = math.log(age) * 52.00961
        ln_chol = math.log(total_chol) * 20.014077
        ln_hdl = math.log(hdl) * -0.905964
        ln_sbp = math.log(systolic) * (1.916 if treated_bp else 1.809)
        smoking_pts = 7.837 if smoker else 0
        base = -172.300168

        s = ln_age + ln_chol + ln_hdl + ln_sbp + smoking_pts + base
        risk = 1 - 0.9402 ** math.exp(s)
    else:
        # Female coefficients (simplified)
        ln_age = math.log(age) * 31.764001
        ln_chol = math.log(total_chol) * 22.465206
        ln_hdl = math.log(hdl) * -1.187731
        ln_sbp = math.log(systolic) * (2.019 if treated_bp else 1.957)
        smoking_pts = 7.574 if smoker else 0
        base = -146.5933061

        s = ln_age + ln_chol + ln_hdl + ln_sbp + smoking_pts + base
        risk = 1 - 0.98767 ** math.exp(s)

    # Convert to percentage
    risk_pct = risk * 100

    return CalcResult(
        calculator_name="Framingham Risk Score for Hard Coronary Heart Disease",
        result=round(risk_pct, 1),
        extracted_values={
            "age": age,
            "sex": sex,
            "total_cholesterol": total_chol,
            "hdl": hdl,
            "systolic_bp": systolic,
            "smoker": smoker,
            "treated_bp": treated_bp
        },
        formula_used="Framingham 10-year CHD risk calculation"
    )


# =============================================================================
# Remaining Calculators (15 additional to complete all 55)
# =============================================================================

def calculate_cha2ds2_vasc(text: str) -> Optional[CalcResult]:
    """Calculate CHA2DS2-VASc Score for Atrial Fibrillation Stroke Risk.

    STRICT: Boolean condition matching is error-prone with clinical notes
    (negation, complex phrasing, context-dependent meaning).
    Always returns None to use LLM fallback for accuracy.
    """
    # STRICT: Boolean condition matching is too error-prone for clinical notes
    # Regex can't handle: "no history of diabetes", "ruled out stroke", etc.
    # Return None to trigger LLM fallback which handles context better
    return None


def calculate_curb65(text: str) -> Optional[CalcResult]:
    """Calculate CURB-65 Score for Pneumonia Severity."""
    score = 0
    findings = {}
    text_lower = text.lower()

    # C - Confusion
    if check_condition(text_lower, ['confusion', 'altered mental', 'disoriented', 'ams']):
        score += 1
        findings['confusion'] = 1

    # U - Urea/BUN > 19 mg/dL (or >7 mmol/L)
    bun = extract_bun(text)
    if bun and bun > 19:
        score += 1
        findings['elevated_bun'] = bun

    # R - Respiratory rate ≥30
    rr = extract_respiratory_rate(text)
    if rr and rr >= 30:
        score += 1
        findings['tachypnea'] = rr

    # B - Blood pressure (SBP <90 or DBP ≤60)
    systolic, diastolic = extract_blood_pressure(text)
    if systolic and systolic < 90:
        score += 1
        findings['hypotension'] = systolic
    elif diastolic and diastolic <= 60:
        score += 1
        findings['hypotension'] = diastolic

    # 65 - Age ≥65
    age = extract_age(text)
    if age and age >= 65:
        score += 1
        findings['age_65_plus'] = age

    return CalcResult(
        calculator_name="CURB-65 Score for Pneumonia Severity",
        result=score,
        extracted_values=findings,
        formula_used="Confusion + Urea + RR + BP + Age≥65 (0-5 points)"
    )


def calculate_centor(text: str) -> Optional[CalcResult]:
    """Calculate Centor Score (Modified/McIsaac) for Strep Pharyngitis."""
    score = 0
    findings = {}
    text_lower = text.lower()

    # Tonsillar exudates (+1)
    if check_condition(text_lower, ['tonsillar exudate', 'exudative tonsil', 'pus on tonsil', 'tonsillar swelling']):
        score += 1
        findings['tonsillar_exudate'] = 1

    # Tender anterior cervical lymphadenopathy (+1)
    if check_condition(text_lower, ['cervical lymphadenopathy', 'lymph node', 'tender nodes', 'swollen glands']):
        score += 1
        findings['lymphadenopathy'] = 1

    # Fever (+1)
    temp = extract_temperature_celsius(text)
    if temp and temp > 38:
        score += 1
        findings['fever'] = temp
    elif check_condition(text_lower, ['fever', 'febrile']):
        score += 1
        findings['fever'] = 1

    # Absence of cough (+1)
    if check_condition(text_lower, ['no cough', 'without cough', 'denies cough', 'cough: none']):
        score += 1
        findings['no_cough'] = 1
    elif not check_condition(text_lower, ['cough']):
        score += 1
        findings['no_cough'] = 1

    # Age modifier (McIsaac)
    age = extract_age(text)
    if age:
        if age < 15:
            score += 1
            findings['age_under_15'] = 1
        elif age > 44:
            score -= 1
            findings['age_over_44'] = -1

    return CalcResult(
        calculator_name="Centor Score (Modified/McIsaac) for Strep Pharyngitis",
        result=max(0, score),
        extracted_values=findings,
        formula_used="Exudate + Lymphadenopathy + Fever + No cough + Age modifier"
    )


def extract_lmp_date(text: str) -> Optional[str]:
    """Extract last menstrual period date."""
    patterns = [
        r'lmp[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'last\s*menstrual\s*period[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def extract_gestational_age_weeks(text: str) -> Optional[float]:
    """Extract gestational age in weeks."""
    patterns = [
        r'(\d+)\s*weeks?\s*(?:and\s*)?(\d+)?\s*days?\s*(?:gestation|gestational|pregnant)',
        r'gestational\s*age[:\s]+(\d+)\s*weeks?(?:\s*(?:and\s*)?(\d+)\s*days?)?',
        r'(\d+)\s*w\s*(\d+)?\s*d\s*gestation',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            weeks = int(m.group(1))
            days = int(m.group(2)) if m.group(2) else 0
            return weeks + days / 7
    return None


def calculate_estimated_due_date(text: str) -> Optional[CalcResult]:
    """Calculate Estimated Due Date from LMP."""
    # Try to find LMP or gestational age
    ga_weeks = extract_gestational_age_weeks(text)

    if ga_weeks:
        # Calculate weeks remaining
        weeks_remaining = 40 - ga_weeks
        days_remaining = int(weeks_remaining * 7)

        return CalcResult(
            calculator_name="Estimated Due Date",
            result=round(weeks_remaining, 1),
            extracted_values={"gestational_age_weeks": ga_weeks, "weeks_remaining": weeks_remaining},
            formula_used="EDD = 40 weeks from LMP; remaining = 40 - current GA"
        )

    return None


def calculate_gestational_age(text: str) -> Optional[CalcResult]:
    """Calculate Estimated Gestational Age."""
    ga_weeks = extract_gestational_age_weeks(text)

    if ga_weeks:
        weeks = int(ga_weeks)
        days = int((ga_weeks - weeks) * 7)

        return CalcResult(
            calculator_name="Estimated Gestational Age",
            result=round(ga_weeks, 2),
            extracted_values={"weeks": weeks, "days": days},
            formula_used="GA in weeks and days"
        )

    return None


def calculate_conception_date(text: str) -> Optional[CalcResult]:
    """Calculate Estimated Date of Conception."""
    ga_weeks = extract_gestational_age_weeks(text)

    if ga_weeks:
        # Conception typically occurs ~2 weeks after LMP
        weeks_since_conception = ga_weeks - 2

        return CalcResult(
            calculator_name="Estimated of Conception",
            result=round(weeks_since_conception, 1),
            extracted_values={"gestational_age": ga_weeks, "weeks_since_conception": weeks_since_conception},
            formula_used="Conception ≈ LMP + 2 weeks"
        )

    return None


def calculate_feverpain(text: str) -> Optional[CalcResult]:
    """Calculate FeverPAIN Score for Strep Pharyngitis."""
    score = 0
    findings = {}
    text_lower = text.lower()

    # Fever in last 24 hours (+1)
    temp = extract_temperature_celsius(text)
    if temp and temp > 38:
        score += 1
        findings['fever'] = temp
    elif check_condition(text_lower, ['fever', 'febrile']):
        score += 1
        findings['fever'] = 1

    # Purulence (pharyngeal/tonsillar exudate) (+1)
    if check_condition(text_lower, ['exudate', 'purulent', 'pus']):
        score += 1
        findings['purulence'] = 1

    # Attend rapidly (within 3 days) (+1)
    if check_condition(text_lower, ['rapid onset', 'acute onset', '1 day', '2 day', '3 day', 'sudden']):
        score += 1
        findings['rapid_attendance'] = 1

    # Inflamed tonsils (+1)
    if check_condition(text_lower, ['inflamed tonsil', 'tonsillar inflammation', 'severe inflammation',
                                     'tonsillitis', 'erythematous tonsil']):
        score += 1
        findings['inflamed_tonsils'] = 1

    # No cough or coryza (+1)
    has_cough = check_condition(text_lower, ['cough'])
    has_coryza = check_condition(text_lower, ['coryza', 'runny nose', 'nasal discharge'])
    if not has_cough and not has_coryza:
        score += 1
        findings['no_cough_coryza'] = 1

    return CalcResult(
        calculator_name="FeverPAIN Score for Strep Pharyngitis",
        result=score,
        extracted_values=findings,
        formula_used="Fever + Purulence + Attend rapidly + Inflamed tonsils + No cough/coryza (0-5)"
    )


def calculate_heart_score(text: str) -> Optional[CalcResult]:
    """Calculate HEART Score for Major Cardiac Events."""
    score = 0
    findings = {}
    text_lower = text.lower()

    # H - History (slightly/moderately/highly suspicious)
    if check_condition(text_lower, ['highly suspicious', 'typical angina', 'classic chest pain']):
        score += 2
        findings['history'] = 2
    elif check_condition(text_lower, ['moderately suspicious', 'atypical']):
        score += 1
        findings['history'] = 1

    # E - ECG (normal/non-specific/significant ST deviation)
    if check_condition(text_lower, ['st elevation', 'st depression', 'stemi', 'nstemi']):
        score += 2
        findings['ecg'] = 2
    elif check_condition(text_lower, ['non-specific', 'lbbb', 'lvh', 'repolarization']):
        score += 1
        findings['ecg'] = 1

    # A - Age
    age = extract_age(text)
    if age:
        if age >= 65:
            score += 2
            findings['age'] = 2
        elif age >= 45:
            score += 1
            findings['age'] = 1

    # R - Risk factors (HTN, DM, smoking, obesity, family hx, hyperlipidemia)
    risk_factors = 0
    if check_condition(text_lower, ['hypertension', 'htn']):
        risk_factors += 1
    if check_condition(text_lower, ['diabetes', 'dm']):
        risk_factors += 1
    if check_condition(text_lower, ['smok']):
        risk_factors += 1
    if check_condition(text_lower, ['obese', 'obesity']):
        risk_factors += 1
    if check_condition(text_lower, ['family history', 'fh of']):
        risk_factors += 1
    if check_condition(text_lower, ['hyperlipidemia', 'high cholesterol', 'dyslipidemia']):
        risk_factors += 1

    if risk_factors >= 3:
        score += 2
        findings['risk_factors'] = 2
    elif risk_factors >= 1:
        score += 1
        findings['risk_factors'] = 1

    # T - Troponin
    if check_condition(text_lower, ['troponin.*elevated', 'elevated troponin', 'troponin positive', 'troponin >3']):
        score += 2
        findings['troponin'] = 2
    elif check_condition(text_lower, ['troponin.*1-3', 'mildly elevated troponin']):
        score += 1
        findings['troponin'] = 1

    return CalcResult(
        calculator_name="HEART Score for Major Cardiac Events",
        result=score,
        extracted_values=findings,
        formula_used="History + ECG + Age + Risk factors + Troponin (0-10)"
    )


def calculate_homa_ir(text: str) -> Optional[CalcResult]:
    """Calculate HOMA-IR (Homeostatic Model Assessment for Insulin Resistance)."""
    # Extract fasting glucose (mg/dL)
    glucose = extract_glucose(text)

    # Extract fasting insulin (μU/mL)
    insulin_patterns = [
        r'(?:fasting\s*)?insulin[:\s,]+(\d+\.?\d*)',
        r'insulin\s*level[:\s,]+(\d+\.?\d*)',
    ]
    insulin = None
    for p in insulin_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            insulin = float(m.group(1))
            break

    if glucose is None or insulin is None:
        return None

    # HOMA-IR = (Glucose mg/dL × Insulin μU/mL) / 405
    homa_ir = (glucose * insulin) / 405

    return CalcResult(
        calculator_name="HOMA-IR (Homeostatic Model Assessment for Insulin Resistance)",
        result=round(homa_ir, 2),
        extracted_values={"fasting_glucose": glucose, "fasting_insulin": insulin},
        formula_used="HOMA-IR = (Glucose × Insulin) / 405"
    )


def calculate_mme(text: str) -> Optional[CalcResult]:
    """Calculate Morphine Milligram Equivalents (MME).

    Handles both formats: "methadone 20 mg" and "20 mg of Methadone".
    Extracts frequency (e.g., "3 times a day") and computes daily dose.
    Uses official MedCalc MME conversion factors.
    """
    text_lower = text.lower()
    total_mme = 0
    medications = {}

    # Official MedCalc MME conversion factors
    # Keys are lowercase search names; values are (factor, unit)
    mme_factors = {
        'codeine': (0.15, 'mg'),
        'fentanyl buccal': (0.13, 'mcg'),
        'fentanyl patch': (2.4, 'mcg'),
        'hydrocodone': (1, 'mg'),
        'hydromorphone': (5, 'mg'),
        'methadone': (4.7, 'mg'),
        'morphine': (1, 'mg'),
        'oxycodone': (1.5, 'mg'),
        'oxymorphone': (3, 'mg'),
        'tapentadol': (0.4, 'mg'),
        'tramadol': (0.2, 'mg'),
        'buprenorphine': (10, 'mg'),
    }

    for drug, (factor, _unit) in mme_factors.items():
        # Pattern 1: "drug 20 mg" or "drug 20mg"
        p1 = rf'{drug}\s+(\d+\.?\d*)\s*(?:mg|mcg|µg)'
        # Pattern 2: "20 mg of drug" or "20mg drug"
        p2 = rf'(\d+\.?\d*)\s*(?:mg|mcg|µg)\s+(?:of\s+)?{drug}'
        dose = None
        for pat in [p1, p2]:
            m = re.search(pat, text_lower)
            if m:
                dose = float(m.group(1))
                break
        if dose is None:
            continue

        # Extract frequency: "drug ... N times a/per day" or "N times a/per day ... drug"
        freq = 1  # Default: once daily
        freq_patterns = [
            rf'{drug}.*?(\d+)\s*times?\s*(?:a|per)\s*day',
            rf'(\d+)\s*times?\s*(?:a|per)\s*day.*?{drug}',
            rf'{drug}.*?(?:once|one\s*time)\s*(?:a|per)\s*day',
            rf'{drug}.*?(?:twice|two\s*times?|2\s*times?)\s*(?:a|per)\s*day',
            rf'{drug}.*?(?:three\s*times?|3\s*times?)\s*(?:a|per)\s*day',
        ]
        m_freq = re.search(freq_patterns[0], text_lower, re.DOTALL)
        if m_freq:
            freq = int(m_freq.group(1))
        else:
            m_freq = re.search(freq_patterns[1], text_lower, re.DOTALL)
            if m_freq:
                freq = int(m_freq.group(1))
            elif re.search(freq_patterns[4], text_lower, re.DOTALL):
                freq = 3
            elif re.search(freq_patterns[3], text_lower, re.DOTALL):
                freq = 2
            elif re.search(freq_patterns[2], text_lower, re.DOTALL):
                freq = 1

        daily_dose = dose * freq
        mme = daily_dose * factor
        total_mme += mme
        medications[drug] = {"dose": dose, "frequency": freq, "daily_dose": daily_dose, "mme": round(mme, 2)}

    if not medications:
        return None

    return CalcResult(
        calculator_name="Morphine Milligram Equivalents (MME) Calculator",
        result=round(total_mme, 1),
        extracted_values=medications,
        formula_used="Sum of (daily_dose × MME_conversion_factor)"
    )


def calculate_perc(text: str) -> Optional[CalcResult]:
    """Calculate PERC Rule for Pulmonary Embolism."""
    criteria_met = 0
    findings = {}
    text_lower = text.lower()

    # Age ≥50
    age = extract_age(text)
    if age and age >= 50:
        criteria_met += 1
        findings['age_50_plus'] = age

    # HR ≥100
    hr = extract_heart_rate(text)
    if hr and hr >= 100:
        criteria_met += 1
        findings['tachycardia'] = hr

    # O2 sat <95% on room air
    spo2_patterns = [r'(?:spo2|o2\s*sat|oxygen\s*sat)[:\s]+(\d+)', r'(\d+)%\s*(?:on\s*room\s*air|ra)']
    for p in spo2_patterns:
        m = re.search(p, text_lower)
        if m:
            spo2 = int(m.group(1))
            if spo2 < 95:
                criteria_met += 1
                findings['hypoxia'] = spo2
            break

    # Unilateral leg swelling
    if check_condition(text_lower, ['unilateral.*swelling', 'leg swelling', 'asymmetric.*edema']):
        criteria_met += 1
        findings['leg_swelling'] = 1

    # Hemoptysis
    if check_condition(text_lower, ['hemoptysis', 'coughing.*blood', 'blood.*sputum']):
        criteria_met += 1
        findings['hemoptysis'] = 1

    # Recent surgery or trauma
    if check_condition(text_lower, ['recent surgery', 'post-op', 'trauma', 'fracture']):
        criteria_met += 1
        findings['surgery_trauma'] = 1

    # Prior PE or DVT
    if check_condition(text_lower, ['prior pe', 'previous pe', 'history of pe', 'prior dvt', 'previous dvt']):
        criteria_met += 1
        findings['prior_pe_dvt'] = 1

    # Hormone use
    if check_condition(text_lower, ['oral contraceptive', 'ocp', 'estrogen', 'hormone replacement', 'hrt']):
        criteria_met += 1
        findings['hormone_use'] = 1

    # PERC is negative if ALL criteria = 0
    perc_negative = criteria_met == 0

    return CalcResult(
        calculator_name="PERC Rule for Pulmonary Embolism",
        result=criteria_met,
        extracted_values={"criteria_positive": findings, "perc_negative": perc_negative},
        formula_used="8 criteria; PERC negative if all 0"
    )


def calculate_qtc_rautaharju(text: str) -> Optional[CalcResult]:
    """Calculate QTc using Rautaharju formula."""
    qt_interval = extract_qt_interval(text)
    heart_rate = extract_heart_rate(text)

    if qt_interval is None or heart_rate is None:
        return None

    # Rautaharju formula: QTc = QT × (120 + HR) / 180
    qtc = qt_interval * (120 + heart_rate) / 180

    return CalcResult(
        calculator_name="QTc Rautaharju Calculator",
        result=round(qtc, 1),
        extracted_values={"qt_interval": qt_interval, "heart_rate": heart_rate},
        formula_used="QTc = QT × (120 + HR) / 180"
    )


def calculate_sirs(text: str) -> Optional[CalcResult]:
    """Calculate SIRS Criteria."""
    criteria_met = 0
    findings = {}

    # Temperature >38°C or <36°C
    temp = extract_temperature_celsius(text)
    if temp:
        if temp > 38 or temp < 36:
            criteria_met += 1
            findings['temperature'] = temp

    # Heart rate >90
    hr = extract_heart_rate(text)
    if hr and hr > 90:
        criteria_met += 1
        findings['tachycardia'] = hr

    # Respiratory rate >20 or PaCO2 <32
    rr = extract_respiratory_rate(text)
    if rr and rr > 20:
        criteria_met += 1
        findings['tachypnea'] = rr
    else:
        # Check PaCO2
        paco2_patterns = [r'paco2[:\s]+(\d+\.?\d*)', r'pco2[:\s]+(\d+\.?\d*)']
        for p in paco2_patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                paco2 = float(m.group(1))
                if paco2 < 32:
                    criteria_met += 1
                    findings['paco2'] = paco2
                break

    # WBC >12,000 or <4,000 or >10% bands
    wbc = extract_wbc(text)
    if wbc:
        if wbc > 12 or wbc < 4:
            criteria_met += 1
            findings['wbc'] = wbc

    # SIRS positive if ≥2 criteria
    sirs_positive = criteria_met >= 2

    return CalcResult(
        calculator_name="SIRS Criteria",
        result=criteria_met,
        extracted_values={"findings": findings, "sirs_positive": sirs_positive},
        formula_used="Temperature + HR + RR/PaCO2 + WBC (≥2 = SIRS positive)"
    )


def calculate_steroid_conversion(text: str) -> Optional[CalcResult]:
    """Calculate Steroid Conversion.

    Supports two modes:
    1. Target steroid specified in question → convert from input to target
       using official MedCalc conversion_dict multipliers
    2. Prednisone equivalent (default fallback) → convert all found steroids
    """
    text_lower = text.lower()

    # Official MedCalc conversion multipliers (from steroid_conversion_calculator.py)
    # Maps (steroid_lowercase, route) → multiplier
    conversion_dict = {
        ("betamethasone", "iv"): 1,
        ("cortisone", "po"): 33.33,
        ("dexamethasone", "iv"): 1,
        ("dexamethasone", "po"): 1,
        ("hydrocortisone", "iv"): 26.67,
        ("hydrocortisone", "po"): 26.67,
        ("methylprednisolone", "iv"): 5.33,
        ("methylprednisolone", "po"): 5.33,
        ("prednisolone", "po"): 6.67,
        ("prednisone", "po"): 6.67,
        ("triamcinolone", "iv"): 5.33,
    }

    # Order matters: check longer names first to avoid substring issues
    # (e.g., 'cortisone' is a substring of 'hydrocortisone')
    steroid_names = ['methylprednisolone', 'hydrocortisone', 'betamethasone',
                     'dexamethasone', 'prednisolone', 'triamcinolone',
                     'prednisone', 'cortisone']

    # Try to detect target steroid conversion (from→to pattern)
    # Look for question keywords suggesting a specific target
    conversion_keywords = ['equivalent', 'convert', 'conversion']
    has_conversion_intent = any(k in text_lower for k in conversion_keywords)

    if has_conversion_intent:
        # Find steroids with doses (input steroid) and steroids without doses (target)
        found_with_dose = {}
        found_names = set()
        for steroid in steroid_names:
            # Pattern 1: "steroid 10 mg" or "steroid 10mg"
            p1 = rf'{steroid}\s+(\d+\.?\d*)\s*mg'
            # Pattern 2: "10 mg of steroid" or "10mg steroid"
            p2 = rf'(\d+\.?\d*)\s*mg\s+(?:of\s+)?{steroid}'
            for pat in [p1, p2]:
                m = re.search(pat, text_lower)
                if m:
                    found_with_dose[steroid] = float(m.group(1))
                    break
            # Use word boundaries to avoid substring matches
            # (e.g., 'cortisone' should not match 'hydrocortisone')
            if re.search(rf'\b{steroid}\b', text_lower):
                found_names.add(steroid)

        # Target = mentioned but has no dose
        target_steroids = found_names - set(found_with_dose.keys())

        if found_with_dose and target_steroids:
            input_steroid = list(found_with_dose.keys())[0]
            input_dose = found_with_dose[input_steroid]
            target_steroid = list(target_steroids)[0]

            # Detect routes
            def detect_route(steroid_name):
                """Detect IV or PO route for a steroid from surrounding text.

                Only uses adjacent patterns (within a few words) to avoid
                picking up routes from other steroids via distant matches.
                """
                route_terms = [('iv', 'iv'), ('intravenous', 'iv'),
                               ('po', 'po'), ('oral', 'po'), ('by mouth', 'po')]
                # Check immediately adjacent: "steroid IV" or "IV steroid"
                for route_str, route_val in route_terms:
                    if re.search(rf'\b{steroid_name}\s+\b{route_str}\b', text_lower):
                        return route_val
                    if re.search(rf'\b{route_str}\b\s+{steroid_name}\b', text_lower):
                        return route_val
                # Check slightly wider context: within ~5 words (no crossing other steroid names)
                for route_str, route_val in route_terms:
                    if re.search(rf'\b{steroid_name}\b\s+(?:\w+\s+){{0,4}}\b{route_str}\b', text_lower):
                        return route_val
                # Default routes based on typical clinical usage
                defaults = {'betamethasone': 'iv', 'cortisone': 'po',
                            'prednisolone': 'po', 'prednisone': 'po',
                            'triamcinolone': 'iv'}
                return defaults.get(steroid_name, 'po')

            input_route = detect_route(input_steroid)
            target_route = detect_route(target_steroid)

            from_key = (input_steroid, input_route)
            to_key = (target_steroid, target_route)

            if from_key in conversion_dict and to_key in conversion_dict:
                from_mult = conversion_dict[from_key]
                to_mult = conversion_dict[to_key]
                result = input_dose * (to_mult / from_mult)
                return CalcResult(
                    calculator_name="Steroid Conversion Calculator",
                    result=round(result, 2),
                    extracted_values={
                        "input_steroid": input_steroid,
                        "input_route": input_route,
                        "input_dose_mg": input_dose,
                        "target_steroid": target_steroid,
                        "target_route": target_route,
                        "from_multiplier": from_mult,
                        "to_multiplier": to_mult,
                    },
                    formula_used=f"Result = dose × (to_multiplier / from_multiplier) = {input_dose} × ({to_mult}/{from_mult})"
                )

    # Fallback: prednisone equivalent mode
    pred_factors = {
        'hydrocortisone': 0.25,
        'cortisone': 0.2,
        'prednisone': 1.0,
        'prednisolone': 1.0,
        'methylprednisolone': 1.25,
        'triamcinolone': 1.25,
        'dexamethasone': 6.67,
        'betamethasone': 6.67,
    }

    total_pred_equiv = 0
    medications = {}

    for steroid, factor in pred_factors.items():
        pattern = rf'{steroid}\s*(\d+\.?\d*)\s*mg'
        m = re.search(pattern, text_lower)
        if not m:
            pattern2 = rf'(\d+\.?\d*)\s*mg\s+(?:of\s+)?{steroid}'
            m = re.search(pattern2, text_lower)
        if m:
            dose = float(m.group(1))
            pred_equiv = dose * factor
            total_pred_equiv += pred_equiv
            medications[steroid] = {"dose_mg": dose, "pred_equivalent": pred_equiv}

    if not medications:
        return None

    return CalcResult(
        calculator_name="Steroid Conversion Calculator",
        result=round(total_pred_equiv, 1),
        extracted_values=medications,
        formula_used="Prednisone equivalent = dose × conversion factor"
    )


def calculate_wells_pe(text: str) -> Optional[CalcResult]:
    """Calculate Wells' Criteria for Pulmonary Embolism."""
    score = 0
    findings = {}
    text_lower = text.lower()

    # Clinical signs of DVT (+3)
    if check_condition(text_lower, ['dvt', 'deep vein', 'leg swelling', 'calf swelling', 'asymmetric edema']):
        score += 3
        findings['clinical_dvt'] = 3

    # PE is #1 diagnosis or equally likely (+3)
    if check_condition(text_lower, ['pe likely', 'pulmonary embolism suspected', 'concern for pe', 'rule out pe']):
        score += 3
        findings['pe_likely'] = 3

    # Heart rate >100 (+1.5)
    hr = extract_heart_rate(text)
    if hr and hr > 100:
        score += 1.5
        findings['tachycardia'] = 1.5

    # Immobilization ≥3 days or surgery in past 4 weeks (+1.5)
    if check_condition(text_lower, ['immobil', 'bedridden', 'recent surgery', 'post-op', 'hospitalized']):
        score += 1.5
        findings['immobilization_surgery'] = 1.5

    # Previous PE or DVT (+1.5)
    if check_condition(text_lower, ['previous pe', 'prior pe', 'history of pe', 'previous dvt', 'prior dvt', 'history of dvt']):
        score += 1.5
        findings['previous_pe_dvt'] = 1.5

    # Hemoptysis (+1)
    if check_condition(text_lower, ['hemoptysis', 'coughing blood', 'blood in sputum']):
        score += 1
        findings['hemoptysis'] = 1

    # Malignancy (+1)
    if check_condition(text_lower, ['cancer', 'malignancy', 'carcinoma', 'tumor', 'chemotherapy']):
        score += 1
        findings['malignancy'] = 1

    return CalcResult(
        calculator_name="Wells' Criteria for Pulmonary Embolism",
        result=score,
        extracted_values=findings,
        formula_used="Sum of criteria (>4 = PE likely, ≤4 = PE unlikely)"
    )


# =============================================================================
# Main calculator dispatcher
# =============================================================================

CALCULATOR_PATTERNS = {
    # Physical
    "body mass index": calculate_bmi,
    "bmi": calculate_bmi,
    "mean arterial pressure": calculate_map,
    "map": calculate_map,
    "ideal body weight": calculate_ideal_body_weight,
    "adjusted body weight": calculate_adjusted_body_weight,
    "body surface area": calculate_body_surface_area,
    "bsa": calculate_body_surface_area,
    "target weight": calculate_target_weight,
    "maintenance fluids": calculate_maintenance_fluids,
    "maintenance fluid": calculate_maintenance_fluids,

    # QTc
    "qtc bazett": calculate_qtc_bazett,
    "bazett": calculate_qtc_bazett,
    "qtc fridericia": calculate_qtc_fridericia,
    "fridericia": calculate_qtc_fridericia,
    "fridericia formula": calculate_qtc_fridericia,
    "qt corrected fridericia": calculate_qtc_fridericia,
    "fredericia": calculate_qtc_fridericia,
    "qtc framingham": calculate_qtc_framingham,
    "framingham qtc": calculate_qtc_framingham,
    "framingham formula": calculate_qtc_framingham,
    "qtc hodges": calculate_qtc_hodges,
    "hodges": calculate_qtc_hodges,

    # Lab
    "creatinine clearance": calculate_creatinine_clearance,
    "cockcroft-gault": calculate_creatinine_clearance,
    "cockroft-gault": calculate_creatinine_clearance,
    "ckd-epi": calculate_ckd_epi_gfr,
    "glomerular filtration rate": calculate_ckd_epi_gfr,
    "gfr": calculate_ckd_epi_gfr,
    "mdrd": calculate_mdrd_gfr,
    "anion gap": calculate_anion_gap,
    "delta gap": calculate_delta_gap,
    "delta ratio": calculate_delta_ratio,
    "albumin corrected anion gap": calculate_albumin_corrected_anion_gap,
    "albumin corrected delta gap": calculate_albumin_corrected_delta_gap,
    "corrected delta gap": calculate_albumin_corrected_delta_gap,
    "albumin corrected delta ratio": calculate_albumin_corrected_delta_ratio,
    "corrected delta ratio": calculate_albumin_corrected_delta_ratio,
    "serum osmolality": calculate_serum_osmolality,
    "osmolality": calculate_serum_osmolality,
    "free water deficit": calculate_free_water_deficit,
    "free water": calculate_free_water_deficit,
    "sodium correction": calculate_sodium_correction,
    "sodium correction for hyperglycemia": calculate_sodium_correction,
    "calcium correction": calculate_calcium_correction,
    "corrected calcium": calculate_calcium_correction,
    "calcium correction for hypoalbuminemia": calculate_calcium_correction,
    "ldl": calculate_ldl,
    "ldl calculated": calculate_ldl,
    "ldl cholesterol": calculate_ldl,
    "friedewald": calculate_ldl,
    "fib-4": calculate_fib4,
    "fibrosis-4": calculate_fib4,
    "fibrosis 4": calculate_fib4,
    "fibrosis-4 index": calculate_fib4,
    "fib4": calculate_fib4,

    # Test-only calculators (14 additional)
    "fractional excretion of sodium": calculate_fena,
    "fena": calculate_fena,
    "glasgow coma": calculate_gcs,
    "gcs": calculate_gcs,
    "meld na": calculate_meld_na,
    "meld-na": calculate_meld_na,
    "meld sodium": calculate_meld_na,
    "child-pugh": calculate_child_pugh,
    "child pugh": calculate_child_pugh,
    "charlson comorbidity": calculate_cci,
    "cci": calculate_cci,
    "charlson": calculate_cci,
    "wells' criteria for dvt": calculate_wells_dvt,
    "wells criteria for dvt": calculate_wells_dvt,
    "wells' criteria for deep vein thrombosis": calculate_wells_dvt,
    "wells criteria for deep vein thrombosis": calculate_wells_dvt,
    "wells dvt": calculate_wells_dvt,
    "revised cardiac risk": calculate_rcri,
    "rcri": calculate_rcri,
    "cardiac risk index": calculate_rcri,
    "sofa": calculate_sofa,
    "sequential organ failure": calculate_sofa,
    "has-bled": calculate_has_bled,
    "hasbled": calculate_has_bled,
    "bleeding risk": calculate_has_bled,
    "glasgow-blatchford": calculate_gbs,
    "blatchford": calculate_gbs,
    "gbs": calculate_gbs,
    "apache ii": calculate_apache_ii,
    "apache 2": calculate_apache_ii,
    "caprini": calculate_caprini,
    "venous thromboembolism": calculate_caprini,
    "vte score": calculate_caprini,
    "psi score": calculate_psi,
    "pneumonia severity": calculate_psi,
    "port score": calculate_psi,
    "framingham risk": calculate_framingham_risk,
    "framingham heart": calculate_framingham_risk,
    "coronary heart disease risk": calculate_framingham_risk,

    # Remaining 15 calculators to complete all 55
    "cha2ds2-vasc": calculate_cha2ds2_vasc,
    "cha2ds2": calculate_cha2ds2_vasc,
    "chads2": calculate_cha2ds2_vasc,
    "atrial fibrillation stroke risk": calculate_cha2ds2_vasc,
    "curb-65": calculate_curb65,
    "curb65": calculate_curb65,
    "curb 65": calculate_curb65,
    "centor": calculate_centor,
    "mcisaac": calculate_centor,
    "strep pharyngitis": calculate_centor,
    "estimated due date": calculate_estimated_due_date,
    "due date": calculate_estimated_due_date,
    "edd": calculate_estimated_due_date,
    "gestational age": calculate_gestational_age,
    "estimated gestational age": calculate_gestational_age,
    "estimated date of conception": calculate_conception_date,
    "estimated of conception": calculate_conception_date,
    "conception date": calculate_conception_date,
    "feverpain": calculate_feverpain,
    "fever pain": calculate_feverpain,
    "heart score": calculate_heart_score,
    "major cardiac events": calculate_heart_score,
    "homa-ir": calculate_homa_ir,
    "homa ir": calculate_homa_ir,
    "homeostatic model": calculate_homa_ir,
    "insulin resistance": calculate_homa_ir,
    "morphine milligram equivalents": calculate_mme,
    "mme": calculate_mme,
    "morphine equivalents": calculate_mme,
    "perc rule": calculate_perc,
    "perc": calculate_perc,
    "qtc rautaharju": calculate_qtc_rautaharju,
    "rautaharju": calculate_qtc_rautaharju,
    "sirs criteria": calculate_sirs,
    "sirs": calculate_sirs,
    "steroid conversion": calculate_steroid_conversion,
    "steroid": calculate_steroid_conversion,
    "prednisone equivalent": calculate_steroid_conversion,
    "wells' criteria for pulmonary embolism": calculate_wells_pe,
    "wells criteria for pulmonary embolism": calculate_wells_pe,
    "wells pe": calculate_wells_pe,
    "wells pulmonary": calculate_wells_pe,
}


def identify_calculator(question: str) -> Optional[str]:
    """Identify which calculator is needed from the question."""
    q = question.lower()

    # Priority patterns - check these first (most specific calculator names)
    # NOTE: Order matters! More specific patterns should come first.
    # "creatinine clearance" questions often mention "adjusted body weight" in instructions,
    # so creatinine clearance must be checked before adjusted body weight.
    priority_patterns = [
        # Renal (check first - these questions often mention body weight adjustments)
        "creatinine clearance",
        "cockcroft-gault",
        "ckd-epi",
        "mdrd",                          # MDRD is more specific — must match before generic GFR
        "glomerular filtration rate",
        # Physical/Anthropometric
        "body mass index",
        "ideal body weight",
        "adjusted body weight",
        "body surface area",
        "mean arterial pressure",
        "target weight",
        "maintenance fluids",
        "maintenance fluid",
        # Electrolytes/Metabolic (albumin-corrected variants must come before generic)
        "albumin corrected anion gap",
        "albumin corrected delta gap",
        "albumin corrected delta ratio",
        "corrected delta gap",
        "corrected delta ratio",
        "anion gap",
        "delta gap",
        "delta ratio",
        "serum osmolality",
        "free water deficit",
        "free water",
        "sodium correction for hyperglycemia",
        "sodium correction",
        "calcium correction for hypoalbuminemia",
        "calcium correction",
        "corrected calcium",
        "ldl cholesterol",
        "ldl calculated",
        "friedewald",
        "fractional excretion of sodium",
        "fena",
        # Cardiac
        "qtc bazett",
        "qt corrected fridericia",
        "qtc fridericia",
        "fridericia formula",
        "qtc framingham",
        "framingham formula",
        "qtc hodges",
        "qtc rautaharju",
        "cha2ds2-vasc",
        "heart score",
        "revised cardiac risk",
        "wells' criteria for pulmonary embolism",
        # Hepatic
        "fib-4",
        "fibrosis-4 index",
        "fibrosis-4",
        "fibrosis 4",
        "meld na",
        "meld-na",
        "child-pugh",
        "steroid conversion",
        # Pulmonary
        "curb-65",
        "psi score",
        "port score",
        "pneumonia severity",
        "perc rule",
        "sequential organ failure",
        "sofa",
        # Infectious/Inflammatory
        "centor",
        "mcisaac",
        "strep pharyngitis",
        "feverpain",
        "sirs criteria",
        "glasgow-blatchford",
        # Hematologic/Coagulation
        "has-bled",
        "wells' criteria for dvt",
        "wells criteria for dvt",
        "wells' criteria for deep vein thrombosis",
        "wells criteria for deep vein thrombosis",
        "caprini",
        "venous thromboembolism",
        "morphine milligram equivalents",
        "mme",
        # ICU Scoring
        "apache ii",
        "charlson comorbidity",
        # Obstetric
        "estimated due date",
        "due date",
        "gestational age",
        "estimated date of conception",
        "estimated of conception",
        "conception date",
        # Other
        "glasgow coma",
        "gcs",
        "homeostatic model",
        "homa-ir",
        "framingham risk",
    ]

    # Check priority patterns first
    for pattern in priority_patterns:
        if pattern in q:
            return pattern

    # Then check other patterns by length (longest match first)
    for pattern, _ in sorted(CALCULATOR_PATTERNS.items(), key=lambda x: -len(x[0])):
        if pattern in q:
            return pattern

    # Special case: steroid conversion detection
    # Questions like "equivalent dosage of Hydrocortisone" don't mention "steroid conversion"
    steroid_names = ['dexamethasone', 'hydrocortisone', 'betamethasone',
                     'methylprednisolone', 'cortisone', 'triamcinolone',
                     'prednisone', 'prednisolone']
    conversion_keywords = ['equivalent', 'convert', 'conversion']
    if any(s in q for s in steroid_names) and any(k in q for k in conversion_keywords):
        return "steroid conversion"

    return None


def calculate(patient_note: str, question: str) -> Optional[CalcResult]:
    """
    Main entry point: identify calculator and compute result.

    Args:
        patient_note: The patient note text
        question: The question asking for a calculation

    Returns:
        CalcResult if successful, None if calculator not found or values missing
    """
    calc_pattern = identify_calculator(question)

    if calc_pattern is None:
        return None

    calc_func = CALCULATOR_PATTERNS[calc_pattern]

    # Combine patient note and question for value extraction
    # (some values like target BMI are in the question)
    combined_text = f"{patient_note}\n{question}"

    return calc_func(combined_text)


# =============================================================================
# Calculator Signatures for Direct Invocation (L3 ReAct Agent)
# =============================================================================

CALCULATOR_SIGNATURES = {
    "Creatinine Clearance (Cockcroft-Gault Equation)": {
        "required": ["age", "sex", "weight_kg", "creatinine_mg_dl"],
        "optional": ["height_cm"],
        "formula": "CrCl = ((140-age) * adjusted_weight * gender_coef) / (Cr * 72)",
        "notes": "Use adjusted body weight based on BMI. Gender coef: male=1.0, female=0.85. If height provided, calculates IBW for weight adjustment."
    },
    "CKD-EPI Equations for Glomerular Filtration Rate": {
        "required": ["age", "sex", "creatinine_mg_dl"],
        "optional": [],
        "formula": "142 * min(Cr/κ,1)^α * max(Cr/κ,1)^-1.200 * 0.9938^age * [1.012 if female]",
        "notes": "CKD-EPI 2021 equation (race-free). κ=0.7(F)/0.9(M), α=-0.241(F)/-0.302(M)"
    },
    "CHA2DS2-VASc Score for Atrial Fibrillation Stroke Risk": {
        "required": ["age", "sex"],
        "optional": ["has_chf", "has_hypertension", "has_stroke_tia", "has_vascular_disease", "has_diabetes"],
        "formula": "Sum: CHF(+1), HTN(+1), Age≥75(+2), DM(+1), Stroke/TIA(+2), Vascular disease(+1), Age 65-74(+1), Female(+1)",
        "notes": "Score 0-9. Each boolean should be True/False."
    },
    "Body Mass Index (BMI)": {
        "required": ["weight_kg", "height_cm"],
        "optional": [],
        "formula": "BMI = weight_kg / (height_m)^2",
        "notes": "Height in cm is converted to meters internally."
    },
    "Ideal Body Weight": {
        "required": ["sex", "height_cm"],
        "optional": [],
        "formula": "Male: 50 + 2.3*(height_in - 60), Female: 45.5 + 2.3*(height_in - 60)",
        "notes": "Devine formula. Height converted to inches internally."
    },
}


def get_signatures() -> Dict[str, Dict]:
    """Return all calculator signatures for prompt injection."""
    from calculator_simple import get_calculator_signatures as _get_all_signatures
    return _get_all_signatures()


def _normalize_calculator_name(name: str) -> str:
    """Normalize calculator name for better matching.

    Strips common suffixes, standardizes separators, and lowercases.
    Returns a cleaned name that's more likely to match registry entries.
    """
    import re
    n = name.strip()
    # Strip trailing " Score" or " Calculator" suffix (case-insensitive)
    n = re.sub(r'\s+(Score|Calculator)\s*$', '', n, flags=re.IGNORECASE)
    return n


def compute_direct(calculator_name: str, values: Dict[str, Any]) -> Optional[CalcResult]:
    """
    Compute calculation from pre-extracted values (no text parsing).

    This is the interface for L3 ReAct agent to call calculators directly
    with structured arguments instead of passing text.

    Args:
        calculator_name: Calculator name (matched against 55-calculator registry)
        values: Dict of extracted values, e.g., {"age": 71, "sex": "male", ...}

    Returns:
        CalcResult if successful, None if calculator not found or values invalid
    """
    import json as _json

    from calculator_simple import compute as _simple_compute

    # Guard: if LLM sent values as a JSON string instead of a dict, parse it
    if isinstance(values, str):
        try:
            values = _json.loads(values)
        except (_json.JSONDecodeError, ValueError):
            return None
        if not isinstance(values, dict):
            return None

    # First try the full 55-calculator registry (handles fuzzy name matching)
    result = _simple_compute(calculator_name, values)
    if result is not None:
        return CalcResult(
            calculator_name=calculator_name,
            result=result,
            extracted_values=values,
            formula_used="",
        )

    # Try again with normalized name (strip " Score" suffix, etc.)
    normalized = _normalize_calculator_name(calculator_name)
    if normalized != calculator_name:
        result = _simple_compute(normalized, values)
        if result is not None:
            return CalcResult(
                calculator_name=calculator_name,
                result=result,
                extracted_values=values,
                formula_used="",
            )

    # Fall back to the 5 handwritten direct implementations for edge cases
    # (they handle special formatting like IBW weight adjustment)
    calc_lower = calculator_name.lower()
    fallback_result = None

    if "creatinine clearance" in calc_lower or "cockcroft" in calc_lower:
        fallback_result = _compute_creatinine_clearance_direct(values)
    elif "ckd-epi" in calc_lower or "glomerular filtration" in calc_lower:
        fallback_result = _compute_ckd_epi_direct(values)
    elif "cha2ds2" in calc_lower:
        fallback_result = _compute_cha2ds2_vasc_direct(values)
    elif "body mass index" in calc_lower or calc_lower == "bmi":
        fallback_result = _compute_bmi_direct(values)
    elif "ideal body weight" in calc_lower or calc_lower == "ibw":
        fallback_result = _compute_ibw_direct(values)

    if fallback_result is not None:
        return fallback_result

    return None


def _compute_creatinine_clearance_direct(values: Dict[str, Any]) -> Optional[CalcResult]:
    """Direct Creatinine Clearance computation from pre-extracted values."""
    try:
        age = float(values["age"])
        sex = str(values["sex"]).lower()
        weight_kg = float(values["weight_kg"])
        creatinine = float(values["creatinine_mg_dl"])
        height_cm = values.get("height_cm")

        # Validate
        if not (18 <= age <= 120):
            return None
        if not (20 <= weight_kg <= 300):
            return None
        if not (0.1 <= creatinine <= 30):
            return None

        # Calculate weight to use based on BMI if height provided
        weight_to_use = weight_kg
        weight_type = "actual"
        bmi = None
        ibw = None

        if height_cm is not None:
            height_cm = float(height_cm)
            height_m = height_cm / 100
            bmi = weight_kg / (height_m ** 2)
            height_in = height_cm / 2.54

            # Calculate Ideal Body Weight
            if sex == 'male':
                ibw = 50 + 2.3 * (height_in - 60)
            else:
                ibw = 45.5 + 2.3 * (height_in - 60)

            # Determine weight adjustment
            if bmi >= 30:  # Obese
                weight_to_use = ibw + 0.4 * (weight_kg - ibw)
                weight_type = "adjusted (obese)"
            elif bmi >= 25:  # Overweight
                weight_to_use = ibw + 0.4 * (weight_kg - ibw)
                weight_type = "adjusted (overweight)"
            elif bmi < 18.5:  # Underweight
                weight_to_use = weight_kg
                weight_type = "actual (underweight)"
            else:  # Normal BMI
                weight_to_use = min(ibw, weight_kg)
                weight_type = "min(IBW, actual)"

        # CrCl formula
        gender_coef = 1.0 if sex == 'male' else 0.85
        crcl = ((140 - age) * weight_to_use * gender_coef) / (creatinine * 72)

        if not (0 < crcl < 300):
            return None

        return CalcResult(
            calculator_name="Creatinine Clearance (Cockcroft-Gault Equation)",
            result=round(crcl, 3),
            extracted_values={
                "age": age,
                "actual_weight": weight_kg,
                "weight_used": round(weight_to_use, 3),
                "weight_type": weight_type,
                "bmi": round(bmi, 2) if bmi else None,
                "ibw": round(ibw, 2) if ibw else None,
                "creatinine": creatinine,
                "sex": sex,
                "gender_coef": gender_coef
            },
            formula_used="CrCl = ((140-age) * weight * gender_coef) / (Cr * 72); gender: male=1.0, female=0.85; weight: BMI>=25 use ABW=IBW+0.4*(actual-IBW), BMI<18.5 use actual, normal use min(IBW,actual)"
        )
    except (KeyError, ValueError, TypeError) as e:
        return None


def _compute_ckd_epi_direct(values: Dict[str, Any]) -> Optional[CalcResult]:
    """Direct CKD-EPI GFR computation from pre-extracted values."""
    try:
        age = float(values["age"])
        sex = str(values["sex"]).lower()
        creatinine = float(values["creatinine_mg_dl"])

        # Validate
        if not (18 <= age <= 120):
            return None
        if not (0.1 <= creatinine <= 30):
            return None

        # CKD-EPI 2021 equation (race-free)
        if sex == 'female':
            kappa = 0.7
            alpha = -0.241
            sex_coef = 1.012
        else:
            kappa = 0.9
            alpha = -0.302
            sex_coef = 1.0

        cr_ratio = creatinine / kappa
        if creatinine <= kappa:
            gfr = 142 * (cr_ratio ** alpha) * (0.9938 ** age) * sex_coef
        else:
            gfr = 142 * (cr_ratio ** -1.200) * (0.9938 ** age) * sex_coef

        if not (0 < gfr < 200):
            return None

        return CalcResult(
            calculator_name="CKD-EPI Equations for Glomerular Filtration Rate",
            result=round(gfr, 3),
            extracted_values={
                "age": age,
                "sex": sex,
                "creatinine": creatinine,
                "kappa": kappa,
                "alpha": alpha
            },
            formula_used="142 * min(Cr/κ,1)^α * max(Cr/κ,1)^-1.200 * 0.9938^age * sex_coef"
        )
    except (KeyError, ValueError, TypeError):
        return None


def _compute_cha2ds2_vasc_direct(values: Dict[str, Any]) -> Optional[CalcResult]:
    """Direct CHA2DS2-VASc computation from pre-extracted values."""
    try:
        age = float(values["age"])
        sex = str(values["sex"]).lower()

        score = 0
        factors = {}

        # Age points
        if age >= 75:
            score += 2
            factors["age_75_plus"] = 2
        elif age >= 65:
            score += 1
            factors["age_65_74"] = 1

        # Sex (female = 1 point)
        if sex == 'female':
            score += 1
            factors["female"] = 1

        # Boolean conditions (optional - default to False if not provided)
        if values.get("has_chf", False):
            score += 1
            factors["chf"] = 1

        if values.get("has_hypertension", False):
            score += 1
            factors["hypertension"] = 1

        if values.get("has_diabetes", False):
            score += 1
            factors["diabetes"] = 1

        if values.get("has_stroke_tia", False):
            score += 2
            factors["stroke_tia"] = 2

        if values.get("has_vascular_disease", False):
            score += 1
            factors["vascular_disease"] = 1

        return CalcResult(
            calculator_name="CHA2DS2-VASc Score for Atrial Fibrillation Stroke Risk",
            result=float(score),
            extracted_values={
                "age": age,
                "sex": sex,
                **factors
            },
            formula_used="Sum: CHF(+1), HTN(+1), Age≥75(+2)/65-74(+1), DM(+1), Stroke(+2), Vascular(+1), Female(+1)"
        )
    except (KeyError, ValueError, TypeError):
        return None


def _compute_bmi_direct(values: Dict[str, Any]) -> Optional[CalcResult]:
    """Direct BMI computation from pre-extracted values."""
    try:
        weight_kg = float(values["weight_kg"])
        height_cm = float(values["height_cm"])

        height_m = height_cm / 100
        bmi = weight_kg / (height_m ** 2)

        return CalcResult(
            calculator_name="Body Mass Index (BMI)",
            result=round(bmi, 3),
            extracted_values={"weight_kg": weight_kg, "height_cm": height_cm},
            formula_used="BMI = weight / height^2"
        )
    except (KeyError, ValueError, TypeError):
        return None


def _compute_ibw_direct(values: Dict[str, Any]) -> Optional[CalcResult]:
    """Direct Ideal Body Weight computation from pre-extracted values."""
    try:
        sex = str(values["sex"]).lower()
        height_cm = float(values["height_cm"])

        height_in = height_cm / 2.54
        if sex == 'male':
            ibw = 50 + 2.3 * (height_in - 60)
        else:
            ibw = 45.5 + 2.3 * (height_in - 60)

        return CalcResult(
            calculator_name="Ideal Body Weight",
            result=round(ibw, 3),
            extracted_values={"sex": sex, "height_cm": height_cm, "height_in": height_in},
            formula_used="IBW = 50/45.5 + 2.3*(height_in - 60)"
        )
    except (KeyError, ValueError, TypeError):
        return None


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Testing calculators_all.py (55 calculators)")
    print("=" * 60)

    # Test original calculators
    print("\n--- Original Calculators ---")

    # Test BMI
    note = "A 45-year-old male. Height: 175 cm. Weight: 80 kg."
    question = "What is the patient's BMI?"
    result = calculate(note, question)
    print(f"BMI: {result}")

    # Test CrCl
    note2 = "An 87-year-old man. Weight: 48 kg. Creatinine: 1.4 mg/dL."
    question2 = "What is the patient's Creatinine Clearance using the Cockcroft-Gault Equation?"
    result2 = calculate(note2, question2)
    print(f"CrCl: {result2}")

    # Test new calculators
    print("\n--- Test-Only Calculators ---")

    # Test FENa
    note3 = "Urine sodium: 15 mEq/L. Serum sodium: 140 mEq/L. Urine creatinine: 80 mg/dL. Serum creatinine: 2.0 mg/dL."
    question3 = "What is the patient's FENa?"
    result3 = calculate(note3, question3)
    print(f"FENa: {result3}")

    # Test GCS
    note4 = "Eye: 4, Verbal: 5, Motor: 6"
    question4 = "What is the patient's Glasgow Coma Score?"
    result4 = calculate(note4, question4)
    print(f"GCS: {result4}")

    # Test MELD-Na
    note5 = "Bilirubin: 2.5 mg/dL. INR: 1.8. Creatinine: 1.5 mg/dL. Sodium: 130 mEq/L."
    question5 = "What is the patient's MELD-Na score?"
    result5 = calculate(note5, question5)
    print(f"MELD-Na: {result5}")

    # Test Child-Pugh
    note6 = "Bilirubin: 2.5 mg/dL. Albumin: 3.0 g/dL. INR: 1.8. Mild ascites."
    question6 = "What is the patient's Child-Pugh score?"
    result6 = calculate(note6, question6)
    print(f"Child-Pugh: {result6}")

    # Test CCI
    note7 = "A 65-year-old man with diabetes and COPD."
    question7 = "What is the patient's Charlson Comorbidity Index?"
    result7 = calculate(note7, question7)
    print(f"CCI: {result7}")

    # Test Wells DVT
    note8 = "Patient with active cancer, calf tenderness, and pitting edema."
    question8 = "What is the patient's Wells' Criteria for DVT score?"
    result8 = calculate(note8, question8)
    print(f"Wells DVT: {result8}")

    # Test RCRI
    note9 = "Patient scheduled for major vascular surgery with history of heart failure."
    question9 = "What is the patient's Revised Cardiac Risk Index?"
    result9 = calculate(note9, question9)
    print(f"RCRI: {result9}")

    # Test APACHE II
    note10 = "A 70-year-old patient. Temperature: 38.5 C. BP: 90/60. HR: 110. RR: 25. pH: 7.30. Sodium: 135. Potassium: 4.5. Creatinine: 2.0. Hematocrit: 35%. WBC: 15. GCS: E4V5M6."
    question10 = "What is the patient's APACHE II score?"
    result10 = calculate(note10, question10)
    print(f"APACHE II: {result10}")

    print("\n--- Summary ---")
    print(f"Total calculators in CALCULATOR_PATTERNS: {len(CALCULATOR_PATTERNS)}")

    # Count unique calculator functions
    unique_funcs = set(CALCULATOR_PATTERNS.values())
    print(f"Unique calculator functions: {len(unique_funcs)}")
