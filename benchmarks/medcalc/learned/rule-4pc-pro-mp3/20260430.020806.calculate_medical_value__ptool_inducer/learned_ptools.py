"""Induced ptools for calculate_medical_value."""

from secretagent.core import implement_via


@implement_via('simulate')
def map_patient_data_to_score(focus: str) -> str:
    """
    Maps extracted patient data to the criteria of a specific medical score or formula to calculate the total.

    Provide the name of the score and the relevant extracted clinical values in the `focus`. The response will break down each criterion, evaluate the patient's data against it, assign the corresponding points, and calculate the final total.

    Pay attention to the exact thresholds, units, and point values defined by the medical score (e.g., Age >= 65, HR > 100, specific biomarker ranges). Make sure to explicitly note criteria that receive 0 points due to lack of evidence, falling outside the risk thresholds, or normal findings.

    Returns:
    Score Name: [Name of the Score]
    - [Criterion 1]: [Patient Data / Observation] -> [Points]
    - [Criterion 2]: [Patient Data / Observation] -> [Points]
    ...
    Total Score: [Calculated Sum]
    """


@implement_via('simulate')
def compute_score_step_by_step(focus: str) -> str:
    """
    Computes a medical score manually step-by-step. Provide the name of the medical score to calculate in the `focus` parameter (e.g., 'CURB-65', 'Caprini VTE').

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
def calculate_clinical_score(focus: str) -> str:
    """
    Calculates a specified medical score by extracting relevant clinical criteria and applying the appropriate scoring formula.

    Information to extract/reason about:
    - Identify the required parameters for the specific score indicated in the `focus` (e.g., 'SOFA score', 'Child-Pugh score', 'Charlson Comorbidity Index').
    - Extract the corresponding clinical values (lab results, vitals, comorbidities, age) from the patient note.

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
    2. Coagulation: Platelets = 110,000/µL -> Score = 1
    3. Liver: Bilirubin = 1.4 mg/dL -> Score = 1
    4. Cardiovascular: MAP = 57.3 mmHg -> Score = 1
    5. Neurological: GCS = 5 -> Score = 4
    6. Renal: Creatinine = 2.2 mg/dL -> Score = 2
    Total SOFA Score = 3 + 1 + 1 + 1 + 4 + 2 = 12
    """


