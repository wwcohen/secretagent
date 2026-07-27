from typing import Literal
import workspace.SportsUnderstanding.workflows.template.operator as operator
import workspace.SportsUnderstanding.workflows.round_5.prompt as prompt_custom
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
        self.answer_generate = operator.AnswerGenerate(self.llm)
        self.custom = operator.Custom(self.llm)
        self.sc_ensemble = operator.ScEnsemble(self.llm)

    async def __call__(self, problem: str):
        """
        Implementation of the workflow
        """
        gens = [await self.answer_generate(input=problem) for _ in range(3)]
        sols = [await self.custom(input=f"Problem: {problem}\nThought: {g['thought']}\nAnswer: {g['answer']}", instruction=prompt_custom.ANSWER_FORMAT_PROMPT) for g in gens]
        solution = await self.sc_ensemble(solutions=[s['response'] for s in sols])
        return solution['response'], self.llm.get_usage_summary()["total_cost"]
