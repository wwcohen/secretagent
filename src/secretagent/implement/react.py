"""Pydantic-ai based ReAct implementation factory.

Replaces the previous text-based LangChain-style ReAct (Yao+ ICLR 2023)
with a pydantic-ai Agent that uses the model's native tool-calling loop
and a clean ReAct preamble (no simulate / function-stub framing in the
prompt).

Usage in config:
    ptools:
      solve:
        method: react_pydantic
        tools:
          - mymodule.search
          - mymodule.lookup

Each benchmark may register this factory with its own preamble via
``register_factory('react_pydantic', ReactPydanticFactory(preamble=...))``;
the default preamble is generic.
"""

from pydantic import Field

from secretagent.core import register_factory
from secretagent.implement.pydantic import SimulatePydanticFactory


class ReactPydanticFactory(SimulatePydanticFactory):
    """Pydantic-ai agent with a clean task preamble (no simulate/stub framing).

    Uses pydantic-ai's native tool-calling loop. The prompt emitted is:
      <preamble>\\n\\n<formatted args>

    Each benchmark registers this factory with its own preamble:
      register_factory('react_pydantic',
                       ReactPydanticFactory(preamble=MY_PREAMBLE))
    """

    preamble: str = Field(
        default=(
            "Answer the following question as best you can. Use the "
            "available tools to gather evidence, then call finish() "
            "with your final answer."
        )
    )

    def setup(self, tools=None, tool_module=None, learner=None,
              preamble=None, **prompt_kw):
        super().setup(tools=tools, tool_module=tool_module,
                      learner=learner, **prompt_kw)
        if preamble is not None:
            self.preamble = preamble

    def create_prompt(self, interface, *args, **kw):
        input_args = interface.format_args(*args, **kw)
        return f"{self.preamble}\n\n{input_args}"


register_factory('react_pydantic', ReactPydanticFactory())
