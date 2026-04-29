"""Auto-generated code-distilled implementation for extract_calculator_values."""

import re
import json


def extract_calculator_values(text, calculator_name, param_descriptions, analysis_context=''):
    """
    Extract calculator input values from clinical text.
    
    Args:
        text: Clinical note text
        calculator_name: Name of the medical calculator
        param_descriptions: Newline-separated parameter descriptions
        analysis_context: Optional pre-analysis context with conditions
    
    Returns:
        dict with 'extracted' (dict of param->value) and 'missing' (list of missing params)
    """
    # Parse parameter descriptions
    params = []
    for line in param_descriptions.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        match = re.match(r'^(\w+):\s*(.*)', line)
        if match:
            param_name = match.group(1)
            param_desc = match.group(2)
            params.append((param_name, param_desc))
    
    if not params:
        return None
    
    extracted = {}
    missing = []
    
    combined_text = text + '\n' + (analysis_context or '')
    
    for param_name, param_desc in params:
        value = _extract_param(param_name, param_desc, text, combined_text, calculator_name, analysis_context)
        if value is not None:
            extracted[param_name] = value
        else:
            missing.append(param_name)
    
    return {'extracted': extracted, 'missing': missing}


def _extract_param(param_name, param_desc, text, combined_text, calculator_name, analysis_context):
    """Extract a single parameter value from text."""
    
    # Handle boolean/condition parameters (has_xxx)
    if param_name.startswith('has_') or param_name.startswith('is_'):
        return _extract_boolean(param_name, param_desc, text, combined_text, analysis_context)
    
    # Handle sex/gender
    if param_name == 'sex':
        return _extract_sex(text, combined_text, analysis_context)
    
    # Handle steroid name
    if param_name == 'steroid_name':
        return _extract_steroid_name(text)
    
    # Handle numeric parameters
    return _extract_numeric(param_name, param_desc, text, combined_text, calculator_name)


def _extract_sex(text, combined_text, analysis_context):
    """Extract patient sex from text."""
    # Check analysis context first
    if analysis_context:
        sex_match = re.search(r'Sex\s*=\s*(male|female)', analysis_context, re.IGNORECASE)
        if sex_match:
            return sex_match.group(1).lower()
        if re.search(r'\bfemale\b', analysis_context, re.IGNORECASE):
            return 'female'
        if re.search(r'\bmale\b', analysis_context, re.IGNORECASE):
            return 'male'
    
    # Look in clinical text - search for common patterns
    # Check for female first (since "female" contains "male")
    text_lower = text.lower()
    
    # Common patterns
    female_patterns = [
        r'\b(\d+[- ]year[- ]old)\s+(female|woman|lady)',
        r'\b(female)\s+patient',
        r'\bpatient\b[^.]{0,30}\b(female)\b',
        r'\b(woman|female)\b[^.]{0,20}\b(patient|presented|admitted|was)',
        r'\b(\d+[- ]year[- ]old)\s+\w*\s*(female|woman)',
        r'\bgirl\b',
        r'\bher\s+(medical|history|physical|examination|airway)\b',
        r'\bshe\s+(was|had|is|presented|stood|weighed)\b',
    ]
    
    male_patterns = [
        r'\b(\d+[- ]year[- ]old)\s+(male|man|gentleman)',
        r'\b(male)\s+patient',
        r'\bpatient\b[^.]{0,30}\b(male)\b',
        r'\b(man|male)\b[^.]{0,20}\b(patient|presented|admitted|was)',
        r'\b(\d+[- ]year[- ]old)\s+\w*\s*(male|man)',
        r'\bboy\b',
        r'\bhis\s+(medical|history|physical|examination|father)\b',
        r'\bhe\s+(was|had|is|presented)\b',
    ]
    
    # Direct patterns first - look for explicit sex mentions near age
    female_direct = re.search(r'\b\d+[- ]year[- ]old\s+(?:\w+\s+)?(female|woman)', text, re.IGNORECASE)
    male_direct = re.search(r'\b\d+[- ]year[- ]old\s+(?:\w+\s+)?(male|man|boy)', text, re.IGNORECASE)
    
    if female_direct and not male_direct:
        return 'female'
    if male_direct and not female_direct:
        return 'male'
    
    # If both found, use the one appearing first
    if female_direct and male_direct:
        if female_direct.start() < male_direct.start():
            return 'female'
        return 'male'
    
    # Try broader patterns
    for pattern in female_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return 'female'
    
    for pattern in male_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return 'male'
    
    # Last resort: look for gendered pronouns
    she_count = len(re.findall(r'\bshe\b', text, re.IGNORECASE))
    he_count = len(re.findall(r'\bhe\b', text, re.IGNORECASE))
    # Be careful with "he" appearing in other words
    he_count_strict = len(re.findall(r'\bhe\b', text, re.IGNORECASE))
    
    if she_count > he_count_strict and she_count > 0:
        return 'female'
    if he_count_strict > she_count and he_count_strict > 0:
        return 'male'
    
    return None


def _extract_boolean(param_name, param_desc, text, combined_text, analysis_context):
    """Extract boolean condition from text."""
    
    # Map param names to condition keywords for analysis context
    condition_map = {
        'has_chf': ['chf', 'congestive heart failure', 'heart failure', 'hf'],
        'has_hypertension': ['hypertension', 'htn', 'high blood pressure'],
        'has_diabetes': ['diabetes', 'diabetes mellitus', 'dm', 'diabetic'],
        'has_stroke_tia': ['stroke', 'tia', 'transient ischemic attack', 'cerebrovascular accident', 'cva', 'stroke_tia'],
        'has_vascular_disease': ['vascular disease', 'vascular_disease', 'peripheral arterial disease', 'pad', 'mi ', 'myocardial infarction', 'aortic plaque'],
        'has_afib': ['atrial fibrillation', 'afib', 'a-fib', 'af'],
        'is_on_anticoagulation': ['anticoagulation', 'anticoagulant', 'warfarin', 'heparin', 'coumadin', 'enoxaparin'],
        'is_intubated': ['intubated', 'intubation', 'mechanical ventilation', 'ventilated'],
        'has_liver_disease': ['liver disease', 'cirrhosis', 'hepatic', 'liver'],
        'has_renal_disease': ['renal disease', 'kidney disease', 'ckd', 'renal failure', 'renal insufficiency'],
        'has_cancer': ['cancer', 'malignancy', 'carcinoma', 'tumor', 'neoplasm', 'oncology'],
    }
    
    # Check analysis context for explicit PRESENT/ABSENT
    if analysis_context:
        # Check conditions PRESENT
        present_match = re.search(r'Conditions?\s*PRESENT[:\s]+([^\n]+)', analysis_context, re.IGNORECASE)
        absent_match = re.search(r'Conditions?\s*ABSENT[:\s]+([^\n]+)', analysis_context, re.IGNORECASE)
        
        present_conditions = present_match.group(1).lower() if present_match else ''
        absent_conditions = absent_match.group(1).lower() if absent_match else ''
        
        # Normalize param name for lookup
        # e.g., has_chf -> chf, has_stroke_tia -> stroke_tia
        condition_key = param_name.replace('has_', '').replace('is_', '')
        
        # Check if the condition key or its variants appear in present/absent lists
        keywords = condition_map.get(param_name, [condition_key])
        keywords.append(condition_key)
        # Also add underscore-replaced version
        keywords.append(condition_key.replace('_', ' '))
        
        for kw in keywords:
            kw_lower = kw.lower().strip()
            if kw_lower in present_conditions:
                return True
            if kw_lower in absent_conditions:
                return False
    
    # Fall back to text analysis
    text_lower = text.lower()
    
    # Get keywords for this condition
    condition_key = param_name.replace('has_', '').replace('is_', '')
    keywords = condition_map.get(param_name, [condition_key.replace('_', ' ')])
    
    for kw in keywords:
        if kw.lower() in text_lower:
            # Check if it's negated
            # Simple negation check
            kw_pos = text_lower.find(kw.lower())
            if kw_pos >= 0:
                prefix = text_lower[max(0, kw_pos - 50):kw_pos]
                if re.search(r'\b(no|without|denies|denied|negative|absent|not|never)\b', prefix):
                    return False
                return True
    
    # If not found at all, we can't determine
    return None


def _extract_steroid_name(text):
    """Extract steroid name from text."""
    steroids = [
        'dexamethasone', 'hydrocortisone', 'prednisone', 'prednisolone',
        'methylprednisolone', 'triamcinolone', 'betamethasone', 'cortisone',
        'fludrocortisone', 'budesonide'
    ]
    text_lower = text.lower()
    for steroid in steroids:
        if steroid in text_lower:
            return steroid
    return None


def _extract_numeric(param_name, param_desc, text, combined_text, calculator_name):
    """Extract a numeric value for a parameter."""
    
    text_lower = text.lower()
    
    # Build search patterns based on parameter name and description
    value = None
    
    # Weight
    if param_name in ('weight_kg', 'weight'):
        value = _find_weight_kg(text)
    
    # Height
    elif param_name in ('height_cm', 'height'):
        value = _find_height_cm(text)
    
    # Age
    elif param_name == 'age':
        value = _find_age(text, combined_text)
    
    # Systolic BP
    elif param_name == 'systolic':
        value = _find_systolic(text)
    
    # Diastolic BP
    elif param_name == 'diastolic':
        value = _find_diastolic(text)
    
    # Heart rate
    elif param_name in ('heart_rate', 'hr'):
        value = _find_heart_rate(text)
    
    # QT interval
    elif param_name in ('qt_msec', 'qt'):
        value = _find_qt(text)
    
    # Sodium
    elif param_name in ('sodium', 'serum_sodium'):
        value = _find_lab_value(text, param_name, param_desc)
    
    # Chloride
    elif param_name == 'chloride':
        value = _find_lab_value(text, param_name, param_desc)
    
    # Bicarbonate
    elif param_name == 'bicarbonate':
        value = _find_lab_value(text, param_name, param_desc)
    
    # BUN
    elif param_name == 'bun':
        value = _find_lab_value(text, param_name, param_desc)
    
    # Glucose
    elif param_name in ('glucose', 'fasting_glucose'):
        value = _find_lab_value(text, param_name, param_desc)
    
    # Creatinine
    elif param_name in ('serum_creatinine', 'creatinine'):
        value = _find_lab_value(text, param_name, param_desc)
    
    # Urine sodium
    elif param_name == 'urine_sodium':
        value = _find_lab_value(text, param_name, param_desc)
    
    # Urine creatinine
    elif param_name == 'urine_creatinine':
        value = _find_lab_value(text, param_name, param_desc)
    
    # Albumin
    elif param_name == 'albumin':
        value = _find_lab_value(text, param_name, param_desc)
    
    # Potassium
    elif param_name in ('potassium', 'k'):
        value = _find_lab_value(text, param_name, param_desc)
    
    # Calcium
    elif param_name in ('calcium', 'ca'):
        value = _find_lab_value(text, param_name, param_desc)
    
    # Fasting insulin
    elif param_name == 'fasting_insulin':
        value = _find_lab_value(text, param_name, param_desc)
    
    # Dose in mg
    elif param_name == 'dose_mg':
        value = _find_dose_mg(text)
    
    # Generic fallback
    else:
        value = _find_lab_value(text, param_name, param_desc)
    
    return value


def _find_weight_kg(text):
    """Find weight in kg from text."""
    # Pattern: XX kg
    patterns = [
        r'(?:weigh(?:t|ed|ing|s)?|(?:body\s+)?weight)[:\s]+(?:of\s+)?(\d+\.?\d*)\s*kg',
        r'(\d+\.?\d*)\s*kg\b(?!\s*/\s*m)',  # kg but not kg/m²
        r'weight[^.]{0,30}?(\d+\.?\d*)\s*kg',
        r'(\d+\.?\d*)\s*kg\s*(?:\(|,|\)|;|\.|\b)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            val = float(matches[0])
            # Sanity check for weight
            if 0.5 < val < 500:
                return val
    
    return None


def _find_height_cm(text):
    """Find height in cm from text."""
    # Pattern: height XX cm or X.XXm
    patterns = [
        r'(?:height|tall|stood)[:\s]+(?:of\s+)?(\d+\.?\d*)\s*cm',
        r'(\d+\.?\d*)\s*cm\s+(?:in\s+height|tall)',
        r'(\d{2,3}\.?\d*)\s*cm\b',
        r'height[^.]{0,30}?(\d+\.?\d*)\s*cm',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            val = float(matches[0])
            if 50 < val < 300:  # reasonable height in cm
                return val
    
    # Check for meters (e.g., 1.83m)
    meter_patterns = [
        r'(\d+\.\d+)\s*m\b(?!(?:m|g|l|eq|in|on))',
        r'(?:height)[:\s]+(?:of\s+)?(\d+\.\d+)\s*m\b',
    ]
    
    for pattern in meter_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            val = float(matches[0])
            if 0.5 < val < 3.0:  # reasonable height in meters
                return val * 100  # convert to cm
    
    # Also check parenthetical patterns like (1.83m, 88 kg)
    paren_match = re.search(r'\((\d+\.\d+)\s*m\s*[,;]', text)
    if paren_match:
        val = float(paren_match.group(1))
        if 0.5 < val < 3.0:
            return val * 100
    
    return None


def _find_age(text, combined_text):
    """Find patient age from text."""
    # Check analysis context
    age_match = re.search(r'Age\s*=\s*(\d+)', combined_text, re.IGNORECASE)
    if age_match:
        return int(age_match.group(1))
    
    # Standard patterns
    patterns = [
        r'(\d+)[- ]year[- ]old',
        r'age(?:d)?\s+(\d+)',
        r'(\d+)\s*years?\s+(?:of\s+)?age',
        r'(\d+)[- ](?:yo|y\.o\.)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    
    # Check for infant ages
    patterns_infant = [
        r'(\d+)[- ](?:month|week|day)[- ]old',
    ]
    for pattern in patterns_infant:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Return as fraction of years or as-is depending on context
            return int(match.group(1))
    
    return None


def _find_systolic(text):
    """Find systolic blood pressure."""
    # Pattern: blood pressure XXX/YY or BP XXX/YY
    patterns = [
        r'(?:blood\s+pressure|bp|b\.p\.)[:\s]+(?:of\s+)?(\d{2,3})\s*/\s*\d{2,3}',
        r'(\d{2,3})\s*/\s*(\d{2,3})\s*mm\s*hg',
        r'(?:blood\s+pressure|bp)[^.]{0,40}?(\d{2,3})\s*/\s*\d{2,3}',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    
    return None


def _find_diastolic(text):
    """Find diastolic blood pressure."""
    patterns = [
        r'(?:blood\s+pressure|bp|b\.p\.)[:\s]+(?:of\s+)?(\d{2,3})\s*/\s*(\d{2,3})',
        r'(\d{2,3})\s*/\s*(\d{2,3})\s*mm\s*hg',
        r'(?:blood\s+pressure|bp)[^.]{0,40}?(\d{2,3})\s*/\s*(\d{2,3})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(2))
    
    return None


def _find_heart_rate(text):
    """Find heart rate."""
    patterns = [
        r'(?:heart\s+rate|hr|pulse)[:\s]+(?:of\s+)?(\d{2,3})\s*(?:bpm|beats|/min|per\s+min)',
        r'(\d{2,3})\s*(?:bpm|beats\s+per\s+min)',
        r'(?:heart\s+rate|hr|pulse)[:\s]+(\d{2,3})\b',
        r'(?:heart\s+rate|hr)[^.]{0,30}?(\d{2,3})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = int(match.group(1))
            if 20 < val < 300:
                return val
    
    return None


def _find_qt(text):
    """Find QT interval."""
    patterns = [
        r'(?:qt\s+(?:interval)?)[:\s]+(?:of\s+)?(\d{3,4})\s*(?:ms(?:ec)?|millisec)',
        r'(\d{3,4})\s*(?:ms(?:ec)?|millisec)',
        r'qt[^.]{0,30}?(\d{3,4})\s*(?:ms|millisec)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = int(match.group(1))
            if 100 < val < 1000:
                return val
    
    return None


def _find_dose_mg(text):
    """Find drug dose in mg."""
    patterns = [
        r'(\d+\.?\d*)\s*mg\b',
        r'dose[:\s]+(?:of\s+)?(\d+\.?\d*)\s*mg',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    
    return None


def _find_lab_value(text, param_name, param_desc):
    """Generic lab value finder using param name and description."""
    
    text_lower = text.lower()
    
    # Build keyword list from param name and description
    keywords = _get_keywords_for_param(param_name, param_desc)
    
    # Get expected unit from description
    unit = _get_unit_from_desc(param_desc)
    
    for keyword in keywords:
        # Try patterns with keyword followed by value
        patterns = []
        kw_escaped = re.escape(keyword)
        
        # Keyword: value unit
        patterns.append(rf'{kw_escaped}[:\s]+(\d+\.?\d*)\s*(?:{re.escape(unit) if unit else ""})?')
        # Keyword value
        patterns.append(rf'{kw_escaped}\s+(\d+\.?\d*)')
        # "Keyword XXX unit" or "Keyword: XXX"  
        patterns.append(rf'{kw_escaped}[^.\n]{{0,30}}?(\d+\.?\d*)')
        
        for pattern in patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                val_str = matches[0].group(1)
                try:
                    val = float(val_str)
                    if val == int(val):
                        val = int(val)
                    return val
                except ValueError:
                    continue
    
    # Try searching for unit patterns if we have a unit
    if unit:
        # Look for number followed by unit
        unit_escaped = re.escape(unit)
        pattern = rf'(\d+\.?\d*)\s*{unit_escaped}'
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        if matches:
            # Filter based on context
            for match in matches:
                val_str = match.group(1)
                try:
                    val = float(val_str)
                    if val == int(val):
                        val = int(val)
                    return val
                except ValueError:
                    continue
    
    # Special handling for serum lab table format "Na+ 130 mEq/L"
    table_value = _find_table_lab_value(text, param_name)
    if table_value is not None:
        return table_value
    
    return None


def _find_table_lab_value(text, param_name):
    """Find lab values from table-formatted text."""
    
    # Map param names to common lab abbreviations and names
    lab_patterns = {
        'sodium': [r'Na\+?\s+(\d+\.?\d*)', r'sodium[:\s]+(\d+\.?\d*)', r'Na\+?\s*[=:]\s*(\d+\.?\d*)'],
        'serum_sodium': [r'(?:Serum\s+)?Na\+?\s+(\d+\.?\d*)', r'sodium[:\s]+(\d+\.?\d*)', r'Na\+?\s*[=:]\s*(\d+\.?\d*)'],
        'chloride': [r'Cl-?\s+(\d+\.?\d*)', r'chloride[:\s]+(\d+\.?\d*)', r'Cl\s*[=:]\s*(\d+\.?\d*)'],
        'bicarbonate': [r'HCO3-?\s+(\d+\.?\d*)', r'bicarbonate[:\s]+(\d+\.?\d*)', r'CO2[:\s]+(\d+\.?\d*)', r'bicarb[:\s]+(\d+\.?\d*)'],
        'potassium': [r'K\+?\s+(\d+\.?\d*)', r'potassium[:\s]+(\d+\.?\d*)'],
        'bun': [r'BUN[:\s]+(\d+\.?\d*)', r'blood\s+urea\s+nitrogen[:\s]+(\d+\.?\d*)', r'urea\s+nitrogen[:\s]+(\d+\.?\d*)'],
        'glucose': [r'(?:fasting\s+)?(?:plasma\s+)?glucose[:\s]+(\d+\.?\d*)', r'blood\s+(?:sugar|glucose)[:\s]+(\d+\.?\d*)', r'glucose[:\s]+(\d+\.?\d*)'],
        'fasting_glucose': [r'fasting\s+(?:plasma\s+)?glucose[:\s]+(\d+\.?\d*)', r'glucose[:\s]+(\d+\.?\d*)', r'FPG[:\s]+(\d+\.?\d*)'],
        'fasting_insulin': [r'fasting\s+insulin[:\s]+(\d+\.?\d*)', r'insulin[:\s]+(\d+\.?\d*)'],
        'serum_creatinine': [r'(?:serum\s+)?creatinine[:\s]+(\d+\.?\d*)', r'Cr(?:eat)?[:\s]+(\d+\.?\d*)', r'sCr[:\s]+(\d+\.?\d*)'],
        'creatinine': [r'creatinine[:\s]+(\d+\.?\d*)', r'Cr[:\s]+(\d+\.?\d*)'],
        'urine_sodium': [r'(?:urine|urinary)\s+(?:Na\+?|sodium)[:\s]+(\d+\.?\d*)', r'U(?:rine)?Na[:\s]+(\d+\.?\d*)'],
        'urine_creatinine': [r'(?:urine|urinary)\s+(?:Cr(?:eat)?(?:inine)?)[:\s]+(\d+\.?\d*)', r'UCr[:\s]+(\d+\.?\d*)'],
        'albumin': [r'albumin[:\s]+(\d+\.?\d*)', r'Alb[:\s]+(\d+\.?\d*)'],
        'calcium': [r'Ca2?\+?\s+(\d+\.?\d*)', r'calcium[:\s]+(\d+\.?\d*)'],
    }
    
    patterns = lab_patterns.get(param_name, [])
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val_str = match.group(1)
            try:
                val = float(val_str)
                if val == int(val):
                    val = int(val)
                return val
            except ValueError:
                continue
    
    # Special: look for serum section vs urine section
    if param_name in ('serum_creatinine', 'serum_sodium'):
        # Look for Serum section
        serum_section = re.search(r'Serum\s*\n((?:.*\n)*?)(?:Urine|Arterial|\n\n)', text, re.IGNORECASE)
        if serum_section:
            section_text = serum_section.group(1)
            base_name = param_name.replace('serum_', '')
            return _find_table_lab_value(section_text, base_name)
    
    if param_name in ('urine_sodium', 'urine_creatinine'):
        # Look for Urine section
        urine_section = re.search(r'Urine\s*\n((?:.*\n)*?)(?:Arterial|\n\n|$)', text, re.IGNORECASE)
        if urine_section:
            section_text = urine_section.group(1)
            base_name = param_name.replace('urine_', '')
            return _find_table_lab_value(section_text, base_name)
    
    # For bicarbonate: also check pH/ABG section
    if param_name == 'bicarbonate':
        # Look for HCO3 pattern
        hco3_match = re.search(r'HCO3[-−]?\s*(?:of\s+)?(\d+\.?\d*)', text, re.IGNORECASE)
        if hco3_match:
            val = float(hco3_match.group(1))
            if val == int(val):
                val = int(val)
            return val
        
        # Check for ABG with pH of X.XX and a pCO2 of XX and HCO3 of XX
        abg_match = re.search(r'pH\s+(?:of\s+)?[\d.]+.*?(?:HCO3|bicarbonate)\s+(?:of\s+)?(\d+\.?\d*)', text, re.IGNORECASE | re.DOTALL)
        if abg_match:
            val = float(abg_match.group(1))
            if val == int(val):
                val = int(val)
            return val
        
        # Look for pattern like "pH of 7.XX and a pCO2 of XX"
        # Also check "alkalosis" context
        # Check text for "CO2" in basic metabolic panel context
        co2_match = re.search(r'(?:total\s+)?CO2[:\s]+(\d+\.?\d*)', text, re.IGNORECASE)
        if co2_match:
            val = float(co2_match.group(1))
            if val == int(val):
                val = int(val)
            return val
    
    return None


def _get_keywords_for_param(param_name, param_desc):
    """Get search keywords for a parameter."""
    keywords = []
    
    # From param name
    name_words = param_name.replace('_', ' ')
    keywords.append(name_words)
    
    # Individual words from param name (for compound names)
    parts = param_name.split('_')
    if len(parts) > 1:
        for part in parts:
            if len(part) > 2:
                keywords.append(part)
    
    # From description - extract the main term
    desc_match = re.match(r'(.+?)(?:\s+in\s+|\s+\()', param_desc)
    if desc_match:
        keywords.append(desc_match.group(1).strip())
    
    return keywords


def _get_unit_from_desc(param_desc):
    """Extract expected unit from parameter description."""
    # Look for "in XXX" pattern
    unit_match = re.search(r'in\s+(\S+(?:\s*/\s*\S+)?)', param_desc)
    if unit_match:
        unit = unit_match.group(1).strip('()')
        return unit
    return None
