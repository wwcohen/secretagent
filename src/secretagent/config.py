"""Hierarchical configuration backed by OmegaConf.
"""

from contextlib import contextmanager
from omegaconf import OmegaConf, DictConfig
from typing import Any
from pathlib import Path
from dotenv import load_dotenv
import os
import warnings

GLOBAL_CONFIG: DictConfig = OmegaConf.create()

def configure(yaml_file=None, cfg=None, dotlist=None, **kw):
    """Merge in config from a DictConfig, YAML file path, or keyword args.

    Arguments:
      yaml_file: will be passed to OmegaConf.load() unless it's None
      cfg: will be passed to OmegaConf.merge() unless it's None
      dotlist: a list of strings like "llm.model=gpt3.5" or None

    All other keyword arguments will be merged with OmegaConf.
    Merge order is yaml_file, cfg, dotlist, kw.
    """
    global GLOBAL_CONFIG

    # we need the pathto.repo to be inserted before we
    # load the yaml, since it might not be present
    GLOBAL_CONFIG = _add_path_to_repo_key(GLOBAL_CONFIG)

    if yaml_file is not None:
        GLOBAL_CONFIG = OmegaConf.merge(GLOBAL_CONFIG, OmegaConf.load(yaml_file))
    if cfg is not None:
        GLOBAL_CONFIG = OmegaConf.merge(GLOBAL_CONFIG, cfg)
    if dotlist is not None:
        GLOBAL_CONFIG = OmegaConf.merge(GLOBAL_CONFIG, OmegaConf.from_dotlist(dotlist))
    if kw:
        GLOBAL_CONFIG = OmegaConf.merge(GLOBAL_CONFIG, kw)

    # if we've loaded a snapshot with someone else's pathto.repo,
    # then override with ours
    GLOBAL_CONFIG = _add_path_to_repo_key(GLOBAL_CONFIG)


_DOTENV_LOADED = False

def _load_dotenv_once():
    """Load the repo's .env into the environment, exactly once.

    The .env is looked up at the repo root (sentinel-anchored) so that
    ``${oc.env:...}`` interpolations resolve regardless of the current
    working directory. Falls back to dotenv's default cwd-upward search
    if the sentinel can't be found.
    """
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    try:
        load_dotenv(find_project_root() / '.env')
    except FileNotFoundError:
        load_dotenv()
    _DOTENV_LOADED = True

def repo_root() -> str:
    """The repo root: ``$PATHTO_REPO`` if set (e.g. via .env), else
    auto-detected from the ``.root-sentinel.txt`` marker.

    When auto-detected, the value is written back into ``os.environ`` so
    that ``${oc.env:PATHTO_REPO}`` resolves to the same path.
    """
    _load_dotenv_once()
    repo = os.environ.get('PATHTO_REPO')
    if not repo:
        repo = str(find_project_root().resolve())
        os.environ['PATHTO_REPO'] = repo
    return repo

def _add_path_to_repo_key(cfg):
    """Set pathto.repo to the actual path to the secretagent repo.
    """
    repo_default = {'pathto':{'repo': repo_root()}}
    cfg = OmegaConf.merge(cfg, repo_default)
    return cfg

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
    try:
        yield GLOBAL_CONFIG
    finally:
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

    .. deprecated:: better practice is to specify locations relative
    to ${root.task}, for experimental "inputs", and ${root.logs},
    for "outputs".  These in turn should be specified relative to
    ${root.repo} which is pre-defined.

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

def reset():
    """Drop all accumulated configuration state.

    OmegaConf.merge is additive, so calling configure() repeatedly piles
    keys onto GLOBAL_CONFIG indefinitely. Tests and drivers that want to
    start a fresh scope should call reset() first.
    """
    global GLOBAL_CONFIG
    GLOBAL_CONFIG = OmegaConf.create()


def save(filename):
    """Save the global configuration in a file.
    """
    global GLOBAL_CONFIG
    # add info about where this was originally saved
    GLOBAL_CONFIG = OmegaConf.merge(
        GLOBAL_CONFIG, 
        {'saved_under': Path(filename).parent.name})
    with open(filename, 'w') as fp:
        fp.write(OmegaConf.to_yaml(GLOBAL_CONFIG))

#
# some utils for working with configs that don't involve changing the global config
#

def load_yaml_cfg(pathlike):
    yaml_path = Path(pathlike)
    cfg = OmegaConf.load(yaml_path)
    # if we've loaded a snapshot with someone else's pathto.repo,
    # then override with ours
    cfg = _add_path_to_repo_key(cfg)
    return cfg

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
    """Make sure everything in a dotlist overrides an actual key in the config.
    """
    for pair in dotlist:
        key, val = pair.split('=')
        if OmegaConf.select(full_cfg, key) is None:
            expected_keys = [pair.split('=')[0] for pair in to_dotlist(full_cfg)]
            warnings.warn(f'{context_msg}: unexpected config key {key} in {pair}: expected {expected_keys}')
