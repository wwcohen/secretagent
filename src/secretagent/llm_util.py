from litellm import completion

def llm(prompt, model, echo_model=False):
  """Use an LLM model.
  """
  if echo_model:
    print(f'calling model {model}')

  response = completion(
    model=model,
    messages=[{"role": "user", "content": prompt}]
  )
  return response.choices[0].message.content

if __name__ == '__main__':
  # example model: together_ai/deepseek-ai/Deepseek-V3.1
  import sys
  print(f'Expected format: {sys.argv[0]} prompt .... MODEL')
  model = sys.argv[-1]
  prompt = sys.argv[1:-1]
  print(llm(' '.join(prompt), model, echo_model=True))
