"""Hierarchical configuration backed by OmegaConf.
"""

from contextlib import contextmanager
from omegaconf import OmegaConf, DictConfig
from typing import Any
from pathlib import Path
import warnings

GLOBAL_CONFIG: DictConfig = OmegaConf.create()

def reset():
    """Drop all accumulated configuration state.

    OmegaConf.merge is additive, so calling configure() repeatedly piles
    keys onto GLOBAL_CONFIG indefinitely. Tests and drivers that want to
    start a fresh scope should call reset() first.
    """
    global GLOBAL_CONFIG
    GLOBAL_CONFIG = OmegaConf.create()


def configure(yaml_file=None, cfg=None, dotlist=None, **kw):
    """Merge in config from a DictConfig, YAML file path, or keyword args.

    Arguments:
      yaml_file: will be passed to OmegaConf.load() unless it's None
      cfg: will be passed to OmegaConf.merge() unless it's None
      dotlist: a list of strings like "llm.model=gpt3.5" or None

    All other keyword arguments will be merged with OmegaConf.
    """
    global GLOBAL_CONFIG
    if yaml_file is not None:
        GLOBAL_CONFIG = OmegaConf.merge(GLOBAL_CONFIG, OmegaConf.load(yaml_file))
    if cfg is not None:
        GLOBAL_CONFIG = OmegaConf.merge(GLOBAL_CONFIG, cfg)
    if dotlist is not None:
        GLOBAL_CONFIG = OmegaConf.merge(GLOBAL_CONFIG, OmegaConf.from_dotlist(dotlist))
    if kw:
        GLOBAL_CONFIG = OmegaConf.merge(GLOBAL_CONFIG, kw)

def get(key: str, default=None) -> Any:
    """Get a value using dot-notation (e.g. 'llm.model').
    """
    val = OmegaConf.select(GLOBAL_CONFIG, key)
    return val if val is not None else default

def require(key: str) -> Any:
    """Get a required value using dot-notation (e.g. 'llm.model').

    If the value is not present or is None an error is thrown.
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
    configure(cfg=cfg, **kw)
    yield GLOBAL_CONFIG
    GLOBAL_CONFIG = saved

def set_root(new_root):
    """Resolve relative paths in config against new_root.

    Finds every config value whose key ends with '_dir' or '_file',
    and if the value is a relative path, prepends new_root to make
    it absolute.
    """
    from pathlib import Path
    new_root = Path(new_root)
    OmegaConf.update(GLOBAL_CONFIG, 'root', str(new_root))

    def _resolve(cfg, prefix=''):
        for key in cfg:
            full_key = f'{prefix}{key}' if prefix else key
            val = cfg[key]
            if isinstance(val, DictConfig):
                _resolve(val, full_key + '.')
            elif isinstance(val, str) and (key.endswith('_dir') or key.endswith('_file')):
                if not Path(val).is_absolute():
                    OmegaConf.update(GLOBAL_CONFIG, full_key, str(new_root / val))

    _resolve(GLOBAL_CONFIG)

def save(filename):
    """Save the global configuration in a file.
    """
    with open(filename, 'w') as fp:
        fp.write(OmegaConf.to_yaml(GLOBAL_CONFIG))

#
# some utils for working with configs that don't involve changing the global config
#

def load_yaml_cfg(pathlike):
    path = Path(pathlike)
    if not path.exists():
        raise ValueError(f'expected config file at {path}')
    return OmegaConf.load(path)

def to_dotlist(cfg):
    """Flatten a nested dict into dot-separated keys."""
    def collect_pairs(cfg, ancestors=[]):
        def lhs(ancestors, key):
            return ".".join(ancestors + [key])
        pairs = []
        for k, v in cfg.items():
            if isinstance(v, DictConfig):
                pairs.extend(collect_pairs(v, ancestors + [k]))
            else:
                pairs.append(f'{lhs(ancestors, k)}={v}')
        return pairs
    return collect_pairs(cfg, [])

def sanity_check(context_msg: str, dotlist, full_cfg):
    """
    """
    for pair in dotlist:
        key, val = pair.split('=')
        if OmegaConf.select(full_cfg, key) is None:
            expected_keys = [pair.split('=')[0] for pair in to_dotlist(full_cfg)]
            warnings.warn(f'{context_msg}: unexpected config key {key} in {pair}: expected {expected_keys}')
