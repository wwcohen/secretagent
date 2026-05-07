"""Context manager that will keep track of what Interfaced are called
while it is active, and also collect llm usage statistics.

Example:

  with record.recorder() as rollout:
    result = sports_understanding_workflow("DeMar DeRozan was called for the goal tend.")

rollout now is a list of Interfaces that were called, in order of
completion, along with usage information for each.

Thread-safe: each thread gets its own recording state via threading.local().
Module-level RECORDING/RECORD are kept in sync for main-thread backward compat.
"""

import threading
from contextlib import contextmanager

_local = threading.local()
RECORDING = False
RECORD = []

@contextmanager
def recorder():
    """Start recording subagent actions.

    Returns a list of dicts, each dict describing a subagent call.
    Thread-safe: each thread records independently.
    """
    global RECORDING, RECORD
    _local.recording = True
    _local.record = []
    RECORDING = True
    RECORD = _local.record
    yield _local.record
    _local.recording = False
    _local.record = []
    RECORDING = False
    RECORD = []

def record(**kw):
    if getattr(_local, 'recording', False):
        _local.record.append({**kw})
