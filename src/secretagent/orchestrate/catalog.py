"""Collect ptool metadata for orchestrator prompts.

The PtoolCatalog gathers Interface signatures and docstrings into a
format that can be rendered into an LLM prompt for pipeline composition.
"""

from dataclasses import dataclass, field
from typing import Any

from secretagent.core import Interface


@dataclass
class PtoolInfo:
    """Metadata about a single ptool for the orchestrator.

    Lightweight dataclass decoupled from Interface so future versions
    can add metrics (cost, latency, success_rate) without touching core.
    """
    name: str
    doc: str
    src: str                # full stub source (signature + docstring)
    param_names: list[str] = field(default_factory=list)
    param_types: dict[str, str] = field(default_factory=dict)
    return_type: str = 'Any'

    # Future: runtime metrics for optimizer-based selection (V2+)
    avg_cost: float | None = None
    avg_latency: float | None = None
    success_rate: float | None = None
    unused_success_rate: float | None = None
    lift: float | None = None


def _type_name(t: Any) -> str:
    """Get a readable name from a type annotation."""
    return getattr(t, '__name__', str(t))


class PtoolCatalog:
    """A collection of ptool metadata, ready to render into a prompt."""

    def __init__(self, ptools: list[PtoolInfo]):
        self.ptools = ptools

    @classmethod
    def from_interfaces(
        cls,
        interfaces: list[Interface],
        exclude: list[str] | None = None,
        include_unimplemented: bool = False,
    ) -> 'PtoolCatalog':
        """Build catalog from Interface objects.

        Args:
            interfaces: list of Interface objects to include
            exclude: names of interfaces to exclude (e.g. the workflow itself)
            include_unimplemented: if False, skip interfaces without an implementation
        """
        exclude_set = set(exclude or [])
        ptools = []
        for iface in interfaces:
            if iface.name in exclude_set:
                continue
            if not include_unimplemented and iface.implementation is None:
                continue
            annotations = iface.annotations
            param_names = [k for k in annotations if k != 'return']
            param_types = {k: _type_name(v) for k, v in annotations.items() if k != 'return'}
            return_type = _type_name(annotations.get('return', str))
            ptools.append(PtoolInfo(
                name=iface.name,
                doc=iface.doc,
                src=iface.src,
                param_names=param_names,
                param_types=param_types,
                return_type=return_type,
            ))
        return cls(ptools)

    @classmethod
    def from_module(
        cls,
        module,
        exclude: list[str] | None = None,
        include_unimplemented: bool = False,
    ) -> 'PtoolCatalog':
        """Build catalog from all Interface objects defined in a module."""
        interfaces = [
            getattr(module, name) for name in dir(module)
            if isinstance(getattr(module, name), Interface)
        ]
        return cls.from_interfaces(interfaces, exclude=exclude,
                                   include_unimplemented=include_unimplemented)

    def render(self) -> str:
        """Render catalog as text for the LLM prompt.

        Returns the raw stub source (signature + docstring) for each ptool,
        separated by blank lines.
        """
        return '\n\n'.join(pt.src.rstrip() for pt in self.ptools)

    @property
    def names(self) -> list[str]:
        """Names of all ptools in the catalog."""
        return [pt.name for pt in self.ptools]

    def __len__(self) -> int:
        return len(self.ptools)

    def __repr__(self) -> str:
        return f'PtoolCatalog({self.names})'
