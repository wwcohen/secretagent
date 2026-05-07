
| Benchmark | n_test | **acc** |
|---|---|---|
| MUSR murder    | 100 | **75.0** |
| MUSR object    | 106 | **68.9** |
| MUSR team      | 100 | **68.0** |
| RuleArena NBA  | 66  | **74.2** |
| NatPlan meeting | 100 | **29.0** |
| NatPlan trip   | 96  | **5.2**  |

The "ReAct + learned ptools" condition you described corresponds to my **Induced (Variant D)** configuration:

- ReAct agent
- Action space = 5 LLM-bound primitives induced from successful ReAct rollouts + `finish`
- Single-pass induction; correct-only trace filter; no descriptions surfaced in system prompt
- All trace gen / induction / eval on DeepSeek-V3 (Together AI), temperature 0 at eval

## Learned ptool modules (seed 42)

| Benchmark | path |
|---|---|
| MUSR murder    | `inducer_results/musr/induced_ptools_seed42_correct_murder.py` |
| MUSR object    | `inducer_results/musr/induced_ptools_seed42_correct_object.py` |
| MUSR team      | `inducer_results/musr/induced_ptools_seed42_correct_team.py` |
| RuleArena NBA  | `inducer_results/rulearena/induced_ptools_seed42_correct_enh_nba.py` |
| NatPlan meeting | `inducer_results/natural_plan/induced_ptools_seed42_correct_llm_meeting.py` |
| NatPlan trip   | `inducer_results/natural_plan/induced_ptools_seed42_correct_llm_trip.py` |

Each module exports 5 primitives: `@implement_via('simulate')`-decorated functions whose docstring is the prompt and whose typed signature is the interface. The agent's ReAct loop registers `{induced_primitives} ∪ {finish}` as its action space.

**External dependency**: each file imports `from ptools.ptools_common import _REACT_STATE` — this is a `reasoning_primitives`-side shared dict the ptools read for narrative / context / problem state. To run these in this repo, replace that with whatever state-injection mechanism this codebase prefers (e.g., pass state explicitly through the function signature, or provide a local `_REACT_STATE` module).

## ReAct + engineered (hand-designed) ptools

| Benchmark | n_test | **acc** |
|---|---|---|
| MUSR murder    | 100 | **48.0** |
| MUSR object    | 106 | **34.0** |
| MUSR team      | 100 | **47.0** |
| RuleArena NBA  | 46  | **58.7** |
| NatPlan meeting | 100 | **25.0** |
| NatPlan trip   | 100 | **15.0** |