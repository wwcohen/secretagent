from secretagent import subagent, configure

@subagent()
def translate(english_sentence: str) -> str:
    """Translate a sentence in English to French.
    """

if __name__ == '__main__':
    configure(service="anthropic", model="claude-haiku-4-5-20251001")
    print(translate("What's for lunch today?"))
