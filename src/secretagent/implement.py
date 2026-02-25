import ast
import inspect
import pathlib
import re

from string import Template
from typing import Callable

from secretagent import config, llm_util, record

def ptp(func, **prompt_kw):
    def wrapper(*args, **kw):
        with config.configuration(**prompt_kw):
            echo = config.get('echo_call')
            if echo: print(f'Calling {func.__name__} {args}...')
            llm_output, stats = _program_trace_prompt_llm(func, *args, **kw)
            if config.get('echo_response'):
                print('--- llm response ---')
                print(llm_response)
                print('--- end response ---')
            answer = _parse_llm_output(func, llm_output)
            if echo: print(f'...{func.__name__} returned {answer}')
            record.record(func=func.__name__, args=args, kw=kw, output=answer, stats=stats)
            return answer
    return wrapper
    
def _program_trace_prompt_llm(func, *args, **kw):
    """Construct a prompt that calls an LLM to predict the output of the function.
    """
    template_file = pathlib.Path(__file__).parent / "prompts" / "program_trace_prompt.txt"
    with open(template_file, 'r') as fp:
        template = Template(fp.read())

    src = inspect.getsource(func)
    trimmed_src = '\n'.join(src.split('\n')[1:])

    # drop the decorator line from the source of func
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
    model_output, stats = llm_util.llm(
        prompt, config.get('model', kw), config.get('echo_model'))
    return model_output, stats

def _parse_llm_output(func, text):
    """Take LLM output and return the final answer, in the correct type.
    """
    try:
        match_result = re.search(r'<answer>(.*)</answer>', text, re.DOTALL|re.MULTILINE)
        final_answer = match_result.group(1).strip()
    except AttributeError:
        raise AttributeError('cannot find final answer')

    return_type = func.__annotations__.get('return', str)
    if return_type in [int, str, float]:
        result = return_type(final_answer)
    else:
        # type is complex - for now don't both validating it
        # with typeguard.check_type(result, return_type)
        result = ast.literal_eval(final_answer)
    return result
