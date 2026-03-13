"""Pydantic-AI based implementation factory for secretagent.

Provides SimulatePydanticFactory, which uses a pydantic-ai Agent
to implement an Interface.
"""

import hashlib
import pathlib
from string import Template
import time
from typing import Callable

from pydantic_ai import Agent
from pydantic_ai_litellm import LiteLLMModel
from litellm import cost_per_token

from secretagent import config, record
from secretagent.cache_util import cached, clear_all_caches
from secretagent.core import Interface, register_factory
from secretagent.implement_core import SimulateFactory
from secretagent.llm_util import echo_boxed

def _run_agent_hashkey(_, kwds):
    """Create a hashkey for the arguments of _run_agent.
    """
    hashable = (
        (kwds['interface'].name,  # use the interface name
         kwds['model_name'],  # a string
         str(kwds['return_type']), # convert type to str
         kwds['prompt'], # a string
         tuple(tool.__name__ for tool in kwds['tools']))) # use function names
    # convert the tuple to a string and encode it to hash
    return hashlib.sha256(str(hashable).encode('utf-8')).hexdigest()

def _run_agent_impl(interface, model_name, return_type, prompt, tools):
    """Run a pydantic agent.
    """
    if config.get('echo.model'):
        print(f'calling model {model_name}')

    if config.get('echo.llm_input'):
        echo_boxed(prompt, 'llm_input')

    # create the Model the agent will use and the Agent
    model = LiteLLMModel(model_name=config.require('llm.model'))
    return_type = interface.annotations.get('return', str)
    agent = Agent(model, output_type=return_type, tools=tools)

    # run the agent and time that
    start_time = time.time()
    result = agent.run_sync(prompt)
    latency = time.time() - start_time

    # get the answer and maybe echo it
    answer = result.output
    if config.get('echo.llm_output'):
        echo_boxed(str(answer), 'llm_output')

    # compute the other stats
    usage = result.usage()
    input_cost, output_cost = cost_per_token(
        model=config.get('llm.model'),
        prompt_tokens=usage.input_tokens,
        completion_tokens=usage.output_tokens,
    )
    stats = dict(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        latency=latency,
        cost=input_cost + output_cost,
    )
    # also send back a summary of messages from the agent
    messages = _summarize_messages(result.all_messages())
    return answer, stats, messages

def _run_agent(interface, model_name, return_type, prompt, tools):
    """Run a pydantic agent, with optional cachier caching via config."""
    return cached(_run_agent_impl, hash_func=_run_agent_hashkey)(
        interface, model_name, return_type, prompt, tools)

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
                tools[i] = tools[i].implementation.implementing_fn

        def result_fn(*args, **kw):
            with config.configuration(**prompt_kw):
                prompt = self.create_prompt(interface, *args, **kw)
                answer, stats, messages = _run_agent(
                    interface=interface,
                    model_name=config.require('llm.model'),
                    return_type=interface.annotations.get('return', str),
                    prompt=prompt,
                    tools=tools)
                record.record(
                    func=interface.name,
                    args=args,
                    kw=kw,
                    output=answer,
                    step_info=messages,
                    stats=stats)
                return answer
        return result_fn

    def create_prompt(self, interface, *args, **kw):
        """Construct a prompt that calls an LLM to predict the output of the function.
        """
        template_path = pathlib.Path(__file__).parent / 'prompt_templates' / 'simulate_pydantic.txt'
        template = Template(template_path.read_text())
        input_args = interface.format_args(*args, **kw)
        if config.get('llm.thinking'):
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
