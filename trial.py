import functools
import inspect

from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Any, Callable, Optional

# registries of defined interfaces and implementation factories

_INTERFACES : list['Interface'] = []
_FACTORIES : dict[str, 'Implementation.Factory'] = {}

class Interface(BaseModel):
    """Pythonic description of an agent, prompted model, or tool.

    Designed so that it can be bound to an Implemention at
    configuration time.
    """
    func: Callable = Field(description="The Python function defined by the stub")
    name: str = Field(description="Name of the stub function")
    doc: str = Field(description="Docstring for stub")
    src: str = Field(description="Source code for the stub")
    annotations: dict[str, type] = Field(description="Type annotations for the stub")
    implementation: Optional[Implementation] = Field(
        default=None,
        description="Implemenation to which Implemenation is currently bound")

    def __call__(self, *args, **kw):
        if self.implementation is None:
            raise NotImplementedError(
                f'no implementation registered for interface "{self.name}"')
        return self.implementation.implementing_fn(*args, **kw)

    def via(self, method: str, *kwargs):
        """Build an implementation for this interface.
        """
        factory = _FACTORIES[method]
        self.implementation = factory.build(self, *kwargs)

def interface(func: Callable) -> Interface:
    """Decorator to make a stub or function and interface.

    Example use:
    @interface
    def translate(english_sentence: str) -> str:
        ""Translate a sentence in English to French.""
        ...

    translate.via('simulate_from_stub', model="claude-haiku")
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

class Implementation(BaseModel):
    """An implemention for an Interface - mainly represented as a
    Python function.

    Also records how the Implemention was created (i.e., what
    Implemention.Factory was used).
    """
    implementing_fn: Callable
    factory_method: str
    factory_kwargs: dict[str, Any] = {}

    class Factory:
        """Build one kind of implementation in a configurable way.
        """
        method: str

        @abstractmethod
        @staticmethod
        def build_fn(interface: 'Interface', **builder_kwargs) -> Callable:
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
                factory_method=self.method,
                factory_kwargs=builder_kwargs)
