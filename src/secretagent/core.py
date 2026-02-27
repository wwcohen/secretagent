"""Core components of SecretAgents package: interfaces and implementations.
"""

import ast
import functools
import inspect
import re

from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from string import Template
from textwrap import dedent
from typing import Any, Callable, Optional

from secretagent import config, llm_util, record

# registries of defined interfaces and implementation factories

_INTERFACES : list['Interface'] = []
_FACTORIES : dict[str, 'Implementation.Factory'] = {}

def all_interfaces() -> list['Interface']:
    return _INTERFACES
    
def all_factories() -> list[tuple[str, 'Implementation.Factory']]:
    return _FACTORIES.items()

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

#
# some Implementation.Factories
#

class DirectFactory(Implementation.Factory):
    """Use the function body as the implementation.
    """
    def build_fn(self, interface: Interface, **_kw) -> Callable:
        return interface.func

class EchoFactory(Implementation.Factory):
    """Just echos the arguments to a function
    """
    def build_fn(self, interface: Interface, echo_doc=False, **_kw) -> Implementation:
        def result_fn(*args, **kw):
            print(f'Called {interface.signature(*args, **kw)}')
            if echo_doc:
                print('doc'.center(40, '-'))
                print(interface.doc)
        return result_fn

class SimulateFactory(Implementation.Factory):
    """Simulate a function call with an LLM.
    """
    def build_fn(self, interface: Interface, **prompt_kw) -> Implementation:
        def result_fn(*args, **kw):
            with config.configuration(**prompt_kw):
                prompt = self.create_prompt(interface, *args, **kw)
                llm_output, stats = llm_util.llm(
                    prompt, config.get('model'), config.get('echo_model'))
                return_type = interface.annotations.get('return', str)
                answer = self.parse_output(return_type, llm_output)
                record.record(func=interface.name, args=args, kw=kw, output=answer, stats=stats)
                return answer
        return result_fn
    
    def create_prompt(self, interface, *args, **kw):
        """Construct a prompt that calls an LLM to predict the output of the function.
        """
        template_str = """
        Consider the following documentation stub for a Python function.  Note
        that this is documentation, not a full implementation.
        ```python
        $stub_src
        ```

        Imagine that this function was fully implemented as suggested by the
        documentation stub, and that function were called with these arguments:
    
        $args

        Propose a possible output of the function for these inputs that is
        consistent with the documentation. Use the following output format:

        $thoughts
        <answer>
        FINAL ANSWER
        </answer>

        If your answer is x, show it as it would printed by a Python
        interpreter called by print(x). Specifically if x is a string do NOT
        include quotes around it.  Also, do not include any text other than
        the final answer between the <answer> and </answer> tags.
        """
        template = Template(dedent(template_str))
        arg_names = list(interface.annotations.keys())[:-1]
        input_args = '; '.join(
            [
                f'{argname} = {repr(argval)}'
                for argval, argname in zip(args, arg_names)
            ] + [
                f'{argname} = {repr(argval)}'
                for argname, argval in kw.items()
            ])
        if config.get('thinking'):
            thoughts = "<thought>\nANY THOUGHTS\n</thought>\n"
        else:
            thoughts = ""
        prompt = template.substitute(
            dict(stub_src=interface.src,
                 args=input_args,
                 thoughts=thoughts))
        return prompt

    def parse_output(self, return_type, text):
        """Take LLM output and return the final answer, in the correct type.
        """
        try:
            match_result = re.search(r'<answer>(.*)</answer>', text, re.DOTALL|re.MULTILINE)
            final_answer = match_result.group(1).strip()
        except AttributeError:
            raise AttributeError('cannot find final answer')
        if return_type in [int, str, float]:
            result = return_type(final_answer)
        else:
            # type is complex - for now don't both validating it
            # with typeguard.check_type(result, return_type)
            result = ast.literal_eval(final_answer)
        return result
    
_FACTORIES['direct'] = DirectFactory()
_FACTORIES['echo'] = EchoFactory()
_FACTORIES['simulate'] = SimulateFactory()

