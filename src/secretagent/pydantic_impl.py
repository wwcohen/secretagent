"""Pydantic-AI based implementation factory for secretagent.

Provides SimulatePydanticFactory, which uses a pydantic-ai Agent
to implement an Interface.
"""

import time

from typing import Callable

from pydantic_ai import Agent
from pydantic_ai_litellm import LiteLLMModel
from litellm import cost_per_token

from secretagent import config, record
from secretagent.core import Interface, Implementation, SimulateFactory, _FACTORIES


class SimulatePydanticFactory(SimulateFactory):
    """Simulate a function call using a pydantic-ai Agent.

    Reuses SimulateFactory.create_prompt() for the prompt, but strips
    the <answer> scaffolding and delegates to a pydantic-ai Agent
    for execution and output parsing.
    """

    def build_fn(self, interface: Interface, tools=None, **prompt_kw) -> Callable:
        tools = tools or []

        def result_fn(*args, **kw):
            with config.configuration(**prompt_kw):
                prompt = self.create_prompt(interface, *args, **kw)
                prompt = _remove_postprocessing_scaffolding(prompt)
                return_type = interface.annotations.get('return', str)
                model = LiteLLMModel(model_name=config.get('model'))
                agent = Agent(model, output_type=return_type, tools=tools)
                start_time = time.time()
                result = agent.run_sync(prompt)
                answer = result.output
                latency = time.time() - start_time
                usage = result.usage()
                input_cost, output_cost = cost_per_token(
                    model=config.get('model'),
                    prompt_tokens=usage.request_tokens,
                    completion_tokens=usage.response_tokens,
                )
                stats = dict(
                    input_tokens=usage.request_tokens,
                    output_tokens=usage.response_tokens,
                    latency=latency,
                    cost=input_cost + output_cost,
                )
                record.record(
                    func=interface.name,
                    args=args, kw=kw,
                    output=answer,
                    messages=_summarize_messages(result.all_messages()),
                    stats=stats)
                return answer

        return result_fn


def _remove_postprocessing_scaffolding(stub_prompt: str) -> str:
    end = stub_prompt.find(' Use the following output format')
    return stub_prompt[:end]


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


_FACTORIES['simulate_pydantic'] = SimulatePydanticFactory()
