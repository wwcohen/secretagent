from typing import Literal
import workspace.FinQA.workflows.template.operator as operator
import workspace.FinQA.workflows.round_9.prompt as prompt_custom
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
        sols = [await self.custom(input=problem, instruction=prompt_custom.SOLVE_PROMPT) for _ in range(3)]
        best = await self.sc_ensemble(solutions=[s['response'] for s in sols], problem=problem)
        review = await self.custom(input=problem + f"\nInitial Solution:\n{best['response']}", instruction=prompt_custom.REVIEW_PROMPT)
        final_ans = await self.custom(input=review['response'], instruction=prompt_custom.FORMAT_PROMPT)
        return final_ans['response'], self.llm.get_usage_summary()["total_cost"]
