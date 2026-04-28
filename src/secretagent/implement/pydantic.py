"""Pydantic-AI based implementation factory for secretagent.

Provides SimulatePydanticFactory, which uses a pydantic-ai Agent
to implement an Interface.
"""

import hashlib
import inspect
import reprlib
import time
from pydantic import Field
from pydantic_ai import Agent
from pydantic_ai_litellm import LiteLLMModel
from litellm import cost_per_token

from secretagent import config, record
from secretagent.cache_util import cached
from secretagent.core import register_factory
from secretagent.implement.core import (
    SimulateFactory, ToolUsingFactory, _format_pydantic_schema)
from secretagent.implement.util import load_template
from secretagent.llm_util import echo_boxed, _retry_with_backoff

def _run_agent_hashkey(_, kwds):
    """Create a hashkey for the arguments of _run_agent.
    """
    retries = config.get('pydantic.retries', 1)
    hashable = (
        (kwds['interface'].name,  # use the interface name
         kwds['model_name'],  # a string
         str(kwds['return_type']), # convert type to str
         kwds['prompt'], # a string
         tuple(tool.__name__ for tool in kwds['tools']),  # use function names
         ) + (() if retries == 1 else (retries,)))
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
    model = LiteLLMModel(model_name=model_name)
    return_type = interface.annotations.get('return', str)
    retries = config.get('pydantic.retries', 1)
    agent = Agent(model, output_type=return_type, tools=tools, retries=retries)

    # run the agent and time that. Wrap in a thread-pool so an optional
    # llm.timeout (in seconds) can bound the total agent wall-clock time.
    # together_ai occasionally stalls on specific prompts; without a
    # timeout the whole pipeline hangs indefinitely.
    timeout = config.get('llm.timeout', None)
    start_time = time.time()
    def _do_run_sync():
        return agent.run_sync(prompt)
    if timeout is not None:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_retry_with_backoff, _do_run_sync)
            try:
                result = future.result(timeout=float(timeout))
            except concurrent.futures.TimeoutError as ex:
                raise TimeoutError(
                    f'pydantic-ai agent exceeded llm.timeout={timeout}s'
                ) from ex
    else:
        result = _retry_with_backoff(_do_run_sync)
    latency = time.time() - start_time

    # get the answer and maybe echo it
    answer = result.output
    if config.get('echo.llm_output'):
        echo_boxed(str(answer), 'llm_output')

    # compute the other stats
    usage = result.usage()
    input_cost, output_cost = cost_per_token(
        model=model_name,
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
    result = cached(_run_agent_impl, hash_func=_run_agent_hashkey)(
        interface, model_name, return_type, prompt, tools)
    if result is None:
        import sys
        sys.stderr.write(
            f'[warn] cached(_run_agent_impl) returned None for model={model_name}; '
            f'bypassing cache once.\n')
        result = _run_agent_impl(interface, model_name, return_type, prompt, tools)
    return result

class SimulatePydanticFactory(SimulateFactory, ToolUsingFactory):
    """Simulate a function call using a pydantic-ai Agent.

    Reuses SimulateFactory.create_prompt() for the prompt, but strips
    the <answer> scaffolding and delegates to a pydantic-ai Agent
    for execution and output parsing.

    Examples:
      foo.implement_via('simulate_pydantic')
      foo.implement_via('simulate_pydantic', tools='__all__')
      foo.implement_via('simulate_pydantic', tools=[bar, baz])

    The options tools can take on several values
      tools = None or missing means don't use tools
      tools = '__all__' means use all other registered interfaces
      tools = [f1,...,fk] where the f's are interfaces or functions
        means just those tools
    """

    tools: list = Field(default_factory=list)
    prompt_kw: dict = Field(default_factory=dict)

    def setup(self, tools=None, tool_module=None, learner=None, **prompt_kw):
        self.tools = self.setup_tools(tools, tool_module=tool_module, learner=learner)
        for tool in self.tools:
            if not inspect.isfunction(tool):
                raise ValueError(
                    f'Tool {reprlib.repr(tool)} is not a function; '
                    f'simulate_pydantic requires plain functions')
        self.prompt_kw = prompt_kw

    def __call__(self, *args, **kw):
        interface = self.bound_interface
        with config.configuration(**self.prompt_kw):
            prompt = self.create_prompt(interface, *args, **kw)
            try:
                answer, stats, messages = _run_agent(
                    interface=interface,
                    model_name=self.llm_model,
                    return_type=interface.annotations.get('return', str),
                    prompt=prompt,
                    tools=self.tools)
            except Exception as ex:
                # pydantic-ai may have made LLM calls before the agent loop
                # raised (e.g. when a tool-call's args don't match the
                # Interface signature). Those costs are unrecoverable from
                # here, so record NaN rather than lying with 0 — aggregation
                # code should treat NaN as "unknown, not zero".
                import math
                record.record(
                    func=interface.name, args=args, kw=kw,
                    output=f'**exception**: {ex}', step_info=[],
                    stats=dict(input_tokens=math.nan, output_tokens=math.nan,
                               latency=math.nan, cost=math.nan))
                raise
            record.record(
                func=interface.name,
                args=args,
                kw=kw,
                output=answer,
                step_info=messages,
                stats=stats)
            return answer

    def create_prompt(self, interface, *args, **kw):
        """Construct a prompt that calls an LLM to predict the output of the function.
        """
        template = load_template('simulate_pydantic.txt')
        input_args = interface.format_args(*args, **kw)
        if config.get('llm.thinking'):
            thoughts = "<thought>\nANY THOUGHTS\n</thought>\n"
        else:
            thoughts = ""
        return_type = interface.annotations.get('return', str)
        schema_block = _format_pydantic_schema(return_type)
        prompt = template.substitute(
            dict(stub_src=interface.src,
                 args=input_args,
                 thoughts=thoughts,
                 schema_block=schema_block))
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
