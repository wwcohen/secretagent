# Held-out test pass for an optimized AFlow workflow.
#
# Selects the best round by MEAN VALIDATION score from workspace results.json
# (selection on validation only), then scores that round's graph once on the
# held-out *_test.jsonl. Bypasses optimizer.test() (hardcoded rounds=[1] and a
# separate workflows_test dir) — same eval path as validation, full control.
#
# Usage:
#   .venv/Scripts/python.exe test_pass.py --dataset SportsUnderstanding [--round N]
import argparse
import asyncio
import importlib
import json
import os
from collections import defaultdict

from scripts.async_llm import LLMsConfig
from benchmarks.bbh import BBHBenchmark
from benchmarks.finqa import FinQABenchmark

BENCH = {"SportsUnderstanding": BBHBenchmark, "FinQA": FinQABenchmark}
EXEC_MODEL = "gemini-2.5-flash-lite"


def best_round(dataset: str) -> int:
    with open(f"workspace/{dataset}/workflows/results.json", encoding="utf-8") as f:
        entries = json.load(f)
    by_round = defaultdict(list)
    for e in entries:
        by_round[e["round"]].append(e["score"])
    means = {r: sum(s) / len(s) for r, s in by_round.items()}
    for r in sorted(means):
        print(f"  round {r:2d}: mean val score {means[r]:.4f} over {len(by_round[r])} repeats")
    best = max(sorted(means), key=lambda r: means[r])
    print(f"BEST ROUND (validation): {best} (mean {means[best]:.4f})")
    return best


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=list(BENCH))
    ap.add_argument("--round", type=int, default=None, help="Round to test (default: best by mean val score)")
    args = ap.parse_args()

    r = args.round if args.round is not None else best_round(args.dataset)
    graph_mod = importlib.import_module(f"workspace.{args.dataset}.workflows.round_{r}.graph")

    exec_cfg = LLMsConfig.default().get(EXEC_MODEL)
    wf = graph_mod.Workflow(name=args.dataset, llm_config=exec_cfg, dataset=args.dataset)

    log_dir = f"test_logs/{args.dataset}/round_{r}"
    os.makedirs(log_dir, exist_ok=True)
    bench = BENCH[args.dataset](
        name=args.dataset,
        file_path=f"data/datasets/{args.dataset.lower()}_test.jsonl",
        log_path=log_dir,
    )
    score, avg_cost, total_cost = await bench.run_evaluation(wf, va_list=None)
    usage = wf.llm.get_usage_summary()
    n = sum(1 for _ in open(bench.file_path, encoding="utf-8"))
    with open(f"{log_dir}/usage.json", "w", encoding="utf-8") as f:
        json.dump({"round": r, "n_cases": n, "score": score,
                   "calls": usage["call_count"],
                   "input_tokens": usage["total_input_tokens"],
                   "output_tokens": usage["total_output_tokens"],
                   "tracked_cost": usage["total_cost"],
                   "calls_per_case": usage["call_count"] / n,
                   "in_tok_per_case": usage["total_input_tokens"] / n,
                   "out_tok_per_case": usage["total_output_tokens"] / n,
                   "cost_per_case": usage["total_cost"] / n}, f, indent=1)
    print(f"TEST RESULT dataset={args.dataset} round={r} "
          f"score={score:.4f} avg_cost=${avg_cost:.6f} total_cost=${total_cost:.4f} "
          f"calls/case={usage['call_count']/n:.2f} out_tok/case={usage['total_output_tokens']/n:.1f}")


if __name__ == "__main__":
    asyncio.run(main())
