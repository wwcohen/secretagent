"""Auto-generated code-distilled implementation for identify_calculator."""

import re


def identify_calculator(question: str, calculator_list: list) -> dict:
    """Identify which medical calculator a question is asking about."""
    
    question_lower = question.lower().strip()
    
    # Define keyword mappings for calculators that might not be directly named in the question
    keyword_mappings = {
        'body mass index': 'Body Mass Index (BMI)',
        'body mass mass index': 'Body Mass Index (BMI)',
        'bmi': 'Body Mass Index (BMI)',
        'mean arterial pressure': 'Mean Arterial Pressure (MAP)',
        'ideal body weight': 'Ideal Body Weight (Devine)',
        'adjusted body weight': 'Adjusted Body Weight',
        'body surface area': 'Body Surface Area (Mosteller)',
        'target weight': 'Target Weight',
        'maintenance fluid': 'Maintenance Fluids (4-2-1 Rule)',
        'maintenance fluids': 'Maintenance Fluids (4-2-1 Rule)',
        'creatinine clearance': 'Creatinine Clearance (Cockcroft-Gault)',
        'cockcroft-gault': 'Creatinine Clearance (Cockcroft-Gault)',
        'cockcroft gault': 'Creatinine Clearance (Cockcroft-Gault)',
        'ckd-epi': 'CKD-EPI GFR (2021)',
        'ckd epi': 'CKD-EPI GFR (2021)',
        'mdrd': 'MDRD GFR',
        'anion gap': 'Anion Gap',
        'albumin corrected anion gap': 'Albumin Corrected Anion Gap',
        'delta ratio': 'Delta Ratio',
        'delta gap': 'Delta Gap',
        'serum osmolality': 'Serum Osmolality',
        'free water deficit': 'Free Water Deficit',
        'sodium correction for hyperglycemia': 'Sodium Correction for Hyperglycemia',
        'sodium correction': 'Sodium Correction for Hyperglycemia',
        'calcium correction for hypoalbuminemia': 'Calcium Correction for Hypoalbuminemia',
        'calcium correction': 'Calcium Correction for Hypoalbuminemia',
        'corrected calcium': 'Calcium Correction for Hypoalbuminemia',
        'ldl calculated': 'LDL Calculated (Friedewald)',
        'friedewald': 'LDL Calculated (Friedewald)',
        'fractional excretion of sodium': 'Fractional Excretion of Sodium (FENa)',
        'fena': 'Fractional Excretion of Sodium (FENa)',
        'steroid conversion': 'Steroid Conversion',
        'equivalent dos': 'Steroid Conversion',
        'cha2ds2-vasc': 'CHA2DS2-VASc Score',
        'cha2ds2 vasc': 'CHA2DS2-VASc Score',
        'chadsvasc': 'CHA2DS2-VASc Score',
        'corrected qt': 'QTc (Bazett)',
        'bazett': 'QTc (Bazett)',
        'qtc': 'QTc (Bazett)',
        'homa-ir': 'HOMA-IR',
        'homa ir': 'HOMA-IR',
        'glasgow coma': 'Glasgow Coma Scale (GCS)',
        'gcs': 'Glasgow Coma Scale (GCS)',
        'apache ii': 'APACHE II',
        'child-pugh': 'Child-Pugh Score',
        'child pugh': 'Child-Pugh Score',
        'meld': 'MELD Score',
        'wells score': 'Wells Score',
        'framingham': 'Framingham Risk Score',
        'caprini': 'Caprini Score',
        'has-bled': 'HAS-BLED Score',
        'curb-65': 'CURB-65 Score',
        'sofa score': 'SOFA Score',
        'sequential organ failure': 'SOFA Score',
        'fibrosis index': 'Fibrosis-4 (FIB-4) Index',
        'fib-4': 'Fibrosis-4 (FIB-4) Index',
        'fib4': 'Fibrosis-4 (FIB-4) Index',
        'charlson comorbidity': 'Charlson Comorbidity Index (CCI)',
        'cci': 'Charlson Comorbidity Index (CCI)',
        'centor': 'Centor Score',
        'pecarn': 'PECARN Pediatric Head Injury',
        'parkland': 'Parkland Formula',
        'winter\'s formula': "Winter's Formula",
        'winters formula': "Winter's Formula",
        'expected pco2': "Winter's Formula",
        'corrected sodium': 'Sodium Correction for Hyperglycemia',
        'a-a gradient': 'A-a Gradient',
        'a-a o2 gradient': 'A-a Gradient',
        'alveolar-arterial': 'A-a Gradient',
    }
    
    # First, try direct matching against calculator list names (case-insensitive)
    # Sort by length descending to match longest/most specific first
    sorted_calculators = sorted(calculator_list, key=lambda x: len(x), reverse=True)
    
    for calc_name in sorted_calculators:
        calc_lower = calc_name.lower()
        # Check if the calculator name (without parenthetical) appears in the question
        # Extract base name and parenthetical
        base_match = re.match(r'^(.*?)(?:\s*\(.*\))?\s*$', calc_name)
        base_name = base_match.group(1).strip().lower() if base_match else calc_lower
        
        if calc_lower in question_lower:
            return {
                'calculator_name': calc_name,
                'confidence': 1.0,
                'reasoning': f'Question directly asks for {calc_name}'
            }
    
    # Check keyword mappings (sorted by key length descending for longest match first)
    sorted_keywords = sorted(keyword_mappings.keys(), key=len, reverse=True)
    
    for keyword in sorted_keywords:
        if keyword in question_lower:
            calc_name = keyword_mappings[keyword]
            # Verify it's in the calculator list
            if calc_name in calculator_list:
                return {
                    'calculator_name': calc_name,
                    'confidence': 0.95,
                    'reasoning': f'Question mentions "{keyword}" which matches {calc_name}'
                }
            # Try partial match on calculator list
            for cl in calculator_list:
                if calc_name.lower() in cl.lower() or cl.lower() in calc_name.lower():
                    return {
                        'calculator_name': cl,
                        'confidence': 0.95,
                        'reasoning': f'Question mentions "{keyword}" which matches {cl}'
                    }
    
    # Check for steroid conversion keywords
    steroid_keywords = ['dexamethasone', 'prednisolone', 'prednisone', 'methylprednisolone', 
                       'hydrocortisone', 'cortisone', 'betamethasone', 'triamcinolone',
                       'equivalent dos', 'steroid conver']
    for sk in steroid_keywords:
        if sk.lower() in question_lower and 'equivalent' in question_lower:
            for cl in calculator_list:
                if 'steroid' in cl.lower() or 'conversion' in cl.lower():
                    return {
                        'calculator_name': cl,
                        'confidence': 0.95,
                        'reasoning': f'Question asks for conversion between steroid medications'
                    }
    
    # Try matching base names from calculator list against question
    for calc_name in sorted_calculators:
        # Remove parenthetical
        base = re.sub(r'\s*\(.*?\)', '', calc_name).strip().lower()
        if len(base) > 3 and base in question_lower:
            return {
                'calculator_name': calc_name,
                'confidence': 0.95,
                'reasoning': f'Question directly mentions {base} calculation'
            }
    
    # Try matching abbreviations in parentheses
    for calc_name in sorted_calculators:
        paren_match = re.search(r'\(([^)]+)\)', calc_name)
        if paren_match:
            abbrev = paren_match.group(1).strip().lower()
            if len(abbrev) >= 2 and re.search(r'\b' + re.escape(abbrev) + r'\b', question_lower):
                return {
                    'calculator_name': calc_name,
                    'confidence': 0.95,
                    'reasoning': f'Question references {abbrev.upper()} which matches {calc_name}'
                }
    
    return None
