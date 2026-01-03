# secretagent
Lightweight codebase for building agentic systems where everything looks like code.

## Quickstart

First provide the type signature and docstring for a Python function,
and decorate it with the 'subagent' decorator

```python
from secretagent import subagent, configure

@subagent()
def translate(english_sentence: str) -> str:
    """Translate a sentence in English to French.
    """
```

Then you can configure an LLM and run your unimplemented Python routine.

```python
>>> configure(service="anthropic", model="claude-haiku-4-5-20251001")
>>> print(translate("What's for lunch today?"))
Qu'est-ce qu'il y a pour le déjeuner aujourd'hui?

```
