"""Auto-generated code-distilled implementation for identify_calculator."""

import re

def identify_calculator(question, calculator_list):
    question_lower = question.lower()
    
    # Build keyword mappings for matching and specific reasoning/confidence
    keyword_map = {
        'Body Mass Index (BMI)': ({'bmi', 'body mass index'}, 0.99, 'Question explicitly asks for BMI'),
        'Mean Arterial Pressure (MAP)': ({'mean arterial pressure'}, 0.99, 'Question asks for mean arterial pressure'),
        'Ideal Body Weight (Devine)': ({'ideal body weight'}, 0.99, 'Question explicitly asks for Ideal Body Weight'),
        'Adjusted Body Weight': ({'adjusted body weight'}, 1.0, 'Question explicitly asks for adjusted body weight'),
        'Body Surface Area (Mosteller)': ({'body surface area'}, 0.99, 'Question asks for body surface area'),
        'Target Weight': ({'target weight'}, 0.99, 'Question asks for target weight'),
        'Maintenance Fluids (4-2-1 Rule)': ({'maintenance fluid'}, 0.99, 'Question explicitly asks for maintenance fluid in mL/hr'),
        'Creatinine Clearance (Cockcroft-Gault)': ({'creatinine clearance', 'cockcroft-gault', 'cockcroft gault'}, 0.99, 'Question explicitly asks for Creatinine Clearance (Cockcroft-Gault)'),
        'CKD-EPI GFR (2021)': ({'ckd-epi', 'ckd epi', '2021 ckd'}, 0.99, 'Question explicitly asks for 2021 CKD-EPI GFR'),
        'MDRD GFR': ({'mdrd'}, 0.99, 'Question explicitly asks for MDRD GFR Equation'),
        'Anion Gap': ({'anion gap'}, 0.99, 'Question explicitly asks for anion gap'),
        'Delta Gap': ({'delta gap'}, 1.0, 'Question explicitly requests the delta gap'),
        'Delta Ratio': ({'delta ratio'}, 0.99, 'Question explicitly asks for delta ratio'),
        'Albumin Corrected Anion Gap': ({'albumin corrected anion gap'}, 0.99, 'Question explicitly asks for Albumin Corrected Anion Gap'),
        'Serum Osmolality': ({'serum osmolality'}, 0.99, 'Question asks for serum osmolality'),
        'Free Water Deficit': ({'free water deficit'}, 0.99, 'Question explicitly asks for free water deficit'),
        'Sodium Correction for Hyperglycemia': ({'sodium correction'}, 0.99, 'Question explicitly asks for Sodium Correction for Hyperglycemia'),
        'Calcium Correction for Hypoalbuminemia': ({'calcium correction for hypoalbuminemia', 'corrected calcium'}, 1.0, 'Question explicitly requests Calcium Correction for Hypoalbuminemia'),
        'LDL Calculated (Friedewald)': ({'ldl'}, 0.99, 'Question explicitly asks for LDL cholesterol.'),
        'Fractional Excretion of Sodium (FENa)': ({'fractional excretion of sodium', 'fena'}, 0.99, 'FENa directly asked'),
        'QTc (Bazett)': ({'bazett'}, 0.99, 'Question explicitly requests Bazett formula for corrected QT interval'),
        'QTc (Fridericia)': ({'fridericia'}, 0.99, 'Question explicitly asks for Fridericia QTc'),
        'QTc (Framingham)': ({'framingham'}, 0.99, 'Question explicitly asks for Framingham QTc'),
        'QTc (Hodges)': ({'hodges'}, 0.99, 'Question explicitly asks for Hodges QTc'),
        'QTc (Rautaharju)': ({'rautaharju'}, 0.99, 'Question explicitly asks for Rautaharju QTc'),
        'CHA2DS2-VASc Score': ({'cha2ds2-vasc', 'cha2ds2'}, 1.0, 'CHA2DS2-VASc Score directly asked'),
        'HEART Score': ({'heart score'}, 0.99, 'Question asks for HEART Score'),
        'Revised Cardiac Risk Index (RCRI)': ({'revised cardiac risk index', 'rcri'}, 0.99, 'Question asks for RCRI'),
        "Wells' Criteria for PE": ({"wells' criteria for pe", 'wells criteria for pe', 'wells.*pe'}, 0.99, "Question asks for Wells' Criteria for PE"),
        'FIB-4 Index': ({'fib-4', 'fib 4'}, 0.99, 'Question asks for FIB-4 Index'),
        'MELD-Na Score': ({'meld-na', 'meld na'}, 0.99, 'Question asks for MELD-Na Score'),
        'Child-Pugh Score': ({'child-pugh', 'child pugh'}, 0.99, 'Question asks for Child-Pugh Score'),
        'Steroid Conversion': ({'steroid', 'equivalent dos'}, 0.99, 'Question asks for steroid dosage equivalence'),
        'CURB-65 Score': ({'curb-65', 'curb 65'}, 0.99, 'Question asks for CURB-65 Score'),
        'PSI/PORT Score': ({'psi/port', 'psi port', 'pneumonia severity'}, 0.99, 'Question asks for PSI/PORT Score'),
        'PERC Rule': ({'perc rule', 'perc'}, 0.99, 'Question asks for PERC Rule'),
        'SOFA Score': ({'sofa score', 'sofa'}, 0.99, 'Question asks for SOFA Score'),
        'Centor Score (McIsaac)': ({'centor', 'mcisaac'}, 0.99, 'Question asks for Centor Score'),
        'FeverPAIN Score': ({'feverpain'}, 0.99, 'Question asks for FeverPAIN Score'),
        'SIRS Criteria': ({'sirs'}, 0.99, 'Question asks for SIRS Criteria'),
        'Glasgow-Blatchford Score (GBS)': ({'glasgow-blatchford', 'glasgow blatchford', 'gbs'}, 0.99, 'Question asks for Glasgow-Blatchford Score'),
        'HAS-BLED Score': ({'has-bled', 'has bled'}, 0.99, 'Question asks for HAS-BLED Score'),
        "Wells' Criteria for DVT": ({"wells' criteria for dvt", 'wells criteria for dvt', 'wells.*dvt'}, 0.99, "Question asks for Wells' Criteria for DVT"),
        'Caprini VTE Score': ({'caprini'}, 0.99, 'Question asks for Caprini VTE Score'),
        'Morphine Milligram Equivalents (MME)': ({'morphine milligram equivalents', 'mme', 'morphine miligram'}, 0.99, 'Question asks for daily MME'),
        'APACHE II Score': ({'apache ii', 'apache 2'}, 0.99, 'Question asks for APACHE II Score'),
        'Charlson Comorbidity Index (CCI)': ({'charlson', 'cci'}, 0.99, 'Question asks for Charlson Comorbidity Index'),
        'Gestational Age': ({'gestational age'}, 0.99, 'Question asks for gestational age'),
        'Estimated Due Date': ({'estimated due date', 'due date'}, 0.99, 'Question asks for estimated due date'),
        'Date of Conception': ({'date of conception', 'conception date'}, 0.99, 'Question asks for date of conception'),
        'Glasgow Coma Scale (GCS)': ({'glasgow coma scale', 'gcs'}, 0.99, 'Question asks for Glasgow Coma Scale'),
        'HOMA-IR': ({'homa-ir', 'homa ir'}, 0.99, 'Question explicitly asks for HOMA-IR score'),
        'Framingham Risk Score': ({'framingham risk'}, 0.99, 'Question asks for Framingham Risk Score'),
    }
    
    # Special handling for QTc Framingham vs Framingham Risk Score
    # and Wells PE vs Wells DVT
    
    best_match = None
    best_score = 0
    
    for calc_name in calculator_list:
        if calc_name in keyword_map:
            keywords, confidence, reasoning = keyword_map[calc_name]
            for kw in keywords:
                if '.*' in kw:
                    if re.search(kw, question_lower):
                        match_score = len(kw)
                        if match_score > best_score:
                            best_score = match_score
                            best_match = (calc_name, confidence, reasoning)
                elif kw in question_lower:
                    match_score = len(kw)
                    if match_score > best_score:
                        best_score = match_score
                        best_match = (calc_name, confidence, reasoning)
    
    if best_match:
        return {
            'calculator_name': best_match[0],
            'confidence': best_match[1],
            'reasoning': best_match[2]
        }
    
    # Fallback: try exact name matching
    for calc_name in calculator_list:
        if calc_name.lower() in question_lower:
            return {
                'calculator_name': calc_name,
                'confidence': 0.95,
                'reasoning': f'Question mentions {calc_name}'
            }
    
    return None
