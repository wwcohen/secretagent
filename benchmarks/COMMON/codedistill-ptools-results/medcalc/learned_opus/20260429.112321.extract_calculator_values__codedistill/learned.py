"""Auto-generated code-distilled implementation for extract_calculator_values."""

import re
import json


def extract_calculator_values(clinical_note, calculator_name, param_definitions, analysis_context=''):
    try:
        # Parse parameter definitions
        params = []
        for line in param_definitions.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            match = re.match(r'^(\w+)\s*:\s*(.+)$', line)
            if match:
                param_name = match.group(1)
                param_desc = match.group(2)
                params.append((param_name, param_desc))
        
        if not params:
            return None
        
        extracted = {}
        missing = []
        
        for param_name, param_desc in params:
            value = _extract_param(param_name, param_desc, clinical_note, calculator_name, analysis_context)
            if value is not None:
                extracted[param_name] = value
            else:
                missing.append(param_name)
        
        return {'extracted': extracted, 'missing': missing}
    except Exception:
        return None


def _extract_param(param_name, param_desc, note, calculator_name, analysis_context):
    # Check if this is a boolean/scoring parameter (contains +1 or similar scoring)
    if re.search(r'\(\+\d+\)', param_desc):
        return _extract_boolean_param(param_name, param_desc, note, analysis_context)
    
    # Check if this is a sex parameter
    if param_name == 'sex':
        return _extract_sex(note)
    
    # Numeric extraction
    return _extract_numeric(param_name, param_desc, note)


def _extract_boolean_param(param_name, param_desc, note, analysis_context):
    # Use analysis context if available
    if analysis_context:
        # Check conditions PRESENT/ABSENT
        present_match = re.search(r'Conditions PRESENT:\s*([^\n]+)', analysis_context)
        absent_match = re.search(r'Conditions ABSENT:\s*([^\n]+)', analysis_context)
        
        present_conditions = present_match.group(1).strip() if present_match else ''
        absent_conditions = absent_match.group(1).strip() if absent_match else ''
        
        # Normalize param_name for matching
        pn_lower = param_name.lower()
        
        if present_conditions.strip().lower() == 'none' and absent_conditions:
            return False
        
        # Check if param_name or related terms appear in present
        if _param_in_conditions(param_name, param_desc, present_conditions):
            return True
        if _param_in_conditions(param_name, param_desc, absent_conditions):
            return False
        
        # If "None" in present and this param isn't specifically listed as present
        if 'none' in present_conditions.lower().split(',')[0].strip().lower():
            return False
    
    # Try to determine from clinical note directly
    return _evaluate_boolean_from_note(param_name, param_desc, note)


def _param_in_conditions(param_name, param_desc, conditions_str):
    if not conditions_str or conditions_str.strip().lower() == 'none':
        return False
    
    conditions_lower = conditions_str.lower()
    pn_lower = param_name.lower()
    
    # Direct match
    if pn_lower in conditions_lower:
        return True
    
    # Map common terms
    mappings = {
        'temperature_abnormal': ['temperature', 'fever', 'hypothermia', 'hyperthermia'],
        'heart_rate_elevated': ['tachycardia', 'heart rate'],
        'respiratory_abnormal': ['tachypnea', 'respiratory'],
        'wbc_abnormal': ['leukocytosis', 'leukopenia', 'wbc'],
        'altered_mental_status': ['altered mental', 'confusion', 'gcs'],
        'sbp_below_90': ['hypotension', 'sbp'],
    }
    
    if pn_lower in mappings:
        for term in mappings[pn_lower]:
            if term in conditions_lower:
                return True
    
    return False


def _evaluate_boolean_from_note(param_name, param_desc, note):
    # Try to extract the threshold from description and compare with note values
    pn = param_name.lower()
    
    # Temperature abnormal: Temp > 38C or < 36C
    if 'temperature' in pn or 'temp' in pn:
        temps = re.findall(r'(?:temperature|temp)\s*(?:of|was|is|:)?\s*(\d+\.?\d*)\s*°?\s*[CcFf]?', note, re.IGNORECASE)
        if not temps:
            temps = re.findall(r'(\d{2}\.?\d*)\s*°\s*[Cc]', note)
        if temps:
            for t in temps:
                tv = float(t)
                if tv > 38 or tv < 36:
                    return True
            return False
        return False
    
    # Heart rate elevated: HR > 90
    if 'heart_rate' in pn:
        hrs = re.findall(r'(?:heart rate|pulse|HR)\s*(?:of|was|is|:)?\s*(\d+)', note, re.IGNORECASE)
        if hrs:
            for h in hrs:
                if int(h) > 90:
                    return True
            return False
        return False
    
    # Respiratory abnormal: RR > 20 or PaCO2 < 32
    if 'respiratory' in pn:
        rrs = re.findall(r'(?:respiratory rate|RR)\s*(?:of|was|is|:)?\s*(\d+)', note, re.IGNORECASE)
        if rrs:
            for r in rrs:
                if int(r) > 20:
                    return True
        paco2s = re.findall(r'(?:PaCO2|pCO2)\s*(?:of|was|is|:)?\s*(\d+\.?\d*)', note, re.IGNORECASE)
        if paco2s:
            for p in paco2s:
                if float(p) < 32:
                    return True
        if rrs or paco2s:
            return False
        return False
    
    # WBC abnormal
    if 'wbc' in pn:
        wbcs = re.findall(r'(?:WBC|white blood cell|leukocyte)\s*(?:count)?\s*(?:of|was|is|:)?\s*([\d,]+\.?\d*)', note, re.IGNORECASE)
        if wbcs:
            for w in wbcs:
                wv = float(w.replace(',', ''))
                if wv > 12000 or wv < 4000:
                    return True
                # Could be in thousands
                if wv > 12 or wv < 4:
                    if wv < 100:  # likely in thousands
                        return True
            return False
        return False
    
    return False


def _extract_sex(note):
    # Look for sex/gender indicators
    male_patterns = [
        r'\b(?:male|man|boy|gentleman)\b',
        r'\b[Hh]is\b',
        r'\b[Hh]e\b'
    ]
    female_patterns = [
        r'\b(?:female|woman|girl|lady)\b',
        r'\b[Hh]er\b',
        r'\b[Ss]he\b'
    ]
    
    # Check first 500 chars for strong indicators
    header = note[:800]
    
    for p in [r'\bmale\b', r'\b[Mm]an\b', r'\bboy\b']:
        if re.search(p, header):
            # Make sure it's not "female"
            m = re.search(p, header)
            if m and p == r'\bmale\b':
                start = max(0, m.start() - 2)
                if header[start:m.start()].lower().endswith('fe'):
                    continue
            return 'male'
    
    for p in [r'\bfemale\b', r'\b[Ww]oman\b', r'\bgirl\b']:
        if re.search(p, header):
            return 'female'
    
    # Broader search
    # Look for "X-year-old male/female/man/woman"
    m = re.search(r'\d+[\s-]*year[\s-]*old\s+(\w+)', note, re.IGNORECASE)
    if m:
        word = m.group(1).lower()
        if word in ('male', 'man', 'boy', 'gentleman'):
            return 'male'
        if word in ('female', 'woman', 'girl', 'lady'):
            return 'female'
    
    # Check pronouns in first part
    if re.search(r'\bfemale\b', note[:1500], re.IGNORECASE):
        return 'female'
    if re.search(r'\bmale\b', note[:1500], re.IGNORECASE):
        # Check not "female"
        for m in re.finditer(r'\bmale\b', note[:1500], re.IGNORECASE):
            start = max(0, m.start() - 2)
            if not note[start:m.start()].lower().endswith('fe'):
                return 'male'
    
    if re.search(r'\b[Ss]he\b', note[:500]):
        return 'female'
    if re.search(r'\b[Hh]e\b', note[:500]):
        return 'male'
    
    return None


def _extract_numeric(param_name, param_desc, note):
    pn = param_name.lower()
    
    # Define search patterns based on parameter name
    value = None
    
    if pn == 'weight_kg':
        value = _find_weight_kg(note)
    elif pn == 'height_cm':
        value = _find_height_cm(note)
    elif pn == 'age':
        value = _find_age(note)
    elif pn == 'sodium' or pn == 'sodium_meq_l':
        value = _find_lab_value(note, [
            r'(?:serum\s+)?sodium\s*(?:level)?\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
            r'Na\+?\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
            r'sodium\s*(?:level)?\s*(?:of|was|is|:)?\s*(\d+\.?\d*)\s*(?:mEq|mmol)',
            r'Na\s*(\d+\.?\d*)\s*(?:mEq|mmol)',
        ], expected_range=(100, 200))
    elif pn == 'glucose' or pn == 'glucose_mg_dl':
        value = _find_lab_value(note, [
            r'(?:serum\s+)?(?:blood\s+)?glucose\s*(?:level)?\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
            r'blood\s+sugar\s*(?:level)?\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
            r'glucose\s*(?:of|was|is|:)?\s*(\d+\.?\d*)\s*(?:mg)',
            r'FBS\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
            r'glucose[:\s]+(\d+\.?\d*)',
        ], expected_range=(20, 2000))
    elif pn == 'systolic':
        value = _find_systolic(note)
    elif pn == 'diastolic':
        value = _find_diastolic(note)
    elif pn == 'creatinine_mg_dl' or pn == 'creatinine':
        value = _find_lab_value(note, [
            r'(?:serum\s+)?creatinine\s*(?:level)?\s*(?:of|was|is|:)?\s*(\d+\.?\d*)\s*mg',
            r'creatinine\s*(?:of|was|is|:)?\s*(\d+\.?\d*)\s*mg',
            r'creatinine\s*(?:level)?[:\s]+(\d+\.?\d*)\s*mg',
            r'creatinine\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
            r'Cr\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
        ], expected_range=(0.1, 30))
    elif pn == 'qt_msec':
        value = _find_lab_value(note, [
            r'QT\s*(?:interval)?\s*(?:of|was|is|:)?\s*(\d+\.?\d*)\s*(?:ms|msec)',
            r'QT\s*(?:interval)?\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
        ], expected_range=(100, 800))
    elif pn == 'heart_rate':
        value = _find_lab_value(note, [
            r'heart\s*rate\s*(?:of|was|is|:)?\s*(\d+\.?\d*)\s*(?:bpm|beats)',
            r'heart\s*rate\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
            r'HR\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
            r'pulse\s*(?:rate)?\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
            r'(\d+)\s*bpm',
        ], expected_range=(20, 300))
    elif pn == 'albumin':
        value = _find_lab_value(note, [
            r'(?:serum\s+)?albumin\s*(?:level)?\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
            r'albumin[:\s]+(\d+\.?\d*)',
        ], expected_range=(0.5, 10))
    elif pn == 'bun' or pn == 'bun_mg_dl':
        value = _find_lab_value(note, [
            r'BUN\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
            r'blood\s+urea\s+nitrogen\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
        ], expected_range=(1, 200))
    elif pn == 'chloride':
        value = _find_lab_value(note, [
            r'chloride\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
            r'Cl\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
        ], expected_range=(70, 130))
    elif pn == 'bicarbonate' or pn == 'co2' or pn == 'hco3':
        value = _find_lab_value(note, [
            r'(?:serum\s+)?bicarbonate\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
            r'HCO3\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
            r'CO2\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
            r'bicarb\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
        ], expected_range=(5, 50))
    elif pn == 'potassium':
        value = _find_lab_value(note, [
            r'potassium\s*(?:level)?\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
            r'K\+?\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
        ], expected_range=(1, 10))
    else:
        # Generic extraction - try to find based on description keywords
        value = _generic_extract(param_name, param_desc, note)
    
    return value


def _find_weight_kg(note):
    # Look for weight in kg
    patterns = [
        r'(?:weigh(?:t|ing|ed|s)?)\s*(?:of|was|is|:)?\s*(\d+\.?\d*)\s*kg',
        r'(\d+\.?\d*)\s*kg\s*(?:body\s*(?:weight|mass))?',
        r'(?:body\s*(?:weight|mass))\s*(?:of|was|is|:)?\s*(\d+\.?\d*)\s*kg',
        r'(\d+)\s*kg',
        r'weight\s*(?:of|was|is|:)?\s*(\d+\.?\d*)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, note, re.IGNORECASE)
        if matches:
            val = float(matches[0])
            if 1 < val < 500:  # reasonable weight range
                return _clean_number(val)
    
    # Check for lbs and convert
    lb_patterns = [
        r'(\d+\.?\d*)\s*(?:lbs?|pounds?)',
        r'weight\s*(?:of|was|is|:)?\s*(\d+\.?\d*)\s*(?:lbs?|pounds?)',
    ]
    for pattern in lb_patterns:
        matches = re.findall(pattern, note, re.IGNORECASE)
        if matches:
            val = float(matches[0]) * 0.453592
            if 1 < val < 500:
                return round(val, 1)
    
    return None


def _find_height_cm(note):
    # Look for height in cm
    patterns = [
        r'(?:height|stature|tall)\s*(?:of|was|is|:)?\s*(\d+\.?\d*)\s*cm',
        r'(\d+\.?\d*)\s*cm\s*(?:height|tall|stature)',
        r'(\d{3})\s*cm',  # 3-digit number followed by cm
        r'height\s*(?:of|was|is|:)?\s*(\d+\.?\d*)\s*cm',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, note, re.IGNORECASE)
        if matches:
            val = float(matches[0])
            if 50 < val < 300:
                return _clean_number(val)
    
    # Check for height in meters (e.g., 1.69 m, 1,65 m)
    m_patterns = [
        r'(?:height|stature)\s*(?:of|was|is|:)?\s*(\d+[.,]\d+)\s*m\b',
        r'(\d+[.,]\d+)\s*m\s*(?:stature|height|tall)',
        r'(\d+[.,]\d+)\s*m\b',
    ]
    
    for pattern in m_patterns:
        matches = re.findall(pattern, note, re.IGNORECASE)
        if matches:
            val_str = matches[0].replace(',', '.')
            val = float(val_str)
            if 1.0 < val < 2.5:
                return _clean_number(val * 100)
    
    # Check for feet/inches
    fi_patterns = [
        r"(\d+)'(\d+)\"",
        r'(\d+)\s*feet?\s*(\d+)\s*inch',
        r"(\d+)\s*ft\s*(\d+)\s*in",
    ]
    for pattern in fi_patterns:
        matches = re.findall(pattern, note, re.IGNORECASE)
        if matches:
            feet, inches = int(matches[0][0]), int(matches[0][1])
            val = (feet * 12 + inches) * 2.54
            if 50 < val < 300:
                return round(val, 1)
    
    return None


def _find_age(note):
    patterns = [
        r'(\d+)[\s-]*year[\s-]*old',
        r'age[d]?\s*(?:of|was|is|:)?\s*(\d+)',
        r'(\d+)\s*(?:yo|y\.o\.)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, note, re.IGNORECASE)
        if matches:
            val = int(matches[0])
            if 0 < val < 150:
                return val
    return None


def _find_systolic(note):
    # Blood pressure patterns: systolic/diastolic
    bp_patterns = [
        r'(?:blood\s*pressure|BP)\s*(?:of|was|is|:)?\s*(\d+)\s*/\s*(\d+)',
        r'(\d+)\s*/\s*(\d+)\s*(?:mm\s*Hg|mmHg)',
        r'(?:systolic\s*(?:blood\s*pressure)?|SBP)\s*(?:of|was|is|:)?\s*(\d+)',
    ]
    
    for i, pattern in enumerate(bp_patterns):
        matches = re.findall(pattern, note, re.IGNORECASE)
        if matches:
            if i < 2:  # BP pattern with both values
                val = float(matches[0][0])
            else:
                val = float(matches[0])
            if 50 < val < 300:
                return _clean_number(val)
    return None


def _find_diastolic(note):
    bp_patterns = [
        r'(?:blood\s*pressure|BP)\s*(?:of|was|is|:)?\s*(\d+)\s*/\s*(\d+)',
        r'(\d+)\s*/\s*(\d+)\s*(?:mm\s*Hg|mmHg)',
        r'(?:diastolic\s*(?:blood\s*pressure)?|DBP)\s*(?:of|was|is|:)?\s*(\d+)',
    ]
    
    for i, pattern in enumerate(bp_patterns):
        matches = re.findall(pattern, note, re.IGNORECASE)
        if matches:
            if i < 2:
                val = float(matches[0][1])
            else:
                val = float(matches[0])
            if 20 < val < 200:
                return _clean_number(val)
    return None


def _find_lab_value(note, patterns, expected_range=None):
    for pattern in patterns:
        matches = re.findall(pattern, note, re.IGNORECASE)
        if matches:
            val = float(matches[0])
            if expected_range:
                low, high = expected_range
                if low <= val <= high:
                    return _clean_number(val)
            else:
                return _clean_number(val)
    return None


def _generic_extract(param_name, param_desc, note):
    # Try to extract based on keywords in the description
    # Extract key terms from description
    desc_lower = param_desc.lower()
    
    # Try to find the unit
    unit_match = re.search(r'in\s+([\w/%]+(?:\s*[\w/%]+)?)\s*\(', param_desc)
    unit = unit_match.group(1) if unit_match else ''
    
    # Try keyword from param name
    keywords = param_name.lower().replace('_', ' ').split()
    
    for keyword in keywords:
        if len(keyword) < 3:
            continue
        pattern = rf'{keyword}\s*(?:of|was|is|:)?\s*(\d+\.?\d*)'
        matches = re.findall(pattern, note, re.IGNORECASE)
        if matches:
            return _clean_number(float(matches[0]))
    
    return None


def _clean_number(val):
    """Return int if whole number, float otherwise."""
    if val == int(val):
        return int(val)
    return val
