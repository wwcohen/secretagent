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

SENTINEL_FILE = '.root-sentinel.txt'
_PATH_KEY_SUFFIXES = ('_dir', '_file', '_module')

def find_project_root(start=None):
    """Walk up from start (default CWD) looking for SENTINEL_FILE.

    Returns the Path of the directory containing the sentinel,
    or raises FileNotFoundError.
    """
    start = Path(start) if start else Path.cwd()
    for p in [start.resolve(), *start.resolve().parents]:
        if (p / SENTINEL_FILE).exists():
            return p
    raise FileNotFoundError(
        f'Could not find {SENTINEL_FILE} in any parent of {start}'
    )

def set_root(new_root):
    """Resolve relative paths in config against new_root.

    .. deprecated:: Use config.save() which now auto-resolves paths
       relative to the project root. Callers should stop calling set_root
       and let relative paths remain relative at runtime.

    Finds every config value whose key ends with '_dir' or '_file',
    and if the value is a relative path, prepends new_root to make
    it absolute.
    """
    new_root = Path(new_root)
    OmegaConf.update(GLOBAL_CONFIG, 'root', str(new_root))

    def _resolve(cfg, prefix=''):
        for key in cfg:
            full_key = f'{prefix}{key}' if prefix else key
            val = cfg[key]
            if isinstance(val, DictConfig):
                _resolve(val, full_key + '.')
            elif isinstance(val, str) and (key.endswith(_PATH_KEY_SUFFIXES)):
                if not Path(val).is_absolute():
                    OmegaConf.update(GLOBAL_CONFIG, full_key, str(new_root / val))

    _resolve(GLOBAL_CONFIG)

def _reroot_paths(cfg, project_root):
    """Return a copy of cfg with _dir/_file/_module paths relative to project_root.

    Relative paths are resolved against CWD first, then made relative
    to project_root.  Absolute paths under project_root are also made
    relative.  Paths outside the project root are left absolute.
    """
    copy = OmegaConf.to_container(cfg, resolve=True)
    cwd = Path.cwd().resolve()
    project_root = Path(project_root).resolve()

    def _walk(d):
        for key, val in d.items():
            if isinstance(val, dict):
                _walk(val)
            elif isinstance(val, str) and (key.endswith(_PATH_KEY_SUFFIXES)):
                p = Path(val)
                if not p.is_absolute():
                    p = cwd / p
                p = p.resolve()
                try:
                    d[key] = str(p.relative_to(project_root))
                except ValueError:
                    d[key] = str(p)

    _walk(copy)
    return OmegaConf.create(copy)

def save(filename):
    """Save the global configuration in a file.

    Paths (keys ending in _dir, _file, or _module) are rewritten to be relative
    to the project root (found via .root-sentinel.txt).  If the project
    root cannot be found, the config is saved as-is.
    """
    try:
        root = find_project_root()
        augmented = OmegaConf.merge(GLOBAL_CONFIG, {'original_working_dir': '.'})
        to_save = _reroot_paths(augmented, root)
    except FileNotFoundError:
        to_save = GLOBAL_CONFIG
    with open(filename, 'w') as fp:
        fp.write(OmegaConf.to_yaml(to_save))

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
