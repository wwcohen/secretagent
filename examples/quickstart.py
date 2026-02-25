from secretagent import ptool, config

# This will implement 'translate' via asking an llm to generate a
# translation.  An Anthropic API key must be stored in your
# environment for this to work.

@ptool.ptool('ptp', model='claude-haiku-4-5-20251001')
def translate(english_sentence: str) -> str:
    """Translate a sentence in English to French.
    """

if __name__ == '__main__':
    print(translate("What's for lunch today?"))
