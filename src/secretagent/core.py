"""Core components of SecretAgents package: interfaces and implementations.
"""

import functools
import inspect

from abc import abstractmethod
from pydantic import BaseModel, Field
from typing import Any, Callable, Optional

# registries of defined interfaces and implementation factories

_INTERFACES : list['Interface'] = []
_FACTORIES : dict[str, 'Implementation.Factory'] = {}

def all_interfaces() -> list['Interface']:
    return _INTERFACES
    
def all_factories() -> list[tuple[str, 'Implementation.Factory']]:
    return _FACTORIES.items()

def register_factory(name: str, factory: 'Implementation.Factory'):
    """Register an Implementation.Factory under the given name."""
    _FACTORIES[name] = factory

class Interface(BaseModel):
    """Pythonic description of an agent, prompted model, or tool.

    Designed so that it can be bound to an Implemention at
    configuration time.
    """
    func: Callable = Field(description="The Python function defined by the stub")
    name: str = Field(description="Name of the stub function")
    doc: str = Field(description="Docstring for stub")
    src: str = Field(description="Source code for the stub")
    # Any rather than type because generic aliases like tuple[str, str, str]
    # are not instances of type, and Pydantic can't validate GenericAlias.
    annotations: dict[str, Any] = Field(description="Type annotations for the stub")
    implementation: Optional['Implementation'] = Field(
        default=None,
        description="Implemenation to which Implemenation is currently bound")

    def __call__(self, *args, **kw):
        if self.implementation is None:
            raise NotImplementedError(
                f'no implementation registered for interface "{self.name}"')
        return self.implementation.implementing_fn(*args, **kw)

    def implement_via(self, method: str, **kwargs):
        """Build an implementation for this interface.
        """
        factory = _FACTORIES[method]
        self.implementation = factory.build_implementation(self, **kwargs)

    def signature(self, *args, **kw):
        arg_str = ', '.join([repr(a) for a in args])
        kw_str = ', '.join([f'{lhs}={repr(rhs)}' for lhs, rhs in kw.items()])
        sep = ', ' if arg_str and kw_str else ''
        return_type = self.annotations['return'].__name__
        return f'{self.name}({arg_str}{sep}{kw_str}) -> {return_type}'


def interface(func: Callable) -> Interface:
    """Decorator to make a stub or function into an Interface.

    Example use:
    @interface
    def translate(english_sentence: str) -> str:
        ""Translate a sentence in English to French.""
        ...

    translate.implement_via('simulate_from_stub', model="claude-haiku")
    """
    full_src = inspect.getsource(func)
    trimmed_src = full_src[full_src.find('\ndef')+1:]
    result = Interface(
        func=func,
        name=func.__name__,
        doc=(func.__doc__ or ''),
        src=trimmed_src,
        annotations=func.__annotations__,
    )
    _INTERFACES.append(result)
    return result

def implement_via(method=None, **method_kw) -> Callable:
    """Decorator to make a stub or function into an Interface,
    and simultaneously provide an implementation.

    Example use:
    @implement_via('simulate_from_stub', model="claude-haiku")
    def translate(english_sentence: str) -> str:
        ""Translate a sentence in English to French.""
        ...
    """
    def wrapper(func):
        result = interface(func)
        result.implement_via(method, **method_kw)
        return result
    return wrapper

class Implementation(BaseModel):
    """An implemention for an Interface - mainly represented as a
    Python function.

    Also records how the Implemention was created (i.e., what
    Implemention.Factory was used).
    """
    implementing_fn: Callable
    factory_method: str
    factory_kwargs: dict[str, Any] = {}

    class Factory(BaseModel):
        """Build one kind of implementation in a configurable way.
        """
        @abstractmethod
        def build_fn(self, interface: 'Interface', **builder_kwargs) -> Callable:
            """Create a callable function that implements the interface.
            """
            ...

        def build_implementation(
                self, interface: 'Interface', **builder_kwargs) -> 'Implementation':
            """Create an Implementation for the interface.
            """
            # wrap the implementing function appropriately
            fn = self.build_fn(interface, **builder_kwargs)

            @functools.wraps(interface.func)
            def wrapped_fn(*fn_args, **fn_kw):
                return fn(*fn_args, **fn_kw)

            return Implementation(
                implementing_fn=wrapped_fn,
                factory_method=self.__class__.__name__,
                factory_kwargs=builder_kwargs)

# auto-register built-in factories
import secretagent.core_impl  # noqa: E402, F401
