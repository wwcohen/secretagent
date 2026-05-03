# Tax benchmark findings

Paper-ready findings. Valid-set (n=50) and test-set (n=100) both with `together_ai/deepseek-ai/DeepSeek-V3.1`.

---

## Test-set results: all 6 strategies (n=100, 2026-04-30)

`dataset.split=test`, model `together_ai/deepseek-ai/DeepSeek-V3.1`.

| Strategy | correct (1%) | exact | avg $/case | extraction_fail | calc_err |
|---|---|---|---|---|---|
| unstructured_baseline | **55%** | 40% | $0.0098 | 0 | 45 |
| workflow | 50% | 49% | $0.0101 | 1 | 49 |
| react_two_phase | 48% | 47% | $0.0137 | 0 | 52 |
| pot | 46% | 45% | $0.0159 | 5 | 49 |
| react | 15% | 15% | $0.0349 | 34 | 51 |
| structured_baseline | 11% | 9% | $0.0068 | 0 | 89 |

`correct` = within 1% relative error (RuleArena convention for tax). `exact` = near-IEEE-exact match (diagnostic; `math.isclose` at `rel_tol=1e-5`). Result dirs: `results/20260429-30.*`.

### Key findings

**1. The calculator, not extraction, is the binding constraint for structured methods.**
Workflow, react_two_phase, and pot all converge to 46–50%, with ~49–52 `calc_err` per 100. Extraction succeeds — the calculator receives a valid `TaxParams` — but the extracted param values are wrong on roughly half the cases. Since the calculator is deterministic, no downstream step can recover from wrong params. The ceiling for any structured method is set by extraction *quality*, not extraction *success*.

**2. Unstructured wins (55%) despite no calculator.**
LLM end-to-end tax reasoning slightly outperforms every pipeline strategy. The 15pp gap between `correct` (55%) and `exact` (40%) is diagnostic: 15 cases where LLM arithmetic lands within 1% of the true answer but is not IEEE-exact. Structured methods show near-zero near-misses (`correct` ≈ `exact`) because the calculator produces an exact answer from whatever params it receives — the error is all-or-nothing. The unstructured baseline's near-misses reflect LLM arithmetic approximation that coincidentally falls within the 1% tolerance band.

**3. React extraction failure is the primary bottleneck; two-phase react fixes it completely.**
Original react: 34/100 extraction failures → 15%. Two-phase react: 0 extraction failures → 48%. The two-phase approach runs `extract_tax_params` via `simulate_pydantic` before the react loop, eliminating the nested-agent constraint that forced react to use `simulate` for extraction. At 48%, `react_two_phase` matches workflow accuracy at 35% higher cost ($0.0137 vs $0.0101/case). The react loop itself is not a bottleneck — extraction was.

**4. Structured baseline is unrecoverable (11%).**
89/100 `calc_err`, many with >100% relative error. Simulating a float from a 75-field context in one shot is not viable. Not a framework issue — the model has no path to produce the correct answer without performing the actual multi-schedule computation.

### Drift from valid to test

| Strategy | valid (n=50) | test (n=100) | Δ |
|---|---|---|---|
| unstructured_baseline | 58% | 55% | −3pp |
| workflow | 60% | 50% | −10pp |
| pot | 48% | 46% | −2pp |
| react | 14% | 15% | +1pp |
| structured_baseline | 10% | 11% | +1pp |
| react_two_phase | — | 48% | — |

Workflow shows the largest drift (−10pp). On n=50 valid, SE ≈ ±7pp; the gap is ~1.4 SEs, consistent with sampling noise. All other methods are stable (≤3pp). No code or config changes between valid and test runs.

---

## Valid-set results: 5 strategies (n=50, 2026-04-27)

`dataset.split=valid`, `cachier.enable_caching=false`, branch `experiment/tax-work` at `bd182d3`.

| Strategy | correct | % | avg $/case |
|---|---|---|---|
| unstructured_baseline | 29/50 | **58%** | $0.0094 |
| structured_baseline | 5/50 | **10%** | $0.0066 |
| workflow | 30/50 | **60%** | $0.0101 |
| pot | 24/50 | **48%** | $0.0170 |
| react | 7/50 | **14%** | $0.0399 |

Oracle (any-of-5): 46/50 (92%). Only 4 cases no strategy solves (`tax_0_49`, `tax_1_17`, `tax_1_82`, `tax_2_40`).

Per-level breakdown:

| Strategy | L0 (17) | L1 (16) | L2 (17) |
|---|---|---|---|
| unstr | 14 (82%) | 9 (56%) | 6 (35%) |
| struct | 4 (24%) | 1 (6%) | 0 (0%) |
| workflow | 11 (65%) | 10 (62%) | 9 (53%) |
| pot | 9 (53%) | 9 (56%) | 6 (35%) |
| react | 4 (24%) | 2 (12%) | 1 (6%) |

**Workflow** extraction succeeds 50/50 (via `simulate_pydantic`); all 20 errors trace to wrong extracted param values, not parser failure. Error shape is bimodal: 5 catastrophic failures (>95% relative error, likely wrong `filing_status` or income fields) and 12 bounded errors (wrong deduction amounts or missed credits). 3 borderline misses under 5% relative error (1.9%, 4.7%, 4.9%).

**React** (7/50): 24/50 extraction failures. `simulate` parser on 75-field `TaxParams` breaks at 48% rate. Among the 26 parseable cases, 7/26 = 27% are correct — the parser failure is the dominant loss, not the react loop. Failure sub-shapes: "cannot find final answer" (15), malformed dict syntax (5), invalid decimal literal (2), malformed constructor (1), truncated string (1).

**PoT** (24/50): 6/50 extraction failures; 0 dict-assignment-on-pydantic crashes (unlike airline's 7/50). With 75 fields, LLM generates wholesale function calls (`params = extract_tax_params(...)`) rather than field-level manipulation — schema complexity suppresses the dict-assignment bug pattern. Cross-strategy: workflow and pot share `extract_tax_params`; `tax_1_17` produces identical wrong predictions in both (same wrong params → same wrong calc answer).

---

## Cross-domain comparison: airline vs tax

Both with DeepSeek-V3.1, n=50 valid.

| Strategy | airline | tax | gap | explanation |
|---|---|---|---|---|
| unstr | 60% | 58% | −2pp | No extraction step; LLM reasoning quality comparable |
| struct | 42% | 10% | −32pp | 75-field one-shot far harder than 5-field |
| workflow | 94% | 60% | −34pp | Extraction param quality degrades with schema size |
| pot | 62% | 48% | −14pp | More calc errors; code-gen less reliable on complex arithmetic |
| react | 58% | 14% | −44pp | Simulate parser breaks on 75-field extraction; works on 5-field |

**Schema complexity is a first-order variable.** The airline→tax gap scales with parser fragility: unstr (no extraction) stays even; workflow (pydantic-ai extraction) loses 34pp; react (simulate extraction) loses 44pp. Tax's 75-field `TaxParams` vs airline's 5-field `AirlineParams` is the domain-side cause. This cleanly demonstrates that schema size compounds framework limitations — a result that generalizes beyond these two domains.

---

## Known biases affecting unstructured baseline

**Sign-flip on refund cases.** The `unstructured.txt` prompt opens with "calculate the income tax *owed*" and treats the sign convention as a trailing clause. On refund cases, DeepSeek-V3.1 follows Form 1040 Line 37 ("Amount you owe") and emits a positive value. Evidence: `tax_1_44` (valid set) — predicted +2076.10 vs GT −2089.20; magnitude error is 0.6% if negated, but sign-flip makes it a `calc_error`. Affects only unstructured baseline; all pipeline strategies (workflow, pot, react) route through the deterministic Python calculator, which uses the correct sign convention.

**Near-miss inflation.** Unstructured's `correct` (55%) exceeds `exact` (40%) by 15pp; structured methods show ≤2pp gaps. The 15 near-misses are LLM arithmetic approximations that land within the 1% tolerance band but are not exact. These cases would be `calc_error` under a tighter threshold, so unstructured's headline advantage over workflow (55% vs 50%) is partly tolerance-sensitive.
