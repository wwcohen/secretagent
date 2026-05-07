"""Implementation.Factory that loads a learned function from a training directory."""

import importlib.util
from glob import glob
from pathlib import Path
from typing import Any

from omegaconf import OmegaConf

from secretagent import config
from secretagent.core import Implementation, _FACTORIES, register_factory


def _load_learned_module(learned_path):
    """Import a learned.py file and return the module."""
    spec = importlib.util.spec_from_file_location('learned', learned_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_FORBIDDEN_NAMES = frozenset([
    'open', 'exec', 'eval', 'compile', '__import__', 'globals', 'locals',
    'getattr', 'setattr', 'delattr', 'breakpoint', 'exit', 'quit',
    'input', 'memoryview', 'type.__subclasses__',
])

_SAFE_MODULES = ['re', 'json', 'datetime', 'math', 'collections',
                 'itertools', 'functools', 'string', 'operator',
                 'copy', 'decimal', 'fractions', 'statistics',
                 'textwrap', 'unicodedata', 'dataclasses', 'enum',
                 'abc', 'typing']


def _load_learned_sandboxed(learned_path, func_name):
    """Load a learned.py file in a restricted namespace and return the function.

    Uses exec with restricted builtins: dangerous operations (open, eval,
    exec, __import__ of non-safe modules) are blocked, but standard library
    modules (re, json, math, etc.) are allowed. This gives enough freedom
    for complex code (regex, helper functions, classes) while blocking
    file I/O and arbitrary imports.
    """
    import builtins as _builtins

    code = Path(learned_path).read_text(encoding='utf-8')

    # Build restricted builtins: allow most, block dangerous ones
    safe_builtins = {k: v for k, v in vars(_builtins).items()
                     if k not in _FORBIDDEN_NAMES}

    # Replace __import__ with one that only allows safe modules
    _real_import = _builtins.__import__
    def _restricted_import(name, *args, **kwargs):
        top_level = name.split('.')[0]
        if top_level not in _SAFE_MODULES:
            raise ImportError(f'import of {name!r} is not allowed in sandboxed code')
        return _real_import(name, *args, **kwargs)
    safe_builtins['__import__'] = _restricted_import

    namespace = {'__builtins__': safe_builtins}
    exec(compile(code, str(learned_path), 'exec'), namespace)
    fn = namespace.get(func_name)
    if fn is None or not callable(fn):
        raise AttributeError(
            f'{learned_path} does not define a function named {func_name!r}')
    return fn


def _find_learned_path(interface_name, learner):
    """Find the most recent learned.py matching the interface and learner."""
    train_dir = config.require('learn.train_dir')
    pattern = str(Path(train_dir) / f'*{interface_name}__{learner}' / 'learned.py')
    matches = sorted(glob(pattern))
    if not matches:
        raise FileNotFoundError(
            f'no learned implementation found matching {pattern}')
    return Path(matches[-1])


def _build_backoff_impl(interface, workdir):
    """Build a backoff implementation from source config yamls.

    Reads each yaml in workdir/source_configs/*.yaml, extracts the
    config for ptools.INTERFACE, verifies they all agree, and builds
    the implementation.
    """
    cfg_files = sorted(workdir.glob('source_configs/*.yaml'))
    if not cfg_files:
        raise FileNotFoundError(
            f'no source config files found in {workdir / "source_configs"}')
    impl_cfg = None
    for cfg_file in cfg_files:
        yaml_cfg = OmegaConf.load(cfg_file)
        ptools_cfg = OmegaConf.to_container(yaml_cfg.get('ptools', {}), resolve=True)
        iface_cfg = ptools_cfg.get(interface.name)
        if iface_cfg is None:
            raise ValueError(
                f'{cfg_file} has no ptools.{interface.name} config')
        if impl_cfg is None:
            impl_cfg = iface_cfg
        elif impl_cfg != iface_cfg:
            raise ValueError(
                f'conflicting ptools.{interface.name} configs across source yamls: '
                f'{impl_cfg} vs {iface_cfg}')
    factory_kws = dict(impl_cfg)
    method = factory_kws.pop('method')
    factory = _FACTORIES[method]
    return factory.build_implementation(interface, **factory_kws)


class LearnedCodeFactory(Implementation.Factory):
    """Load a learned implementation from a training directory.

    At build time, finds the most recent timestamped directory matching
    TRAIN_DIR/*INTERFACE__LEARNER/learned.py, imports the function named
    INTERFACE from it, and binds that as the implementation.

    If backoff=True, also builds the original implementation from the
    source config yamls. The bound function calls the learned function
    first, falling back to the backoff implementation when the learned
    function returns None.

    Examples:
      foo.implement_via('learned_code', learner='rote')
      foo.implement_via('learned_code', learner='rote', backoff=True)
    """

    learned_fn: Any = None
    backoff_impl: Any = None

    def setup(self, learner: str, backoff: bool = False, sandbox: bool = None, **_kw):
        interface = self.bound_interface
        learned_path = _find_learned_path(interface.name, learner)
        # Default: sandbox for codedistill/e2e_codedistill (LLM-generated code), no sandbox for rote
        if sandbox is None:
            sandbox = (learner in ('codedistill', 'e2e_codedistill'))
        if sandbox:
            self.learned_fn = _load_learned_sandboxed(learned_path, interface.name)
        else:
            mod = _load_learned_module(learned_path)
            fn = getattr(mod, interface.name, None)
            if fn is None:
                raise AttributeError(
                    f'{learned_path} does not define a function named {interface.name!r}')
            self.learned_fn = fn
        if backoff:
            self.backoff_impl = _build_backoff_impl(interface, learned_path.parent)

    def __call__(self, *args, **kw):
        result = self.learned_fn(*args, **kw)
        if result is None and self.backoff_impl is not None:
            return self.backoff_impl.implementing_fn(*args, **kw)
        return result

register_factory('learned_code', LearnedCodeFactory())
