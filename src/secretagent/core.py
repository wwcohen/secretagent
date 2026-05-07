"""Core components of SecretAgents package: interfaces and implementations.
"""

import ast
import inspect

from pydantic import BaseModel, Field
from typing import Any, Callable, Optional

from secretagent import config

# registries of defined interfaces and implementation factories

_INTERFACES : list['Interface'] = []
_FACTORIES : dict[str, 'Implementation.Factory'] = {}

def all_interfaces() -> list['Interface']:
    return _INTERFACES
    
def all_factories() -> list[tuple[str, 'Implementation.Factory']]:
    """Return all registered Implementation.Factory's."""
    return list(_FACTORIES.items())

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

    def format_args(self, *args, **kw) -> str:
        """Format positional and keyword args as 'name = value; ...' string."""
        arg_names = list(self.annotations.keys())[:-1]
        parts = [
            f'{argname} = {repr(argval)}'
            for argval, argname in zip(args, arg_names)
        ] + [
            f'{argname} = {repr(argval)}'
            for argname, argval in kw.items()
        ]
        if len(parts) != len(args) + len(kw):
            raise ValueError(f'cannot format {self.signature()} for {args=} {kw=} - note type hints are needed!')
        return '; '.join(parts)

    def signature(self, *args, **kw):
        arg_str = ', '.join([repr(a) for a in args])
        kw_str = ', '.join([f'{lhs}={repr(rhs)}' for lhs, rhs in kw.items()])
        sep = ', ' if arg_str and kw_str else ''
        return_type = self.annotations['return'].__name__
        return f'{self.name}({arg_str}{sep}{kw_str}) -> {return_type}'


def interface(func: Callable | None = None, **_kw) -> Interface | Callable:
    """Decorator to make a stub or function into an Interface.

    Example use:
    @interface
    def translate(english_sentence: str) -> str:
        ""Translate a sentence in English to French.""
        ...

    translate.implement_via('simulate_from_stub', model="claude-haiku")

    Generated ptools sometimes use ``@interface(method="...")``. Binding
    methods are still supplied through config, so decorator keywords are
    accepted and ignored for compatibility with generated code.
    """
    if func is None:
        return lambda f: interface(f)

    full_src = inspect.getsource(func)
    trimmed_src = full_src[full_src.find('\ndef')+1:]
    if not config.get('simulate.full_src'):
        # Strip body after docstring so src only has signature + docstring
        try:
            tree = ast.parse(trimmed_src)
            func_node = tree.body[0]
            docstring_node = func_node.body[0]
            if (isinstance(docstring_node, ast.Expr)
                and isinstance(docstring_node.value, (ast.Constant, ast.Str))):
                end_lineno = docstring_node.end_lineno
                # Retain an Ellipsis (...) immediately after the docstring
                if (len(func_node.body) > 1
                    and isinstance(func_node.body[1], ast.Expr)
                    and isinstance(func_node.body[1].value, ast.Constant)
                    and func_node.body[1].value.value is ...):
                    end_lineno = func_node.body[1].end_lineno
                lines = trimmed_src.splitlines(keepends=True)
                trimmed_src = ''.join(lines[:end_lineno])
        except (SyntaxError, IndexError):
            pass
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

def implement_via_config(ptool_module, tools_cfg):
    """Bind the tools in tool_module to implementations specified by a
    config. The tools_cfg should look something like the following.

    implementations:
      analyze_sentence:
        method: simulate
      sport_for:
        method: simulate

    Optional parse post-processing: add a ``parse`` key to any interface
    config to wrap the implementation with a parse step.

      calendar_scheduling:
        method: simulate
        parse:
          method: simulate      # LLM re-parses the raw output
          # or: method: direct, fn: my_module.my_parser
    """
    for func_name, factory_kws in tools_cfg.items():
        factory_kws = dict(factory_kws)
        # get the method and remove it from the config for this tool
        method = factory_kws.pop('method')
        parse_cfg = factory_kws.pop('parse', None)
        iface = getattr(ptool_module, func_name)
        iface.implement_via(method, **factory_kws)
        if parse_cfg:
            _add_parse_wrapper(iface, parse_cfg)


def _add_parse_wrapper(iface, parse_cfg):
    """Wrap an interface's implementation with a parse post-processing step.

    Creates a lightweight parse interface that inherits the original
    interface's return type and docstring, so that ``simulate`` knows
    the expected output format.
    """
    parse_cfg = dict(parse_cfg)
    parse_method = parse_cfg.pop('method')
    return_type = iface.annotations.get('return', str)

    parse_iface = Interface(
        func=lambda raw_output: raw_output,
        name=f'{iface.name}__parse',
        doc=f'Parse and normalize raw output into the expected format.\n\n{iface.doc}',
        src='',
        annotations={'raw_output': str, 'return': return_type},
    )
    parse_iface.implement_via(parse_method, **parse_cfg)

    original_fn = iface.implementation.implementing_fn
    def wrapped(*args, **kw):
        raw = original_fn(*args, **kw)
        return parse_iface(str(raw))
    iface.implementation.implementing_fn = wrapped


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

        Subclasses override setup() and __call__():
        - setup(**builder_kwargs) configures per-interface state on self
        - __call__(*args, **kw) is the implementing function

        Each call to build_implementation() creates a fresh copy of the
        factory, so setup() can safely store per-interface state on self,
        to be used by __call__() later on.
        """
        bound_interface: Optional['Interface'] = Field(
            default=None,
            description="Interface this factory copy is bound to (set by build_implementation)")
        model: str | None = Field(
            default=None,
            description="LLM model override; defaults to config llm.model")

        @property
        def llm_model(self) -> str:
            """Return the model to use: explicit override or config default."""
            return self.model or config.require('llm.model')

        @property
        def __name__(self):
            """Function-like name for the bound factory."""
            if self.bound_interface is not None:
                return self.bound_interface.name
            return self.__class__.__name__


        def setup(self, **builder_kwargs):
            """Configure per-interface state on self."""
            pass

        def __call__(self, *args, **kw):
            """The implementing function."""
            raise NotImplementedError(
                f'{self.__class__.__name__} must override __call__')

        def build_implementation(
                self, interface: 'Interface', **builder_kwargs) -> 'Implementation':
            """Create an Implementation for the interface.

            Creates a fresh copy of this factory so that per-interface state
            can be stored on self without affecting the global prototype.
            """
            factory = self.model_copy()
            factory.bound_interface = interface
            factory.model = builder_kwargs.pop('model', None)
            factory.setup(**builder_kwargs)

            return Implementation(
                implementing_fn=factory,
                factory_method=self.__class__.__name__,
                factory_kwargs=builder_kwargs)

# auto-register built-in factories
import secretagent.implement  # noqa: E402, F401
import secretagent.orchestrate  # noqa: E402, F401
