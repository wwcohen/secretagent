"""Pydantic-AI based implementation factory for secretagent.

Provides SimulatePydanticFactory, which uses a pydantic-ai Agent
to implement an Interface.
"""

import time

from textwrap import dedent
from typing import Callable
from string import Template

from pydantic_ai import Agent
from pydantic_ai_litellm import LiteLLMModel
from litellm import cost_per_token

from secretagent import config, record
from secretagent.core import Interface, register_factory
from secretagent.core_impl import SimulateFactory


class SimulatePydanticFactory(SimulateFactory):
    """Simulate a function call using a pydantic-ai Agent.

    Reuses SimulateFactory.create_prompt() for the prompt, but strips
    the <answer> scaffolding and delegates to a pydantic-ai Agent
    for execution and output parsing.
    """

    def build_fn(self, interface: Interface, tools=None, **prompt_kw) -> Callable:
        tools = tools or []
        # pydantic seems to need tools to be functions, not just callable
        for i in range(len(tools)):
            if isinstance(tools[i], Interface):
                tools[i] = tools[i].func

        def result_fn(*args, **kw):
            with config.configuration(**prompt_kw):
                prompt = self.create_prompt(interface, *args, **kw)
                return_type = interface.annotations.get('return', str)
                model = LiteLLMModel(model_name=config.get('model'))
                agent = Agent(model, output_type=return_type, tools=tools)
                start_time = time.time()
                result = agent.run_sync(prompt)
                latency = time.time() - start_time
                answer = result.output
                usage = result.usage()
                input_cost, output_cost = cost_per_token(
                    model=config.get('model'),
                    prompt_tokens=usage.input_tokens,
                    completion_tokens=usage.output_tokens,
                )
                stats = dict(
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    latency=latency,
                    cost=input_cost + output_cost,
                )
                record.record(
                    func=interface.name,
                    args=args,
                    kw=kw,
                    output=answer,
                    messages=_summarize_messages(result.all_messages()),
                    stats=stats)
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
        consistent with the documentation.
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

def _summarize_messages(messages):
    """Summarize pydantic-ai messages into a simple list of steps.

    Extracts model thoughts (text), tool calls (name + args),
    and tool returns (name + output).
    """
    steps = []
    for msg in messages:
        for part in msg.parts:
            match part.part_kind:
                case 'text':
                    if part.content.strip():
                        steps.append({'thought': part.content})
                case 'tool-call':
                    steps.append({'tool_call': part.tool_name, 'args': part.args})
                case 'tool-return':
                    steps.append({'tool_return': part.tool_name, 'output': part.content})
    return steps


register_factory('simulate_pydantic', SimulatePydanticFactory())
