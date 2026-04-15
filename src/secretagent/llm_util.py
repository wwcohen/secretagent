"""Access an LLM model, and monitor cost, latency, etc.
"""

import sys
import time
from typing import Any

from secretagent import config
from secretagent.cache_util import cached
from litellm import completion, completion_cost, token_counter

def echo_boxed(text: str, tag:str = ''):
    """Echo some text in a pretty box."""
    lines = text.split('\n')
    width = max(len(line) for line in lines)
    print('┌' + tag.center(width+2, '─') + '┐')
    for line in lines:
        print('│ ' + line.ljust(width) + ' │')
    print('└' + '─' * (width + 2) + '┘')

def _default_max_tokens(model: str) -> int | None:
  """Return a sensible max_tokens default for models that require one."""
  if 'gemini-2.5' in model or 'gemini-3' in model:
    return 65536
  if 'gemini-2.0' in model:
    return 8192
  return None

def _llm_impl(prompt: str, model: str) -> tuple[str, dict[str, Any]]:
  """Use an LLM model.

  Returns result as a string plus a dictionary of measurements,
  including # input_tokens, # output_tokens, latency in seconds, and cost.

  Set config 'llm.stream' to True to stream responses (visible with echo.stream).
  """
  if config.get('echo.model'):
    print(f'calling model {model}')

  if config.get('echo.llm_input'):
    echo_boxed(prompt, 'llm_input')

  messages = [dict(role='user', content=prompt)]
  stream = config.get('llm.stream', False)
  max_tokens = config.get('llm.max_tokens', None) or _default_max_tokens(model)
  temperature = config.get('llm.temperature', None)
  reasoning_effort = config.get('llm.reasoning_effort', None)
  extra_kw = {}
  if max_tokens:
    extra_kw['max_tokens'] = int(max_tokens)
  if temperature is not None:
    extra_kw['temperature'] = float(temperature)
  if reasoning_effort is not None:
    extra_kw['reasoning_effort'] = reasoning_effort
  start_time = time.time()

  if stream:
    chunks = []
    response_stream = completion(
        model=model, messages=messages, stream=True,
        stream_options={'include_usage': True},
        **extra_kw,
    )
    for chunk in response_stream:
      delta = ''
      if chunk.choices:
        delta = chunk.choices[0].delta.content or ''
      chunks.append(delta)
      if config.get('echo.stream') and delta:
        sys.stderr.write(delta)
        sys.stderr.flush()
    if config.get('echo.stream'):
      sys.stderr.write('\n')
    latency = time.time() - start_time
    model_output = ''.join(chunks)

    # Estimate tokens since streaming doesn't reliably return usage
    input_tokens = token_counter(model=model, messages=messages)
    output_tokens = token_counter(model=model, text=model_output)
    try:
      from litellm import model_cost
      cost_info = model_cost.get(model, {})
      cost = (input_tokens * cost_info.get('input_cost_per_token', 0) +
              output_tokens * cost_info.get('output_cost_per_token', 0))
    except Exception:
      cost = 0.0

    stats = dict(
      input_tokens=input_tokens,
      output_tokens=output_tokens,
      latency=latency,
      cost=cost,
    )
    if config.get('evaluate.record_details'):
      stats['trace'] = dict(
          prompt=prompt, raw_response=model_output,
          reasoning_content=None, model=model,
      )
  else:
    response = completion(model=model, messages=messages, **extra_kw)
    latency = time.time() - start_time
    msg = response.choices[0].message
    content = msg.content or ''
    reasoning = getattr(msg, 'reasoning_content', None) or ''
    # Thinking models (e.g. Qwen 3.5) sometimes put <answer> tags in
    # reasoning_content instead of content. Prefer content; fall back
    # to reasoning_content only if content lacks the expected tags.
    if content and '<answer>' in content:
      model_output = content
    elif reasoning and '<answer>' in reasoning:
      # Extract only the LAST <answer>...</answer> block from reasoning,
      # since earlier ones are the model thinking about the format.
      import re
      matches = re.findall(r'<answer>(.*?)</answer>', reasoning, re.DOTALL)
      if matches:
        last_answer = matches[-1].strip()
        model_output = f'<answer>{last_answer}</answer>'
      else:
        model_output = reasoning
    else:
      model_output = content or reasoning

    stats = dict(
      input_tokens=response.usage.prompt_tokens,
      output_tokens=response.usage.completion_tokens,
      latency=latency,
      cost=completion_cost(completion_response=response),
    )
    if config.get('evaluate.record_details'):
      stats['trace'] = dict(
          prompt=prompt, raw_response=content,
          reasoning_content=reasoning if reasoning else None,
          model=model,
      )

  if config.get('echo.llm_output'):
    echo_boxed(model_output, 'llm_output')

  return model_output, stats

def llm(prompt: str, model: str) -> tuple[str, dict[str, Any]]:
  """Use an LLM model, with optional cachier caching via config.

  See cache_util.py for why this weird process is necessary.
  """
  return cached(_llm_impl)(prompt, model)
