import ast
import collections
import functools
import inspect
import logging
import pathlib
import re

from string import Template

import llm_util

GLOBAL_CONFIG = dict(
    service="anthropic",
    model="claude-3-haiku-20240307")

def configure(**kw):
    """Set global coniguration properties."""
    GLOBAL_CONFIG.update(kw)

def get_config(key: str, local_config=None):
    """Get a value from the local_config or global_config.

    Prefer the local_config if both are set.
    """
    if local_config:
        return local_config.get(key) or GLOBAL_CONFIG.get(key)
    else:
        return GLOBAL_CONFIG.get(key)

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
        prompt, get_config('service', kw), get_config('model', kw))

def parse_llm_output(func, text):
    """Take LLM output and return the final answer, in the correct type."""
    return_type = func.__annotations__.get('return', str)
    final_answer = re.search(r'<answer>\n?(.*)\n?</answer>', text).group(1)
    result = None
    try:
        # type is something simple like 'str', 'int'
        result = return_type(final_answer)
    except TypeError:
        # type is complex - for now don't both validating it
        result = ast.literal_eval(final_answer)
    return result

def subagent(echo=False):
    """Mark a function as something to be implemented via an LLM prompt.
    """
    def inner_stub(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            if echo: print(f'Calling {func.__name__} {args}...')
            llm_response = program_trace_prompt_llm(func, *args, **kw)
            answer = parse_llm_output(func, llm_response)
            if echo: print(f'...{func.__name__} returned {answer}')
            return answer
        return wrapper
    return inner_stub
    
