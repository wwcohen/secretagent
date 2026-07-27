from typing import Literal
import workspace.FinQA.workflows.template.operator as operator
import workspace.FinQA.workflows.round_10.prompt as prompt_custom
from scripts.async_llm import create_llm_instance


from scripts.evaluator import DatasetType

class Workflow:
    def __init__(
        self,
        name: str,
        llm_config,
        dataset: DatasetType,
    ) -> None:
        self.name = name
        self.dataset = dataset
        self.llm = create_llm_instance(llm_config)
        self.custom = operator.Custom(self.llm)

    async def __call__(self, problem: str):
        """
        Implementation of the workflow
        """
        solution = await self.custom(input=problem, instruction=prompt_custom.SOLVE_PROMPT)
        critique = await self.custom(input=problem + f"\nInitial Solution:\n{solution['response']}", instruction=prompt_custom.CRITIQUE_PROMPT)
        revise = await self.custom(input=problem + f"\nInitial Solution:\n{solution['response']}\nCritique:\n{critique['response']}", instruction=prompt_custom.REVISE_PROMPT)
        return revise['response'], self.llm.get_usage_summary()["total_cost"]
