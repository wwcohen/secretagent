"""Auto-generated code-distilled implementation for identify_calculator."""

import re


def identify_calculator(question, calculator_list):
    question_lower = question.lower()
    
    # Direct keyword mapping: question keywords -> calculator name
    # Order matters - more specific patterns should come first
    keyword_mappings = [
        # QTc formulas - very specific
        (r'hodges\s*(formula|equation|method)', 'QTc (Hodges)', 0.99, 'Question specifically mentions Hodges Formula for corrected QT interval'),
        (r'framingham\s*(formula|equation|method).*q\s*t', 'QTc (Framingham)', 0.99, 'Question directly references the Framingham formula for QT correction'),
        (r'q\s*t.*framingham\s*(formula|equation|method)', 'QTc (Framingham)', 0.99, 'Question directly references the Framingham formula for QT correction'),
        (r'fridericia\s*(formula|equation|method)', 'QTc (Fridericia)', 0.99, 'Question specifically mentions Fridericia Formula for corrected QT interval'),
        (r'bazett\s*(formula|equation|method)', 'QTc (Bazett)', 0.95, 'Question specifically mentions Bazett Formula for corrected QT interval'),
        (r'rautaharju\s*(formula|equation|method)', 'QTc (Rautaharju)', 0.99, 'Question specifically mentions Rautaharju Formula for corrected QT interval'),
        
        # GFR equations - specific
        (r'2021\s*ckd[\s-]*epi', 'CKD-EPI GFR (2021)', 0.98, 'Question specifically mentions 2021 CKD-EPI Creatinine equation for calculating GFR'),
        (r'ckd[\s-]*epi.*2021', 'CKD-EPI GFR (2021)', 0.98, 'Question specifically mentions 2021 CKD-EPI Creatinine equation for calculating GFR'),
        (r'mdrd\s*gfr', 'MDRD GFR', 0.95, 'Question explicitly mentions "MDRD GFR Equation" and requests calculation of Glomerular Filtration Rate'),
        (r'mdrd.*glomerular', 'MDRD GFR', 0.95, 'Question explicitly mentions "MDRD GFR Equation" and requests calculation of Glomerular Filtration Rate'),
        (r'cockcroft[\s-]*gault', 'Creatinine Clearance (Cockcroft-Gault)', 0.95, 'Question mentions Cockcroft-Gault equation for creatinine clearance'),
        
        # Sodium/electrolyte corrections
        (r'sodium\s*correct.*hyperglycemia', 'Sodium Correction for Hyperglycemia', 0.99, 'Question specifically asks for sodium correction for hyperglycemia using the sodium correction equation'),
        (r'corrected\s*sodium.*hyperglycemia', 'Sodium Correction for Hyperglycemia', 0.99, 'Question specifically asks for sodium correction for hyperglycemia using the sodium correction equation'),
        (r'calcium\s*correct.*hypoalbuminemia', 'Calcium Correction for Hypoalbuminemia', 0.95, 'Question asks for calcium correction for hypoalbuminemia'),
        (r'corrected\s*calcium.*hypoalbuminemia', 'Calcium Correction for Hypoalbuminemia', 0.95, 'Question asks for calcium correction for hypoalbuminemia'),
        
        # Specific scores and criteria - with word boundaries
        (r'perc\s*rule', 'PERC Rule', 0.95, 'Question specifically asks about criteria met for the PERC Rule for Pulmonary Embolism'),
        (r"wells.*deep\s*vein\s*thrombosis|wells.*\bdvt\b", "Wells' Criteria for DVT", 0.95, "Question directly references Wells' criteria for Deep Vein Thrombosis"),
        (r"wells.*pulmonary\s*embolism|wells.*\bpe\b", "Wells' Criteria for PE", 0.95, "Question directly references Wells' criteria for Pulmonary Embolism"),
        (r'cha2ds2[\s-]*vasc', 'CHA2DS2-VASc Score', 1.0, 'Question directly asks for CHA2DS2-VASc Score'),
        (r'sirs\s*criteri', 'SIRS Criteria', 0.95, 'Question directly asks for SIRS criteria and matches available calculator name'),
        (r'child[\s-]*pugh', 'Child-Pugh Score', 0.99, 'Question directly asks for Child-Pugh Score'),
        (r'meld[\s-]*na', 'MELD-Na Score', 0.95, 'Question explicitly asks for MELD Na score, which directly matches the available calculator name.'),
        (r'\bsofa\s*score', 'SOFA Score', 0.95, 'Question asks for SOFA Score'),
        (r'\bheart\s*score', 'HEART Score', 0.95, 'Question asks for HEART Score'),
        (r'revised\s*cardiac\s*risk\s*index|rcri', 'Revised Cardiac Risk Index (RCRI)', 0.98, 'Question explicitly mentions "Revised Cardiac Risk Index" which matches exactly with available calculator'),
        (r'curb[\s-]*65', 'CURB-65 Score', 0.95, 'Question asks for CURB-65 Score'),
        (r'psi[\s/]*port', 'PSI/PORT Score', 0.95, 'Question asks for PSI/PORT Score'),
        (r'centor\s*score|mcisaac', 'Centor Score (McIsaac)', 0.95, 'Question asks for Centor Score'),
        (r'feverpain', 'FeverPAIN Score', 0.95, 'Question asks for FeverPAIN Score'),
        (r'glasgow[\s-]*blatchford|gbs\s*score', 'Glasgow-Blatchford Score (GBS)', 0.95, 'Question asks for Glasgow-Blatchford Score'),
        (r'has[\s-]*bled', 'HAS-BLED Score', 0.95, 'Question asks for HAS-BLED Score'),
        (r'caprini', 'Caprini VTE Score', 0.95, 'Question asks for Caprini VTE Score'),
        (r'morphine\s*milligram\s*equiv|mme', 'Morphine Milligram Equivalents (MME)', 0.95, 'Question asks for Morphine Milligram Equivalents'),
        (r'apache\s*ii', 'APACHE II Score', 0.95, 'Question asks for APACHE II Score'),
        (r'charlson\s*comorbidity|cci', 'Charlson Comorbidity Index (CCI)', 0.95, 'Question asks for Charlson Comorbidity Index'),
        (r'fib[\s-]*4', 'FIB-4 Index', 0.95, 'Question asks for FIB-4 Index'),
        (r'glasgow\s*coma\s*scale|gcs', 'Glasgow Coma Scale (GCS)', 0.95, 'Question asks for Glasgow Coma Scale'),
        (r'homa[\s-]*ir', 'HOMA-IR', 0.95, 'Question asks for HOMA-IR calculation'),
        (r'framingham\s*risk\s*score', 'Framingham Risk Score', 0.95, 'Question asks for Framingham Risk Score'),
        (r'steroid\s*conversion', 'Steroid Conversion', 0.95, 'Question asks for Steroid Conversion'),
        (r'gestational\s*age', 'Gestational Age', 0.95, 'Question asks for Gestational Age'),
        (r'estimated\s*due\s*date', 'Estimated Due Date', 0.95, 'Question asks for Estimated Due Date'),
        (r'date\s*of\s*conception', 'Date of Conception', 0.95, 'Question asks for Date of Conception'),
        
        # Body measurements
        (r'adjusted\s*body\s*weight', 'Adjusted Body Weight', 0.95, 'Question asks for adjusted body weight calculation'),
        (r'ideal\s*body\s*weight', 'Ideal Body Weight (Devine)', 0.95, 'Question explicitly mentions "Ideal Body Weight Formula" and asks for ideal body weight in kg'),
        (r'target\s*weight', 'Target Weight', 0.85, 'Question specifically asks for target weight calculation based on height and target BMI'),
        (r'body\s*surface\s*area', 'Body Surface Area (Mosteller)', 0.95, 'Question specifically asks for body surface area calculation'),
        (r'body\s*mass\s*(mass\s*)?index|bmi', 'Body Mass Index (BMI)', 0.95, 'Question explicitly mentions "body mass mass index (BMI)" and references kg/m² units, which directly matches the BMI calculator'),
        
        # Fluid/electrolyte calculations
        (r'free\s*water\s*deficit', 'Free Water Deficit', 0.95, 'Question specifically asks for free water deficit calculation'),
        (r'maintenance\s*fluid', 'Maintenance Fluids (4-2-1 Rule)', 0.95, 'Question directly asks about maintenance fluid calculation using standard clinical parameters'),
        (r'serum\s*osmolality', 'Serum Osmolality', 0.95, 'Question directly asks for serum osmolality calculation and provides relevant clinical parameters'),
        
        # Gaps and ratios
        (r'albumin\s*correct.*anion\s*gap', 'Albumin Corrected Anion Gap', 0.95, 'Question asks for albumin corrected anion gap'),
        (r'delta\s*ratio', 'Delta Ratio', 0.95, 'Question specifically mentions delta ratio calculation'),
        (r'delta\s*gap', 'Delta Gap', 0.95, 'Question directly mentions delta gap calculation'),
        (r'anion\s*gap', 'Anion Gap', 0.95, 'Question asks for anion gap calculation'),
        
        # Other
        (r'mean\s*arterial\s*pressure', 'Mean Arterial Pressure (MAP)', 0.95, 'Question directly asks for mean arterial pressure and specifies units (mm Hg)'),
        (r'fractional\s*excretion\s*of\s*sodium|fena', 'Fractional Excretion of Sodium (FENa)', 0.99, 'FENa directly asked'),
        (r'ldl\s*(cholest|calc)', 'LDL Calculated (Friedewald)', 0.99, 'The question directly asks for LDL cholesterol concentration in mg/dL, which is calculated using the Friedewald formula.'),
        (r'creatinine\s*clearance', 'Creatinine Clearance (Cockcroft-Gault)', 0.95, 'Question asks for creatinine clearance calculation'),
    ]
    
    # Try each pattern
    for pattern, calc_name, confidence, reasoning in keyword_mappings:
        if re.search(pattern, question_lower):
            # Verify the calculator exists in the list
            if calc_name in calculator_list:
                return {
                    'calculator_name': calc_name,
                    'confidence': confidence,
                    'reasoning': reasoning
                }
    
    # Fallback: try to find best match by comparing question words with calculator names
    question_words = set(re.findall(r'[a-z0-9]+', question_lower))
    # Remove common words
    stop_words = {'what', 'is', 'the', 'patient', 'patients', 'in', 'terms', 'of', 'you', 
                  'should', 'use', 'medical', 'values', 'and', 'health', 'status', 'when',
                  'they', 'were', 'first', 'admitted', 'to', 'hospital', 'prior', 'any',
                  'treatment', 'please', 'output', 'your', 'answer', 'based', 'on', 'using',
                  'a', 'for', 'how', 'many', 'are', 'does', 'do', 'has', 'have', 'that',
                  'this', 'with', 'from', 'by', 'an', 'be', 'it', 'at', 'or', 'if', 'as',
                  'may', 'take', 'mg', 'dl', 'ml', 'kg', 'hr', 'mm', 'hg', 'meq', 'l',
                  'msec', 'min', 'm2', 's', 'number', 'criteria', 'met', 'score', 'formula',
                  'equation', 'rule', 'index', 'what', 'calculate', 'calculation'}
    
    question_words -= stop_words
    
    best_match = None
    best_score = 0
    
    for calc_name in calculator_list:
        calc_lower = calc_name.lower()
        calc_words = set(re.findall(r'[a-z0-9]+', calc_lower))
        calc_words -= stop_words
        
        if not calc_words:
            continue
            
        # Check if calculator name (without parenthetical) appears in question
        # Strip parenthetical content for matching
        base_name = re.sub(r'\s*\(.*?\)\s*', ' ', calc_lower).strip()
        base_name_clean = re.sub(r'[^a-z0-9\s]', '', base_name)
        
        # Direct substring match of base name in question
        if base_name_clean and base_name_clean in question_lower:
            score = len(base_name_clean) * 3
            if score > best_score:
                best_score = score
                best_match = calc_name
                continue
        
        # Word overlap score
        overlap = question_words & calc_words
        if overlap:
            score = len(overlap) / len(calc_words)
            if score > best_score:
                best_score = score
                best_match = calc_name
    
    if best_match and best_score > 0:
        confidence = min(0.95, 0.5 + best_score * 0.15) if best_score < 3 else 0.95
        return {
            'calculator_name': best_match,
            'confidence': confidence,
            'reasoning': f'Best match found based on keyword overlap with question'
        }
    
    return None
