# tau-bench Retail Report

## Setup

**Benchmark**: tau-bench retail (Sierra Research, 2024).  
114 tasks covering order cancellation, exchange, return, and modification for a synthetic retail database (50 products, 500 users, 1000 orders).

**Evaluation**: DB-based pass@1. Task succeeds if the agent's final database state matches the expected state after applying required write actions. Binary (0 or 1) per task, averaged over the `dev` split (60 tasks, seed=42).

**Models**:
- Agent: `together_ai/deepseek-ai/DeepSeek-V3.1`
- User simulator: `gpt-5.2` (OpenAI)

**Scoring note**: Tasks where all expected actions are read-only trivially pass (DB unchanged = gold state). ~8% of dev tasks fall in this category. This is visible in the baseline scores.

---

## Results (n=60 dev)

| Experiment | Accuracy | Agent cost/task | Total cost |
|---|---|---|---|
| `react` | **80%** | $0.086 | $6.49 |
| `workflow` | **67%** | $0.094 | $7.29 |
| `structured_baseline` | 8% | $0.029 | $3.37 |
| `unstructured_baseline` | 8% | $0.012 | $2.55 |

*Agent cost excludes user simulator ($0.022–$0.031/task for gpt-5.2).*

---

## Experiment Descriptions

### react (80%)
Free-form ReAct agent (`simulate_pydantic`) with access to all 16 retail tools. One `retail_agent` call per conversation turn; pydantic-ai handles the internal tool-calling loop. No structural guidance on tool order or task decomposition.

### workflow (67%)
PTP-style router: each turn, `classify_intent` identifies the request type, then routes to a specialized `plan_*` agent (simulate_pydantic) with a restricted tool subset. Two LLM calls per turn.

The 13-point gap vs react likely comes from:
1. **Extra failure point**: mis-classification mid-conversation (e.g., customer adds a second request, intent changes)
2. **Restricted tools**: `plan_exchange` doesn't have modify-order tools; edge cases fall through to `plan_generic`
3. **Cost overhead**: extra classify_intent call adds latency and occasionally times out

### structured_baseline / unstructured_baseline (8%)
No tool access. Structured_baseline uses a rigid 3-step decomposition (classify → plan → format), all simulate. Unstructured_baseline uses a single simulate call. Both score 8% — the trivially-passing read-only tasks — confirming tools are required.

---

## Key Findings

**1. Tools are necessary.** Without tool access, accuracy collapses to ~8% regardless of how sophisticated the prompt decomposition is. The 8% represents read-only tasks where the expected DB state happens to match the initial state.

**2. Free-form ReAct is a strong baseline.** 80% on dev significantly exceeds the published DeepSeek R1 score of 63.9% (tau-bench leaderboard). The gap is partly attributable to gpt-5.2 as user simulator being more cooperative than the leaderboard's setup.

**3. Guided decomposition (workflow) closes most of the gap but not all.** 67% vs 80% — the router adds structure at the cost of fragility. The per-turn routing overhead (extra LLM call + restricted tools) introduces failure modes that free-form React avoids.

**4. The right level for PTP decomposition is within a turn, not across turns.** Both react and workflow call the agent once per turn. The difference is in how the agent is instructed. This suggests the natural PTP extension is a structured multi-subflow prompt within a single `simulate_pydantic` call — guiding which tools to call in which order without adding extra classification overhead.

---

## Next Experiments

| Experiment | Hypothesis | Status |
|---|---|---|
| `ptp` | Single call with multi-subflow trace in prompt matches or beats react | ⬜ Pending |
| `react` (full, n=114 base) | Reproduce leaderboard conditions | ⬜ Pending |
| Final `test` split eval | Locked results for publication | ⬜ Hold until methods frozen |

---

## Reference

- tau-bench: Yao et al., 2024. [arXiv:2407.09974](https://arxiv.org/abs/2407.09974)
- DeepSeek R1 score (63.9% retail): [DeepSeek API changelog 2025-05-28](https://api-docs.deepseek.com/updates)
- PTP: Cohen & Cohen, 2024. [arXiv:2409.15359](https://arxiv.org/abs/2409.15359)
