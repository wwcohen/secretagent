from secretagent import config
from secretagent.core import implement_via

# This will implement 'translate' via asking an llm to generate a
# translation.  An Anthropic API key must be stored in your
# environment for this to work.

# a barebones example 

@implement_via('simulate', model='claude-haiku-4-5-20251001')
def translate(english_sentence: str) -> str:
    """Translate a sentence in English to French.
    """

# an example with a structured Pydantic output 

from pydantic import BaseModel

class FrenchEnglishTranslation(BaseModel):
    english_text: str
    french_text: str

from secretagent.pydantic_impl import SimulatePydanticFactory
@implement_via('simulate_pydantic', model='claude-haiku-4-5-20251001')
def translate_structured(english_sentence: str) -> FrenchEnglishTranslation:
    """Translate a sentence in English to French.
    """

if __name__ == '__main__':
    print(translate("What's for lunch today?"))
    print(translate_structured("What's for lunch today?"))
