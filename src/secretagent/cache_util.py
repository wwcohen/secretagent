"""Lazy cachier decoration that respects runtime config.

Instead of using @cachier at decoration time (which bakes in params
before config is loaded), this module provides a `cached()` wrapper
that reads cachier config at call time and applies it dynamically.
"""

from secretagent import config

# Cache of decorated functions: (fn, config_key) -> decorated_fn
_DECORATED = {}


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
        from cachier import cachier as cachier_decorator
        _DECORATED[cache_key] = cachier_decorator(**merged)(fn)

    return _DECORATED[cache_key]


def clear_all_caches():
    """Clear all cachier caches created through cached()."""
    for decorated_fn in _DECORATED.values():
        try:
            decorated_fn.clear_cache()
        except Exception:
            pass
    _DECORATED.clear()
