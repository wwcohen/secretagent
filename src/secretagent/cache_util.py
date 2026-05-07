"""Lazy cachier decoration that respects runtime config.

Instead of using @cachier at decoration time (which bakes in params
before config is loaded), this module provides a `cached()` wrapper
that reads cachier config at call time and applies it dynamically.
"""

import os
import pickle
import warnings

from secretagent import config

# Cache of decorated functions: (fn, config_key) -> decorated_fn
_DECORATED = {}


def _disable_watchdog_observer():
    """Monkey-patch watchdog.observers.Observer to a no-op.

    cachier's default observer uses macOS fsevents to watch the cache
    file; under heavy sequential access the observer thread and the
    caller deadlock inside libsystem_pthread. Our use case runs one
    process at a time and doesn't need cross-process cache invalidation,
    so we can safely disable the observer entirely.

    Call this once, before the first cachier decorator is constructed.
    Idempotent.
    """
    try:
        import watchdog.observers
    except ImportError:
        return
    if getattr(watchdog.observers, '_secretagent_patched', False):
        return

    class _NoopObserver:
        def __init__(self, *a, **kw): pass
        def start(self): pass
        def stop(self): pass
        def join(self, *a, **kw): pass
        def schedule(self, *a, **kw): return None
        def unschedule(self, *a, **kw): pass
        def unschedule_all(self): pass
        def is_alive(self): return False

    watchdog.observers.Observer = _NoopObserver
    watchdog.observers._secretagent_patched = True


def cached(fn, **cachier_kw):
    """Return a cachier-decorated version of fn using current config.

    If cachier.enable_caching is False in config, returns fn directly.
    Otherwise, decorates fn with @cachier using params from config.cachier
    (merged with any explicit cachier_kw). The decorated version is cached
    and reused until the config changes.
    """
    cachier_cfg = dict(config.get('cachier', {}) or {})
    enable = cachier_cfg.pop('enable_caching', True)

    if not enable:
        return fn

    # Merge config params with explicit kwargs (explicit wins)
    merged = {**cachier_cfg, **cachier_kw}

    # Cache the decorated function, keyed by (fn, config snapshot)
    cache_key = (fn, str(sorted(merged.items())))
    if cache_key not in _DECORATED:
        # Disable watchdog observer BEFORE importing cachier — fixes a
        # macOS-only deadlock where the fsevents observer thread and the
        # main thread mutually block waiting on libsystem_pthread locks.
        _disable_watchdog_observer()
        from cachier import cachier as cachier_decorator
        _DECORATED[cache_key] = cachier_decorator(**merged)(fn)

    return _DECORATED[cache_key]


_STATS_KEYS = {'input_tokens', 'output_tokens', 'latency', 'cost'}


def _is_stats_dict(obj):
    """True if obj is a dict containing the expected stats keys."""
    return isinstance(obj, dict) and _STATS_KEYS.issubset(obj)


def _find_stats(val):
    """Find a stats dict inside a cached return value (typically a tuple)."""
    if _is_stats_dict(val):
        return val
    if isinstance(val, tuple):
        for item in val:
            if _is_stats_dict(item):
                return item
    return None


def extract_cached_stats(cache_dir=None):
    """Extract stats dicts from the cachier cache of LLM calls.

    Scans all cachier pickle files in cache_dir, and for each cached
    return value finds the stats dict (identified by having keys
    input_tokens, output_tokens, latency, cost).

    Args:
        cache_dir: Path to the cachier cache directory.  If None,
            uses the configured cachier.cache_dir.

    Returns:
        List of stats dicts, each with keys like input_tokens,
        output_tokens, latency, cost.
    """
    if cache_dir is None:
        cache_dir = config.get('cachier', {}).get('cache_dir')
    if cache_dir is None:
        raise ValueError("No cache_dir specified and none configured in cachier.cache_dir")

    stats_list = []
    for fname in os.listdir(cache_dir):
        fpath = os.path.join(cache_dir, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, 'rb') as f:
                cache_dict = pickle.load(f)
        except (pickle.UnpicklingError, EOFError, Exception):
            continue
        if not isinstance(cache_dict, dict):
            continue
        for entry in cache_dict.values():
            val = getattr(entry, 'value', None)
            if val is None:
                continue
            stats = _find_stats(val)
            if stats is not None:
                stats_list.append(stats)
    return stats_list


def clear_all_caches():
    """Clear all cachier caches created through cached()."""
    for decorated_fn in _DECORATED.values():
        try:
            decorated_fn.clear_cache()
        except Exception as e:
            warnings.warn(f"Failed to clear cache for {decorated_fn.__name__}: {e}")
    _DECORATED.clear()
