from typing import Literal
import workspace.FinQA.workflows.template.operator as operator
import workspace.FinQA.workflows.round_7.prompt as prompt_custom
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
        revs = [await self.custom(input=problem + f"\nInitial Solution:\n{s['response']}", instruction=prompt_custom.REVIEW_PROMPT) for s in sols]
        return (await self.sc_ensemble(solutions=[r['response'] for r in revs], problem=problem))['response'], self.llm.get_usage_summary()["total_cost"]
