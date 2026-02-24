import os

import anthropic
import google.generativeai as genai
import ollama
import openai
import together

# infrastructure for checkpointing LLMs results and running against
# multiple models

def _result(str_response, **kw):
  """Stub to allow more detailed logging later.
  """
  return str_response

def llm(prompt, service='anthropic', model=None, echo_service=False):
  """Use an LLM model.
  """
  if echo_service:
    print(f'calling service={service} model={model}')
  if service == 'openai':
    if model is None: model='gpt-4o-mini'
    client = openai.OpenAI()
    completion = client.chat.completions.create(
      model=model,
      messages=[
        {"role": "user", "content": prompt}
      ]
    )
    r = completion.choices[0].message.content
    return _result(r)
  elif service == 'gemini':
    if not model: model = 'gemini-1.5-flash'
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel(model)
    response = model.generate_content(prompt)
    try:
      num_output_tokens = model.count_tokens(response.text)
    except ValueError as ex:
      print(ex)
      return '** Gemini response blocked **'
    return _result(response.text)
  elif service == 'anthropic':
    if not model: model='claude-3-5-sonnet-20240620'  #claude-3-haiku-20240307, claude-3-sonnet-20240229
    client = anthropic.Anthropic(
      api_key=os.environ.get('ANTHROPIC_API_KEY'))
    try:
      message = client.messages.create(
        max_tokens=4096,
        model=model,
        temperature=0,
        messages=[{"role": "user", "content": prompt}])
      return _result(message.content[0].text)
    except anthropic.BadRequestError as ex:
      return _result(repr(ex))
  elif service == 'together':
    client = together.Together(api_key=os.environ.get("TOGETHER_API_KEY"))
    if not model: model = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    completion = client.chat.completions.create(
      model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
      max_tokens=8192,
      messages=[
        {"role": "user", 
         "content": prompt,
         }
      ],
    )
    r = completion.choices[0].message.content
    return _result(r)
  elif service == 'ollama':
    response = ollama.chat(model=model, messages=[
      dict(
        role='user',
        content=prompt)
    ])
    return _result(r.message.content)
  elif service == 'null':
    return 'null service was used - no answer'
  else:
    raise ValueError(f'invalid service {service}')
