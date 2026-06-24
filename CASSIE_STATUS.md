# secretagent "basics" grid — status snapshot (2026-06-24)

Reproduction of the paper's "basics" strategy grid on two gemini models, run
from the repo root via `secretagent.cli.basics`. Accuracy = % correct on the
evaluation pool (`n` per task). Strategies: unstructured / structured zero-shot
baselines, hand-coded `workflow`, program-of-thought (`pot`), and `ReAct`.

## gemini-3.1-pro-preview (strong model)

| task | n | unstruct | structured | workflow | pot | react |
|---|--:|--:|--:|--:|--:|--:|
| bbh/date_understanding | 100 | 98 | 98 | 95 | 96 | 83 ⚠ |
| bbh/geometric_shapes | 75 | 84 | 84 | 73 | 84 | 81 |
| bbh/penguins_in_a_table | 60 | 100 | 100 | 95 | 95 | **13 ✗** |
| bbh/sports_understanding | 75 | 99 | 99 | 99 | 99 | 97 |
| natural_plan/calendar | — | — | — | — | — | — |
| natural_plan/meeting | — | — | — | — | — | — |
| natural_plan/trip | — | — | — | — | — | — |

## gemini-2.5-flash-lite (cheap model)

| task | n | unstruct | structured | workflow | pot | react |
|---|--:|--:|--:|--:|--:|--:|
| bbh/date_understanding | 100 | 67 | 56 | 87 | 87 | ✗ 503 |
| bbh/geometric_shapes | 75 | 60 | 17 | 36 | 37 | ✗ 503 |
| bbh/penguins_in_a_table | 60 | 85 | 47 | 53 | 48 | ✗ 503 |
| bbh/sports_understanding | 75 | 77 | 87 | 92 | 83 | ✗ 503 |
| natural_plan/calendar | 100 | 41 | 43 | 48 | 48 | 32 ᵒ |
| natural_plan/meeting | 100 | 62 | 26 | 15 | 15 | 10 ᵒ |
| natural_plan/trip | 100 | 6 | 10 | 11 | 11 | 11 ᵒ |

**Legend:** plain = valid · ⚠ = valid, flagged · ✗ = not usable, rerun needed ·
ᵒ = old engine (pre-merge), rerun needed · — = not run yet

## Notes / flags

- **penguins pro `react` = 13% ⚠✗** — the strong model emits verbose
  meta-commentary that the LLM-based `extract_option_letter` can't parse
  (52/60 → NaN). The ReAct engine merge (`ToolFactory`) fixed this on
  claude-haiku (90%) but **not** on pro-preview. `date` pro `react` shows a mild
  dose of the same (13/100 NaN, still 83%). **Discussion item.**
- **flash-lite `react` (BBH) ✗** — blocked by persistent 503s on
  `gemini-2.5-flash-lite` (50–58 of each task's examples failed; a sustained
  40–70% error rate over 24h+). The numbers from that run are congestion noise,
  not real performance.
- **flash-lite `react` (natural_plan) ᵒ** — ran clean, but on the *old* engine
  (pre-merge); needs a rerun for consistency.
- **pro natural_plan** — not run yet (entire NP half on the strong model).

## Decisions needed

1. **Cheap model.** `gemini-2.5-flash-lite` is persistently throttled;
   `gemini-3.1-flash-lite` and `gemini-2.5-flash` are healthy (8/8 on probe).
   Switching means rerunning the whole flash half for column consistency
   (~$5–10, completes cleanly) vs. continuing to wait on 2.5-flash-lite.
2. **pro natural_plan scope.** Full pools (~$100, ~10–20 h) vs. an `--n 25`
   minibatch (~$25, a few hours) for an approximate NP-on-pro row, vs. hold.