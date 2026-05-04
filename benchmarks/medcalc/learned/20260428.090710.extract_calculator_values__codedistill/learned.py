"""Auto-generated code-distilled implementation for extract_calculator_values."""

import re
import json


def extract_calculator_values(clinical_note, calculator_name, param_descriptions, medical_analysis=''):
    """
    Extract calculator input values from a clinical note based on parameter descriptions.
    """
    result = {'extracted': {}, 'missing': []}
    
    # Parse parameter descriptions
    params = parse_params(param_descriptions)
    
    for param_name, param_desc in params:
        value = extract_value(clinical_note, calculator_name, param_name, param_desc, medical_analysis)
        if value is not None:
            result['extracted'][param_name] = value
        else:
            result['missing'].append(param_name)
    
    return result


def parse_params(param_descriptions):
    """Parse parameter descriptions into list of (name, description) tuples."""
    params = []
    lines = param_descriptions.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = re.match(r'^(\w+):\s*(.*)', line)
        if match:
            params.append((match.group(1), match.group(2)))
    return params


def extract_value(note, calculator_name, param_name, param_desc, medical_analysis):
    """Extract a single parameter value from the clinical note."""
    
    # Determine parameter type from description
    param_lower = param_name.lower()
    desc_lower = param_desc.lower()
    
    # Check if it's a boolean/condition parameter (True/False type)
    if '(true/false)' in desc_lower or '(+1)' in desc_lower:
        return extract_boolean(note, param_name, param_desc, medical_analysis)
    
    # Check if it's a score parameter (like APACHE II sub-scores)
    if param_name.endswith('_score'):
        return extract_score(note, param_name, param_desc, medical_analysis, calculator_name)
    
    # Check if it's sex/gender
    if param_name == 'sex':
        return extract_sex(note, medical_analysis)
    
    # It's a numeric value
    return extract_numeric(note, param_name, param_desc, calculator_name, medical_analysis)


def extract_boolean(note, param_name, param_desc, medical_analysis):
    """Extract boolean values based on medical analysis and note content."""
    param_lower = param_name.lower()
    
    # Use medical analysis if available
    if medical_analysis:
        present_match = re.search(r'Conditions PRESENT:\s*([^\n]+)', medical_analysis)
        absent_match = re.search(r'Conditions ABSENT:\s*([^\n]+)', medical_analysis)
        
        present_conditions = []
        absent_conditions = []
        
        if present_match:
            present_conditions = [c.strip().lower() for c in present_match.group(1).split(',')]
        if absent_match:
            absent_conditions = [c.strip().lower() for c in absent_match.group(1).split(',')]
        
        # For has_ prefixed params like has_chf, has_hypertension, etc.
        if param_lower.startswith('has_'):
            condition = param_lower[4:]  # strip 'has_'
            
            # Map parameter names to condition keywords
            condition_mappings = {
                'chf': ['chf', 'congestive heart failure', 'heart_failure', 'heart failure'],
                'hypertension': ['hypertension'],
                'diabetes': ['diabetes', 'diabetes_mellitus'],
                'stroke_tia': ['stroke', 'tia', 'stroke_tia'],
                'vascular_disease': ['vascular_disease', 'vascular disease', 'mi', 'pad', 'peripheral arterial disease'],
            }
            
            keywords = condition_mappings.get(condition, [condition])
            
            for cond in present_conditions:
                for kw in keywords:
                    if kw in cond or cond in kw:
                        return True
            
            for cond in absent_conditions:
                for kw in keywords:
                    if kw in cond or cond in kw:
                        return False
            
            # Also check the note directly
            return check_condition_in_note(note, condition, param_desc)
        
        # For SIRS-type criteria and similar boolean scoring
        # Map param names to conditions in analysis
        sirs_mappings = {
            'temperature_abnormal': ['temperature_abnormal', 'fever', 'febrile', 'hypothermia', 'hyperthermia'],
            'heart_rate_elevated': ['heart_rate_elevated', 'tachycardia'],
            'respiratory_abnormal': ['respiratory_abnormal', 'tachypnea'],
            'wbc_abnormal': ['wbc_abnormal', 'leukocytosis', 'leukopenia'],
        }
        
        keywords = sirs_mappings.get(param_lower, [param_lower])
        
        for cond in present_conditions:
            for kw in keywords:
                if kw in cond or cond in kw:
                    return True
        
        for cond in absent_conditions:
            for kw in keywords:
                if kw in cond or cond in kw:
                    return False
    
    # Default: try to determine from note
    return extract_boolean_from_note(note, param_name, param_desc)


def extract_boolean_from_note(note, param_name, param_desc):
    """Try to determine boolean value directly from note text."""
    note_lower = note.lower()
    param_lower = param_name.lower()
    
    # SIRS criteria
    if 'temperature' in param_lower:
        temps = re.findall(r'(?:temperature|temp)[:\s]*(\d+\.?\d*)\s*[°]?\s*[cfCF]', note)
        if not temps:
            temps = re.findall(r'(\d+\.?\d*)\s*[°]\s*[cfCF]', note)
        for t in temps:
            t_val = float(t)
            if t_val > 50:  # Fahrenheit
                t_val = (t_val - 32) * 5 / 9
            if t_val > 38 or t_val < 36:
                return True
        return False
    
    if 'heart_rate' in param_lower:
        hrs = re.findall(r'(?:heart rate|pulse|hr)[:\s]*(\d+)', note_lower)
        for hr in hrs:
            if int(hr) > 90:
                return True
        return False
    
    if 'respiratory' in param_lower:
        rrs = re.findall(r'(?:respiratory rate|rr)[:\s]*(\d+)', note_lower)
        for rr in rrs:
            if int(rr) > 20:
                return True
        return False
    
    if 'wbc' in param_lower:
        wbcs = re.findall(r'(?:wbc|white blood cell)[:\s]*(\d+[,.]?\d*)', note_lower)
        for wbc in wbcs:
            wbc_val = float(wbc.replace(',', ''))
            if wbc_val > 12000 or wbc_val < 4000:
                return True
            if wbc_val > 12 or wbc_val < 4:  # might be in thousands
                return True
        return False
    
    return None


def check_condition_in_note(note, condition, param_desc):
    """Check if a condition is present in the clinical note."""
    note_lower = note.lower()
    
    condition_keywords = {
        'chf': ['congestive heart failure', 'heart failure', 'chf'],
        'hypertension': ['hypertension', 'htn'],
        'diabetes': ['diabetes', 'diabetic', 'dm type', 'type 2 diabetes', 'type 1 diabetes'],
        'stroke_tia': ['stroke', 'tia', 'transient ischemic attack', 'cerebrovascular accident', 'cva'],
        'vascular_disease': ['myocardial infarction', 'peripheral arterial disease', 'pad', 'aortic plaque', 'vascular disease'],
    }
    
    keywords = condition_keywords.get(condition, [condition.replace('_', ' ')])
    
    for kw in keywords:
        if kw in note_lower:
            return True
    return False


def extract_sex(note, medical_analysis=''):
    """Extract patient sex from the note."""
    note_lower = note.lower()
    
    # Check medical analysis first
    if medical_analysis:
        demo_match = re.search(r'Sex=(\w+)', medical_analysis)
        if demo_match:
            return demo_match.group(1).lower()
    
    # Common patterns
    # Look for explicit sex/gender mentions
    male_patterns = [
        r'\b(\d+[- ]year[- ]old)\s+(?:\w+\s+)*male\b',
        r'\bmale\s+patient\b',
        r'\b(?:man|boy|gentleman)\b',
        r'\bhis\b.*\bhe\b',
        r'\b(\d+[- ]year[- ]old)\s+(?:\w+\s+)*man\b',
        r'\b(\d+[- ]year[- ]old)\s+(?:\w+\s+)*boy\b',
    ]
    
    female_patterns = [
        r'\b(\d+[- ]year[- ]old)\s+(?:\w+\s+)*female\b',
        r'\bfemale\s+patient\b',
        r'\b(?:woman|girl|lady)\b',
        r'\b(\d+[- ]year[- ]old)\s+(?:\w+\s+)*woman\b',
        r'\b(\d+[- ]year[- ]old)\s+(?:\w+\s+)*girl\b',
    ]
    
    # Check for female first (to handle cases with both "male" in "female")
    for pattern in female_patterns:
        if re.search(pattern, note_lower):
            return 'female'
    
    for pattern in male_patterns:
        if re.search(pattern, note_lower):
            return 'male'
    
    # Pronoun-based detection
    he_count = len(re.findall(r'\bhe\b', note_lower))
    she_count = len(re.findall(r'\bshe\b', note_lower))
    his_count = len(re.findall(r'\bhis\b', note_lower))
    her_count = len(re.findall(r'\bher\b', note_lower))
    
    male_score = he_count + his_count
    female_score = she_count + her_count
    
    if male_score > female_score + 2:
        return 'male'
    elif female_score > male_score + 2:
        return 'female'
    
    return None


def extract_numeric(note, param_name, param_desc, calculator_name, medical_analysis=''):
    """Extract a numeric value from the clinical note."""
    note_lower = note.lower()
    param_lower = param_name.lower()
    
    # Age extraction
    if param_lower == 'age':
        return extract_age(note, medical_analysis)
    
    # Weight extraction
    if param_lower in ('weight_kg', 'weight'):
        return extract_weight(note)
    
    # Height extraction  
    if param_lower in ('height_cm', 'height'):
        return extract_height(note)
    
    # Blood pressure - systolic
    if param_lower == 'systolic':
        return extract_systolic(note)
    
    # Blood pressure - diastolic
    if param_lower == 'diastolic':
        return extract_diastolic(note)
    
    # Creatinine
    if param_lower in ('creatinine_mg_dl', 'creatinine'):
        return extract_creatinine(note)
    
    # Sodium
    if param_lower == 'sodium':
        return extract_sodium(note)
    
    # Chloride
    if param_lower == 'chloride':
        return extract_chloride(note)
    
    # Bicarbonate
    if param_lower == 'bicarbonate':
        return extract_bicarbonate(note)
    
    # Calcium
    if param_lower == 'calcium':
        return extract_calcium(note)
    
    # Albumin
    if param_lower == 'albumin':
        return extract_albumin(note)
    
    # Total cholesterol
    if param_lower == 'total_cholesterol':
        return extract_total_cholesterol(note)
    
    # HDL
    if param_lower == 'hdl':
        return extract_hdl(note)
    
    # Triglycerides
    if param_lower == 'triglycerides':
        return extract_triglycerides(note)
    
    # BUN
    if param_lower == 'bun':
        return extract_bun(note)
    
    # Potassium
    if param_lower == 'potassium':
        return extract_potassium(note)
    
    # Heart rate
    if param_lower in ('heart_rate', 'hr'):
        return extract_heart_rate(note)
    
    # Respiratory rate
    if param_lower in ('respiratory_rate', 'rr'):
        return extract_respiratory_rate(note)
    
    # Temperature
    if param_lower in ('temperature', 'temp', 'temperature_c'):
        return extract_temperature(note)
    
    # GCS
    if param_lower in ('gcs', 'glasgow_coma_scale'):
        return extract_gcs(note)
    
    # PaO2
    if param_lower == 'pao2':
        return extract_pao2(note)
    
    # FiO2
    if param_lower == 'fio2':
        return extract_fio2(note)
    
    # pH
    if param_lower in ('ph', 'arterial_ph'):
        return extract_ph(note)
    
    # Hematocrit
    if param_lower == 'hematocrit':
        return extract_hematocrit(note)
    
    # WBC
    if param_lower == 'wbc':
        return extract_wbc(note)
    
    # Platelets
    if param_lower == 'platelets':
        return extract_platelets(note)
    
    # INR
    if param_lower == 'inr':
        return extract_inr(note)
    
    # Bilirubin
    if param_lower in ('bilirubin', 'total_bilirubin'):
        return extract_bilirubin(note)
    
    # Generic extraction attempt
    return generic_extract(note, param_name, param_desc)


def extract_age(note, medical_analysis=''):
    """Extract patient age from note."""
    if medical_analysis:
        age_match = re.search(r'Age=(\d+)', medical_analysis)
        if age_match:
            return int(age_match.group(1))
    
    # Pattern: X-year-old
    match = re.search(r'(\d+)[- ]+year[- ]*old', note.lower())
    if match:
        return int(match.group(1))
    
    # Pattern: age X or aged X
    match = re.search(r'age[d]?\s+(?:of\s+)?(\d+)', note.lower())
    if match:
        return int(match.group(1))
    
    # Pattern: X-month-old (convert to fraction or return months)
    match = re.search(r'(\d+)[- ]+month[- ]*old', note.lower())
    if match:
        months = int(match.group(1))
        return months / 12.0
    
    return None


def extract_weight(note):
    """Extract patient weight in kg."""
    note_lower = note.lower()
    
    # Pattern: weight X kg or weighing X kg
    patterns = [
        r'(?:body\s+)?weight[:\s]+(?:of\s+)?(\d+\.?\d*)\s*kg',
        r'weighing\s+(\d+\.?\d*)\s*kg',
        r'weighs\s+(\d+\.?\d*)\s*kg',
        r'weight\s*(?:=|was|is|of)\s*(\d+\.?\d*)\s*kg',
        r'(\d+\.?\d*)\s*kg\s*(?:\(|,|\s|;)',
        r'weight\s*[-=:]\s*(\d+\.?\d*)\s*kg',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 0.5 < val < 500:  # reasonable weight range
                return val
    
    # Try to find kg mentioned near weight context
    # Pattern: X kg (Y lb)
    match = re.search(r'(\d+\.?\d*)\s*kg\s*\(\d+', note_lower)
    if match:
        val = float(match.group(1))
        if 0.5 < val < 500:
            return val
    
    # Pattern: last reported body weight X kg
    match = re.search(r'body\s+weight\s+(\d+\.?\d*)\s*kg', note_lower)
    if match:
        return float(match.group(1))
    
    # Look for weight = X kg pattern more broadly
    match = re.search(r'weight\s*[=:]\s*(\d+\.?\d*)\s*kg', note_lower)
    if match:
        return float(match.group(1))
    
    # Broader: just X kg in context
    matches = re.findall(r'(\d+\.?\d*)\s*kg\b', note_lower)
    for m in matches:
        val = float(m)
        if 1 < val < 300:
            return val
    
    return None


def extract_height(note):
    """Extract patient height in cm."""
    note_lower = note.lower()
    
    # Pattern: height X cm or X cm tall
    patterns = [
        r'height[:\s]+(?:of\s+)?(\d+\.?\d*)\s*cm',
        r'(\d+\.?\d*)\s*cm\s*(?:tall|\()',
        r'height\s*(?:=|was|is|of)\s*(\d+\.?\d*)\s*cm',
        r'length\s*(?:=|was|is|of)\s*(\d+\.?\d*)\s*cm',
        r'height\s*[-=:]\s*(\d+\.?\d*)\s*cm',
        r'(\d+)\s*cm\s*\(\d+\s*ft',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 30 < val < 250:  # reasonable height range in cm
                return val
    
    # Pattern: X ft Y in -> convert to cm
    match = re.search(r'(\d+)\s*(?:ft|feet|\')\s*(\d+)\s*(?:in|inches|\")', note_lower)
    if match:
        feet = int(match.group(1))
        inches = int(match.group(2))
        cm = (feet * 12 + inches) * 2.54
        return round(cm, 1)
    
    # Try to find cm in height/length context
    match = re.search(r'(?:length|height)\s*=\s*(\d+\.?\d*)\s*cm', note_lower)
    if match:
        return float(match.group(1))
    
    # Broader pattern
    matches = re.findall(r'(\d+\.?\d*)\s*cm\b', note_lower)
    for m in matches:
        val = float(m)
        if 40 < val < 250:
            # Check context - is it near height/length/tall
            idx = note_lower.find(m + ' cm')
            if idx == -1:
                idx = note_lower.find(m + 'cm')
            if idx >= 0:
                context = note_lower[max(0, idx-50):idx+20]
                if any(w in context for w in ['height', 'tall', 'length', 'stature']):
                    return val
    
    return None


def extract_systolic(note):
    """Extract systolic blood pressure."""
    note_lower = note.lower()
    
    # Pattern: blood pressure X/Y or BP X/Y
    patterns = [
        r'(?:blood\s+pressure|bp)[:\s]+(?:was\s+|of\s+|is\s+)?(\d+)\s*/\s*\d+',
        r'(\d+)\s*/\s*\d+\s*mm\s*hg',
        r'(\d+)\s*/\s*\d+\s*mmhg',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 50 < val < 300:
                return val
    
    return None


def extract_diastolic(note):
    """Extract diastolic blood pressure."""
    note_lower = note.lower()
    
    patterns = [
        r'(?:blood\s+pressure|bp)[:\s]+(?:was\s+|of\s+|is\s+)?\d+\s*/\s*(\d+)',
        r'\d+\s*/\s*(\d+)\s*mm\s*hg',
        r'\d+\s*/\s*(\d+)\s*mmhg',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 20 < val < 200:
                return val
    
    return None


def extract_creatinine(note):
    """Extract serum creatinine in mg/dL."""
    note_lower = note.lower()
    
    # Pattern: creatinine X mg/dL
    patterns = [
        r'(?:serum\s+)?creatinine[:\s]+(?:of\s+|was\s+|is\s+|level\s+(?:of\s+)?)?(\d+\.?\d*)\s*mg\s*/\s*d[lL]',
        r'creatinine\s*(?:=|:|\s)\s*(\d+\.?\d*)\s*mg\s*/\s*d[lL]',
        r'(?:serum\s+)?creatinine[:\s]+(\d+\.?\d*)\s*mg',
        r'creatinine\s+(?:of|was|is|=)\s+(\d+\.?\d*)\s*mg',
        r'(?:serum\s+)?creatinine[:\s]+(?:of\s+)?(\d+\.?\d*)',
        r'scr\s*(?:=|:|\s)\s*(\d+\.?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 0.1 < val < 30:
                return val
    
    # Check for μmol/L and convert
    match = re.search(r'creatinine[:\s]+(\d+\.?\d*)\s*[μu]mol', note_lower)
    if match:
        umol = float(match.group(1))
        return round(umol / 88.4, 2)
    
    return None


def extract_sodium(note):
    """Extract serum sodium in mEq/L."""
    note_lower = note.lower()
    
    patterns = [
        r'(?:serum\s+)?(?:na\+?|sodium)[:\s]+(\d+\.?\d*)\s*(?:meq|mmol|mEq)',
        r'(?:na\+?|sodium)\s*(?:=|:|\s)\s*(\d+\.?\d*)\s*(?:meq|mmol)',
        r'(?:na\+?|sodium)[:\s]+(\d+\.?\d*)',
        r'na\+?\s+(\d+\.?\d*)\s*(?:meq|mmol)',
        r'na\+?\s+(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 100 < val < 180:
                return int(val) if val == int(val) else val
    
    return None


def extract_chloride(note):
    """Extract serum chloride in mEq/L."""
    note_lower = note.lower()
    
    patterns = [
        r'(?:cl-?|chloride)[:\s]+(\d+\.?\d*)\s*(?:meq|mmol)',
        r'(?:cl-?|chloride)\s*(?:=|:|\s)\s*(\d+\.?\d*)',
        r'cl-?\s+(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 70 < val < 130:
                return int(val) if val == int(val) else val
    
    return None


def extract_bicarbonate(note):
    """Extract serum bicarbonate in mEq/L."""
    note_lower = note.lower()
    
    patterns = [
        r'(?:hco3-?|bicarbonate)[:\s]+(\d+\.?\d*)\s*(?:meq|mmol)',
        r'(?:hco3-?|bicarbonate)\s*(?:=|:|\s)\s*(\d+\.?\d*)',
        r'hco3-?\s+(\d+)',
        r'(?:co2|tco2)[:\s]+(\d+\.?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 5 < val < 60:
                return int(val) if val == int(val) else val
    
    # Try arterial blood gas for bicarbonate
    # Sometimes listed as HCO3 in ABG
    match = re.search(r'(?:arterial|abg).*?hco3[:\s-]*(\d+\.?\d*)', note_lower, re.DOTALL)
    if match:
        val = float(match.group(1))
        if 5 < val < 60:
            return int(val) if val == int(val) else val
    
    return None


def extract_calcium(note):
    """Extract serum calcium in mg/dL."""
    note_lower = note.lower()
    
    patterns = [
        r'(?:serum\s+)?(?:ca2?\+?|calcium)[:\s]+(\d+\.?\d*)\s*mg\s*/\s*d[lL]',
        r'(?:ca2?\+?|calcium)\s*(?:=|:|\s)\s*(\d+\.?\d*)\s*mg',
        r'(?:ca2?\+?|calcium)[:\s]+(\d+\.?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 4 < val < 20:
                return val
    
    return None


def extract_albumin(note):
    """Extract serum albumin in g/dL."""
    note_lower = note.lower()
    
    patterns = [
        r'albumin[:\s]+(\d+\.?\d*)\s*g\s*/\s*d[lL]',
        r'albumin\s*(?:=|:|\s)\s*(\d+\.?\d*)\s*g',
        r'albumin[:\s]+(\d+\.?\d*)',
        r'albumin\s+(?:of|was|is|=)\s+(\d+\.?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 0.5 < val < 7:
                return val
    
    return None


def extract_total_cholesterol(note):
    """Extract total cholesterol in mg/dL."""
    note_lower = note.lower()
    
    patterns = [
        r'total\s+cholesterol[:\s]+(\d+\.?\d*)',
        r'cholesterol[:\s]+(\d+\.?\d*)\s*mg',
        r'cholesterol[:\s]+(\d+\.?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 50 < val < 500:
                return int(val) if val == int(val) else val
    
    return None


def extract_hdl(note):
    """Extract HDL cholesterol in mg/dL."""
    note_lower = note.lower()
    
    patterns = [
        r'hdl[:\s]+(\d+\.?\d*)',
        r'hdl\s*(?:cholesterol)?[:\s]+(\d+\.?\d*)',
        r'high[- ]density\s+lipoprotein[:\s]+(\d+\.?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 10 < val < 150:
                return int(val) if val == int(val) else val
    
    return None


def extract_triglycerides(note):
    """Extract triglycerides in mg/dL."""
    note_lower = note.lower()
    
    patterns = [
        r'triglyceride[s]?[:\s]+(\d+\.?\d*)',
        r'tg[:\s]+(\d+\.?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 20 < val < 2000:
                return int(val) if val == int(val) else val
    
    return None


def extract_bun(note):
    """Extract BUN in mg/dL."""
    note_lower = note.lower()
    
    patterns = [
        r'(?:blood\s+urea\s+nitrogen|bun)[:\s]+(\d+\.?\d*)',
        r'bun\s*(?:=|:|\s)\s*(\d+\.?\d*)',
        r'urea\s+nitrogen[:\s]+(\d+\.?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 1 < val < 200:
                return val
    
    return None


def extract_potassium(note):
    """Extract serum potassium in mEq/L."""
    note_lower = note.lower()
    
    patterns = [
        r'(?:k\+?|potassium)[:\s]+(\d+\.?\d*)\s*(?:meq|mmol)',
        r'(?:k\+?|potassium)\s*(?:=|:|\s)\s*(\d+\.?\d*)',
        r'k\+?\s+(\d+\.?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 1.5 < val < 9:
                return val
    
    return None


def extract_heart_rate(note):
    """Extract heart rate in bpm."""
    note_lower = note.lower()
    
    patterns = [
        r'(?:heart\s+rate|pulse|hr)[:\s]+(\d+)',
        r'(?:heart\s+rate|pulse|hr)\s*(?:=|was|is|of)\s*(\d+)',
        r'(\d+)\s*(?:bpm|beats?\s*per\s*min)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = int(match.group(1))
            if 20 < val < 300:
                return val
    
    return None


def extract_respiratory_rate(note):
    """Extract respiratory rate."""
    note_lower = note.lower()
    
    patterns = [
        r'(?:respiratory\s+rate|rr)[:\s]+(\d+)',
        r'(?:respiratory\s+rate|rr)\s*(?:=|was|is|of)\s*(\d+)',
        r'(\d+)\s*breaths?\s*/?\s*min',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = int(match.group(1))
            if 5 < val < 60:
                return val
    
    return None


def extract_temperature(note):
    """Extract temperature in Celsius."""
    note_lower = note.lower()
    
    patterns = [
        r'(?:temperature|temp)[:\s]+(\d+\.?\d*)\s*[°]?\s*c\b',
        r'(\d+\.?\d*)\s*°\s*c\b',
        r'(?:temperature|temp)[:\s]+(\d+\.?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 30 < val < 45:
                return val
            elif val > 50:  # Fahrenheit
                return round((val - 32) * 5 / 9, 1)
    
    return None


def extract_gcs(note):
    """Extract Glasgow Coma Scale score."""
    note_lower = note.lower()
    
    patterns = [
        r'(?:gcs|glasgow\s+coma\s+(?:scale|score))[:\s]+(\d+)',
        r'(?:gcs|glasgow)[:\s]+(?:of\s+)?(\d+)',
        r'gcs\s*(?:=|was|is|of)\s*(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = int(match.group(1))
            if 3 <= val <= 15:
                return val
    
    return None


def extract_pao2(note):
    """Extract PaO2 in mmHg."""
    note_lower = note.lower()
    
    patterns = [
        r'pao2[:\s]+(\d+\.?\d*)',
        r'pao2\s*(?:=|:|\s)\s*(\d+\.?\d*)',
        r'po2[:\s]+(\d+\.?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 20 < val < 700:
                return val
    
    return None


def extract_fio2(note):
    """Extract FiO2."""
    note_lower = note.lower()
    
    patterns = [
        r'fio2[:\s]+(\d+\.?\d*)\s*%',
        r'fio2[:\s]+(\d+\.?\d*)',
        r'fio2\s*(?:=|:|\s)\s*(\d+\.?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if val > 1:
                return val / 100  # Convert percentage
            return val
    
    # Room air = 0.21
    if 'room air' in note_lower:
        return 0.21
    
    return None


def extract_ph(note):
    """Extract arterial pH."""
    note_lower = note.lower()
    
    patterns = [
        r'(?:arterial\s+)?ph[:\s]+(\d+\.?\d*)',
        r'ph\s*(?:=|was|is|of)\s*(\d+\.?\d*)',
        r'ph\s+(\d+\.\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 6.5 < val < 8.0:
                return val
    
    return None


def extract_hematocrit(note):
    """Extract hematocrit percentage."""
    note_lower = note.lower()
    
    patterns = [
        r'(?:hematocrit|hct)[:\s]+(\d+\.?\d*)\s*%',
        r'(?:hematocrit|hct)\s*(?:=|:|\s)\s*(\d+\.?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 10 < val < 70:
                return val
    
    return None


def extract_wbc(note):
    """Extract WBC count."""
    note_lower = note.lower()
    
    patterns = [
        r'(?:wbc|white\s+blood\s+cell)[:\s]+(\d+[,.]?\d*)',
        r'(?:wbc|white\s+blood\s+cell)\s*(?:=|:|\s)\s*(\d+[,.]?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val_str = match.group(1).replace(',', '')
            val = float(val_str)
            return val
    
    return None


def extract_platelets(note):
    """Extract platelet count."""
    note_lower = note.lower()
    
    patterns = [
        r'(?:platelet[s]?|plt)[:\s]+(\d+[,.]?\d*)',
        r'(?:platelet[s]?|plt)\s*(?:=|:|\s)\s*(\d+[,.]?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val_str = match.group(1).replace(',', '')
            val = float(val_str)
            return val
    
    return None


def extract_inr(note):
    """Extract INR."""
    note_lower = note.lower()
    
    patterns = [
        r'(?:inr)[:\s]+(\d+\.?\d*)',
        r'inr\s*(?:=|:|\s)\s*(\d+\.?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 0.5 < val < 15:
                return val
    
    return None


def extract_bilirubin(note):
    """Extract total bilirubin in mg/dL."""
    note_lower = note.lower()
    
    patterns = [
        r'(?:total\s+)?bilirubin[:\s]+(\d+\.?\d*)',
        r'bilirubin\s*(?:=|:|\s)\s*(\d+\.?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 0.1 < val < 50:
                return val
    
    return None


def extract_score(note, param_name, param_desc, medical_analysis, calculator_name):
    """Extract score-type values for calculators like APACHE II."""
    
    if 'APACHE II' in calculator_name:
        return extract_apache_score(note, param_name, param_desc, medical_analysis)
    
    # Generic score extraction
    return None


def extract_apache_score(note, param_name, param_desc, medical_analysis):
    """Extract individual APACHE II sub-scores by computing from raw values and medical analysis."""
    note_lower = note.lower()
    
    # Parse conditions from medical analysis
    present_conditions = []
    absent_conditions = []
    age = None
    
    if medical_analysis:
        present_match = re.search(r'Conditions PRESENT:\s*([^\n]+)', medical_analysis)
        absent_match = re.search(r'Conditions ABSENT:\s*([^\n]+)', medical_analysis)
        age_match = re.search(r'Age=(\d+)', medical_analysis)
        
        if present_match:
            present_conditions = [c.strip().lower() for c in present_match.group(1).split(',')]
        if absent_match:
            absent_conditions = [c.strip().lower() for c in absent_match.group(1).split(',')]
        if age_match:
            age = int(age_match.group(1))
    
    param_lower = param_name.lower()
    
    if param_lower == 'age_score':
        if age is None:
            age_val = extract_age(note, medical_analysis)
            if age_val is not None:
                age = int(age_val)
        if age is not None:
            if age < 45:
                return 0
            elif age < 55:
                return 2
            elif age < 65:
                return 3
            elif age < 75:
                return 5
            else:
                return 6
        return None
    
    if param_lower == 'chronic_health_score':
        # Check for chronic organ insufficiency or immunocompromised
        has_chronic = False
        for cond in present_conditions:
            if any(kw in cond for kw in ['chronic_organ', 'immunocompromised', 'cirrhosis', 'chronic_liver',
                                          'chronic_renal', 'chronic_respiratory', 'immunosuppressed']):
                has_chronic = True
                break
        
        if not has_chronic:
            for cond in absent_conditions:
                if any(kw in cond for kw in ['chronic_organ', 'immunocompromised']):
                    return 0
        
        if has_chronic:
            # Check if surgical - elective vs emergency, or non-surgical
            return 5  # default for non-surgical or emergency
        return 0
    
    if param_lower == 'gcs_score':
        gcs = extract_gcs(note)
        if gcs is not None:
            return 15 - gcs
        # Check medical analysis for GCS-related conditions
        # If the patient is described as alert/oriented, GCS ~ 15 -> score 0
        if any('altered_mental' in c or 'confusion' in c for c in present_conditions):
            return 1  # mildly impaired
        return None
    
    if param_lower == 'temperature_score':
        temp = extract_temperature(note)
        if temp is not None:
            return apache_temp_score(temp)
        # Check if fever/hypothermia in conditions
        if any('fever' in c or 'hyperthermia' in c for c in present_conditions):
            # Try to get actual temperature
            temps = re.findall(r'(\d+\.?\d*)\s*°?\s*[fF]', note)
            for t in temps:
                t_c = (float(t) - 32) * 5 / 9
                if 30 < t_c < 45:
                    return apache_temp_score(t_c)
            temps = re.findall(r'(\d+\.?\d*)\s*°?\s*[cC]', note)
            for t in temps:
                t_c = float(t)
                if 30 < t_c < 45:
                    return apache_temp_score(t_c)
            return 1  # default mild fever
        return 0
    
    if param_lower == 'map_score':
        sys_bp = extract_systolic(note)
        dia_bp = extract_diastolic(note)
        if sys_bp is not None and dia_bp is not None:
            mean_ap = dia_bp + (sys_bp - dia_bp) / 3
            return apache_map_score(mean_ap)
        # Check conditions
        if any('hypotension' in c for c in present_conditions):
            return 2
        if any('hypotension' in c for c in absent_conditions):
            return 0
        return 0
    
    if param_lower == 'heart_rate_score':
        hr = extract_heart_rate(note)
        if hr is not None:
            return apache_hr_score(hr)
        if any('tachycardia' in c for c in present_conditions):
            return 0  # mild tachycardia might be 0 for APACHE
        return 0
    
    if param_lower == 'respiratory_rate_score':
        rr = extract_respiratory_rate(note)
        if rr is not None:
            return apache_rr_score(rr)
        if any('tachypnea' in c for c in present_conditions):
            return 1
        return 0
    
    if param_lower == 'oxygenation_score':
        pao2 = extract_pao2(note)
        fio2 = extract_fio2(note)
        if fio2 is not None and fio2 >= 0.5:
            # Use A-a gradient
            # A-aDO2 = (713 * FiO2) - (PaCO2/0.8) - PaO2
            paco2 = extract_paco2(note)
            if pao2 is not None and paco2 is not None:
                aa_gradient = (713 * fio2) - (paco2 / 0.8) - pao2
                return apache_aado2_score(aa_gradient)
        elif pao2 is not None:
            return apache_pao2_score(pao2)
        
        if any('hypoxemia' in c or 'hypoxia' in c for c in present_conditions):
            return 0  # mild
        return 0
    
    if param_lower == 'ph_score':
        ph = extract_ph(note)
        if ph is not None:
            return apache_ph_score(ph)
        if any('acidosis' in c for c in present_conditions):
            return 2
        if any('alkalosis' in c or 'respiratory_alkalosis' in c for c in present_conditions):
            return 1
        return 0
    
    if param_lower == 'sodium_score':
        na = extract_sodium(note)
        if na is not None:
            return apache_sodium_score(na)
        if any('hyponatremia' in c for c in present_conditions):
            return 2  # moderate
        return 0
    
    if param_lower == 'potassium_score':
        k = extract_potassium(note)
        if k is not None:
            return apache_potassium_score(k)
        return 0
    
    if param_lower == 'creatinine_score':
        cr = extract_creatinine(note)
        has_arf = any('acute_renal_failure' in c or 'acute_renal' in c or 'arf' in c for c in present_conditions)
        if cr is not None:
            score = apache_creatinine_score(cr)
            if has_arf:
                score *= 2
            return score
        return 0
    
    if param_lower == 'hematocrit_score':
        hct = extract_hematocrit(note)
        if hct is not None:
            return apache_hct_score(hct)
        if any('anemia' in c for c in present_conditions):
            return 2
        return 0
    
    if param_lower == 'wbc_score':
        wbc = extract_wbc(note)
        if wbc is not None:
            # Normalize to per mm3
            if wbc < 100:
                wbc *= 1000
            return apache_wbc_score(wbc)
        if any('leukocytosis' in c for c in present_conditions):
            return 1
        return 0
    
    return None


def extract_paco2(note):
    """Extract PaCO2."""
    note_lower = note.lower()
    patterns = [
        r'paco2[:\s]+(\d+\.?\d*)',
        r'pco2[:\s]+(\d+\.?\d*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, note_lower)
        if match:
            val = float(match.group(1))
            if 10 < val < 120:
                return val
    return None


def apache_temp_score(temp_c):
    """APACHE II temperature scoring."""
    if temp_c >= 41:
        return 4
    elif temp_c >= 39:
        return 3
    elif temp_c >= 38.5:
        return 1
    elif temp_c >= 36:
        return 0
    elif temp_c >= 34:
        return 1
    elif temp_c >= 32:
        return 2
    elif temp_c >= 30:
        return 3
    else:
        return 4


def apache_map_score(mean_ap):
    """APACHE II MAP scoring."""
    if mean_ap >= 160:
        return 4
    elif mean_ap >= 130:
        return 3
    elif mean_ap >= 110:
        return 2
    elif mean_ap >= 70:
        return 0
    elif mean_ap >= 50:
        return 2
    else:
        return 4


def apache_hr_score(hr):
    """APACHE II heart rate scoring."""
    if hr >= 180:
        return 4
    elif hr >= 140:
        return 3
    elif hr >= 110:
        return 2
    elif hr >= 70:
        return 0
    elif hr >= 55:
        return 2
    elif hr >= 40:
        return 3
    else:
        return 4


def apache_rr_score(rr):
    """APACHE II respiratory rate scoring."""
    if rr >= 50:
        return 4
    elif rr >= 35:
        return 3
    elif rr >= 25:
        return 1
    elif rr >= 12:
        return 0
    elif rr >= 10:
        return 1
    elif rr >= 6:
        return 2
    else:
        return 4


def apache_aado2_score(aa):
    """APACHE II A-aDO2 scoring (when FiO2 >= 0.5)."""
    if aa >= 500:
        return 4
    elif aa >= 350:
        return 3
    elif aa >= 200:
        return 2
    else:
        return 0


def apache_pao2_score(pao2):
    """APACHE II PaO2 scoring (when FiO2 < 0.5)."""
    if pao2 > 70:
        return 0
    elif pao2 >= 61:
        return 1
    elif pao2 >= 55:
        return 3
    else:
        return 4


def apache_ph_score(ph):
    """APACHE II arterial pH scoring."""
    if ph >= 7.7:
        return 4
    elif ph >= 7.6:
        return 3
    elif ph >= 7.5:
        return 1
    elif ph >= 7.33:
        return 0
    elif ph >= 7.25:
        return 2
    elif ph >= 7.15:
        return 3
    else:
        return 4


def apache_sodium_score(na):
    """APACHE II sodium scoring."""
    if na >= 180:
        return 4
    elif na >= 160:
        return 3
    elif na >= 155:
        return 2
    elif na >= 150:
        return 1
    elif na >= 130:
        return 0
    elif na >= 120:
        return 2
    elif na >= 111:
        return 3
    else:
        return 4


def apache_potassium_score(k):
    """APACHE II potassium scoring."""
    if k >= 7:
        return 4
    elif k >= 6:
        return 3
    elif k >= 5.5:
        return 1
    elif k >= 3.5:
        return 0
    elif k >= 3:
        return 1
    elif k >= 2.5:
        return 2
    else:
        return 4


def apache_creatinine_score(cr):
    """APACHE II creatinine scoring (before ARF doubling)."""
    if cr >= 3.5:
        return 4
    elif cr >= 2.0:
        return 3
    elif cr >= 1.5:
        return 2
    elif cr >= 0.6:
        return 0
    else:
        return 2


def apache_hct_score(hct):
    """APACHE II hematocrit scoring."""
    if hct >= 60:
        return 4
    elif hct >= 50:
        return 2
    elif hct >= 46:
        return 1
    elif hct >= 30:
        return 0
    elif hct >= 20:
        return 2
    else:
        return 4


def apache_wbc_score(wbc):
    """APACHE II WBC scoring (in cells/mm3)."""
    if wbc >= 40000:
        return 4
    elif wbc >= 20000:
        return 2
    elif wbc >= 15000:
        return 1
    elif wbc >= 3000:
        return 0
    elif wbc >= 1000:
        return 2
    else:
        return 4


def generic_extract(note, param_name, param_desc):
    """Generic extraction for unrecognized parameters."""
    note_lower = note.lower()
    
    # Try to find the parameter by its description keywords
    # Extract key terms from description
    desc_lower = param_desc.lower()
    
    # Look for unit hints
    unit_match = re.search(r'in\s+(\w+(?:/\w+)?)', desc_lower)
    
    # Try using the parameter name as keyword
    search_term = param_name.replace('_', ' ').lower()
    
    pattern = re.escape(search_term) + r'[:\s]+(\d+\.?\d*)'
    match = re.search(pattern, note_lower)
    if match:
        return float(match.group(1))
    
    return None
