"""Self-contained ptools module wrapping induced helpers.

Hand-derived from the winning induction variant in learned/rule-4pc-pro-mp3.
Designed to be ingested by OrchestrationLearner via inspect.getsource:
the file MUST have no indirection — every symbol the supervisor sees
lives here.
"""

import re
from typing import Optional

from secretagent.core import interface, implement_via

# Reuse the existing medcalc machinery (formulas + calculator engine).
# Only computational helpers are imported; nothing that wires interfaces.
import calculator_simple
import calculators


# =============================================================================
# Induced ptools (inlined from learned/rule-4pc-pro-mp3)
# =============================================================================

@implement_via('simulate')
def map_patient_data_to_score(patient_note: str, focus: str) -> str:
    """
    Maps extracted patient data to the criteria of a specific medical score or formula to calculate the total.

    Provide the patient's clinical note in `patient_note` and the name of the score in the `focus`. The response will break down each criterion, evaluate the patient's data against it, assign the corresponding points, and calculate the final total.

    Pay attention to the exact thresholds, units, and point values defined by the medical score (e.g., Age >= 65, HR > 100, specific biomarker ranges). Make sure to explicitly note criteria that receive 0 points due to lack of evidence, falling outside the risk thresholds, or normal findings.

    Returns:
    Score Name: [Name of the Score]
    - [Criterion 1]: [Patient Data / Observation] -> [Points]
    - [Criterion 2]: [Patient Data / Observation] -> [Points]
    ...
    Total Score: [Calculated Sum]
    """


@implement_via('simulate')
def compute_score_step_by_step(patient_note: str, focus: str) -> str:
    """
    Computes a medical score manually step-by-step. Provide the patient's note in `patient_note` and the name of the medical score to calculate in the `focus` parameter (e.g., 'CURB-65', 'Caprini VTE').

    The response will structure the calculation by:
    1. Listing all the criteria evaluated for the score.
    2. Stating the patient's specific extracted data or status for each criterion.
    3. Assigning the exact point value (including 0 points for absent symptoms or normal findings) for each criterion.
    4. Providing the explicit mathematical sum of the points to reach the final total score.

    Pay attention to the specific definitions, thresholds, and exclusions for each scoring criterion to ensure accurate point assignment.

    Returns:
    - **[Criterion 1]**: [Patient's status/value] ([X] points)
    - **[Criterion 2]**: [Patient's status/value] ([Y] points)
    ...
    Calculation: [X] + [Y] + ... = [Total Score]
    """


@implement_via('simulate')
def calculate_clinical_score(patient_note: str, focus: str) -> str:
    """
    Calculates a specified medical score by extracting relevant clinical criteria and applying the appropriate scoring formula.

    Information to extract/reason about:
    - Identify the required parameters for the specific score indicated in the `focus` (e.g., 'SOFA score', 'Child-Pugh score', 'Charlson Comorbidity Index').
    - Extract the corresponding clinical values (lab results, vitals, comorbidities, age) from the `patient_note`.

    How the response should be structured:
    - Provide a step-by-step list of each parameter evaluated.
    - Note the extracted patient value for each parameter.
    - State the points assigned based on the specific scoring criteria.
    - Provide a final summation equation yielding the total score.

    What the agent should pay attention to:
    - Accurately apply clinical thresholds, age brackets, and unit conversions.
    - Account for missing information properly (e.g., defaulting to normal/0 points if the score guidelines permit, or noting the missing data).
    - Ensure strict arithmetic correctness when summing the assigned points.

    Returns:
    A structured string detailing the score calculation step-by-step.

    Example:
    Score Calculation: SOFA score
    1. Respiration: PaO2/FiO2 = 160 -> Score = 3
    2. Coagulation: Platelets = 110,000/uL -> Score = 1
    3. Liver: Bilirubin = 1.4 mg/dL -> Score = 1
    4. Cardiovascular: MAP = 57.3 mmHg -> Score = 1
    5. Neurological: GCS = 5 -> Score = 4
    6. Renal: Creatinine = 2.2 mg/dL -> Score = 2
    Total SOFA Score = 3 + 1 + 1 + 1 + 4 + 2 = 12
    """

# =============================================================================
# Public entry point — calculate_medical_value
# =============================================================================

@interface
def calculate_medical_value(patient_note: str, question: str) -> float:
    """Calculate a medical value from a patient note and question.
    
    CRITICAL INSTRUCTIONS:
    1. Identify the requested medical score or calculator from the question.
    2. Read the patient note carefully. Extract every clinical detail relevant to the scoring criteria (age, vitals, lab values, medical history).
    3. Mentally apply the exact scoring criteria and point values for the requested score. For missing data, assume normal/0 points unless guidelines state otherwise.
    4. Carefully sum all the points to calculate the final total score.
    5. You MUST return ONLY the final numerical score as a single float (e.g., 2.0, 15.0).
    6. DO NOT output any text, reasoning, units, or equations. Returning anything other than a float will cause a system crash.

    SCORE-SPECIFIC REMINDERS (use these exact criteria to ensure accuracy):
    - Caprini Score:
      1 pt: Age 41-60, Minor surgery, BMI >25, Swollen legs, Varicose veins, Pregnancy/postpartum, Oral contraceptives/HRT, Unexplained miscarriages, Sepsis (<1mo), Serious lung disease/COPD, Acute MI, CHF (<1mo), IBD, Medical patient on bed rest.
      2 pts: Age 61-74, Arthroscopic surgery, Major open surgery (>45min), Laparoscopic surgery (>45min), Malignancy, Confined to bed (>72h), Immobilizing plaster cast, Central venous access.
      3 pts: Age >=75, Hx of VTE, Family hx of VTE, Thrombophilia.
      5 pts: Elective major lower extremity arthroplasty, Hip/pelvis/leg fracture (<1mo), Stroke (<1mo), Multiple trauma (<1mo), Acute spinal cord injury (<1mo).
    - HAS-BLED: H (HTN, SBP>160) = 1, A (Abnormal Renal OR Liver) = 1 each (max 2), S (Stroke hx) = 1, B (Bleeding hx/predisposition) = 1, L (Labile INRs, TTR<60%) = 1, E (Age>65) = 1, D (Drugs like Antiplatelets/NSAIDs OR Alcohol >=8 drinks/wk) = 1 each (max 2).
    - CHA2DS2-VASc: C (CHF) = 1, H (HTN) = 1, A2 (Age >=75) = 2, D (Diabetes) = 1, S2 (Stroke/TIA, including current event) = 2, V (Prior MI, PAD, aortic plaque) = 1, A (Age 65-74) = 1, Sc (Female sex) = 1.
    - Glasgow-Blatchford Score (GBS): BUN: 18.2-22.3 mg/dL (2), 22.4-27.9 (3), 28-70 (4), >70 (6). Hb Men: 12-12.9 g/dL (1), 10-11.9 (3), <10 (6). Hb Women: 10-11.9 g/dL (1), <10 (6). Systolic BP: 100-109 mmHg (1), 90-99 (2), <90 (3). HR >=100 (1). Melena (1), Syncope (2), Hepatic disease (2), Cardiac failure (2). (If missing, assume 0 points).
    - FeverPAIN: Fever >38°C (1), Purulent tonsils (1), Attend rapidly within 3 days (1), Severely inflamed tonsils (1), No cough/coryza (1).
    - PERC Rule (1 pt for each met, max 8): Age >=50, HR >=100, SaO2 <95%, Unilateral leg swelling, Hemoptysis, Recent surgery/trauma (<4wks), Prior PE/DVT, Hormone use.
    - SIRS Criteria (1 pt for each met, max 4): Temp >38°C or <36°C, HR >90, RR >=20 or PaCO2 <32, WBC >12k or <4k or >10% bands.
    - Centor Score (Modified/McIsaac): Age <3 (0), Age 3-14 (+1), 15-44 (0), >=45 (-1). Tonsillar exudate (+1), Tender anterior cervical adenopathy (+1), Fever >38°C (+1), Absence of cough (+1).
    - HEART Score: History: Highly suspicious (2), Mod (1), Slight (0). ECG: ST depression (2), Nonspecific (1), Normal (0). Age: >=65 (2), 45-64 (1), <45 (0). Risk factors (HTN, hypercholesterolemia, DM, obesity, smoking, fam hx): >=3 RFs or prior atherosclerotic disease (2), 1-2 RFs (1), None (0). Troponin: >=3x normal (2), 1-3x normal (1), <= normal (0).
    - Wells' Criteria for PE: Clinical signs of DVT (3.0), PE is #1 diagnosis or equally likely (3.0), HR >100 (1.5), Immobilization >=3 days OR surgery in past 4 weeks (1.5), Prior PE/DVT (1.5), Hemoptysis (1.0), Malignancy w/ treatment <6mo (1.0).
    - Child-Pugh Score (Sum of 5 categories, min 5 points): Encephalopathy: None (1), Gr 1-2 (2), Gr 3-4 (3). Ascites: None (1), Mild/Mod (2), Severe (3). Bilirubin (mg/dL): <2 (1), 2-3 (2), >3 (3). Albumin (g/dL): >3.5 (1), 2.8-3.5 (2), <2.8 (3). INR: <1.7 (1), 1.7-2.2 (2), >2.2 (3).
    - Revised Cardiac Risk Index (RCRI): High-risk surgery (1), Ischemic heart disease (1), CHF (1), Cerebrovascular disease/Stroke/TIA (1), Insulin-dependent diabetes (1), Pre-op Creatinine >2.0 mg/dL (1).
    - Charlson Comorbidity Index (CCI): MI (1), CHF (1), PVD (1), Cerebrovascular disease (1), Dementia (1), COPD (1), Connective tissue disease (1), Peptic ulcer (1), Mild liver disease (1), Diabetes uncomplicated (1). Hemiplegia (2), Mod/severe renal disease (2), Diabetes with end-organ damage (2), Any tumor/leukemia/lymphoma (2). Mod/severe liver disease (3). Metastatic solid tumor (6), AIDS (6). Age: 50-59 (1), 60-69 (2), 70-79 (3), 80+ (4).
    """




def _extract_number(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value)
    if s.startswith('**exception'):
        return None
    try:
        return float(s)
    except ValueError:
        pass
    for pat in (r'<answer>\s*([\d.eE+-]+)\s*</answer>', r'ANSWER:\s*([\d.eE+-]+)'):
        m = re.search(pat, s)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    nums = re.findall(r'-?\d+\.?\d*', s)
    if nums:
        try:
            return float(nums[-1])
        except ValueError:
            pass
    return None