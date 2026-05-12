"""Workflow-distilled Class 3 MedCalc implementation.

This artifact uses the induced ptools from the stateless-oc0-mp3 MedCalc
toolbox. The original quick Gemini output for this directory was truncated,
so this repaired workflow keeps the generated Class 3 binding usable while
remaining conservative: it abstains unless a numeric answer is easy to parse.
"""

import re

from secretagent.core import implement_via


@implement_via('simulate')
def calculate_clinical_score(focus: str) -> str:
    """
    Extract relevant clinical variables from a patient note and apply standard
    medical formulas or scores to derive a result.
    """


@implement_via('simulate')
def compute_clinical_value(focus: str) -> str:
    """
    Extract clinical parameters from patient notes and apply medical formulas
    or unit conversions to derive a diagnostic or therapeutic value.
    """


@implement_via('simulate')
def apply_clinical_score(focus: str) -> str:
    """
    Extract clinical variables required by a specified scoring system and
    calculate the final score based on provided criteria.
    """


def _extract_numeric(text):
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    s = str(text)
    if s.startswith('**exception'):
        return None

    answer_match = re.search(
        r'<answer>\s*(-?\d+(?:\.\d+)?)\s*</answer>', s, re.IGNORECASE)
    if answer_match:
        return float(answer_match.group(1))

    labelled_patterns = [
        r'(?:final\s+answer|answer|result|total|score)\s*[:=]\s*(-?\d+(?:\.\d+)?)',
        r'is\s+(-?\d+(?:\.\d+)?)\s*(?:mg|ml|mm|points?|score|%)?\b',
    ]
    for pattern in labelled_patterns:
        matches = re.findall(pattern, s, flags=re.IGNORECASE)
        if matches:
            return float(matches[-1])
    return None


def calculate_medical_value(patient_note: str, question: str):
    prompt = (
        'Use the patient note and question to compute the requested medical '
        'calculator value. Return a concise calculation and clearly label the '
        'final numeric answer.\n\n'
        f'Patient note:\n{patient_note}\n\nQuestion:\n{question}'
    )
    q = question.lower()
    score_terms = (
        'score', 'criteria', 'risk index', 'gcs', 'sirs', 'perc', 'curb',
        'wells', 'has-bled', 'cha2ds2', 'child-pugh', 'meld', 'sofa',
        'apache', 'heart', 'centor', 'feverpain', 'caprini',
    )
    try:
        if any(term in q for term in score_terms):
            raw = apply_clinical_score(prompt)
        elif any(term in q for term in ('calculate', 'equation', 'formula', 'clearance')):
            raw = compute_clinical_value(prompt)
        else:
            raw = calculate_clinical_score(prompt)
    except Exception:
        return None
    return _extract_numeric(raw)
