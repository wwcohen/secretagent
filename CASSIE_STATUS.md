# secretagent "basics" grid — status snapshot (2026-07-08)

Reproduction of the paper's "basics" strategy grid on two gemini models, run
from the repo root via `secretagent.cli.basics`. Accuracy = % correct on the
evaluation pool (`n` per task). Strategies: unstructured / structured zero-shot
baselines, hand-coded `workflow`, program-of-thought (`pot`), and `ReAct`.

## gemini-3.1-pro-preview (strong model) — complete

| task | n | unstruct | structured | workflow | pot | react |
|---|--:|--:|--:|--:|--:|--:|
| bbh/date_understanding | 100 | 98 | 98 | 95 | 96 | 83 |
| bbh/geometric_shapes | 75 | 84 | 84 | 73 | 84 | 81 |
| bbh/penguins_in_a_table | 60 | 100 | 100 | 95 | 95 | **13 ⚠** |
| bbh/sports_understanding | 75 | 99 | 99 | 99 | 99 | 97 |
| natural_plan/calendar | 100 | 95 | 95 | 83 | 73 | 94 |
| natural_plan/meeting | 100 | 95 | 95 | 90 | 82 | 96 |
| natural_plan/trip | 100 | 93 | 100 | 99 | 99 | 90 |

## gemini-2.5-flash-lite (cheap model) — complete

| task | n | unstruct | structured | workflow | pot | react |
|---|--:|--:|--:|--:|--:|--:|
| bbh/date_understanding | 100 | 67 | 56 | 87 | 87 | 24 |
| bbh/geometric_shapes | 75 | 60 | 17 | 36 | 37 | 55 |
| bbh/penguins_in_a_table | 60 | 85 | 47 | 53 | 48 | 25 ⚠ |
| bbh/sports_understanding | 75 | 77 | 87 | 92 | 83 | 85 |
| natural_plan/calendar | 100 | 41 | 43 | 48 | 48 | 40 |
| natural_plan/meeting | 100 | 60 | 26 | 15 | 18 | 22 |
| natural_plan/trip | 100 | 6 | 10 | 11 | 11 | 8 |

**Legend:** plain = valid · ⚠ = valid but anomalously low (suspected harness/format
issue, see notes)

## Notes / flags

- **penguins `react` (both models) ⚠** — pro 13%, flash 25%. Added a regex
  fast-path in `penguins_react_workflow` (grab a trailing `(X)` before the
  LLM extractor); it helped flash (23→25) but **not pro**. Diagnosis (proven by
  the regex): pro's ReAct step **emits no answer letter at all** in 52/60 cases
  (verbose meta-commentary about the function), so no extractor — regex or LLM —
  can recover it. The problem is **upstream in the ReAct step**, not extraction.
  The professor's `ToolFactory` merge fixed this on claude-haiku (90%) but not
  gemini. **Discussion item: fix the ReAct prompt/framing so pro actually
  answers** (an extractor patch can't help). `date react` has a mild dose too.
- **calendar `pot` (pro) 13% → 73% — FIXED.** Root cause: the PoT sandbox
  blocked `import json` (the LLM-generated scheduling code imports it), so 86/100
  crashed. Fixed by adding a safe stdlib set (json, re, math, datetime, …) to the
  executor's authorized imports (`implement/core.py`). Also bumped meeting pot
  (pro 79→82, flash 15→18).
- **Windows encoding crashes — FIXED.** The unstructured baselines were hitting
  `'charmap' codec` errors on non-cp1252 LLM output; the driver now runs cells in
  Python UTF-8 mode (`cli/basics.py`). Scores unchanged (those examples were
  wrong regardless), but the grid is now crash-free (0 json / 0 charmap).
- **flash-lite `react` (BBH)** — now valid: the persistent-503 backlog was
  drained via a convergence loop (5 passes reusing cached successes). Numbers
  above are real.
- **flash-lite `react` (natural_plan)** — reran on the new engine (convergence
  loop drained the 503 tail); now valid. calendar 40 / meeting 22 / trip 8
  (vs old-engine 32 / 10 / 11).

## Decisions / open items

1. **Cheap model** *(resolved for now).* The whole flash half is complete on
   `gemini-2.5-flash-lite` — its throttle cleared and the react cells were
   drained via convergence loops. Switching to `gemini-3.1-flash-lite` /
   `2.5-flash` is now optional (only if the prof prefers a different cheap
   model), no longer blocking.
2. **penguins `react`** (the one remaining ⚠) — regex fast-path added (helped
   flash, not pro). Pro can only be improved by fixing the ReAct prompt so the
   strong model actually emits an answer (professor's domain), or report as-is.