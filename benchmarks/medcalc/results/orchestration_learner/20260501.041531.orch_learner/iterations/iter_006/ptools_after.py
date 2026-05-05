"""Self-contained ptools module wrapping induced helpers.

Hand-derived from the winning induction variant in learned/rule-4pc-pro-mp3.
Designed to be ingested by OrchestrationLearner via inspect.getsource:
the file MUST have no indirection — every symbol the supervisor sees
lives here.
"""

import re
import time
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
@implement_via('direct')
def calculate_medical_value(patient_note: str, question: str) -> float:
    """Calculate a medical value from a patient note and question.
    
    CRITICAL INSTRUCTIONS:
    1. Identify the requested medical score or calculator from the question.
    2. Read the patient note carefully. Extract every clinical detail relevant to the scoring criteria (age, vitals, lab values, medical history).
    3. Mentally apply the exact scoring criteria and point values for the requested score. For missing data, assume normal/0 points unless guidelines state otherwise.
    4. Carefully sum all the points to calculate the final total score.
    5. You MUST return ONLY the final numerical score as a single float (e.g., 2.0, 15.0).
    6. DO NOT output any text, reasoning, units, or equations. Returning anything other than a float will cause a system crash.
    """
    hints = {
        "has-bled": "HAS-BLED: Hypertension (SBP>160) = 1, Abnormal renal function = 1, Abnormal liver function = 1, Stroke = 1, Bleeding history or predisposition = 1, Labile INRs = 1, Age >65 = 1, Drugs (NSAIDs/antiplatelets) = 1, Alcohol = 1.",
        "caprini": "Caprini (2005): 1 pt: Age 41-60, Minor surgery, BMI>25, Swollen legs, Varicose veins, Pregnancy, Oral contraceptives, Acute MI, CHF, Sepsis, Medical patient on bed rest, Abnormal pulmonary function. 2 pts: Age 61-74, Major surgery >45 min, Malignancy, Confined to bed >72h, Immobilizing cast, Central venous access. 3 pts: Age >=75, History of VTE, Family history VTE, Factor V Leiden/Prothrombin/Lupus/Anticardiolipin. 5 pts: Stroke <1 month, Elective major lower extremity arthroplasty, Hip/pelvis/leg fracture, Multiple trauma <1 month, Acute spinal cord injury.",
        "cha2ds2-vasc": "CHA2DS2-VASc: CHF(1), Hypertension(1), Age>=75(2), Diabetes(1), Stroke/TIA/Thromboembolism(2), Vascular disease(1), Age 65-74(1), Female sex(1).",
        "glasgow-blatchford": "Glasgow-Blatchford (GBS): BUN (mg/dL) 18.2-27.9(2), 28.0-69.9(3), 70-139.9(4), >=140(6) OR BUN (mmol/L) 6.5-7.9(2), 8.0-9.9(3), 10.0-24.9(4), >=25.0(6). Hgb men <10g/dL(6), 10-11.9(3), 12-12.9(1). Hgb women <10g/dL(6), 10-11.9(1). SBP 100-109(1), 90-99(2), <90(3). HR >=100(1). Melena(1). Syncope(2). Hepatic disease(2). Heart failure(2).",
        "feverpain": "FeverPAIN: Fever in past 24h(1), Purulence on tonsils(1), Attend rapidly <=3 days(1), Severely Inflamed tonsils(1), No cough/coryza(1).",
        "heart": "HEART Score: History slightly suspicious(1) or highly suspicious(2). ECG normal(0), nonspecific repolarization(1), significant ST depression(2). Age 45-64(1), >=65(2). Risk factors (HTN, hypercholesterolemia, diabetes, obesity, smoking, family history CAD): 1-2 factors(1), >=3 factors or history of CAD(2). Troponin 1-3x limit(1), >3x limit(2).",
        "sirs": "SIRS Criteria: Temp >38.0 or <36.0 (1). HR >90 (1). RR >20 or PaCO2 <32 (1). WBC >12,000 or <4,000 or >10% bands (1).",
        "perc": "PERC Rule: All must be false to rule out PE. Age >=50(1). HR >=100(1). O2 sat <95%(1). Prior DVT/PE(1). Recent trauma/surgery <=4 weeks(1). Hemoptysis(1). Exogenous estrogen(1). Unilateral leg swelling(1).",
        "wells": "Wells PE: Clinical signs DVT (3). Alt diagnosis less likely (3). HR >100 (1.5). Immobilization >=3 days or surgery in past 4 weeks (1.5). Prior DVT/PE (1.5). Hemoptysis (1). Malignancy (1).",
        "centor": "Centor Score: Fever(1), Tonsillar exudate(1), Tender anterior cervical adenopathy(1), Absence of cough(1). Age 3-14(1), 15-44(0), >=45(-1).",
        "sofa": "SOFA: Respiration PaO2/FiO2 <400(1), <300(2), <200(3), <100(4). Coagulation Platelets <150k(1), <100k(2), <50k(3), <20k(4). Liver Bilirubin 1.2-1.9(1), 2.0-5.9(2), 6.0-11.9(3), >12.0(4). Cardiovascular MAP <70(1), Dopamine<=5 or Dobutamine(2), Dopamine>5 or Epi<=0.1 or Norepi<=0.1(3), Dopamine>15 or Epi>0.1 or Norepi>0.1(4). CNS GCS 13-14(1), 10-12(2), 6-9(3), <6(4). Renal Creatinine 1.2-1.9(1), 2.0-3.4(2), 3.5-4.9(3), >5.0(4).",
        "child-pugh": "Child-Pugh: Bilirubin <2(1), 2-3(2), >3(3). Albumin >3.5(1), 2.8-3.5(2), <2.8(3). INR <1.7(1), 1.7-2.2(2), >2.2(3). Ascites None(1), Mild/Moderate(2), Severe(3). Encephalopathy None(1), Grade 1-2(2), Grade 3-4(3).",
        "charlson": "Charlson Comorbidity Index: MI(1), CHF(1), PVD(1), CVA/TIA(1), Dementia(1), COPD(1), Connective tissue disease(1), Peptic ulcer(1), Mild liver disease(1), Diabetes without complications(1). Hemiplegia(2), Moderate/severe renal disease(2), Diabetes with end-organ damage(2), Tumor(2), Leukemia(2), Lymphoma(2). Moderate/severe liver disease(3). Metastatic solid tumor(6), AIDS(6). Age 50-59(1), 60-69(2), 70-79(3), 80+(4)."
    }
    
    q_lower = question.lower()
    injected_hint = ""
    for key, hint_text in hints.items():
        if key in q_lower:
            injected_hint = f"\n\nCRITICAL SCORING RUBRIC FOR THIS CALCULATION:\n{hint_text}\nCarefully check the patient note against each of these criteria."
            break
            
    modified_question = question + injected_hint
    
    # Simple retry loop to fix litellm timeouts and framework extraction crashes
    for attempt in range(3):
        try:
            return _simulate_calculate_medical_value(patient_note, modified_question)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1)


@implement_via('simulate')
def _simulate_calculate_medical_value(patient_note: str, question: str) -> float:
    """Calculate a medical value from a patient note and question.
    
    CRITICAL INSTRUCTIONS:
    1. Identify the requested medical score or calculator from the question.
    2. Read the patient note carefully. Extract every clinical detail relevant to the scoring criteria (age, vitals, lab values, medical history).
    3. Mentally apply the exact scoring criteria and point values for the requested score. For missing data, assume normal/0 points unless guidelines state otherwise.
    4. Carefully sum all the points to calculate the final total score.
    5. You MUST return ONLY the final numerical score as a single float (e.g., 2.0, 15.0).
    6. DO NOT output any text, reasoning, units, or equations. Returning anything other than a float will cause a system crash.
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