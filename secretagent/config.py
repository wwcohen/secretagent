from contextlib import contextmanager

GLOBAL_CONFIG = {}

def configure(**kw):
    """Set global configuration properties.
    """
    global GLOBAL_CONFIG
    GLOBAL_CONFIG.update(kw)

def get(key: str, local_config=None):
    """Get a value from the local_config or global_config.

    Prefer the local_config if both are set.
    """
    global GLOBAL_CONFIG
    if local_config:
        return local_config.get(key) or GLOBAL_CONFIG.get(key)
    else:
        return GLOBAL_CONFIG.get(key)

@contextmanager
def configuration(**kw):
    """Add some additional configuration information.

    Original configuration will be restored on exit.
    """
    global GLOBAL_CONFIG
    saved_config = {**GLOBAL_CONFIG}
    configure(**kw)
    yield GLOBAL_CONFIG
    GLOBAL_CONFIG = saved_config

