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

_REGISTRY : dict[str, Optional[Implementation]] = {}

def ptool(method=None, **method_kw):
    """Decorator to mark a function as a 'pseudo tool'.

    Pseudo tools are called like Python functions but their
    implementations can be changed on the fly.  In particular they can
    be configured to be implementated by an LLM or an agent.
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
                raise NotImplementedError(f'ptool "{func.__name__}" is not bound to any implementation')
        return wrapper
    return inner_stub
    
def implement_via(func: Callable, method: str, **kw):
    """Register an Implementation for a ptool.

    The implementation will be created by the indicated method.
    Valid methods and their arguments are:
    
    'echo', echo_goal=False:  just echo the inputs and optionally
      the docstring and return null.

    'one_prompt' or 'ptp', model=...: show an LLM the ptool stub,
      including the docstring, ask it to predict the output, and then
      try and convert the predicted output to the expected return
      value.

    Any previously registered implementation will be replaced by the
    new one.

    """
    match method:
        case 'echo':
            _REGISTRY[func.__name__] = Implementation(
                fn = _echo_wrapper(func, **kw),
                method='echo', kwargs=kw)
        case 'ptp' | 'one_prompt':
            _REGISTRY[func.__name__] = Implementation(
                fn = implement.ptp(func, **kw),
                method='echo', kwargs=kw)
        case _:
            raise NotImplementedError(f'Invalid implementation method {method}')

def _echo_wrapper(func, echo_goal=False):
    """A toy function to drop into an Implementation
    """
    @functools.wraps(func)
    def echo_call(*args, **kw):
        print(f'Called {func.__name__} on {args} {kw}')
        if echo_goal:
            print('Goal', func.__doc__)
        return None
    return echo_call

#
# testing
#

@ptool(method='ptp', model="claude-haiku-4-5-20251001")
def sport_for(player_or_event: str) -> str:
    """Return the sport associated with a famous player."""
    ...

if __name__ == '__main__':
    # raise error
    try:
        print('init', sport_for('Kobe Bryant'))
    except Exception as ex:
        print(f'raised: {ex}')

    implement_via(sport_for, 'echo')
    # echo, no goal
    print('echo', sport_for('Kobe Bryant'))

    implement_via(sport_for, 'echo', echo_goal=True)
    # echo, with goal
    print('echo w goal', sport_for('Kobe Bryant'))

    implement_via(sport_for, 'ptp', model="claude-haiku-4-5-20251001")
    # echo, with goal
    print('rebound to ptp', sport_for('Kobe Bryant'))


