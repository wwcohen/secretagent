"""Access an LLM model, and monitors cost, latency, etc.
"""

import time
from litellm import completion, token_counter, completion_cost

def llm(prompt: str, model: str, echo_model: bool = False) -> tuple[str, dict[str,...]]: 
  """Use an LLM model.

  Returns result as a string plus a dictionary of measurements,
  including # input_tokens, # output_tokens, latency in seconds, and 
  """
  if echo_model:
    print(f'calling model {model}')

  messages = [dict(role='user', content=prompt)]
  start_time = time.time()
  response = completion(
    model=model,
    messages=messages
  )
  latency = time.time() - start_time
  model_output = response.choices[0].message.content
  stats = dict(
    input_tokens=token_counter(
      model=model, messages=messages),
    output_tokens=token_counter(
      model=model, messages=[
        dict(role='user', content=model_output)]),
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
