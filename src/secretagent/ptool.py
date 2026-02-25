import functools
import inspect

from pydantic import BaseModel
from typing import Any, Callable, Optional

from secretagent import implement

class Implementation(BaseModel):
    """An implemention of a ptool.

    Also records provenance information.
    """
    fn: Callable
    method: str
    kwargs: dict[str, Any] = {}

# the registry map ptool names to their implementions

_REGISTRY : dict[str, Optional[Implementation]] = {}

def ptool(method=None, **method_kw):
    """Decorator to mark a function as a 'pseudo tool (ptool)'.

    ptools usually have input/output type signatures and docstrings to
    explain what they should do, but usually do not have any
    associated function definition.  When a ptool is called from
    Python, the function call is forwarded to an appropriate
    Implementation.
    

    ptools can be called like Python functions but their
    implementations can be changed on the fly.  In particular they can
    be configured to be implemented by an LLM or an agent.

    If a 'method' is provided, then an implementation will be
    constructed when the ptool is added to the registry - just as if
    implement_via was called after ptool construction.
    """
    def inner_stub(func):
        # if an implementation method is specified register that
        if method is not None:
            implement_via(func, method, **method_kw)
        # the decorated function will call whatever's currently registered
        @functools.wraps(func)
        def wrapper(*args, **kw):
            try:
                return _REGISTRY[func.__name__].fn(*args, **kw)
            except KeyError:
                raise NotImplementedError(f'no implementation registered for ptool "{func.__name__}"')
        return wrapper
    return inner_stub
    
def implement_via(func: Callable, method: str, **kw):
    """Register an Implementation for the ptool 'func'.

    The implementation will be created by the indicated method.
    Valid methods and their arguments are:
    
    'echo', echo_goal=False:  just echo the inputs and optionally
      the docstring and return null.

    'simulate_from_stub', model=...: show an LLM the ptool stub,
      including the docstring, ask it to predict the output, and then
      try and convert the predicted output to the expected return
      value.

    'direct': implement the ptool like an ordinary python function (so
      there should be a code implementation given, like an ordinary
      python function).

    Any previously registered implementation will be replaced by the
    new one.

    """
    match method:
        case 'direct':
            original = getattr(func, '__wrapped__', func)
            _REGISTRY[func.__name__] = Implementation(
                fn=original, method='direct', kwargs=kw)
        case 'echo':
            _REGISTRY[func.__name__] = Implementation(
                fn=implement.echo_func_call(func, **kw), method='echo', kwargs=kw)
        case 'simulate_from_stub':
            _REGISTRY[func.__name__] = Implementation(
                fn=implement.simulate_from_stub(func, **kw),
                method='echo', kwargs=kw)
        case _:
            raise NotImplementedError(f'Invalid implementation method {method}')

def list() -> list[dict[str, Any]]:
    """Return a list of registered ptools with their method and kwargs."""
    return [{'name': name, 'method': impl.method, 'kwargs': impl.kwargs}
            for name, impl in _REGISTRY.items()]

