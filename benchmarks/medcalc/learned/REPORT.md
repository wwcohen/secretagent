# Ptool Induction on MedCalc — Findings

**Date:** 2026-04-26
**Pipeline:** trace gen (gemini-3.1-flash-lite + thinking + simulate_pydantic_thinking
prompt) → ptool_inducer over react step_info[].thought → simulate_pydantic
held-out eval on 110-case medcalc/train (seed=43)

## Headline

| variant                 | acc    | input tokens |
|-------------------------|--------|--------------|
| **stateless-oc0-mp3**   | **0.664** | **848K** |
| state-oc1-mp8           | 0.664  | 1116K        |
| state-oc0-mp8           | 0.636  | 1160K        |
| stateless-oc0-mp5       | 0.609  | 1297K        |
| stateless-oc0-mp8       | 0.600  | 1285K        |
| ...                     | ...    | ...          |
| react_eval (baseline)   | 0.582  | 2129K        |

Best induced configuration **beats the hand-written react baseline by 8.2 points**
(0.664 vs 0.582) while using **40% of the input tokens** (848K vs 2129K).

## What worked

- **only-correct=False** consistently outperforms only-correct=True. Recovery
  reasoning in failed rollouts is informative training data, not noise. Discarding
  it for "cleanliness" hurt both directions of the matrix.
- **max_ptools=3** is the sweet spot for this task. mp=5/8 added thinly-supported
  categories (the merge step caps unique categories at ~6 anyway). The induced
  3-tool set — `calculate_clinical_score`, `compute_clinical_value`,
  `apply_clinical_score` — is a tighter cut of the same competence as the 3
  hand-written tools (`identify_calculator`, `extract_clinical_values`,
  `compute_calculation`) and gives the agent room to reason instead of orchestrate.

## What did NOT work

- **State injection didn't pay off.** Best stateless and best state-aware tied on
  accuracy; stateless won on cost. Plan agent's R2 about state-aware being
  essential for `(focus: str)` ptools turned out wrong — gemini-flash-lite passes
  detailed `focus` strings carrying their own context (e.g.
  `'Child-Pugh Score for a 59-year-old female: bilirubin 1.2, albumin 4.3, ...'`),
  so the helpers don't need to read the patient note from `_REACT_STATE`.
  Recommend skipping state injection unless evidence emerges that some
  reasoning category benefits from raw note access.

## Surprises

- **Gemini-3.1-flash-lite is much stronger on medcalc than expected** — the
  baseline react with this model + thinking + thought-scaffolding gets 58.2%,
  vs. the historical DeepSeek-V3.1 baseline of 19.3%. Worth double-checking the
  result holds on the test split before drawing strong conclusions. The
  high-thinking + reasoning-text prompt may be doing most of the work.
- **The induced agent is dramatically cheaper** — fewer tool calls per case
  because the new tools subsume what the old pipeline split across three
  sequential calls. Lower tokens → lower latency → bigger throughput at the
  same dollar.

## Framework changes shipped

These were latent issues that the plan exposed; all are backward-compatible
(opt-in via new config keys; defaults preserve existing behaviour):

- `src/secretagent/learn/ptool_inducer.py` — populate `self.dataset` so
  `base.Learner.learn()` doesn't `AttributeError` on the standard CLI.
- `src/secretagent/implement/pydantic.py` — opt into alternate prompt template
  via `simulate_pydantic.template`; pass `llm.reasoning_effort` through to
  pydantic-ai's `ModelSettings.thinking`; capture the `'thinking'` part_kind
  in `_summarize_messages` alongside `'text'`.
- `src/secretagent/implement/prompt_templates/simulate_pydantic_thinking.txt`
  — new alternate template that wires the `$thoughts` placeholder and adds a
  hard reasoning requirement before each tool call.

## Out of scope

Did not run OrchestrationLearner. `benchmarks/medcalc/ptools_induced.py` +
`conf/induced_orch.yaml` are the bridge — orchestrate's supervisor can ingest
the file via `inspect.getsource` and start improving from this baseline.
