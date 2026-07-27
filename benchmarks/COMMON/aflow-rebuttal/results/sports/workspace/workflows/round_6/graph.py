from typing import Literal
import workspace.SportsUnderstanding.workflows.template.operator as operator
import workspace.SportsUnderstanding.workflows.round_6.prompt as prompt_custom
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
        initial = await self.custom(input=problem, instruction=prompt_custom.ANSWER_FORMAT_PROMPT)
        solution = await self.custom(input=f"Problem: {problem}\nInitial Answer: {initial['response']}", instruction=prompt_custom.REVIEW_PROMPT)
        return solution['response'], self.llm.get_usage_summary()["total_cost"]
