"""Pydantic-ai based ReAct implementation factory.

Replaces the previous text-based LangChain-style ReAct (Yao+ ICLR 2023)
with a pydantic-ai Agent that uses the model's native tool-calling loop
and a clean ReAct preamble (no simulate / function-stub framing in the
prompt).

Usage in config:
    ptools:
      solve:
        method: react_pydantic
        tools:
          - mymodule.search
          - mymodule.lookup
"""

import inspect
import json
import re
import time
from typing import Any

from pydantic import Field

from secretagent.core import register_factory
from secretagent.implement.pydantic import SimulatePydanticFactory


class ReactPydanticFactory(SimulatePydanticFactory):
    """Pydantic-ai agent with a clean task preamble (no simulate/stub framing).

    Uses pydantic-ai's native tool-calling loop. The prompt emitted is:
      <preamble>\\n\\n<formatted args>

    Each benchmark registers this factory with its own preamble:
      register_factory('react_pydantic',
                       ReactPydanticFactory(preamble=MY_PREAMBLE))
    """

    preamble: str = Field(
        default=(
            "Answer the following question as best you can. Use the "
            "available tools to gather evidence, then call finish() "
            "with your final answer."
        )
    )

    def setup(self, tools=None, tool_module=None, learner=None,
              preamble=None, **prompt_kw):
        super().setup(tools=tools, tool_module=tool_module,
                      learner=learner, **prompt_kw)
        if preamble is not None:
            self.preamble = preamble

    def create_prompt(self, interface, *args, **kw):
        input_args = interface.format_args(*args, **kw)
        return f"{self.preamble}\n\n{input_args}"


register_factory('react_pydantic', ReactPydanticFactory())

def _parse_action(text: str) -> tuple[str | None, str | None]:
    """First ``Action:`` / ``Action Input:`` pair (text-only ReAct path)."""
    action_m = re.search(r'Action\s*:\s*(.+?)(?:\n|$)', text)
    if not action_m:
        return None, None
    tool_name = action_m.group(1).strip()
    input_m = re.search(
        r'Action\s+Input\s*:\s*(.*?)(?=\n(?:Observation|Thought|Action|Final Answer)\s*:|\Z)',
        text[action_m.end() :],
        re.DOTALL,
    )
    action_input = input_m.group(1).strip() if input_m else ''
    return tool_name, action_input


def _parse_final_answer(text: str) -> str | None:
    """Extract the final answer from 'Final Answer: ...'."""
    m = re.search(r'Final Answer\s*:\s*(.*)', text, re.DOTALL)
    if m and m.group(1).strip():
        return m.group(1).strip()
    return None


def _tool_result_for_observation(tool_result: Any) -> Any:
    """Shrink ``react_images`` in tool JSON so scratchpad text is not megabytes of base64."""
    if not isinstance(tool_result, dict):
        return tool_result
    out = dict(tool_result)
    ri = out.get('react_images')
    if isinstance(ri, dict):
        out['react_images'] = {
            k: (
                f'<base64 elided, {len(v)} chars>'
                if isinstance(v, str) and len(v) > 200
                else v
            )
            for k, v in ri.items()
        }
    return out


def _truncate_at_observation(text: str) -> str:
    """Remove any hallucinated Observation the LLM may have generated."""
    m = re.search(r'\nObservation\s*:', text)
    if m:
        return text[:m.start()]
    return text


# ---------------------------------------------------------------------------
# Tool description helpers
# ---------------------------------------------------------------------------

def _tool_description(fn) -> str:
    """LangChain-style description: name: first line of docstring."""
    name = fn.__name__
    doc = (fn.__doc__ or '').strip().split('\n')[0]
    return f'{name}: {doc}'


def _all_tool_descriptions(tools: dict[str, callable]) -> str:
    return '\n'.join(_tool_description(fn) for fn in tools.values())


def _tool_names(tools: dict[str, callable]) -> str:
    return ', '.join(tools.keys())


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

def _coerce_arg(fn, arg_str: str, react_images: dict | None = None):
    """Call fn with arg_str, coercing to the declared parameter type (non-VLM ReAct)."""
    sig = inspect.signature(fn, follow_wrapped=True)
    params = list(sig.parameters.values())
    accepts_react_images = 'react_images' in sig.parameters
    call_kw = {'react_images': react_images} if accepts_react_images else {}
    typed_params = [p for p in params if p.name != 'react_images']

    if not typed_params:
        return fn(**call_kw)
    if len(typed_params) == 1:
        ann = typed_params[0].annotation
        if ann is inspect.Parameter.empty or ann is str:
            return fn(arg_str, **call_kw)
        try:
            return fn(ann(arg_str), **call_kw)
        except (ValueError, TypeError):
            return fn(arg_str, **call_kw)
    parts = [p.strip() for p in re.split(r'[|,]', arg_str)]
    coerced = []
    for part, param in zip(parts, typed_params):
        ann = param.annotation
        if ann is inspect.Parameter.empty or ann is str:
            coerced.append(part)
        else:
            try:
                coerced.append(ann(part))
            except (ValueError, TypeError):
                coerced.append(part)
    return fn(*coerced, **call_kw)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class ReactFactory(SimulateFactory):
    """LangChain-style zero-shot ReAct factory.

    Runs a Thought / Action / Action Input / Observation loop via repeated
    LLM calls, using ``Final Answer:`` to terminate.

    Config keys (passed as builder kwargs in the YAML ``ptools:`` block):
        tools:     list of dotted-path references to tool functions
        max_steps: maximum number of Thought/Action rounds (default 8)

    Runtime config:
        vlm.enabled or react.use_vlm: when truthy, use VLM calls for each ReAct step
    """

    tools: dict = Field(default_factory=dict)
    max_steps: int = 8

    prompt_kw: dict = Field(default_factory=dict)

    def setup(self, tools=None, max_steps=8, **prompt_kw):
        raw = resolve_tools(self.bound_interface, tools)
        self.tools = {fn.__name__: fn for fn in raw}
        self.max_steps = int(max_steps)
        self.prompt_kw = prompt_kw

    def __call__(self, *args, **kw):
        interface = self.bound_interface
        model_name = self.llm_model
        call_kw = dict(kw)
        call_images = call_kw.pop('images', None)
        working_images = dict(call_images or {})
        use_vlm = bool(config.get('vlm.enabled', config.get('react.use_vlm', False)))

        with config.configuration(**self.prompt_kw):
            # Build the initial prompt
            template = _load_template('react.txt')
            input_args = interface.format_args(*args, **call_kw)
            tool_descs = _all_tool_descriptions(self.tools)
            tool_name_list = _tool_names(self.tools)

            prompt = template.substitute(
                stub_src=interface.src,
                input_args=input_args,
                tool_descriptions=tool_descs,
                tool_names=tool_name_list,
            )

            scratchpad = ''
            steps: list[dict] = []
            total_stats = dict(input_tokens=0, output_tokens=0, latency=0.0, cost=0.0)
            answer: str | None = None
            start_time = time.time()

            try:
                for step_num in range(1, self.max_steps + 1):
                    # Prompt ends with "Thought:" — LLM continues from there
                    full_prompt = prompt + scratchpad
                    if use_vlm:
                        messages = create_vlm_messages(
                            prompt=full_prompt,
                            images=(working_images or None),
                            system_prompt=config.get('vlm.system_prompt') or '',
                        )
                        response, stats = call_vlm(messages=messages, output_mode='freeform')
                    else:
                        response, stats = llm_call(full_prompt, model_name)
                    for k in total_stats:
                        total_stats[k] += stats.get(k, 0)

                    # Reconstruct the full text for parsing
                    if use_vlm:
                        thought, final, tool_name, tool_input = (
                            react_vlm_util.parse_react_vlm_step(response))
                    else:
                        prefixed = f'Thought: {response}'
                        truncated = _truncate_at_observation(prefixed)
                        thought = _parse_thought(truncated)
                        final = _parse_final_answer(truncated)
                        tool_name, tool_input = _parse_action(prefixed)

                    if thought:
                        steps.append({'thought': thought})

                    # Final Answer terminates the loop
                    if final is not None:
                        answer = final
                        break

                    # No action and no final answer — treat as direct answer
                    if tool_name is None:
                        answer = thought or response.strip()
                        if not thought:
                            steps.append({'thought': answer})
                        break

                    # Build scratchpad for this step
                    scratchpad += (
                        f' {thought or ""}\n'
                        f'Action: {tool_name}\n'
                        f'Action Input: {tool_input}\n'
                    )

                    steps.append({'tool_call': tool_name, 'args': tool_input})

                    # Dispatch to tool (case-insensitive fallback)
                    resolved_name = tool_name
                    if resolved_name not in self.tools:
                        for k in self.tools:
                            if k.lower() == resolved_name.lower():
                                resolved_name = k
                                break

                    if resolved_name in self.tools:
                        try:
                            if use_vlm:
                                tool_result = react_vlm_util.coerce_react_tool_input(
                                    self.tools[resolved_name],
                                    tool_input,
                                    working_images,
                                )
                            else:
                                tool_result = _coerce_arg(
                                    self.tools[resolved_name],
                                    tool_input,
                                    react_images=working_images,
                                )
                            if isinstance(tool_result, dict):
                                returned_images = tool_result.get('react_images')
                                if isinstance(returned_images, dict):
                                    before = set(working_images.keys())
                                    working_images.update({
                                        k: v for k, v in returned_images.items()
                                        if isinstance(k, str) and isinstance(v, str)
                                    })
                                    added = sorted(
                                        set(working_images.keys()) - before
                                    )
                                    if added and use_vlm:
                                        print(
                                            f'[react] merged screenshots into next VLM turn: '
                                            f'+{added}  (all keys: {sorted(working_images.keys())})',
                                            flush=True,
                                        )
                                observation = json.dumps(
                                    _tool_result_for_observation(tool_result)
                                )
                            else:
                                observation = str(tool_result)
                        except Exception as e:
                            observation = f'Error calling {resolved_name}: {e}'
                    else:
                        available = ', '.join(self.tools.keys())
                        observation = (
                            f'Unknown action "{tool_name}". '
                            f'Available actions: [{available}]'
                        )

                    steps.append({'tool_return': resolved_name, 'output': observation})
                    scratchpad += f'Observation: {observation}\nThought:'
            except Exception as ex:
                total_stats['latency'] = time.time() - start_time
                record.record(
                    func=interface.name, args=args, kw=call_kw,
                    output=f'**exception**: {ex}', step_info=steps,
                    stats=total_stats)
                raise

            total_stats['latency'] = time.time() - start_time

            if answer is None:
                answer = ''

            # Convert to declared return type
            return_type = interface.annotations.get('return', str)
            if return_type is not str and answer:
                answer = self.parse_output(return_type, f'<answer>{answer}</answer>')

            record.record(
                func=interface.name, args=args, kw=call_kw,
                output=answer, step_info=steps, stats=total_stats,
            )
            return answer


register_factory('react', ReactFactory())
