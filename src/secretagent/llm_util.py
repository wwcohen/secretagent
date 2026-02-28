"""Access an LLM model, and monitors cost, latency, etc.
"""

import time


from secretagent import config
from litellm import completion, completion_cost


def _print_boxed(text: str, tag:str = ''):
  lines = text.split('\n')
  width = max(len(line) for line in lines)
  print('┌' + tag.center(width+2, '─') + '┐')
  for line in lines:
    print('│ ' + line.ljust(width) + ' │')
  print('└' + '─' * (width + 2) + '┘')

  
def llm(prompt: str, model: str) -> tuple[str, dict[str,...]]: 
  """Use an LLM model.

  Returns result as a string plus a dictionary of measurements,
  including # input_tokens, # output_tokens, latency in seconds, and 
  """
  if config.get('echo_model'):
    print(f'calling model {model}')

  if config.get('echo_llm_input'):
    _print_boxed(prompt, 'llm_input')

  messages = [dict(role='user', content=prompt)]
  start_time = time.time()
  response = completion(
    model=model,
    messages=messages
  )
  latency = time.time() - start_time
  model_output = response.choices[0].message.content

  if config.get('echo_llm_output'):
    _print_boxed(model_output, 'llm_output')

  stats = dict(
    input_tokens=response.usage.prompt_tokens,
    output_tokens=response.usage.completion_tokens,
    latency=latency,
    cost=completion_cost(completion_response=response),
  )
  return model_output, stats


if __name__ == '__main__':
  # example model: together_ai/deepseek-ai/Deepseek-V3.1
  import sys
  from pprint import pprint
  print(f'Expected format: {sys.argv[0]} prompt .... MODEL')
  model = sys.argv[-1]
  prompt = sys.argv[1:-1]
  pprint(llm(' '.join(prompt), model, echo_model=True))

