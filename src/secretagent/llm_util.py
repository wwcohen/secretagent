"""Access an LLM model, and monitors cost, latency, etc.
"""

import time

from secretagent import config
from secretagent.cache_util import cached, clear_all_caches
from litellm import completion, completion_cost

def echo_boxed(text: str, tag:str = ''):
    """Echo some text in a pretty box."""
    lines = text.split('\n')
    width = max(len(line) for line in lines)
    print('┌' + tag.center(width+2, '─') + '┐')
    for line in lines:
        print('│ ' + line.ljust(width) + ' │')
    print('└' + '─' * (width + 2) + '┘')

def _llm_impl(prompt: str, model: str) -> tuple[str, dict[str,...]]:
  """Use an LLM model.

  Returns result as a string plus a dictionary of measurements,
  including # input_tokens, # output_tokens, latency in seconds, and
  """
  if config.get('echo.model'):
    print(f'calling model {model}')

  if config.get('echo.llm_input'):
    echo_boxed(prompt, 'llm_input')

  messages = [dict(role='user', content=prompt)]
  start_time = time.time()
  response = completion(
    model=model,
    messages=messages
  )
  latency = time.time() - start_time
  model_output = response.choices[0].message.content

  if config.get('echo.llm_output'):
    echo_boxed(model_output, 'llm_output')

  stats = dict(
    input_tokens=response.usage.prompt_tokens,
    output_tokens=response.usage.completion_tokens,
    latency=latency,
    cost=completion_cost(completion_response=response),
  )
  return model_output, stats

def llm(prompt: str, model: str) -> tuple[str, dict[str,...]]:
  """Use an LLM model, with optional cachier caching via config."""
  return cached(_llm_impl)(prompt, model)

