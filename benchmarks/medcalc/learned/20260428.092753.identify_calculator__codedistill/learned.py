"""Auto-generated code-distilled implementation for identify_calculator."""

import re


def identify_calculator(question: str, calculator_list: list) -> dict:
    """
    Identifies which medical calculator is being referenced in a question
    by matching the question text against a list of available calculators.
    
    Returns a dict with calculator_name, confidence, and reasoning.
    """
    question_lower = question.lower().strip()
    
    # Define keyword mappings for calculators that might not be mentioned by exact name
    keyword_mappings = {
        'Body Mass Index (BMI)': ['body mass index', 'bmi', 'body mass mass index'],
        'Mean Arterial Pressure (MAP)': ['mean arterial pressure', 'map'],
        'Ideal Body Weight (Devine)': ['ideal body weight'],
        'Adjusted Body Weight': ['adjusted body weight'],
        'Body Surface Area (Mosteller)': ['body surface area'],
        'Target Weight': ['target weight'],
        'Maintenance Fluids (4-2-1 Rule)': ['maintenance fluid', 'maintenance fluids', '4-2-1 rule'],
        'Creatinine Clearance (Cockcroft-Gault)': ['creatinine clearance', 'cockcroft-gault', 'cockcroft gault'],
        'CKD-EPI GFR (2021)': ['ckd-epi', 'ckd epi', '2021 ckd-epi'],
        'MDRD GFR': ['mdrd gfr', 'mdrd'],
        'Anion Gap': ['anion gap'],
        'Delta Gap': ['delta gap'],
        'Delta Ratio': ['delta ratio'],
        'Albumin Corrected Anion Gap': ['albumin corrected anion gap'],
        'Serum Osmolality': ['serum osmolality'],
        'Free Water Deficit': ['free water deficit'],
        'Sodium Correction for Hyperglycemia': ['sodium correction', 'corrected sodium'],
        'Calcium Correction for Hypoalbuminemia': ['calcium correction', 'corrected calcium'],
        'LDL Calculated (Friedewald)': ['ldl', 'friedewald'],
        'SIRS Criteria': ['sirs criteria', 'sirs critiera', 'sirs'],
        'APACHE II Score': ['apache ii', 'apache 2'],
        'CHA2DS2-VASc Score': ['cha2ds2-vasc', 'cha2ds2 vasc', 'chads2-vasc', 'chads vasc'],
        'HAS-BLED Score': ['has-bled', 'has bled'],
        'Glasgow Coma Scale (GCS)': ['glasgow coma', 'gcs'],
        'Wells Criteria for Pulmonary Embolism': ['wells criteria', 'wells score', 'pulmonary embolism'],
        'CURB-65 Score': ['curb-65', 'curb 65'],
        'Child-Pugh Score': ['child-pugh', 'child pugh'],
        'MELD Score': ['meld score', 'meld na'],
        'Charlson Comorbidity Index': ['charlson comorbidity', 'charlson'],
        'Sequential Organ Failure Assessment (SOFA) Score': ['sofa score', 'sofa', 'sequential organ failure'],
        'Caprini Score': ['caprini'],
        'HEART Score': ['heart score'],
        'Framingham Risk Score': ['framingham'],
        'Revised Cardiac Risk Index': ['revised cardiac risk', 'rcri', 'lee index'],
        'PSI/PORT Score': ['psi/port', 'psi port', 'pneumonia severity'],
        'HOMA-IR': ['homa-ir', 'homa ir'],
        'Fibrosis-4 (FIB-4)': ['fib-4', 'fib 4', 'fibrosis-4', 'fibrosis 4'],
        'Corrected QT Interval (QTc)': ['corrected qt', 'qtc'],
        'National Institutes of Health Stroke Scale (NIHSS)': ['nihss', 'nih stroke scale'],
        'Centor Score': ['centor'],
        'Padua Prediction Score': ['padua'],
        'PERC Rule': ['perc rule', 'perc'],
    }
    
    # First, try exact name match in the question (case-insensitive)
    best_match = None
    best_match_len = 0
    
    for calc_name in calculator_list:
        calc_lower = calc_name.lower()
        if calc_lower in question_lower:
            if len(calc_lower) > best_match_len:
                best_match = calc_name
                best_match_len = len(calc_lower)
    
    if best_match:
        return {
            'calculator_name': best_match,
            'confidence': 0.99,
            'reasoning': f'Question explicitly mentions the calculator by name and describes its specific use case'
        }
    
    # Try keyword mappings
    best_match = None
    best_confidence = 0
    best_reasoning = ''
    best_keyword_len = 0
    
    for calc_name, keywords in keyword_mappings.items():
        # Only consider calculators that are in the provided list
        if calc_name not in calculator_list:
            continue
        for keyword in keywords:
            if keyword in question_lower:
                # Longer keyword matches get priority
                if len(keyword) > best_keyword_len:
                    best_keyword_len = len(keyword)
                    best_match = calc_name
                    best_confidence = 0.95
                    best_reasoning = f'Question mentions "{keyword}" which matches {calc_name}'
    
    if best_match:
        return {
            'calculator_name': best_match,
            'confidence': best_confidence,
            'reasoning': best_reasoning
        }
    
    # Try matching parts of calculator names against the question
    best_match = None
    best_match_score = 0
    
    for calc_name in calculator_list:
        # Extract meaningful words from the calculator name
        # Remove parenthetical parts for matching
        clean_name = re.sub(r'\([^)]*\)', '', calc_name).strip()
        name_words = [w.lower() for w in clean_name.split() if len(w) > 2]
        
        if not name_words:
            # Try the full name lowered
            if calc_name.lower() in question_lower:
                return {
                    'calculator_name': calc_name,
                    'confidence': 0.95,
                    'reasoning': f'Direct match found for {calc_name}'
                }
            continue
        
        # Count how many significant words from the calculator name appear in the question
        matches = sum(1 for w in name_words if w in question_lower)
        score = matches / len(name_words) if name_words else 0
        
        # Also check parenthetical content
        paren_match = re.search(r'\(([^)]*)\)', calc_name)
        if paren_match:
            paren_content = paren_match.group(1).lower()
            if paren_content in question_lower:
                score += 0.5
        
        if score > best_match_score:
            best_match_score = score
            best_match = calc_name
    
    if best_match and best_match_score >= 0.5:
        confidence = min(0.95, 0.5 + best_match_score * 0.4)
        return {
            'calculator_name': best_match,
            'confidence': round(confidence, 2),
            'reasoning': f'Question matches keywords associated with {best_match}'
        }
    
    # Last resort: try fuzzy-ish matching on significant terms
    for calc_name in calculator_list:
        # Try matching without spaces and special chars
        calc_simplified = re.sub(r'[^a-z0-9]', '', calc_name.lower())
        question_simplified = re.sub(r'[^a-z0-9]', '', question_lower)
        if calc_simplified in question_simplified:
            return {
                'calculator_name': calc_name,
                'confidence': 0.85,
                'reasoning': f'Fuzzy match found for {calc_name}'
            }
    
    if best_match:
        return {
            'calculator_name': best_match,
            'confidence': 0.5,
            'reasoning': f'Best partial match found: {best_match}'
        }
    
    return None
