"""Auto-generated end-to-end implementation for calculate_medical_value."""

import re
import math

def calculate_medical_value(text, question):
    parsed = parse_input(text, question)
    if parsed is None:
        return None
    result = solve(parsed)
    if result is None:
        return None
    return format_output(result)

def parse_input(text, question):
    if "Creatinine Clearance" not in question and "Cockroft-Gault" not in question:
        return None
    
    age = extract_age(text)
    sex = extract_sex(text)
    weight = extract_weight(text)
    height = extract_height(text)
    creatinine = extract_creatinine(text)
    
    if any(v is None for v in [age, sex, weight, height, creatinine]):
        return None
    
    return {
        'age': age,
        'sex': sex,
        'weight_kg': weight,
        'height_cm': height,
        'creatinine': creatinine
    }

def extract_age(text):
    # Try various age patterns
    patterns = [
        r'(?:A|An)\s+(\d+)-year-old',
        r'(?:A|An)\s+(\d+)\s*-\s*year\s*-?\s*old',
        r'(?:a|an)\s+(\d+)-year-old',
        r'(?:a|an)\s+(\d+)\s*-\s*year\s*-?\s*old',
        r'aged?\s+(\d+)\s*year',
        r'(\d+)\s*-?\s*year\s*-?\s*old',
        r'age\s+(?:of\s+)?(\d+)',
        r'(\d+)\s+years?\s+(?:of\s+)?age',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None

def extract_sex(text):
    text_lower = text.lower()
    # Look for explicit gender indicators
    patterns_female = [
        r'\b(?:female|woman|girl|lady)\b',
        r'\bshe\b',
        r'\bher\b',
    ]
    patterns_male = [
        r'\b(?:male|man|boy|gentleman)\b',
        r'\bhis\b',
        r'\bhe\b',
    ]
    
    # Check in first 500 chars for primary gender identification
    first_part = text[:500].lower()
    
    female_score = 0
    male_score = 0
    
    for p in patterns_female:
        if re.search(p, first_part):
            female_score += 10
    for p in patterns_male:
        if re.search(p, first_part):
            male_score += 10
    
    # Also check full text but with lower weight
    for p in patterns_female:
        matches = re.findall(p, text_lower)
        female_score += len(matches)
    for p in patterns_male:
        matches = re.findall(p, text_lower)
        male_score += len(matches)
    
    if female_score > male_score:
        return 'female'
    elif male_score > female_score:
        return 'male'
    return None

def extract_weight(text):
    # Look for weight in kg
    patterns = [
        r'weigh(?:ed|s|ing)?\s+(\d+\.?\d*)\s*kg',
        r'weight\s*(?:was|is|of|:)?\s*(\d+\.?\d*)\s*kg',
        r'body\s*weight\s*(?:was|is|of|:)?\s*(\d+\.?\d*)\s*kg',
        r'(\d+\.?\d*)\s*kg\s*(?:\(|in\s+weight)',
        r'weight[:\s]+(\d+\.?\d*)\s*kg',
        r'(\d+\.?\d*)\s*kg\b',
    ]
    
    # Also check for lbs conversion
    patterns_lb = [
        r'weigh(?:ed|s|ing)?\s+(\d+\.?\d*)\s*(?:lb|lbs|pounds)',
        r'(\d+\.?\d*)\s*(?:lb|lbs)\b',
    ]
    
    for p in patterns:
        matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            val = float(m)
            if 20 <= val <= 300:
                return val
    
    for p in patterns_lb:
        matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            val = float(m) * 0.453592
            if 20 <= val <= 300:
                return val
    
    return None

def extract_height(text):
    # Height in cm
    patterns_cm = [
        r'height\s*(?:was|is|of|:)?\s*(\d+\.?\d*)\s*cm',
        r'(\d+\.?\d*)\s*cm\s*(?:tall|in\s*height)',
        r'(?:was|is)\s+(\d+\.?\d*)\s*cm\s*tall',
        r'(\d+\.?\d*)\s*cm\s*(?:\(|\,)',
        r'height[:\s]+(\d+\.?\d*)\s*cm',
    ]
    
    for p in patterns_cm:
        matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            val = float(m)
            if 50 <= val <= 250:
                return val
    
    # Try general cm pattern
    cm_matches = re.findall(r'(\d+\.?\d*)\s*cm\b', text)
    for m in cm_matches:
        val = float(m)
        if 100 <= val <= 250:
            return val
    
    # Height in feet and inches
    patterns_ft = [
        r'(\d+)\s*ft\s*(\d+\.?\d*)\s*in',
        r"(\d+)\s*'\s*(\d+\.?\d*)\s*\"",
        r'(\d+)\s*feet?\s*(\d+\.?\d*)\s*inch',
    ]
    for p in patterns_ft:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            feet = int(m.group(1))
            inches = float(m.group(2))
            total_inches = feet * 12 + inches
            return total_inches * 2.54
    
    # Height in meters
    patterns_m = [
        r'height\s*(?:was|is|of|:)?\s*(\d+\.?\d*)\s*m\b',
        r'(\d+\.?\d*)\s*m\s*(?:tall|in\s*height)',
        r'(?:was|is)\s+(\d+\.?\d*)\s*m\s*tall',
    ]
    for p in patterns_m:
        matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            val = float(m)
            if 1.0 <= val <= 2.5:
                return val * 100
    
    # Try pattern like "1.75 m"
    m_matches = re.findall(r'(\d+\.\d+)\s*m\b', text)
    for m in m_matches:
        val = float(m)
        if 1.0 <= val <= 2.5:
            return val * 100
    
    # ft in pattern with parentheses like "180 cm (5 ft 11 in)"
    # Already covered by cm patterns
    
    # Try inches pattern
    inch_patterns = [
        r'(\d+)\s*inches?\b',
        r'height\s*(?:was|is|of|:)?\s*(\d+)\s*inches?',
    ]
    for p in inch_patterns:
        matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            val = int(m)
            if 48 <= val <= 84:
                return val * 2.54
    
    return None

def extract_creatinine(text):
    """Extract serum creatinine in mg/dL"""
    # First try to find creatinine specifically labeled as serum/blood creatinine
    # Patterns for mg/dL
    patterns_mgdl = [
        r'(?:serum\s+)?creatinine\s*(?:was|is|of|:)?\s*(\d+\.?\d*)\s*mg/d[Ll]',
        r'(?:serum\s+)?creatinine[,\s]+(\d+\.?\d*)\s*mg/d[Ll]',
        r'[Cc]r(?:eatinine)?\s*(?:was|is|of|:|=)\s*(\d+\.?\d*)\s*mg/d[Ll]',
        r'[Cc]r\s*(?:was|is|of|:|=)\s*(\d+\.?\d*)\b',
        r'creatinine\s*(?:was|is|of|:)?\s*(\d+\.?\d*)\s*mg/d[Ll]',
        r'creatinine[:\s]+(\d+\.?\d*)\s*mg/d[Ll]',
        r'creatinine\s+(\d+\.?\d*)\s*mg/d[Ll]',
    ]
    
    # Patterns for µmol/L (need conversion: divide by 88.4)
    patterns_umol = [
        r'(?:serum\s+)?creatinine\s*(?:was|is|of|:)?\s*(\d+\.?\d*)\s*(?:μmol/L|µmol/L|umol/L|mmol/L)',
        r'[Cc]r(?:eatinine)?\s*(?:was|is|of|:|=)\s*(\d+\.?\d*)\s*(?:μmol/L|µmol/L|umol/L|mmol/L)',
        r'creatinine[,\s]+(\d+\.?\d*)\s*(?:μmol/L|µmol/L|umol/L|mmol/L)',
    ]
    
    # Try mg/dL first
    for p in patterns_mgdl:
        matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            val = float(m)
            if 0.1 <= val <= 30:
                return val
    
    # Try µmol/L
    for p in patterns_umol:
        matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            val = float(m)
            # mmol/L vs µmol/L
            # Check which unit
            full_match = re.search(p, text, re.IGNORECASE)
            if full_match:
                match_text = full_match.group(0)
                if 'mmol' in match_text.lower():
                    # mmol/L - this is unusual for creatinine, likely µmol/L mislabeled
                    # or actually mmol/L (very high). Check context
                    if val < 1:
                        # Likely mmol/L, convert: 1 mmol/L = 113.12 µmol/L
                        val_umol = val * 1000  # convert to µmol/L
                        return val_umol / 88.4
                    else:
                        # Treat as mmol/L for creatinine
                        # Actually in some contexts creatinine in mmol/L 
                        # e.g., 78 mmol/L probably means µmol/L
                        if val > 10:
                            return val / 88.4
                        else:
                            return val * 1000 / 88.4
                else:
                    # µmol/L
                    return val / 88.4
    
    # Try broader patterns
    broader = [
        r'[Cc]reatinine\s*(?:level\s*)?(?:was|is|of|:|=)?\s*(\d+\.?\d*)',
        r'Cr\s*(?:was|is|of|:|=|,)\s*(\d+\.?\d*)',
    ]
    
    for p in broader:
        matches = list(re.finditer(p, text))
        for match in matches:
            val = float(match.group(1))
            # Check what unit follows
            after = text[match.end():match.end()+30]
            if re.match(r'\s*mg/d[Ll]', after):
                if 0.1 <= val <= 30:
                    return val
            elif re.match(r'\s*(?:μmol|µmol|umol)/[Ll]', after):
                return val / 88.4
            elif re.match(r'\s*mmol/[Ll]', after):
                if val > 10:
                    return val / 88.4
                else:
                    return val * 1000 / 88.4
            elif 0.1 <= val <= 30:
                # Guess mg/dL
                return val
    
    return None

def solve(params):
    age = params['age']
    sex = params['sex']
    weight_kg = params['weight_kg']
    height_cm = params['height_cm']
    creatinine = params['creatinine']
    
    if creatinine <= 0:
        return None
    
    # Calculate BMI
    height_m = height_cm / 100.0
    bmi = weight_kg / (height_m ** 2)
    
    # Calculate IBW (Devine formula)
    height_inches = height_cm / 2.54
    
    if sex == 'male':
        ibw = 50 + 2.3 * (height_inches - 60)
    else:
        ibw = 45.5 + 2.3 * (height_inches - 60)
    
    # Determine adjusted body weight
    if bmi < 18.5:
        # Underweight: use actual weight
        adj_weight = weight_kg
    elif bmi < 25:
        # Normal: use min(IBW, actual weight)
        adj_weight = min(ibw, weight_kg)
    else:
        # Overweight/Obese: use adjusted body weight
        adj_weight = ibw + 0.4 * (weight_kg - ibw)
    
    # Cockcroft-Gault equation
    crcl = ((140 - age) * adj_weight) / (72 * creatinine)
    
    if sex == 'female':
        crcl *= 0.85
    
    return crcl

def format_output(result):
    return round(result, 5)
