"""Context manager that will keep track of what Interfaced are called
while it is active, and also collect llm usage statistics.

Example:

  with record.recorder() as rollout:
    result = sports_understanding_workflow("DeMar DeRozan was called for the goal tend.")
    
rollout now is a list of Interfaces that were called, in order of
completion, along with usage information for each.
"""

from contextlib import contextmanager

RECORDING = False
RECORD = []

@contextmanager
def recorder():
    """Start recording subagent actions.

    Returns a list of dicts, each dict describing a subagent call.
    """
    global RECORDING, RECORD
    RECORDING = True
    RECORD = []
    yield RECORD
    RECORDING = False
    RECORD = []

def record(**kw):
    global RECORDING, RECORD
    if RECORDING:
        RECORD.append({**kw})
