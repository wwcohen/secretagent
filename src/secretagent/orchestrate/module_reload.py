"""Helpers for reloading evolved ptools modules during orchestration.

OrchestrationLearner repeatedly executes edited ptools source under the same
module name. A plain ``exec_module`` leaves two kinds of stale state behind:

* module globals for functions that were removed by a later edit;
* Interface objects registered by earlier executions of the same module.

Both are local to the orchestration workflow. This module keeps that cleanup
out of the shared core/implementation factories.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _drop_interfaces_for_module(module_name: str) -> int:
    """Remove registered Interface objects defined by module_name."""
    from secretagent.core import all_interfaces

    interfaces = all_interfaces()
    before = len(interfaces)
    interfaces[:] = [
        iface for iface in interfaces
        if getattr(iface.func, '__module__', None) != module_name
    ]
    return before - len(interfaces)


def exec_ptools_module(module: ModuleType, path: str | Path) -> ModuleType:
    """Re-execute a ptools file into an existing module object cleanly."""
    module_name = module.__name__
    path = Path(path)
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f'could not load module spec for {path}')

    _drop_interfaces_for_module(module_name)

    module.__dict__.clear()
    module.__dict__.update(
        __name__=module_name,
        __file__=str(path),
        __package__=spec.parent,
        __loader__=spec.loader,
        __spec__=spec,
        __builtins__=__builtins__,
    )
    spec.loader.exec_module(module)
    return module
