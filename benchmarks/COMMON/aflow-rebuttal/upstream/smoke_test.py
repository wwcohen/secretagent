# Smoke test: Gemini OpenAI-compat endpoint through AFlow's AsyncLLM.
import asyncio

from scripts.async_llm import LLMsConfig, AsyncLLM


async def main():
    cfgs = LLMsConfig.default()
    for name in ["gemini-2.5-flash-lite", "gemini-3.1-pro-preview"]:
        print(f"\n===== {name} =====")
        llm = AsyncLLM(cfgs.get(name))
        resp = await llm("Answer the question inside XML tags, e.g. <answer>...</answer>. "
                         "Question: is the sky blue on a clear day? Reply yes or no.")
        summary = llm.get_usage_summary()
        print(f"SMOKE OK: tags_present={'<answer>' in (resp or '')} "
              f"calls={summary['call_count']} cost=${summary['total_cost']:.6f}")


if __name__ == "__main__":
    asyncio.run(main())
