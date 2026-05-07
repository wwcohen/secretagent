# tau-bench Retail Benchmark

## TL;DR

**Why tau-bench retail?** tau-bench (Sierra Research, 2024) is an agent benchmark for customer service. The retail domain simulates an agent handling order management requests (cancel, modify, exchange, return) against a live database of 500 users, 1000 orders, and 50 product types. Unlike TabMWP, tau-bench requires multi-turn conversations, stateful tool use, and explicit user confirmation — a genuinely agentic setting.

The benchmark tests:
- **Agentic tool use**: Can the agent look up user/order/product info and make the right DB changes?
- **Policy compliance**: Does the agent follow rules (authenticate, confirm before writes, stay in scope)?
- **Multi-turn reasoning**: Can the agent track context across 5-15 conversation turns?

---

## Status

| Phase | Status |
|---|---|
| Phase 1: Data setup | ✅ Done |
| Phase 2: Environment port (tau_env.py) | ✅ Done |
| Phase 3: ptools + outer loop | ✅ Done |
| Phase 4: expt.py | ✅ Done |
| Phase 5: react + baseline conf files | ✅ Done |
| Phase 6: n=10 smoke run | ✅ Done |
| Phase 7: n=50 evaluation run | ⬜ Pending |
| Phase 8: Export + report + plot | ⬜ Pending |
| Phase 9: Additional experiment configs | ⬜ Future |

---

## Data

**Source:** Sierra Research, tau2-bench (MIT License).
[github.com/sierra-research/tau2-bench](https://github.com/sierra-research/tau2-bench)

**Files in `data/` (gitignored, download with `download.py`):**
- `db.json` (2.7 MB) — shared retail database: 50 products, 500 users, 1000 orders
- `tasks.json` (338 KB) — 114 task definitions
- `policy.md` (7 KB) — agent policy guidelines

**Split policy:** All 114 tasks are used by default (split `base`). Final eval uses the same 114 tasks.

**Database:** One shared `db.json`. Each task resets the DB to its initial state before running (`TauEnv.reset(task_id)`). Tasks differ only in which user/order is involved.

---

## Architecture

### tau_env.py (self-contained, no tau2 dependency)

- **Data models**: `Variant`, `Product`, `User`, `Order`, `RetailDB` — ported from tau2
- **RetailTools**: 16 operations (8 read + 6 write + 2 generic) — ported from tau2
- **Task models**: `Task`, `UserScenario`, `EvaluationCriteria` — minimal subset
- **TauEnv**: `reset(task_id)` → fresh DB copy + initial user message; `score()` → DB comparison

### ptools.py

```python
# 16 retail tool stubs (direct: delegate to _CURRENT_ENV.tools)
find_user_id_by_name_zip, find_user_id_by_email
get_order_details, get_product_details, get_item_details, get_user_details
list_all_product_types, calculate
cancel_pending_order, modify_pending_order_{address,items,payment}
modify_user_address, exchange_delivered_order_items
return_delivered_order_items, transfer_to_human_agents

# Agent: simulate_pydantic with all 16 tools
retail_agent(conversation_str: str) -> str

# User simulator: prompt_llm (gpt-5.2)
user_simulator(conversation_str: str, task_instructions: str) -> str

# Top-level: direct (outer conversation loop)
tau_solve(task_id: str) -> str  # returns reward as "0.0" or "1.0"
```

### Conversation loop (inside `tau_solve`):

```
initial_message = env.reset(task_id)   # from task instructions
for turn in range(max_turns=15):
    agent_response = retail_agent(conversation_str)   # simulate_pydantic + tools
    if transfer_requested or max_turns: break
    user_response  = user_simulator(conversation_str, task_instructions)
    if "[DONE]" in user_response: break
reward = env.score()  # DB comparison
```

### Scoring

Compare final agent DB state to "gold" state (initial DB + expected write actions applied).
- Both match → 1.0
- Any mismatch → 0.0

Note: `NL_ASSERTION`-based scoring (requires LLM judge) is not implemented. Tasks with `reward_basis: ["DB", "NL_ASSERTION"]` are scored on DB only — may inflate scores for tasks where the DB change alone is insufficient.

---

## Experiments

| expt_name | conf file | Agent method | Description |
|---|---|---|---|
| `react` | `conf/react.yaml` | `simulate_pydantic` + 16 tools | ReAct agent with full tool access |
| `unstructured_baseline` | `conf/unstructured_baseline.yaml` | `simulate` (no tools) | No tool access; establishes tools are required |

**Planned (Phase 9):**
- `structured_baseline`: 3-step rigid workflow (identify_intent → plan_actions → respond)
- `workflow`: PTP-style guided trace

All experiments use:
- Agent model: `together_ai/deepseek-ai/DeepSeek-V3.1`
- User simulator: `gpt-5.2` (OpenAI)
- Dataset: 114 tasks, `split=base`, `shuffle_seed=42`

---

## Key findings (preliminary, n=1)

- Task 70 (helmet exchange) scored **1.0** in the quick-test
- ~5 agent turns, ~5 user turns per task
- Cost: ~$0.07/task (agent $0.05 + user simulator $0.012)
- Tool errors (e.g., wrong payment method) are handled gracefully by pydantic-ai

---

## Delivering results to the team

### Phase 8: Export, report, plot

```bash
# From project root:

# 1. Check accuracy + cost
uv run python -m secretagent.cli.results average \
  --metric correct --metric cost- \
  benchmarks/tau_bench_retail/results/*/

# 2. Export
uv run python -m secretagent.cli.results export \
  --as tau_bench_retail \
  benchmarks/tau_bench_retail/results/*/

# 3. Plot (cost vs accuracy)
uv run python -m secretagent.cli.results plot \
  --metric correct --metric cost- \
  --output benchmarks/tau_bench_retail/tau_bench_plot.png \
  benchmarks/tau_bench_retail/results/*/
```

---

## Conceptual context

### Why tau-bench after TabMWP

TabMWP showed PTP-style decomposition works for data-dependent reasoning. tau-bench tests the next level: stateful, multi-turn, policy-constrained agentic behavior. The agent must:
1. **Authenticate** the user (not in TabMWP)
2. **Plan** which tool calls to make (multiple steps, not predetermined)
3. **Confirm** before writes (policy compliance)
4. **Recover** from errors (wrong IDs, invalid operations)

### Comparison to published results

tau-bench leaderboard (taubench.com, retail domain):
- GPT-4o: ~50-55% pass@1
- DeepSeek-R1: ~63.9% pass@1 (per DeepSeek changelog 2025-05-28)
- GPT-5.2: presumably higher (used as user simulator on leaderboard)

Our target: match or approach DeepSeek-R1's 63.9% with `react` config.

### References

- **tau-bench**: Yao et al., "tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains," 2024.
- **tau2-bench**: Sierra Research, 2025. [arXiv:2506.07982](https://arxiv.org/pdf/2506.07982)
- **PTP**: Cohen & Cohen, 2024. [arXiv:2409.15359](https://arxiv.org/abs/2409.15359)
