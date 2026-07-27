from typing import Literal
import workspace.SportsUnderstanding.workflows.template.operator as operator
import workspace.SportsUnderstanding.workflows.round_7.prompt as prompt_custom
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
        self.sc_ensemble = operator.ScEnsemble(self.llm)

    async def __call__(self, problem: str):
        """
        Implementation of the workflow
        """
        responses = [await self.custom(input=problem, instruction=prompt_custom.ANSWER_FORMAT_PROMPT) for _ in range(5)]
        solution = await self.sc_ensemble(solutions=[r['response'] for r in responses])
        return solution['response'], self.llm.get_usage_summary()["total_cost"]
