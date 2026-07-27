# A2 sanity check: run the seed round_1 workflows on 4 validation cases each.
import asyncio
import os

from scripts.async_llm import LLMsConfig
from benchmarks.bbh import BBHBenchmark
from benchmarks.finqa import FinQABenchmark
from workspace.SportsUnderstanding.workflows.round_1.graph import Workflow as SportsWF
from workspace.FinQA.workflows.round_1.graph import Workflow as FinQAWF

os.makedirs("sanity_logs", exist_ok=True)
EXEC = LLMsConfig.default().get("gemini-2.5-flash-lite")


async def main():
    swf = SportsWF(name="SportsUnderstanding", llm_config=EXEC, dataset="SportsUnderstanding")
    sb = BBHBenchmark(name="SportsUnderstanding",
                      file_path="data/datasets/sportsunderstanding_validate.jsonl",
                      log_path="sanity_logs")
    print("SPORTS (avg_score, avg_cost, total_cost):", await sb.run_evaluation(swf, [0, 1, 2, 3]))

    fwf = FinQAWF(name="FinQA", llm_config=EXEC, dataset="FinQA")
    fb = FinQABenchmark(name="FinQA",
                        file_path="data/datasets/finqa_validate.jsonl",
                        log_path="sanity_logs")
    print("FINQA (avg_score, avg_cost, total_cost):", await fb.run_evaluation(fwf, [0, 1, 2, 3]))


if __name__ == "__main__":
    asyncio.run(main())
