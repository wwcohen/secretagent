"""Hierarchical configuration backed by OmegaConf.
"""

from contextlib import contextmanager
from omegaconf import OmegaConf, DictConfig
from typing import Any

GLOBAL_CONFIG: DictConfig = OmegaConf.create()

def configure(yaml_file=None, cfg=None, **kw):
    """Merge in config from a DictConfig, YAML file path, or keyword args.

    Arguments:
      yaml_file: will be passed to OmegaConf.load() unless it's None
      cfg: will be passed to OmegaConf.merge() unless it's None

    All other keyword arguments will be merged with OmegaConf.
    """
    global GLOBAL_CONFIG
    if yaml_file is not None:
        GLOBAL_CONFIG = OmegaConf.merge(GLOBAL_CONFIG, OmegaConf.load(yaml_file))
    if cfg is not None:
        GLOBAL_CONFIG = OmegaConf.merge(GLOBAL_CONFIG, cfg)
    if kw:
        GLOBAL_CONFIG = OmegaConf.merge(GLOBAL_CONFIG, kw)

def get(key: str, default=None) -> Any:
    """Get a value using dot-notation (e.g. 'llm.model').
    """
    val = OmegaConf.select(GLOBAL_CONFIG, key)
    return val if val is not None else default

def require(key: str) -> Any:
    """Get a required value using dot-notation (e.g. 'llm.model').

    If the value is not present or is None, throw an error.
    """
    val = get(key)
    if val is None:
        raise ValueError(f'required key {key} is not in configuration')
    return val

@contextmanager
def configuration(cfg=None, **kw):
    """Temporarily merge additional configuration.

    Original configuration will be restored on exit.
    """
    global GLOBAL_CONFIG
    saved = GLOBAL_CONFIG.copy()
    configure(cfg, **kw)
    yield GLOBAL_CONFIG
    GLOBAL_CONFIG = saved
