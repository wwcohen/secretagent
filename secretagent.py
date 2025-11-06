import ast
import collections
import functools
import inspect
import logging
import pathlib
import re

from contextlib import contextmanager
from string import Template

import llm_util

#
# global configuration of the secretagent package
#

GLOBAL_CONFIG = {}

def configure(**kw):
    """Set global configuration properties.
    """
    global GLOBAL_CONFIG
    GLOBAL_CONFIG.update(kw)

def get_config(key: str, local_config=None):
    """Get a value from the local_config or global_config.

    Prefer the local_config if both are set.
    """
    global GLOBAL_CONFIG
    if local_config:
        return local_config.get(key) or GLOBAL_CONFIG.get(key)
    else:
        return GLOBAL_CONFIG.get(key)

@contextmanager
def configuration(**kw):
    """Add some additional configuration information.

    Original configuration will be restored on exit.
    """
    global GLOBAL_CONFIG
    saved_config = {**GLOBAL_CONFIG}
    configure(**kw)
    yield GLOBAL_CONFIG
    GLOBAL_CONFIG = saved_config

#
# recording subagent actions
#

RECORDING = False
RECORD = []

@contextmanager
def recorder():
    """Start recording subagent actions.

    Returns a list of dicts, each dict describing a subagent call.
    """
    global RECORDING, RECORD
    RECORDING = True; RECORD = []
    yield RECORD
    RECORDING = False; RECORD = []    

def _record(**kw):
    global RECORDING, RECORD
    if RECORDING:
        RECORD.append({**kw})

#
# core machinery for subagents
#

def program_trace_prompt_llm(func, *args, **kw):
    """Construct a prompt that calls an LLM to predict the output of the function.
    """
    template_file = pathlib.Path(__file__).parent / "prompts" / "program_trace_prompt.txt"
    with open(template_file, 'r') as fp:
        template = Template(fp.read())

    # drop the decorator line from the source of func
    full_src = inspect.getsource(func)
    trimmed_src = '\n'.join(full_src.split('\n')[1:])
    # format the inputs
    input_args = '; '.join(
        [
            f'{argname} = {repr(argval)}'
            for argval, (argname, _) in zip(args, func.__annotations__.items())
        ] + [
            f'{argname} = {repr(argval)}'
            for argname, argval in kw
        ])
    prompt = template.substitute(dict(stub_src=trimmed_src, args=input_args))
    return llm_util.llm(
        prompt, get_config('service', kw), get_config('model', kw), get_config('echo_service'))

def parse_llm_output(func, text):
    """Take LLM output and return the final answer, in the correct type.
    """
    try:
        match_result = re.search(r'<answer>(.*)</answer>', text, re.DOTALL|re.MULTILINE)
        final_answer = match_result.group(1).strip()
    except AttributeError:
        raise AttributeError('cannot find final answer')

    return_type = func.__annotations__.get('return', str)
    try:
        # type is something simple like 'str', 'int'
        result = return_type(final_answer)
    except TypeError:
        # type is complex - for now don't both validating it
        result = ast.literal_eval(final_answer)
    return result

def subagent(**subagent_kw):
    """Decorator to mark a function as implemented via an LLM prompt.
    """
    def inner_stub(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            with configuration(**subagent_kw):
                echo = get_config('echo_call')
                if echo: print(f'Calling {func.__name__} {args}...')
                llm_response = program_trace_prompt_llm(func, *args, **kw)
                if get_config('echo_response'):
                    print('--- llm response ---')
                    print(llm_response)
                    print('--- end response ---')
                answer = parse_llm_output(func, llm_response)
                if echo: print(f'...{func.__name__} returned {answer}')
                _record(func=func.__name__, args=args, kw=kw, output=answer)
            return answer
        return wrapper
    return inner_stub
    
