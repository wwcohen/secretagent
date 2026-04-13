# Prompt: Create PowerPoint Slides for Population-Based Pipeline Optimization

Create a professional academic PowerPoint presentation (25-27 slides) for presenting at a research group meeting. The audience is ML/AI researchers familiar with LLMs and agentic systems. Use clean, minimal design with diagrams where appropriate.

---

## Slide 1: Title Slide

**Title:** Population-Based Pipeline Optimization for LLM Agentic Systems
**Subtitle:** Evolutionary search over code + prompts + configs + workflow structure
**Context:** Built on secretagent framework — "everything looks like code"
**Date:** April 2026

---

## Slide 2: Motivation & Problem Statement

**The Problem:**
- Complex LLM pipelines have many configuration decisions: which model, which prompting strategy, how to decompose tasks, error handling, routing logic
- Currently: manual grid search (`cli.optimize`) or ad-hoc tuning
- No systematic way to jointly optimize code, prompts, configs, and workflow structure

**Why This Matters:**
- Agentic systems are especially hard to optimize — incremental, interactive experimentation makes it easy to lose track of what was tried
- GEPA (ICLR 2026 Oral) showed evolutionary prompt optimization works, but only optimizes prompts
- We can optimize a **strictly broader search space**: code + prompts + configs + workflow structure

---

## Slide 3: secretagent Framework Overview

**Core Abstraction: Everything is an Interface**

```python
@interface
def identify_calculator(question: str, calculators: list[str]) -> dict:
    """Identify which medical calculator is needed."""
    ...  # stub — implementation bound later

# Bind to different strategies:
identify_calculator.implement_via('simulate')        # LLM predicts output
identify_calculator.implement_via('prompt_llm', ...) # Custom prompt template
identify_calculator.implement_via('direct', fn=...)  # Python code
identify_calculator.implement_via('orchestrate')     # LLM generates pipeline
```

**Key Principle:** The strategy (how interfaces are bound to implementations) is serializable as YAML. Every experiment is tagged with its complete strategy, making results reproducible.

---

## Slide 4: What Can Be Optimized

Show a table or diagram of the search space dimensions:

| Dimension | Example | How It's Changed |
|-----------|---------|-------------------|
| **Model** | Qwen3.5-9B → DeepSeek-V3.1 → GLM-5.1 | upgrade/downgrade transforms |
| **Method** | simulate → prompt_llm → direct → program_of_thought | swap_strategy transform |
| **Prompt/Docstring** | Rewrite interface docstring for better LLM simulation | evolve transform |
| **Pipeline Code** | Reorder calls, add error handling, add routing | repair, route, restructure transforms |
| **Workflow Structure** | Decompose expensive steps, add lookup shortcuts | expand, induce transforms |
| **Candidate Combination** | Merge best parts of two pipeline variants | crossover transform |

**vs GEPA:** GEPA optimizes only prompts. We optimize all 6 dimensions simultaneously.

---

## Slide 5: Architecture Overview (Full System Diagram)

**Diagram showing the three-layer hierarchy:**

```
┌─────────────────────────────────────────────────────┐
│  Layer 3: POPULATION-BASED OPTIMIZATION             │
│  ┌───────────────────────────────────────────────┐  │
│  │ Meta-Optimizer (LLM) guides mutation selection │  │
│  │ Population of pipeline candidates              │  │
│  │ Instance-wise Pareto front selection           │  │
│  │ Budget-aware evolutionary loop                 │  │
│  └───────────────────────────────────────────────┘  │
│           ↓ proposes mutations                       │
│  ┌───────────────────────────────────────────────┐  │
│  │ Layer 2: TRANSFORM CATALOG (11 operators)      │  │
│  │ Code transforms: repair, route, restructure,   │  │
│  │   expand, induce, crossover                    │  │
│  │ Config transforms: upgrade, downgrade,          │  │
│  │   swap_strategy, prune                         │  │
│  │ Evolution: evolve (GEPA-style ptool refinement) │  │
│  └───────────────────────────────────────────────┘  │
│           ↓ modifies                                 │
│  ┌───────────────────────────────────────────────┐  │
│  │ Layer 1: PIPELINE COMPOSITION                  │  │
│  │ LLM composes pipeline from ptool catalog       │  │
│  │ Pipeline = compiled Python calling ptools      │  │
│  │ Profiler measures per-ptool cost/accuracy      │  │
│  └───────────────────────────────────────────────┘  │
│           ↓ executes                                 │
│  ┌───────────────────────────────────────────────┐  │
│  │ Foundation: INTERFACE SYSTEM                   │  │
│  │ @interface stubs → implement_via() binding     │  │
│  │ Recorder captures all calls + LLM stats       │  │
│  │ Config-driven strategy serialization           │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## Slide 6: The Population Loop

**SEED → EVALUATE → SELECT → GUIDE → MUTATE → ACCEPT → BUDGET**

Show as a circular flow diagram with 7 nodes:

1. **SEED**: Generate initial population
   - compose_then_mutate: start from baseline, apply transforms for diversity
   - compose_n: generate N independent pipelines from scratch

2. **EVALUATE**: Run pipeline on stratified minibatch, collect per-ptool profiles

3. **SELECT**: Instance-wise Pareto front — keep candidates best on ≥1 example

4. **GUIDE**: Meta-optimizer LLM sees population + profiles + operators → proposes 1-3 mutations

5. **MUTATE**: Apply proposed transforms (code generation + ruff fix + compile)

6. **ACCEPT**: Evaluate mutated candidates, update profiles

7. **BUDGET**: Check cost budget (hard_stop / soft_stop / pareto mode)

**Repeat 3→7 until budget exhausted or target accuracy reached.**

---

## Slide 7: The Meta-Optimizer

**An LLM that reasons about how to improve other LLM pipelines.**

Show the meta-optimizer's input/output:

**Input:**
- Population summary (candidates, accuracies, mutation histories)
- Per-candidate profiling (cost breakdown, error patterns per ptool)
- Available operators (11 transforms with descriptions)
- Budget status (spent / limit / mode)

**Output:**
```json
[
  {"operator": "evolve", "candidate_index": 0,
   "reasoning": "extract_values_with_context has 51% cost fraction..."},
  {"operator": "swap_strategy", "candidate_index": 0,
   "reasoning": "identify_calculator could be Python + LLM fallback..."}
]
```

**Key Design:** The meta-optimizer makes ALL optimization decisions — which operator, which candidate, why. It replaces hardcoded heuristics with LLM reasoning.

---

## Slide 8: Instance-Wise Pareto Front

**Novel selection mechanism:** A candidate survives if it's the best on ANY single test case.

**Diagram:** Show 3 candidates with per-case performance:

| Case | Candidate A | Candidate B | Candidate C |
|------|-------------|-------------|-------------|
| BMI calculation | ✓ 1.0 | ✓ 1.0 | ✗ 0.0 |
| APACHE II score | ✗ 0.0 | ✗ 0.0 | **✓ 1.0** ← best |
| Wells PE score | **✓ 1.0** ← best | ✗ 0.0 | ✗ 0.0 |
| CKD-EPI GFR | ✗ 0.0 | **✓ 1.0** ← best | ✗ 0.0 |

All 3 are on the Pareto front because each is best on ≥1 case. This preserves **specialist diversity** — candidates that solve different subsets of the problem survive, enabling routing and crossover.

**vs. Aggregate Pareto:** Traditional Pareto on (accuracy, cost) would collapse to 1-2 candidates. Instance-wise keeps more diversity.

---

## Slide 9: Transform Catalog — Code Generation Pipeline

**Every LLM-based transform uses:**

```
Pipeline Code + Profiling Data + Transform Instruction
        ↓
   LLM generates new Python code
        ↓
   Extract ```python block
        ↓
   ruff check --fix (auto-format + lint)
        ↓
   Compile into Pipeline object (exec)
        ↓
   Validate (syntax + imports resolve)
```

**The transform_base.txt template provides:**
- Current pipeline code
- Profiling summary (per-ptool cost, errors, accuracy)
- Available tool stubs (ptool signatures + docstrings)
- Function signature
- Specific transform instruction (e.g., "add conditional routing", "decompose expensive calls")

---

## Slide 10: Transform Catalog — The 11 Operators

**Code transforms (LLM rewrites pipeline):**

| Operator | What it does | When it triggers |
|----------|-------------|------------------|
| **repair** | Add try/except, fallbacks for failing ptools | Error patterns detected |
| **route** | Add if/elif dispatch by input type | High accuracy variance across cases |
| **restructure** | Reorder calls (cheap first), add early exits, cache | Cost/latency patterns |
| **expand** | Break expensive multi-step ptool into focused sub-calls | High cost + low accuracy ptool |
| **induce** | Add lookup tables / shortcuts for common patterns | High-cost ptools with repeating inputs |
| **crossover** | Merge best parts of two parent pipelines | Population has ≥2 diverse candidates |

**Config transforms (change strategy bindings):**

| Operator | What it does |
|----------|-------------|
| **swap_strategy** | Change method (simulate → direct+fallback, simulate → prompt_llm) |
| **upgrade** | Switch to stronger model |
| **downgrade** | Switch to cheaper model |
| **prune** | Remove low-lift ptools |

**Evolution:**

| Operator | What it does |
|----------|-------------|
| **evolve** | GEPA-style evolutionary refinement of individual ptool prompts/implementations |

---

## Slide 11: Budget Tracking

**Three modes for different optimization strategies:**

| Mode | Behavior | Use Case |
|------|----------|----------|
| **hard_stop** | Stop immediately when budget exhausted (even mid-iteration) | Strict cost control |
| **soft_stop** | Finish current iteration, then stop | Balanced |
| **pareto** | Budget is advisory; stop when Pareto front converges | Quality-focused |

**Tracked costs:**
- Meta-optimizer guide calls
- Transform LLM calls (repair, route, evolve, etc.)
- Evaluation calls (running ptools on minibatches)
- Composition calls

**NOT tracked:** Per-run cost of the final pipeline (that's the pipeline's own cost)

---

## Slide 12: Profiling System

**Per-ptool metrics that drive optimization decisions:**

```
Pipeline accuracy: 80.0%, avg cost: $0.0020/case, 110 cases

Per-ptool breakdown:
  extract_values_with_context: cost_frac=53.1%, calls/case=1.0, avg_cost=$0.0011
  identify_calculator:         cost_frac=27.5%, calls/case=1.0, avg_cost=$0.0006
  reason_about_scoring:        cost_frac=17.7%, calls/case=0.3, avg_cost=$0.0013
  repair_missing_values:       cost_frac= 1.2%, calls/case=0.0, avg_cost=$0.0005
  simulate_medical_value:      cost_frac= 0.6%, calls/case=0.0, avg_cost=$0.0014
```

**How profiling feeds the meta-optimizer:**
- High cost_fraction → candidate for downgrade, swap_strategy, or expand
- High error_rate → candidate for repair or upgrade
- High accuracy variance → candidate for route
- Low lift → candidate for prune

---

## Slide 13: Model Catalog

**Dynamic model catalog loaded from YAML (not hardcoded):**

| Tier | Models | Price Range |
|------|--------|-------------|
| **Tier 1** (most capable) | GLM-5.1, MiniMax-M2.7 | $0.30-$4.40/M tokens |
| **Tier 2** (strong) | Qwen3.5-397B, DeepSeek-V3.1, Kimi-K2.5, GLM-5 | $0.20-$3.60 |
| **Tier 3** (efficient) | Qwen3-Coder, MiniMax-M2.5, Qwen3-235B | $0.20-$1.20 |
| **Tier 4** (budget) | GPT-OSS-120B, Qwen3.5-9B, GPT-OSS-20B | $0.05-$0.60 |
| **Reasoning** | DeepSeek-R1 | $3.00-$7.00 |

Upgrade/downgrade transforms traverse this catalog. Artificial Analysis API integration provides real-time benchmark data for model comparison.

---

## Slide 14: Test Benchmark — MedCalc-Bench

**Medical calculation benchmark with 55 calculators across multiple domains:**
- 10,543 train cases (HuggingFace dataset)
- Categories: equation-based (±5% tolerance) and rule-based (exact match)
- Stratified sampling by calculator name

**Pipeline levels tested:**
| Level | Method | Accuracy | Cost |
|-------|--------|----------|------|
| L0 | Direct LLM prompt | 73.1% | $0.58 |
| L1 | Simulate (docstring) | 65.5% | $0.54 |
| L2 | Python + LLM fallback | 67.3% | $0.18 |
| L3 | Program of Thought | 74.9% | $1.27 |
| **L4** | **Pipeline (our baseline)** | **78.9%** | **$0.15** |

Reference numbers on 275 cases (5/calc) with Qwen3.5-9B.

---

## Slide 15: Experimental Setup

**Optimization configuration:**
- Actor model: DeepSeek-V3.1 ($0.60/$1.70 per 1M tokens)
- Meta-optimizer model: DeepSeek-V3.1 (same)
- Population size: 3
- Budget: $25
- Caching: enabled (cachier)
- Eval set: 1-2 questions per calculator (55-110 cases)
- Final report: 4 questions per calculator (220 cases)

**All LLM calls routed through interfaces:**
- `reason_about_scoring` (scoring calculator analysis)
- `extract_values_with_context` (value extraction with calculator context)
- `repair_missing_values` (re-extraction for missing values)
- Full profiling visibility for all 5 LLM-backed ptools

---

## Slide 16: Experimental Results — What Worked

**Infrastructure validated end-to-end:**

1. **Profiling captures all ptools** — after routing inline `llm()` calls through interfaces, the profiler sees the full cost picture (5 ptools visible)

2. **Config changes affect evaluation** — downgrade from DeepSeek-V3.1 to Qwen3-Coder dropped accuracy 80.0% → 78.2% (verified: configs propagate)

3. **Meta-optimizer makes intelligent proposals:**
   - "upgrade extract_values_with_context — 51% cost fraction, likely accuracy bottleneck"
   - "swap_strategy identify_calculator — could be Python + LLM fallback"
   - "evolve reason_about_scoring — high cost per call, could improve prompt efficiency"

4. **Evolve transform runs real evolutionary search** — 2 generations, 3 variants each, fitness evaluation on train cases

5. **316 tests pass**, 46 human-style commits

---

## Slide 17: Experimental Results — What Didn't Work (Yet)

**No accuracy improvement in this session:**

| Configuration | Baseline | Best | Issue |
|---------------|----------|------|-------|
| Direct pipeline (V3.1, 2/calc) | 80.0% | 80.0% | Config transforms can't improve already-good pipeline |
| Direct pipeline (V3.1, 1/calc) | 71.0% | 71.0% | Delegate Pipeline too thin for code transforms |
| Orchestrated pipeline (V3.1) | 62.9% | 62.9% | LLM-generated code starts lower |

**Root causes identified:**

1. **Delegate Pipeline problem**: Hand-coded `pipeline_workflow` is a static Python function. The Pipeline object wrapping it is just `return calculate_medical_value(...)` — code transforms have nothing meaningful to rewrite.

2. **`instance_scores` never populated**: Pareto front returns ALL candidates (no instance-wise selection). The feature was designed but the plumbing connecting evaluation results to per-case scores was missing.

3. **Config not restored between candidates**: After evaluating candidate A's config, candidate B inherits A's settings.

4. **`should_apply` gates override meta-optimizer**: Transforms have hardcoded thresholds (e.g., `error_rate > 0.3`) that block mutations the meta-optimizer proposed. Wrong answers aren't "errors" in the profiler's sense.

---

## Slide 18: Key Architectural Insights

**Lesson 1: Profiling visibility is foundational**
The optimizer can only optimize what it can see. When extraction called `llm()` directly (bypassing interfaces), the profiler was blind to 70% of the pipeline's cost. Routing everything through `@interface` was essential.

**Lesson 2: The Pipeline must contain real code**
A thin delegate (`return workflow(...)`) gives code transforms nothing to modify. The Pipeline needs to contain the actual logic — either via `method: orchestrate` (LLM generates it) or by injecting the workflow source directly.

**Lesson 3: Meta-optimizer should be the authority**
Hardcoded `should_apply()` thresholds conflict with the meta-optimizer's reasoning. If the LLM says "upgrade this ptool," the transform should execute, not second-guess with `error_rate > 0.3`.

**Lesson 4: Instance-wise selection needs instance-wise data**
The Pareto front is designed for per-case specialization, but without populating `instance_scores` from results.jsonl, it degenerates to "return all candidates."

---

## Slide 19: Related Work Landscape

**Positioning in the literature — where this system fits among approaches to LLM pipeline optimization:**

### Prompt Optimization
- **GEPA** (ICLR 2026 Oral): Evolutionary prompt optimization with trace-informed mutation. SOTA for prompt-only search. Uses execution traces to guide which prompts to mutate. **Limitation:** optimizes only prompts, not code/structure/models.
- **DSPy** (Khattab et al., 2023): Declarative framework compiling LLM pipelines from signatures. Optimizes prompts via bootstrapping and teleprompters. **Limitation:** fixed pipeline structure, no code generation, no evolutionary search.
- **OPRO** (Yang et al., 2023): LLM-as-optimizer — uses LLM to propose prompt improvements from past scores. **Limitation:** single-objective, no population, no code.
- **EvoPrompt** (Guo et al., 2024): Evolutionary prompt optimization using genetic operators (crossover, mutation). **Limitation:** prompt-only, no profiling-driven guidance.

### Pipeline / Workflow Optimization
- **AutoGen** (Wu et al., 2023): Multi-agent conversation framework. Agents are handcrafted, not evolved. No automatic optimization loop.
- **LangGraph**: Stateful agent workflows as graphs. Manual design, no optimization.
- **MetaGPT** (Hong et al., 2023): Multi-agent software development. Fixed roles, not evolved.

### Program Synthesis / Code Search
- **AlphaCode / AlphaCode 2**: Generate + filter programs via population. **Similar spirit** but targets competitive programming, not pipeline optimization.
- **FunSearch** (Romera-Paredes et al., 2024): Evolutionary search over programs using LLM mutations. **Closest in approach** — but searches for single functions, not multi-component pipelines.
- **Program of Thought** (Chen et al., 2023): LLM generates Python code to solve reasoning tasks. Used as one of our implementation strategies (`program_of_thought` factory).

### Multi-Objective / Pareto Optimization
- **NSGA-II, MOEA/D**: Classical multi-objective evolutionary algorithms. We adapt the Pareto concept to instance-wise selection (per-case dominance rather than per-objective dominance).
- **Quality-Diversity** (MAP-Elites): Maintain diverse archive of high-performing solutions. Similar philosophy to our instance-wise Pareto — keep candidates that specialize on different subsets.

### Key Differentiators of Our Approach

| | Prompt Optimization | Code Search | Our System |
|---|---|---|---|
| Search space | Prompts | Single functions | Code + prompts + configs + workflow |
| Guidance | Score history | Generate & filter | LLM meta-optimizer + profiling |
| Selection | Top-k or tournament | Pass test cases | Instance-wise Pareto |
| Budget | Untracked | N/A | 3 tracked modes |
| Composition | Manual | N/A | LLM-generated from ptool catalog |
| Model selection | Fixed | Fixed | Dynamic catalog with 13+ models |

---

## Slide 20: Comparison with GEPA (Detailed)

| Dimension | GEPA (ICLR 2026) | Our System |
|-----------|-------------------|------------|
| **Search space** | Prompts only | Code + prompts + configs + workflow structure |
| **Mutation operators** | LLM-based prompt rewrite | 11 operators (code, config, evolution) |
| **Selection** | Aggregate fitness | Instance-wise Pareto front |
| **Guidance** | Trace-informed (execution trace in prompt) | Profile-informed (per-ptool cost/accuracy metrics) |
| **Budget awareness** | No | 3 budget modes (hard/soft/pareto) |
| **Model selection** | Fixed | Dynamic catalog with upgrade/downgrade |
| **Composition** | Manual | LLM-generated (orchestrate factory) |
| **Code generation** | No | Yes (LLM writes Python, ruff-fixed, compiled) |

**Key differentiator:** GEPA optimizes what the LLM says. We optimize what the LLM does — the actual code, workflow structure, and configuration of the pipeline.

---

## Slide 21: What's Next — Immediate Fixes

**Priority 1: Make transforms actually generate code**
- swap_strategy should write Python (regex matcher + LLM fallback), not just flip config
- upgrade/downgrade should rewrite prompts for the new model's strengths
- All transforms use the existing `_generate_code` + ruff pipeline

**Priority 2: Populate instance_scores**
- Extract per-case correctness from results.jsonl
- Enable real Pareto selection and specialist routing

**Priority 3: Remove should_apply hard gates**
- Let the meta-optimizer decide which transforms to apply
- Transforms execute what the meta-optimizer proposes

**Priority 4: Save/restore config between candidates**
- Use `config.configuration()` context manager
- Each candidate evaluated in isolation

---

## Slide 22: What's Next — Research Directions

**Real-time visualization:**
- Structured JSON event log from optimizer
- Browser-based dashboard showing Pareto front evolution, agent interactions, pipeline code diffs

**Adaptive operator selection:**
- Track which operators succeed/fail per generation
- Meta-optimizer learns operator effectiveness over time

**Cross-benchmark generalization:**
- Any benchmark can plug into the optimizer with `conf/splits.yaml` + evaluator
- Test on MuSR, BBH/sports_understanding, etc.

**Interleaving learning and optimization:**
- Learners produce new implementations (from `learn/` module)
- Optimizer evaluates and selects the best
- Iterate: learn → compose → optimize → learn

---

## Slide 23: Implementation Summary

**New code (this session):**
- 7 new Python modules (budget, population, meta_optimizer, 4 transforms)
- 3 transform stubs implemented (induce, expand, restructure)
- 3 prompt templates (meta_guide, crossover, compose enhanced)
- Model catalog YAML
- MedCalc benchmark integration (3 new interfaces, runner, configs)

**Metrics:**
- 46 commits (human-style, small, focused)
- 316 tests pass (0 failures)
- ~2,500 lines of new code
- 11 registered transforms (all implemented)

**Infrastructure proven:**
- End-to-end population loop works
- Meta-optimizer proposes intelligent mutations
- Config changes affect evaluation (verified with accuracy delta)
- Profiling captures all LLM calls
- Budget tracking operational

---

## Slide 24: secretagent Design Principles (Recap)

**1. Strategies are serializable** — Every implementation strategy is a YAML config. Experiments are reproducible.

**2. Experiments are trackable** — Every result is tagged with the complete strategy + date. The `savefile` package handles this automatically.

**3. Learning creates new implementations** — Learners output config for new implementations. The optimizer evaluates and selects.

**4. Optimization searches strategy space** — The population optimizer evaluates strategies and recommends good ones. Search space and results are saved for tracking.

---

## Slide 25: Demo / Questions

Show:
1. The meta-optimizer's actual output (JSON proposals with reasoning)
2. The profiling breakdown for MedCalc pipeline
3. A before/after of pipeline code modified by a transform
4. The population summary showing candidates with mutation histories

---

## Design Notes for Slide Creation

- Use CMU colors (dark red #A4152A, dark gray #333333) or neutral academic palette
- Diagrams should use boxes-and-arrows style, not decorative
- Code snippets in monospace, syntax highlighted if possible
- Keep text minimal on slides — details go in speaker notes
- The SEED→EVALUATE→SELECT→GUIDE→MUTATE→ACCEPT→BUDGET loop diagram is the centerpiece
- The GEPA comparison table is key for positioning the contribution
- Include the "what didn't work" slide — academic audiences appreciate honesty about limitations
