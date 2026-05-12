"""FHIR interaction tools for MedAgentBench.

Provides fhir_get and fhir_post as plain callables that pydantic-ai
can use as tools. Also manages server verification and POST logging.

POST log is thread-local to support parallel case evaluation.
"""

import json
import threading
import requests

FHIR_API_BASE = "http://localhost:8080/fhir/"

# Thread-local storage for per-case POST log
_local = threading.local()


def set_api_base(base: str):
    """Set the FHIR API base URL."""
    global FHIR_API_BASE
    FHIR_API_BASE = base


def verify_fhir_server() -> bool:
    """Check that the FHIR server is reachable."""
    try:
        resp = requests.get(f"{FHIR_API_BASE}metadata", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def clear_post_log():
    """Clear the POST log before each evaluation case."""
    _local.post_log = []


def get_post_log() -> list[dict]:
    """Return a copy of the POST log for evaluation."""
    return list(getattr(_local, 'post_log', []))


def log_post(url: str, payload: dict):
    """Append a POST entry to the thread-local log."""
    if not hasattr(_local, 'post_log'):
        _local.post_log = []
    _local.post_log.append({"url": url, "payload": payload})


def _send_get_request_raw(url, params=None, headers=None):
    """Raw GET request matching the original MedAgentBench utils.send_get_request interface.

    Returns dict with 'status_code' and 'data' keys (or 'error' on failure).
    Used by refsol.py graders to query the FHIR server for expected answers.

    Note: matches the original utils.py behavior exactly — checks Content-Type
    with == (not 'in'), so application/fhir+json falls through to response.text.
    """
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        ct = response.headers.get('Content-Type', '')
        if ct == 'application/json':
            return {"status_code": response.status_code, "data": response.json()}
        return {"status_code": response.status_code, "data": response.text}
    except Exception as e:
        return {"error": str(e)}


def fhir_get(url: str) -> str:
    """Send a GET request to the FHIR server.

    The url should be the full FHIR endpoint with query parameters,
    e.g. "http://localhost:8080/fhir/Patient?family=Smith&birthdate=1990-01-01"

    Returns the JSON response as a string, or an error message.
    """
    try:
        separator = '&' if '?' in url else '?'
        full_url = f"{url}{separator}_format=json"
        response = requests.get(full_url, timeout=30)
        response.raise_for_status()
        if 'application/json' in response.headers.get('Content-Type', ''):
            return json.dumps(response.json())
        return response.text
    except Exception as e:
        return f"Error in sending the GET request: {e}"


def fhir_post(url: str, payload: str) -> str:
    """Send a POST request to create a FHIR resource.

    The url is the FHIR endpoint (e.g. "http://localhost:8080/fhir/MedicationRequest").
    The payload is a JSON string with the resource data.

    Returns a success message or an error message.
    """
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError) as e:
        return f"Invalid POST request: {e}"
    log_post(url, data)
    return (
        "POST request accepted and executed successfully. "
        "Please call FINISH if you have got answers for all the "
        "questions and finished all the requested tasks"
    )
