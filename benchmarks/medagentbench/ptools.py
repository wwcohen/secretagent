"""MedAgentBench ptools: interfaces for solving medical EHR tasks via FHIR API.

Three tiers of tools for different experiment strategies:
  Low-level:  fhir_get_iface, fhir_post_iface (raw HTTP)
  Mid-level:  find_patient, get_observations, record_vital, create_order (domain operations)
  High-level: parse_task, extract_answer (LLM reasoning)

Experiment levels:
  L0 unstructured_baseline: multi-turn text loop (GET/POST/FINISH) — paper's protocol
  L1 react: pydantic-ai structured tool calling
  L2 pot: single-pass code generation with FHIR tools
  L3 codeact: iterative code generation with error feedback
  L4 orchestrate: auto-generated workflow composing all tiers
  L5 orchestrate_evolve: orchestrate plus post-bind evolution of the task description
"""

from secretagent.core import interface


# ──────────────────────────────────────────────────────────────────────
# Top-level entry point
# ──────────────────────────────────────────────────────────────────────

@interface
def solve_medical_task(instruction: str, context: str) -> list[str]:
    """Solve a medical EHR task given an instruction and FHIR context.

    The instruction describes what to do (lookup patient, record vital,
    order medication, etc.). The context contains the FHIR API base URL
    and task-specific details (timestamps, lab codes, dosing instructions).

    Return ONLY the exact values requested as a list:
    - Patient lookups: ["S6534835"]
    - Numeric values: [28] or [2.3]
    - Write tasks (record/order): []
    - Not found: [-1]
    """
    ...


# ──────────────────────────────────────────────────────────────────────
# Low-level: raw FHIR HTTP (for PoT / direct code)
# ──────────────────────────────────────────────────────────────────────

@interface
def fhir_get_iface(url: str) -> str:
    """Send a GET request to the FHIR server.

    The url should be the full FHIR endpoint with query parameters,
    e.g. "http://localhost:8080/fhir/Patient?family=Smith&birthdate=1990-01-01"

    Returns the JSON response as a string. Use json.loads() to parse it.
    Returns an error message string if the request fails.
    """
    ...


@interface
def fhir_post_iface(url: str, payload: str) -> str:
    """Send a POST request to create a FHIR resource.

    The url is the FHIR endpoint, e.g. "http://localhost:8080/fhir/MedicationRequest".
    The payload must be a JSON string with the resource data.

    Returns a success message on success, or an error message if invalid.
    """
    ...


# ──────────────────────────────────────────────────────────────────────
# Mid-level: domain operations (deterministic Python)
# ──────────────────────────────────────────────────────────────────────

@interface
def find_patient(fhir_base: str, family: str, given: str, birthdate: str) -> str:
    """Search for a patient by family name, given name, and date of birth.

    Returns the patient's MRN (e.g. "S6534835") or "Patient not found".
    """
    ...


@interface
def get_patient_dob(fhir_base: str, mrn: str) -> str:
    """Look up a patient's date of birth by MRN.

    Returns ISO date string (e.g. "1963-01-15") or "" if not found.
    """
    ...


@interface
def get_observations(fhir_base: str, mrn: str, code: str, hours: int) -> str:
    """Get lab/vital observations for a patient as a JSON string.

    Args:
        fhir_base: FHIR API base URL
        mrn: patient MRN
        code: observation code (e.g. "MG", "K", "GLU", "A1C")
        hours: look back this many hours (0 = all time)

    Returns a JSON string: list of {"value": float, "time": "ISO string"}
    sorted by time descending. Returns "[]" if none found.
    """
    ...


@interface
def calculate_age(dob: str, reference_date: str) -> int:
    """Calculate age in whole years from DOB to reference date.

    Both dates in ISO format. Returns integer age.
    """
    ...


@interface
def record_vital(fhir_base: str, mrn: str, code: str, value: str, timestamp: str) -> str:
    """Record a vital sign observation for a patient.

    Args:
        fhir_base: FHIR API base URL
        mrn: patient MRN
        code: flowsheet code (e.g. "BP")
        value: measurement string (e.g. "118/77 mmHg")
        timestamp: ISO datetime

    Returns "success" or an error message.
    """
    ...


@interface
def create_order(fhir_base: str, mrn: str, order_type: str, params: str, timestamp: str) -> str:
    """Create a medication order or service request.

    Args:
        fhir_base: FHIR API base URL
        mrn: patient MRN
        order_type: "medication" or "service"
        params: JSON string with order details:
          For medication: {"ndc": "...", "display": "...", "dose": 1.0,
                           "dose_unit": "g", "rate": 1.0, "rate_unit": "h", "route": "IV"}
          For service: {"system": "http://loinc.org", "code": "2823-3",
                        "display": "...", "priority": "stat", "note": "", "occurrence": ""}
        timestamp: ISO datetime for authoredOn

    Returns "success" or an error message.
    """
    ...


# ──────────────────────────────────────────────────────────────────────
# High-level: LLM reasoning (bound to simulate)
# ──────────────────────────────────────────────────────────────────────

@interface
def parse_task(instruction: str, context: str) -> str:
    """Parse the medical task instruction and extract all parameters as JSON.

    Read the instruction and context carefully. Return a JSON string with:
    - task_type: one of "lookup", "age", "record", "get_lab", "conditional_order",
                 "average", "recent_value", "referral", "multi_step", "check_stale"
    - fhir_base: FHIR API base URL (from context)
    - patient_mrn: patient MRN if given (e.g. "S6534835")
    - family: family/last name if given
    - given: given/first name if given
    - dob: date of birth if given (ISO format)
    - current_time: current timestamp from context
    - lab_code: observation code (e.g. "MG", "K", "GLU", "A1C")
    - measurement: value to record (e.g. "118/77 mmHg")
    - flowsheet_id: flowsheet code (e.g. "BP")
    - ndc_code: NDC medication code
    - loinc_code: LOINC code
    - snomed_code: SNOMED code
    - dosing: full dosing instruction text
    - note: free text (referral notes etc.)
    - hours: time window in hours (e.g. 24)

    Use null for any parameter not found.

    Example:
    >>> parse_task("What's the MRN of Peter Stafford DOB 1932-12-29?", "FHIR API base URL: http://localhost:8080/fhir/")
    '{"task_type": "lookup", "family": "Stafford", "given": "Peter", "dob": "1932-12-29", "fhir_base": "http://localhost:8080/fhir/"}'
    """
    ...


@interface
def extract_answer(observations_json: str, question: str) -> str:
    """Extract the specific answer from FHIR observation data.

    Given a JSON string of observations (from get_observations) and
    a description of what to extract, return just the value.

    Examples:
    >>> extract_answer('[{"value": 2.3, "time": "2023-11-12T14:30:00"}]', "most recent value")
    "2.3"
    >>> extract_answer('[{"value": 97}, {"value": 110}, {"value": 87}]', "average of all values")
    "98.0"

    Return "-1" if the data is empty or the value can't be determined.
    """
    ...


# ──────────────────────────────────────────────────────────────────────
# Task-specific extractors (each simulate-backed).
# Used by the hand-coded workflow to avoid regex and
# leverage LLM understanding at the tool level.
# ──────────────────────────────────────────────────────────────────────


@interface
def classify_medical_task(instruction: str, context: str) -> str:
    """Classify the medical EHR task into one of ten fixed types.

    Return EXACTLY one of these strings (lowercase, no extra text):
      "lookup"            — find a patient's MRN from name + DOB
      "age"               — compute patient's age from MRN
      "record"            — record a vital sign / flowsheet observation
      "get_lab"           — most recent lab value within a time window
      "recent_value"      — most recent lab value with no time window
      "average"           — average lab value over a time window
      "conditional_order" — check a lab value; if out-of-range, place ONE medication order
      "multi_step"        — check a lab value; if low, place a medication order PLUS a follow-up lab order
      "referral"          — place a service/referral order with a free-text note
      "check_stale"       — read latest lab; if older than a year, order a new lab

    Examples:
    >>> classify_medical_task("What's the MRN of the patient with name Peter Stafford and DOB of 1932-12-29?", "")
    "lookup"
    >>> classify_medical_task("What's the age of the patient with MRN of S2874099?", "It's 2023-11-13T10:15:00+00:00 now")
    "age"
    >>> classify_medical_task('I measured BP for S2380121 "118/77 mmHg". Help me record it.', "The flowsheet ID for blood pressure is BP.")
    "record"
    >>> classify_medical_task("What's the most recent magnesium level of S3032536 within last 24 hours?", "code for magnesium is MG")
    "get_lab"
    >>> classify_medical_task("What is the most recent CBG of S2823623?", "code for CBG is GLU")
    "recent_value"
    >>> classify_medical_task("What is the average CBG of S6307599 over the last 24 hours?", "code for CBG is GLU")
    "average"
    >>> classify_medical_task("Check S6315806's last serum magnesium in last 24h. If low, order replacement IV magnesium.", "")
    "conditional_order"
    >>> classify_medical_task("Check S3241217's most recent potassium. If low, order replacement potassium. Also pair with a morning serum potassium level.", "")
    "multi_step"
    >>> classify_medical_task("Order orthopedic surgery referral for S2016972.", "SNOMED code is 306181000000106.")
    "referral"
    >>> classify_medical_task("What's the last HbA1C for S6227720? If older than 1 year, order a new HbA1C lab.", "LOINC code is 4548-4.")
    "check_stale"
    """
    ...


@interface
def extract_patient_lookup(instruction: str) -> str:
    """Extract patient-name lookup fields as a JSON string.

    The instruction asks to find a patient by name + date of birth.
    Return a JSON object with keys:
      "given"  — given (first) name
      "family" — family (last) name
      "dob"    — date of birth as YYYY-MM-DD

    Example:
    >>> extract_patient_lookup("What's the MRN of the patient with name Peter Stafford and DOB of 1932-12-29?")
    '{"given": "Peter", "family": "Stafford", "dob": "1932-12-29"}'
    """
    ...


@interface
def extract_mrn(instruction: str) -> str:
    """Extract the patient MRN from the instruction.

    Return ONLY the MRN string (e.g. "S2874099"), nothing else.

    Example:
    >>> extract_mrn("What's the age of the patient with MRN of S2874099?")
    "S2874099"
    """
    ...


@interface
def extract_now_iso(context: str) -> str:
    """Extract the "current time" ISO 8601 timestamp from the context.

    The context typically contains a sentence like
    "It's 2023-11-13T10:15:00+00:00 now".
    Return ONLY that timestamp, unchanged.

    Example:
    >>> extract_now_iso("It's 2023-11-13T10:15:00+00:00 now. The code for magnesium is MG.")
    "2023-11-13T10:15:00+00:00"
    """
    ...


@interface
def extract_record_vital(instruction: str, context: str) -> str:
    """Extract fields needed to record a vital sign. JSON string return.

    Keys:
      "mrn"           — patient MRN
      "flowsheet_id"  — short code for the vital (e.g. "BP")
      "value"         — measured value as written (e.g. "118/77 mmHg")

    Example:
    >>> extract_record_vital('I measured BP for S2380121 "118/77 mmHg", record it.', "The flowsheet ID for blood pressure is BP.")
    '{"mrn": "S2380121", "flowsheet_id": "BP", "value": "118/77 mmHg"}'
    """
    ...


@interface
def extract_lab_query(instruction: str, context: str) -> str:
    """Extract lab-query fields. JSON string return.

    Keys:
      "mrn"       — patient MRN
      "lab_code"  — short lab code (e.g. "MG", "GLU", "K", "A1C")
      "hours"     — time window in hours (0 if no window specified)

    Example:
    >>> extract_lab_query("Most recent magnesium of S3032536 within last 24 hours?", "code for magnesium is MG")
    '{"mrn": "S3032536", "lab_code": "MG", "hours": 24}'
    >>> extract_lab_query("Most recent CBG of S2823623?", "code for CBG is GLU")
    '{"mrn": "S2823623", "lab_code": "GLU", "hours": 0}'
    """
    ...


@interface
def extract_referral(instruction: str, context: str) -> str:
    """Extract service-referral order fields. JSON string return.

    Keys:
      "mrn"          — patient MRN
      "snomed_code"  — SNOMED referral code from the context
      "display"      — short display name for the referral type
      "note"         — free-text comment / Situation-Background block

    Example:
    >>> extract_referral(
    ...     'Order orthopedic surgery referral for S2016972. "Situation: acute left knee injury..."',
    ...     "SNOMED code for orthopedic surgery referral is 306181000000106.",
    ... )
    '{"mrn": "S2016972", "snomed_code": "306181000000106", "display": "orthopedic surgery referral", "note": "Situation: acute left knee injury..."}'
    """
    ...


@interface
def extract_cond_med_order(instruction: str, context: str) -> str:
    """Extract fields for a conditional single-medication order. JSON string return.

    Covers task types where a lab value is checked and, if out-of-range,
    ONE medication order is placed (e.g. low magnesium → replacement IV
    magnesium).

    Keys:
      "mrn"       — patient MRN
      "lab_code"  — short lab code to check (e.g. "MG")
      "hours"     — time window for the lab check (0 if none)
      "ndc_code"  — NDC medication code
      "display"   — medication display name (e.g. "replacement IV magnesium")

    Example:
    >>> extract_cond_med_order(
    ...     "Check S6315806's serum magnesium in last 24h. If low, order replacement IV magnesium.",
    ...     "code for magnesium is MG. NDC for replacement IV magnesium is 0338-1715-40.",
    ... )
    '{"mrn": "S6315806", "lab_code": "MG", "hours": 24, "ndc_code": "0338-1715-40", "display": "replacement IV magnesium"}'
    """
    ...


@interface
def extract_multi_step_order(instruction: str, context: str) -> str:
    """Extract fields for a multi-step conditional order. JSON string return.

    Covers task types where a low lab value triggers BOTH a medication
    order AND a follow-up lab order (e.g. low potassium → replacement
    potassium + morning serum potassium check).

    Keys:
      "mrn"                 — patient MRN
      "lab_code"            — lab code for the initial check (e.g. "K")
      "ndc_code"            — NDC medication code
      "med_display"         — medication display name
      "followup_loinc_code" — LOINC code for the follow-up lab order
      "followup_display"    — display name for the follow-up lab order

    If the follow-up LOINC code is not given explicitly, use
    "2823-3" for potassium serum.

    Example:
    >>> extract_multi_step_order(
    ...     "Check S3241217's most recent potassium. If low, order replacement potassium. Pair with a morning serum potassium level.",
    ...     "code for potassium is K. NDC for replacement potassium is 40032-917-01.",
    ... )
    '{"mrn": "S3241217", "lab_code": "K", "ndc_code": "40032-917-01", "med_display": "replacement potassium", "followup_loinc_code": "2823-3", "followup_display": "Potassium serum"}'
    """
    ...


@interface
def extract_stale_check(instruction: str, context: str) -> str:
    """Extract fields for a stale-lab check. JSON string return.

    Reads the latest lab value; if older than a cutoff (commonly 1 year),
    place a new lab order.

    Keys:
      "mrn"         — patient MRN
      "lab_code"    — short lab code (e.g. "A1C")
      "loinc_code"  — LOINC code to use when ordering a new lab
      "display"     — display name for the lab order (e.g. "HbA1C")

    Example:
    >>> extract_stale_check(
    ...     "Last HbA1C for S6227720? If older than 1 year, order a new HbA1C lab.",
    ...     "code for HbA1C is A1C. LOINC code for ordering HbA1C lab is 4548-4.",
    ... )
    '{"mrn": "S6227720", "lab_code": "A1C", "loinc_code": "4548-4", "display": "HbA1C"}'
    """
    ...
