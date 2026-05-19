# Ptool Orchestrator — Vision & Ideal Features

This document describes the full long-term vision for the orchestrator
system, beyond what V1 implements.

## Core Thesis

Each ptool has observable costs (latency, tokens, dollars) and observable
value (how much it contributes to correctness). An off-the-shelf
optimizer selects the best subset of ptools under a budget, and a
powerful LLM wires them into a coherent pipeline. The orchestrator is the
system that manages this selection → composition → execution → evaluation
→ improvement loop.

## V1 (Current)

- Single LLM call composes available ptools into a pipeline
- Generated Python code, compiled via exec()
- Retry with error feedback (pass@k)
- ruff --fix cleanup pass
- Integrates with existing eval/config/recording infrastructure

---

## V2: Metric Collection & Aggregation

### Per-Ptool Metrics

After evaluation runs, aggregate per-ptool metrics from results.jsonl:

- **avg_cost** — average USD per call (from litellm completion_cost)
- **avg_latency** — average seconds per call
- **success_rate** — fraction of problems where this ptool was used AND
  the final answer was correct
- **unused_success_rate** — fraction where this ptool was NOT used AND
  the answer was correct
- **lift** — `success_rate - unused_success_rate` (causal effect estimate
  of including this ptool)

Data source: the existing `record.py` rollouts in results.jsonl capture
which ptools are called per case. Combined with the evaluator's
`compare_predictions` metric, this gives all the data needed.

### Metric Store

A persistent JSON/Parquet store mapping `(ptool_name, dataset, config) →
metrics`. Updated after each evaluation run. Accessible via CLI:

```bash
uv run -m secretagent.cli.ptool_metrics --results-dir results/
```

---

## V3: Optimizer-Based Ptool Selection

### The Selection Problem

Given:
- A set of N available ptools with metrics (cost, latency, lift)
- A budget constraint (max total cost per problem, or max latency)

Select the subset S ⊂ ptools that maximizes expected accuracy subject to
the budget.

### Approaches (in order of complexity)

1. **Greedy by lift** — rank ptools by lift, add greedily until budget
   exhausted. Simple, interpretable, good baseline.

2. **Knapsack** — model as 0-1 knapsack: value = lift, weight = cost.
   scipy.optimize or dynamic programming. Handles budget constraints
   cleanly.

3. **Bayesian optimization** — treat the problem as a black-box function:
   ptool subset → accuracy. Use BO to explore the combinatorial space.
   Expensive (each evaluation requires running the pipeline) but finds
   non-obvious interactions.

4. **Reinforcement learning** — model ptool selection as a sequential
   decision. Each step: add or remove a ptool, observe accuracy change.
   Overkill for V3 but interesting research direction.

### Selection → Composition Flow

```
All ptools with metrics
    ↓
Optimizer: select subset under budget
    ↓
LLM: compose selected ptools into pipeline
    ↓
Evaluate on validation set
    ↓
Update metrics
    ↓
Repeat
```

---

## V4: Pipeline Bank

### Storage

Save generated pipelines for retrieval and reuse:

```python
@dataclass
class PipelineRecord:
    pipeline_id: str
    task_description: str
    ptool_names: list[str]
    source_code: str
    generated_by_model: str
    generated_at: datetime
    metrics: dict  # {accuracy, cost, latency} on eval set
    dataset_name: str
    config_snapshot: dict
```

### Retrieval

When composing for a new task:
1. Embed the task description
2. Search the bank for similar tasks (cosine similarity)
3. If a good match exists, offer it as a starting point
4. The LLM can adapt an existing pipeline instead of generating from scratch

### Versioning

Track pipeline evolution over time:
- When ptool metrics change, re-evaluate stored pipelines
- Flag pipelines whose accuracy has degraded
- Automatically suggest re-composition

---

## V5: Multi-Step Composition

### Analyze → Compose → Refine

For complex tasks, a single prompt may not be enough. The multi-step
approach (used in the old AgentProject):

1. **Analyze** — examine the task, dataset samples, and available tools.
   Output: task type, complexity, key challenges, recommended pattern.

2. **Compose** — given the analysis, design concrete pipeline stages.
   Output: Python code for the workflow function.

3. **Refine** — review the composed pipeline for robustness. Add
   validation steps, handle edge cases, improve error handling.
   Output: improved Python code.

Each step uses a focused prompt, reducing the cognitive load on the LLM.

### When to use multi-step

- Task has > 5 available ptools
- Task description is vague or complex
- Previous single-step attempts failed
- Domain requires validation or error handling

---

## V6: Self-Correction Loop

### Pipeline-Level Retry

If a generated pipeline achieves low accuracy on a validation set:

1. Sample N failures from the validation run
2. Analyze failure patterns (wrong tool used, wrong argument order, etc.)
3. Feed failures back to the LLM with the original pipeline code
4. Generate improved pipeline
5. Re-evaluate

### Ptool-Level Feedback

If a specific ptool consistently fails:
- Try a different implementation method (simulate → program_of_thought)
- Escalate to a stronger model for that ptool
- Add validation/retry around that ptool call

---

## V7: Pipeline Comparison & A/B Testing

### Experiment Framework

Run multiple pipeline variants on the same dataset:

```yaml
experiments:
  - name: hand_coded
    config: conf/murder.yaml
  - name: orchestrated_v1
    config: conf/murder_orchestrated.yaml
  - name: orchestrated_optimized
    config: conf/murder_optimized.yaml
```

### Comparison Report

Automated report showing:
- Accuracy per variant (with confidence intervals)
- Cost per problem per variant
- Latency per problem per variant
- Statistical significance tests
- Pipeline source code diffs

---

## V8: Audit Trail & Reproducibility

### Deterministic Execution Log

For each pipeline execution, record:
- Which ptools were called, in what order
- Input/output for each ptool call
- LLM stats (tokens, cost, latency) per call
- Total pipeline cost and latency

This is largely already implemented via `record.py`. The addition is:
- Saving the pipeline source code alongside results
- Making the log machine-parseable for the optimizer

### Reproducibility

Given a PipelineRecord + config snapshot + dataset:
- Re-execute the exact same pipeline
- Verify identical results (deterministic given same cache)
- Diff results between runs

---

## V9: Cost Budget Constraints

### Budget-Aware Composition

The orchestrator prompt includes a cost budget:

```
Budget: $0.05 per problem.
Available tools with estimated costs:
  - extract_suspects_and_evidence: ~$0.003/call
  - verify_alibis: ~$0.003/call
  - deduce_murderer: ~$0.004/call
  - raw_answer: ~$0.002/call

Select tools and compose a pipeline that stays within budget.
```

### Dynamic Budget Allocation

During execution, track cumulative cost. If approaching budget:
- Skip optional validation steps
- Use cheaper model variants for remaining ptools
- Fall back to simpler pipeline patterns

---

## V10: Advanced Features

### Prompt Caching

Together AI supports prompt caching — if the same catalog prefix is used
across multiple composition calls, the prefix is cached. This reduces
cost for iterative composition.

### Parallel Pipeline Branches

Some tasks benefit from parallel execution:
```python
result_a = path_a(input)
result_b = path_b(input)
final = merge(result_a, result_b)
```

The orchestrator should be able to generate DAG-structured pipelines,
not just linear sequences.

### Meta-Learning Across Datasets

Ptool metrics from one dataset inform selection on similar datasets.
Transfer learning for ptool selection: "ptools that help on MUSR murder
mysteries tend to also help on other deductive reasoning tasks."

### Distillation Integration

Once a good pipeline is found:
1. Run it on a large dataset to collect traces
2. Use the `learn/` package to distill traces into Python implementations
3. Replace expensive LLM-backed ptools with learned Python functions
4. Iterate: re-optimize with the cheaper implementations

This closes the loop between orchestration and the existing learning
system.
