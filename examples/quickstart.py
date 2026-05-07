"""A simple example of how to use the secretagent package.

Usage:
    uv run examples/quickstart.py
    uv run examples/quickstart.py --model together_ai/google/gemma-3n-E4B-it
"""

import sys

from pydantic import BaseModel

from secretagent.core import interface, implement_via

DEFAULT_MODEL = 'claude-haiku-4-5-20251001'

# This will implement 'translate' via asking an llm to generate a
# translation.  An Anthropic API key must be stored in your
# environment for this to work.

# Values of 'llm.model' are passed to the litellm backend, so anything
# litellm understands will work.

@interface
def translate(english_sentence: str) -> str:
    """Translate a sentence in English to French.
    """

# A second example with a structured output.  The 'simulate_pydantic'
# implementation is more powerful - it's backed up by the Pydantic AI
# package, which also supports tools calls in a ReAct framework - and
# is also better at structured outputs.

class FrenchEnglishTranslation(BaseModel):
    english_text: str
    french_text: str

@interface
def translate_structured(english_sentence: str) -> FrenchEnglishTranslation:
    """Translate a sentence in English to French.
    """

if __name__ == '__main__':
    model = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    print(f'Using model: {model}')

    translate.implement_via('simulate', llm={'model': model})
    print('unstructured', translate("What's for lunch today?"))

    translate_structured.implement_via('simulate_pydantic', llm={'model': model})
    print('pydantic', translate_structured("What's for lunch today?"))

    # example of supplying your own custom prompt
    translate.implement_via(
        'prompt_llm',
        prompt_template_str='Translate $english_sentence to French - just return one sentence.',
        answer_pattern=None,
        llm={'model': model})
    print('Custom prompt', translate("What's for lunch today?"))
    
