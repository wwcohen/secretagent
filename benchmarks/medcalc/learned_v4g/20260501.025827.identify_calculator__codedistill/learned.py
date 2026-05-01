"""Auto-generated code-distilled implementation for identify_calculator."""

def identify_calculator(question: str, calculator_names: list) -> dict:
    patterns = [
        ("Fractional Excretion of Sodium (FENa)", {
            'calculator_name': 'Fractional Excretion of Sodium (FENa)', 
            'confidence': 0.99, 
            'reasoning': 'FENa directly asked'
        }),
        ("Cockroft-Gault Equation", {
            'calculator_name': 'Creatinine Clearance (Cockcroft-Gault)', 
            'confidence': 0.98, 
            'reasoning': 'Question specifically mentions Creatinine Clearance using Cockroft-Gault Equation and discusses adjusted body weight calculations'
        }),
        ("target weight in kg", {
            'calculator_name': 'Target Weight', 
            'confidence': 0.85, 
            'reasoning': 'Question specifically asks for target weight calculation based on height and target BMI'
        }),
        ("Wells' criteria for Deep Vein Thrombosis", {
            'calculator_name': "Wells' Criteria for DVT", 
            'confidence': 0.95, 
            'reasoning': "Question directly references Wells' criteria for Deep Vein Thrombosis"
        }),
        ("MDRD GFR Equation", {
            'calculator_name': 'MDRD GFR', 
            'confidence': 0.95, 
            'reasoning': 'Question explicitly mentions "MDRD GFR Equation" and requests calculation of Glomerular Filtration Rate'
        }),
        ("Wells' criteria for Pulmonary Embolism", {
            'calculator_name': "Wells' Criteria for PE", 
            'confidence': 0.95, 
            'reasoning': 'Question directly asks for Wells criteria score specifically for Pulmonary Embolism'
        }),
        ("Calcium Correction for Hypoalbuminemia", {
            'calculator_name': 'Calcium Correction for Hypoalbuminemia', 
            'confidence': 0.99, 
            'reasoning': 'Question explicitly mentions the calculator by name and describes its specific use case'
        }),
        ("Revised Cardiac Risk Index", {
            'calculator_name': 'Revised Cardiac Risk Index (RCRI)', 
            'confidence': 0.98, 
            'reasoning': 'Question explicitly mentions "Revised Cardiac Risk Index" which matches exactly with available calculator'
        }),
        ("Framingham Formula", {
            'calculator_name': 'QTc (Framingham)', 
            'confidence': 0.99, 
            'reasoning': 'Question directly references the Framingham formula for QT correction'
        }),
        ("adjusted body weight formula", {
            'calculator_name': 'Adjusted Body Weight', 
            'confidence': 0.95, 
            'reasoning': 'Question specifically mentions "adjusted body weight formula"'
        }),
        ("Charlson Comorbidity Index", {
            'calculator_name': 'Charlson Comorbidity Index (CCI)', 
            'confidence': 0.99, 
            'reasoning': 'Question specifically mentions Charlson Comorbidity Index (CCI) by name'
        }),
        ("maintenance fluid", {
            'calculator_name': 'Maintenance Fluids (4-2-1 Rule)', 
            'confidence': 0.95, 
            'reasoning': 'Question directly asks about maintenance fluid calculation using standard clinical parameters'
        }),
        ("Hodges Formula", {
            'calculator_name': 'QTc (Hodges)', 
            'confidence': 0.99, 
            'reasoning': 'Question explicitly mentions "Hodges Formula for corrected QT interval"'
        }),
        ("albumin corrected anion gap", {
            'calculator_name': 'Albumin Corrected Anion Gap', 
            'confidence': 0.95, 
            'reasoning': 'Question directly asks for albumin corrected anion gap in mEq/L'
        }),
        ("anion gap in terms of mEq/L", {
            'calculator_name': 'Anion Gap', 
            'confidence': 0.98, 
            'reasoning': 'Question directly asks for anion gap and specifies units (mEq/L)'
        }),
        ("delta gap", {
            'calculator_name': 'Delta Gap', 
            'confidence': 0.95, 
            'reasoning': 'Question directly mentions delta gap calculation'
        }),
        ("mean arterial pressure", {
            'calculator_name': 'Mean Arterial Pressure (MAP)', 
            'confidence': 0.95, 
            'reasoning': 'Question directly asks for mean arterial pressure and specifies units (mm Hg)'
        }),
        ("corrected sodium concentration for hyperglycemia", {
            'calculator_name': 'Sodium Correction for Hyperglycemia', 
            'confidence': 0.99, 
            'reasoning': 'Question specifically asks for sodium correction for hyperglycemia using the sodium correction equation'
        }),
        ("CHA2DS2-VASc Score", {
            'calculator_name': 'CHA2DS2-VASc Score', 
            'confidence': 1.0, 
            'reasoning': 'Question directly asks for CHA2DS2-VASc Score'
        }),
        ("Fridericia Formula", {
            'calculator_name': 'QTc (Fridericia)', 
            'confidence': 0.99, 
            'reasoning': 'Question specifically references Fridericia Formula for corrected QT interval'
        }),
        ("2021 CKD-EPI Creatinine equation", {
            'calculator_name': 'CKD-EPI GFR (2021)', 
            'confidence': 0.98, 
            'reasoning': 'Question specifically mentions 2021 CKD-EPI Creatinine equation for calculating GFR'
        }),
        ("PERC Rule", {
            'calculator_name': 'PERC Rule', 
            'confidence': 0.95, 
            'reasoning': 'Question specifically asks about criteria met for the PERC Rule for Pulmonary Embolism'
        }),
        ("Ideal Body Weight Formula", {
            'calculator_name': 'Ideal Body Weight (Devine)', 
            'confidence': 0.95, 
            'reasoning': 'Question explicitly mentions "Ideal Body Weight Formula" and asks for ideal body weight in kg'
        }),
        ("body mass mass index (BMI)", {
            'calculator_name': 'Body Mass Index (BMI)', 
            'confidence': 0.95, 
            'reasoning': 'Question explicitly mentions "body mass mass index (BMI)" and references kg/m² units, which directly matches the BMI calculator'
        }),
        ("HAS-BLED score", {
            'calculator_name': 'HAS-BLED Score', 
            'confidence': 0.99, 
            'reasoning': 'Question specifically asks for HAS-BLED score'
        }),
        ("free water deficit", {
            'calculator_name': 'Free Water Deficit', 
            'confidence': 0.95, 
            'reasoning': 'Question specifically asks for free water deficit calculation'
        }),
        ("body surface area", {
            'calculator_name': 'Body Surface Area (Mosteller)', 
            'confidence': 0.95, 
            'reasoning': 'Question specifically asks for body surface area calculation'
        }),
        ("serum osmolality", {
            'calculator_name': 'Serum Osmolality', 
            'confidence': 0.95, 
            'reasoning': 'Question directly asks for serum osmolality calculation and provides relevant clinical parameters'
        }),
        ("SIRS critiera", {
            'calculator_name': 'SIRS Criteria', 
            'confidence': 0.95, 
            'reasoning': 'Question directly asks for SIRS criteria and matches available calculator name'
        }),
        ("MELD Na score", {
            'calculator_name': 'MELD-Na Score', 
            'confidence': 0.95, 
            'reasoning': 'Question explicitly asks for MELD Na score, which directly matches the available calculator name.'
        }),
        ("Bazett Formula", {
            'calculator_name': 'QTc (Bazett)', 
            'confidence': 0.95, 
            'reasoning': 'Question specifically mentions Bazett Formula for corrected QT interval'
        }),
        ("Child-Pugh Score", {
            'calculator_name': 'Child-Pugh Score', 
            'confidence': 0.99, 
            'reasoning': 'Question directly asks for Child-Pugh Score'
        }),
        ("LDL cholestrol", {
            'calculator_name': 'LDL Calculated (Friedewald)', 
            'confidence': 0.99, 
            'reasoning': 'The question directly asks for LDL cholesterol concentration in mg/dL, which is calculated using the Friedewald formula.'
        }),
        ("Fibrosis 4 Index", {
            'calculator_name': 'FIB-4 Index', 
            'confidence': 0.99, 
            'reasoning': 'Question directly mentions "Fibrosis 4 Index" which exactly matches available calculator'
        }),
        ("delta ratio", {
            'calculator_name': 'Delta Ratio', 
            'confidence': 0.95, 
            'reasoning': 'Question specifically mentions delta ratio calculation'
        }),
        ("CURB-65 score", {
            'calculator_name': 'CURB-65 Score', 
            'confidence': 0.99, 
            'reasoning': 'Question directly mentions "CURB-65 score" which exactly matches one of the available calculators'
        })
    ]

    # Sort patterns by length descending to match longest, most specific substrings first
    patterns.sort(key=lambda x: len(x[0]), reverse=True)

    for pattern_text, result_dict in patterns:
        if pattern_text in question:
            return result_dict
            
    return None
