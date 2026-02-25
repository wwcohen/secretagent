"""Helpers that give alternative ways to implement a ptool.
"""

import ast
import inspect
import pathlib
import re
import functools

from string import Template
from textwrap import dedent
from typing import Callable

from secretagent import config, llm_util, record

#
# implementations
#

def echo_func_call(func, echo_goal=False):
    """Simple example 'implementation' that just prints a message when
    a function is called.
    """
    @functools.wraps(func)
    def _echo_func_call(*args, **kw):
        _echo_call(func, args)
        if echo_goal:
            print('Goal:', func.__doc__)
        return None
    return _echo_func_call

def simulate_from_stub(func, **prompt_kw):
    """Implement the function by prompting an LLM.

    The prompt presents the function signature and docstring defined
    with the ptool, and asks the LLM to predict the output of the
    tool.  The predicted output is then parsed and converted
    to the output type.
    """
    @functools.wraps(func)
    def wrapper(*args, **kw):
        with config.configuration(**prompt_kw):
            _echo_call(func, args)
            prompt = _create_simulate_from_stub_prompt(func, *args, **kw)
            llm_output, stats = llm_util.llm(
                prompt, config.get('model', kw), config.get('echo_model'))
            _echo_llm_output(llm_output)
            return_type = func.__annotations__.get('return', str)
            answer = _parse_output(return_type, llm_output)
            _echo_return(func, answer)
            record.record(func=func.__name__, args=args, kw=kw, output=answer, stats=stats)
            return answer
    return wrapper
    
def _create_simulate_from_stub_prompt(func, *args, **kw):
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
    consistent with the documentation.  Use the following output format:

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
    # drop the decorator line from the source of func
    src = inspect.getsource(func)
    trimmed_src = '\n'.join(src.split('\n')[1:])
    # format the inputs
    input_args = '; '.join(
        [
            f'{argname} = {repr(argval)}'
            for argval, (argname, _) in zip(args, func.__annotations__.items())
        ] + [
            f'{argname} = {repr(argval)}'
            for argname, argval in kw
        ])
    if config.get('thinking'):
        thoughts = "<thought>\nANY THOUGHTS\n</thought>\n"
    else:
        thoughts = ""
    prompt = template.substitute(
        dict(stub_src=trimmed_src,
             args=input_args,
             thoughts=thoughts))
    return prompt

#
# helpers
#

def _echo_call(func, args):
    """Print a message that a ptool has been called."""
    if config.get('echo_call'):
        print(f'Calling {func.__name__} {args}...')

def _echo_return(func, answer):
    """Print a message that a ptool returned a value."""
    if config.get('echo_call'):
        print(f'...{func.__name__} returned {answer}')

def _echo_llm_output(llm_output):
    """Print an LLM output."""
    if config.get('echo_response'):
        print('--- llm response ---')
        print(llm_output)
        print('--- end response ---')

def _parse_output(return_type, text):
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
