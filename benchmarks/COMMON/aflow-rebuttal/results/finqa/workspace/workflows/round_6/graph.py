from typing import Literal
import workspace.FinQA.workflows.template.operator as operator
import workspace.FinQA.workflows.round_6.prompt as prompt_custom
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
        review_input = f"Problem:\n{problem}\n\nInitial Solution:\n{solution['response']}"
        review = await self.custom(input=review_input, instruction=prompt_custom.REVIEW_PROMPT)
        return review['response'], self.llm.get_usage_summary()["total_cost"]
