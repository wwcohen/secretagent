from contextlib import contextmanager

RECORDING = False
RECORD = []

@contextmanager
def recorder():
    """Start recording subagent actions.

    Returns a list of dicts, each dict describing a subagent call.
    """
    global RECORDING, RECORD
    RECORDING = True; RECORD = []
    yield RECORD
    RECORDING = False; RECORD = []    

def _record(**kw):
    global RECORDING, RECORD
    if RECORDING:
        RECORD.append({**kw})
