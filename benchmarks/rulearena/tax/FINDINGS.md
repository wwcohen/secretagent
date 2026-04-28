# Tax benchmark findings

Living document. Add findings as they're confirmed; update when stronger evidence arrives.

---

## Gemini-2.5-flash burns `max_tokens` budget on hidden reasoning

**What.** With `gemini/gemini-2.5-flash` on `unstructured_baseline`, `output_tokens` reflects *thinking + visible* tokens together. Visible text fills only 25-100% of the budget; the rest is invisible reasoning. On complex cases the cap hits before `<answer>` is emitted; the parser falls back to the last `$`-amount and grabs an intermediate calculation value.

**Evidence** (`results/20260425.041752.unstructured_baseline/`, `max_tokens=16384`):

| Case | Level | output_tokens | visible chars | chars/token | Outcome |
|------|-------|---------------|---------------|-------------|---------|
| `tax_0_95` | L0 | 7901 | 6375 | 1.24 | clean: `<answer>14475.68</answer>` ✓ |
| `tax_1_44` | L1 | 16380 (cap) | 7019 | 0.43 | truncated; pred `2.00` (grabbed `$2,` from mid-number) |
| `tax_1_17` | L1 | 16380 (cap) | 4039 | 0.25 | truncated; pred `104062.00` (intermediate gross-receipts line) |

Hidden-thinking ratio scales with case complexity, not input length: simplest case used ~0 hidden tokens; harder L1 case used ~3× visible.

**Caveats.**
- Specific to thinking models (`gemini-2.5-flash`, presumably `gemini-2.5-pro`).
- `gemini-2.5-flash-lite` did not exhibit this on a 1-case workflow smoke (insufficient evidence; revisit).
- Production model `together_ai/deepseek-ai/DeepSeek-V3.1` does NOT have this asymmetry. Airline ran `unstructured_baseline` cleanly at `max_tokens=8192` — tax should be similar; verify on the real run.

**Mitigations measured (n=3 valid: tax_0_95 L0, tax_1_44 L1, tax_1_17 L1):**

| Variant | `reasoning_effort` | `max_tokens` | Correct | output_tokens (per case) | Total cost | Results dir |
|---|---|---|---|---|---|---|
| A (initial) | default | 8192 | 1/3 | 8188 / 8188 / 8188 (all cap) | $0.069 | `20260425.040350.unstructured_baseline/` |
| B | default | 16384 | 1/3 | 7901 / 16380 / 16380 (L1 cap) | $0.110 | `20260425.041752.unstructured_baseline/` |
| C | **low** | 16384 | **3/3** | 3465 / 7164 / 6764 | **$0.052** | `20260425.043240.unstructured_baseline_loweffort_16k/` |
| D | default | 32768 | 3/3 | 7505 / 14190 / 17232 | $0.105 | `20260425.043431.unstructured_baseline_default_32k/` |

**Conclusion.** `reasoning_effort=low` resolves truncation at 2× lower cost than just raising `max_tokens`. C and D produce bit-identical predictions (incl. refunds to the cent) — the extra hidden thinking in D adds no correctness, only spend. `effort=low` also makes Gemini behave more like production DeepSeek (no hidden-thinking budget), so smoke results are a more faithful proxy.

**Recommended smoke-test settings for Gemini.**
```
llm.model=gemini/gemini-2.5-flash llm.reasoning_effort=low llm.max_tokens=16384
```

**Production caveat.** This whole finding concerns Gemini-2.5-flash. Production runs use `together_ai/deepseek-ai/DeepSeek-V3.1`. DeepSeek's `output_tokens` is visible-text-only; the airline run is succeeding at `max_tokens=8192`, and tax should follow. **Verify on the first real DeepSeek run** before assuming.

---

## Unstructured prompt biases the model toward unsigned `Amount you owe`

**What.** `prompt_templates/unstructured.txt` line 1 frames the task as *"calculate the income tax **owed** by the taxpayer"* and only mentions *"negative if overpaid/refunded"* at the end of line 6. On refund cases, DeepSeek-V3.1 walks Form 1040 to **Line 37 ("Amount you owe")** and reports that value as **positive** — i.e., the dataset's sign convention (positive=owed, negative=refund, per `compute_tax_calculator` docstring) is contradicted by the model's natural reading of the prompt.

**Evidence** (`results/20260425.063518.unstructured_baseline/`, DeepSeek-V3.1, 4 calculation_error cases):

| Case | Level | predicted | expected | Diagnosis |
|---|---|---|---|---|
| `tax_1_44` | L1 (refund) | +2076.10 | -2089.20 | **Pure sign-flip**: \|pred + exp\|/\|exp\| = 0.6%, would be `correct=1.0` if negated. Model's chain ends *"Line 37 = $18,120.30 - $16,044.20 = $2,076.10. So tax owed = $2,076.10. <answer>2076.10</answer>"*. |
| `tax_1_17` | L1 (refund) | +5444.01 | -6600.99 | Sign-flip + 18% magnitude error (real reasoning error in addition to sign). |
| `tax_2_56` | L2 (refund) | -3299.21 | -9570.32 | Correct sign, 65% magnitude error. Not a sign-flip case. |
| `tax_2_59` | L2 (owed)   | +10316.15 | +6745.74 | Correct sign, 53% magnitude error. Not a sign-flip case. |

So sign-flip is **1 of 4** calculation errors in the only run with non-cached DeepSeek data on this strategy. Smaller than first suspected but real and deterministic (reproduced on cache replay 2026-04-25 14:44).

**Why it happens.** The prompt's opening sentence ("tax owed") and the Form 1040 worksheet itself both report the result as a **positive amount** (Line 37). The instruction to negate refunds is a single trailing clause; the model finishes a long arithmetic chain and emits the last number it computed without revisiting the sign convention.

**Caveats.**
- Only the unstructured baseline is exposed: the other 4 strategies (`structured_baseline`, `workflow`, `pot`, `react`) bypass `unstructured.txt` and route through `extract_tax_params` + `compute_tax_calculator`, where the sign is produced by the deterministic Python calculator (`calculators.tax.compute_tax_fee`).
- Airline doesn't have an analogous failure surface (its outputs are always non-negative fees).
- Affects DeepSeek-V3.1 (production model). Other models may or may not exhibit the same bias — not measured.

**Mitigation candidates (not yet applied — pending discussion with advisor).**
- Move the sign convention to the front of the prompt, e.g. *"Compute the **net** federal tax: positive if the taxpayer owes, negative if a refund is due."*
- Or post-hoc: detect "refund"/"overpaid" keywords in the model's reasoning and negate; mirrors the existing `_parse_numeric_answer` fallback-1 path.
- Either change invalidates cached unstructured calls and would require re-running airline's unstructured baseline for parity.

**Action.** Documented; defer fix to advisor discussion. Production run kept with current prompt for cross-domain comparability with airline.

---

## `simulate` factory parser doesn't strip commas before `float()`

**What.** With `compute_tax_answer.method=simulate` (`structured_baseline`), the LLM may emit comma-formatted dollar amounts inside `<answer>...</answer>` (e.g. `-25,502.0`). `simulate`'s parser calls `float()` on the extracted string, which raises `ValueError: could not convert string to float: '-25,502.0'`. The whole case is lost as an exception.

**Evidence** (`results/20260425.044520.structured_baseline/`):
- `tax_0_95`: `raw_response` = 28 chars literally `<answer>\n-25,502.0\n</answer>`. All 1,770 chars of computation went to `reasoning_content`. Parser raised. Predicted value bubbled up as `**exception raised**: could not convert string to float: '-25,502.0'`. Failure mode = `extraction_failure`.
- `tax_1_44` and `tax_1_17` parsed fine (model happened to format without commas) but `tax_1_17` was ~13% off in pure model quality (-7458.11 vs -6600.99).

**Caveats.**
- Airline does NOT exhibit this because its outputs are integer dollars (no commas naturally emitted, and no `.X` decimal).
- Tax outputs are floats with cents — comma formatting is the LLM default. Affects any float-output domain.
- DeepSeek-V3.1 may not default to comma-formatting in this scaffold; verify on real run.

**Possible fixes (not yet applied):**
- Patch `compute_tax_answer`'s docstring to forbid commas in the answer (cheapest, tax-local).
- Patch `secretagent.implement.core.parse_output` to strip commas before float coercion (right fix, framework-wide; touches code currently in use by the live airline run, so deferred).

**Cross-strategy implication (for the paper).** As strategies shift from explicit-prompt (unstructured) toward scaffold-driven (simulate, react), responsibility for output formatting moves from the prompt designer to the framework. Each handoff exposes a new parser-LLM mismatch surface. Tax surfaces one that airline doesn't.

---

## PoT: schema hallucination on rich pydantic models

**What.** PoT's generated code accesses extracted-params using **form-line surface names** from `forms_text`, not the **pydantic field names**. With `TaxParams` (70 fields, many named after IRS-form labels), the LLM hallucinates dict-style keys that don't exist.

**Evidence** (`results/20260425.045958.pot/`, case `tax_1_17`, has `self_employed=True`):
- Generated code: `tax_params.get("Schedule C (Form 1040)_Line 1 - Gross receipts or sales", 0.0)`
- Actual field name: `gross_receipts`
- Two stacked failures: (a) `.get()` on pydantic raises (the predicted asymmetry); (b) even if dict, the key wouldn't match — silently returns `0.0`, corrupting arithmetic.
- L0 and the simple L1 refund cases (`tax_0_95`, `tax_1_44`) succeeded because their generated code used attribute access or didn't need Schedule C. Complex cases reliably fail.

**Caveats.**
- Surface area is domain-dependent: airline (5 fields, terse names) is much harder to hallucinate against than tax (70 fields, IRS-form labels).
- DeepSeek-V3.1 may behave differently; verify on real run.
- Cost of failure is not zero — `tax_1_17` consumed 17,893 output tokens (highest of any smoke case so far) before giving up.

**Mitigation candidates.** See `benchmarks/rulearena/INFRA_FIXES.md` § 2 (pot pydantic asymmetry); the additional schema-fidelity issue argues for **explicit pydantic-schema injection into the pot prompt**, not just relying on type annotations.

---

## React + Gemini-flash + `extract_*_params.method=simulate` is broken

**What.** Under `make react` with `gemini/gemini-2.5-flash` and the locked-in #8 scoped override `extract_tax_params.method=simulate`, all 3 smoke cases fail at the framework layer (NaN stats — failure before aggregation).

**Evidence** (`results/20260425.050635.react/`):
- `tax_0_95`, `tax_1_44`: `**exception raised**: cannot find final answer` — `simulate.parse_output` at `src/secretagent/implement/core.py:191`. pydantic-ai's Agent calls the extract tool → tool invokes `simulate` → Gemini doesn't emit the scaffold `simulate` expects → parse raises.
- `tax_1_17`: `**exception raised**: No choices returned from LiteLLM` — Gemini API returned empty (transient flake or content filter on this case).

**Conflict between two locked-in decisions, exposed by Gemini smoke:**
- **#8** says: scope `extract_*_params.method=simulate` in react because pydantic-ai can't nest pydantic-ai tools.
- **Empirical from #6 sub-step 5.6 + this run**: `simulate` + Gemini-flash is unreliable — Gemini doesn't always emit `simulate`'s `<answer>` scaffold when invoked through pydantic-ai's tool dispatch.

The two collide only for **(Gemini-flash × tax × react)**. DeepSeek-V3.1 (production) reliably emits the scaffold; airline ran clean with the same config.

**Action: defer.** Documented as known smoke-only failure. Production with DeepSeek is the real test. Revisit if production also fails.

---

## Cache key is `(prompt, model)` only

Tuning `max_tokens` / `reasoning_effort` / `temperature` via DOTPAIRS does NOT bust the cache (key is computed in `src/secretagent/llm_util.py:163` from `_llm_impl(prompt, model)` args only). Telltale of a stale-cache hit: re-run completes in <1s with bit-identical predictions and stats. Force a fresh call with `cachier.enable_caching=false`.

---

## Cross-domain Phase C lessons from airline (2026-04-27)

The airline benchmark completed a full Phase C followup cycle on `experiment/infra-fixes` (post-merge with `experiment/infra-followups`). Four framework commits landed on top of the existing INFRA #1/#3/#4/#6 fixes:

| Sha | Tag | Summary |
|---|---|---|
| `c850231` | F1 | defensive None bypass on pydantic `_run_agent` cache (mirrors INFRA #6 into the pydantic-ai path) |
| `863a259` | F2 | `model_validate` dicts when `return_type` is a BaseModel — surfaces ValidationError at parser boundary |
| `1cc91fa` | F3 | fence-block fallback when `<answer>` tag is missing (recovers ` ```python ClassName(...) ``` ` shapes) |
| `fd84417` | **F4** | **pydantic schema injection** into `simulate` / `simulate_pydantic` prompts — embeds `model_json_schema()` so the LLM sees actual field names instead of inferring from the function signature |

Airline n=50 / seed=137 / V3.1 / `cachier.enable_caching=false`:

| strategy | branch B | followups | Δ |
|---|---|---|---|
| unstr | 44% | 60% | +16 pp |
| struct | 40% | 42% | +2 pp |
| **workflow** | 76% | **94%** | **+18 pp** |
| pot | 60% | 62% | +2 pp |
| **react V3.1** | 0% | **58%** | **+58 pp** |
| react gemini-2.5 | 6% | 52% | +46 pp |

### What this means for tax

1. **F4 is the primary lever, and tax should benefit MORE than airline.** TaxParams is ~75 fields vs AirlineParams's 5. The PoT entry in this FINDINGS already documents that schema hallucination on rich pydantic models is severe for tax (e.g. `tax_params.get("Schedule C (Form 1040)_Line 1 - Gross receipts or sales", 0.0)`). F4 puts the actual field names directly in the prompt — for tax, this is a prediction of large lift on react and workflow.

2. **PoT pydantic/dict asymmetry is now visible, not invisible.** Airline's pot run on followups produced 7/50 cases of `Code execution failed at line 'params["X"] = Y'` — F4 helped the LLM use the *correct* field names, but the LLM still emits dict-assignment code that crashes on a pydantic instance. The asymmetry IS the bug; F4 doesn't fix it. **INFRA #2.C** (sandbox preamble `params = params.model_dump() if hasattr(params, 'model_dump') else params`) or **#2.A** (re-type `compute_tax_calculator(params: TaxParams)`) is the unblocker for pot. Existing tax FINDINGS entry "PoT: schema hallucination on rich pydantic models" gets validated by airline's data — pursue both #2.E (now done as F4) AND #2.C/D for tax pot.

3. **Workflow on tax should approach a similar ceiling to airline (94%).** Airline workflow uses `extract_airline_params` (simulate) → `compute_airline_calculator` (simulate). Both calls return a pydantic model in extraction's case → F4 fires. Tax has the same structure. Note: the 2026-04-26 15:05 tax workflow run hit a 50/50 wipe from a sustained TogetherAI 500-burst (NOT a framework regression — INFRA #4's 3-attempt retry budget got swamped). Rerun when TogetherAI is healthy.

4. **Transport noise is bursty on TogetherAI.** INFRA #4's 3-attempt budget is too thin for sustained outages — airline's V3.1 react lost 12/50 to 5xx, and tax workflow lost 50/50 in one stretch. If a tax run shows a 5xx cluster, treat as environmental and rerun rather than diagnosing further. INFRA #4 retry-bump is now a known followup (filed for post-Mon meeting).

5. **`<answer>` tag scaffold reliability differs by model.** Airline's gemini followups run still left 20/50 cases as "cannot find final answer" — F3 fence-fallback didn't catch gemini's verbose multi-fence chain-of-thought shape. The existing tax FINDINGS entry "React + Gemini-flash + extract_*_params.method=simulate is broken" describes the same symptom from the smoke run; F4 reduces the rate but doesn't eliminate it on gemini. Keep that FINDINGS entry's caveat live.

### Predicted Phase C tax numbers

Translating airline's effects to tax (no claim of precision; orientation only):
- **react** — biggest expected gain. Airline V3.1 baseline 0% → followups 58%. Tax react with V3.1 likely lifts substantially from current branch B baseline (whatever the existing tax FINDINGS records — probably also near 0%).
- **workflow** — large gain expected. Airline 76% → 94%. Tax workflow currently has no clean post-followups data point (the 04-26 run is the 50/50 transport wipe). Re-run priority.
- **pot** — modest gain expected, capped by the dict-assignment asymmetry. Without INFRA #2.C/D, tax pot will hit `tax_params["X"] = Y` crashes the same way airline did.
- **struct / unstr** — small gain at best. Both return numeric types where F4 doesn't fire on the top-level call.

### Things tax-specific NOT yet known

- Whether tax exhibits gemini's "verbose multi-fence" parser shape that F3 missed on airline. If gemini is in scope for tax experiments, that residual will likely resurface.
- Whether the `tax_1_17` complex case (with `self_employed=True` triggering Schedule C) shifts from `extraction_failure` to `KeyError` after F4 — that is, whether F4 gives the LLM enough schema to recover or just makes the bug visible at a deeper layer.

Source data and full analysis: `benchmarks/rulearena/airline/FINDINGS.md` Phase C postscript and the working sheet at `/c/tmp/react_followups.md`.

---

## Phase C results: tax 5-strategy V3.1 sweep (2026-04-27)

All runs: `together_ai/deepseek-ai/DeepSeek-V3.1`, n=50, seed=137, `cachier.enable_caching=false` (cache-busted for F4 prompt change). Branch `experiment/tax-work` at `bd182d3` (all 8 Phase B+C framework commits).

### Headline

| strategy | correct | % | mean cost/case | failure breakdown |
|---|---|---|---|---|
| unstructured_baseline | 29/50 | **58%** | $0.0094 | 21 calc_error |
| structured_baseline | 5/50 | **10%** | $0.0066 | 45 calc_error |
| **workflow** | 30/50 | **60%** | $0.0101 | 20 calc_error |
| pot | 24/50 | **48%** | $0.0170 | 20 calc_error, 6 extraction_failure |
| react (V3.1) | 7/50 | **14%** | $0.0399 | 19 calc_error, 24 extraction_failure |

Per-level:

| strategy | L0 (17) | L1 (16) | L2 (17) |
|---|---|---|---|
| unstr | 14 (82%) | 9 (56%) | 6 (35%) |
| struct | 4 (24%) | 1 (6%) | 0 (0%) |
| workflow | 11 (65%) | 10 (62%) | 9 (53%) |
| pot | 9 (53%) | 9 (56%) | 6 (35%) |
| react | 4 (24%) | 2 (12%) | 1 (6%) |

Oracle (any-of-5): **46/50 (92%)**. Best pair: workflow + unstr = 41/50 (82%) = workflow + pot. Only 4 cases no strategy solves (tax_0_49, tax_1_17, tax_1_82, tax_2_40).

### Comparison with airline Phase C followups

| strategy | airline | tax | gap | explanation |
|---|---|---|---|---|
| unstr | 60% | 58% | −2 pp | Comparable — both are raw LLM reasoning |
| struct | 42% | 10% | −32 pp | Tax's 75-field complexity overwhelms one-shot simulate |
| **workflow** | **94%** | **60%** | **−34 pp** | Extraction quality on 75 fields is the bottleneck, not the calculator |
| pot | 62% | 48% | −14 pp | No dict-asymmetry crashes on tax (see below); calc errors dominate |
| react | 58% | 14% | −44 pp | `simulate` parser breaks on 75-field extraction (see below) |

**Tax is universally harder than airline** except on unstr (which bypasses extraction). The gap scales with extraction complexity: strategies that extract a pydantic model (workflow, pot, react) all underperform their airline counterparts, and the gap widens with parser fragility (react worst, workflow least bad).

### Predictions from "Cross-domain Phase C lessons" — scorecard

| Prediction | Result |
|---|---|
| "F4's lever should be bigger on tax" | **Partially confirmed.** F4 eliminated the schema-hallucination `KeyError` patterns that dominated airline branch-B react (0%) and pot. But tax's improvement is capped by a *different* bottleneck: extraction quality on 75 fields. Workflow reached 60% (not 94%), and react only 14%. |
| "Workflow should approach airline's 94% ceiling" | **Falsified.** 60%, not 94%. The 75-field TaxParams extraction via simulate_pydantic succeeds on all 50 cases (no extraction_failure), but extracts wrong param values on 20/50. Airline's 5-field AirlineParams was easier to extract correctly. |
| "PoT will hit `params['X'] = Y` dict-assignment crashes" | **Falsified.** 0/50 dict-assignment crashes (airline had 7/50). With 75 fields, the LLM calls tools wholesale (`params = extract_tax_params(forms_text)`) rather than manipulating individual fields. Schema complexity suppresses the dict-asymmetry bug. |
| "struct/unstr: small gain at best" | **Confirmed.** No prior tax n=50 baseline exists for direct comparison, but struct at 10% and unstr at 58% are consistent with "F4 doesn't fire on numeric return types." |

### Per-strategy residual analysis

#### Unstructured baseline (29/50 = 58%)

21 calculation errors, 0 extraction failures, 0 transport. Clean run.

Error magnitude: 3 under 5%, 6 at 5-10%, 3 at 10-25%, 2 at 25-50%, 4 at 50-100%, 3 over 100%.

The sign-flip finding (documented earlier in this file) persists: `tax_1_44` predicted +2076.10 vs GT -2089.20 (pure sign-flip, 0.6% magnitude error if negated). The prompt's "tax owed" framing still biases the model on refund cases.

Steep level gradient: L0 82% → L1 56% → L2 35%. Unstr dominates on L0 (highest of all strategies) because simple cases are easy to reason about in one shot; complex cases (L2 with multiple schedules) expose the model's arithmetic limits.

#### Structured baseline (5/50 = 10%)

45 calculation errors, 0 extraction failures. INFRA #1 (comma coercion) is working — no comma-format parsing failures, confirming that finding is resolved.

Catastrophically bad: 22/45 errors exceed 100% relative error. Many cases show 12-13 output_tokens with ~1s latency — the model emits a terse hallucinated number with no visible reasoning (computation goes to `reasoning_content`). The model cannot one-shot a 75-field tax calculation. This was expected from the airline comparison (airline struct = 42%, already the weakest pipeline strategy) but the magnitude is worse: tax struct is bounded by compute-layer quality and **not improvable by framework changes**.

Level gradient: L0 24% → L1 6% → L2 0%.

#### Workflow (30/50 = 60%)

20 calculation errors, 0 extraction failures, 0 transport. All 50 cases completed clean.

**Extraction succeeds 50/50** (simulate_pydantic for extract_tax_params), meaning the pydantic-ai Agent returns a valid TaxParams object for every case. The 20 errors are all calculation errors where the extracted param values were wrong, not where extraction failed. The calculator is deterministic; every error traces to wrong params.

Error shape is bimodal:
- 5 catastrophic failures (>95% rel error): `tax_0_49` (pred=0.0), `tax_1_99` (pred=0.0), `tax_2_2` (pred=-61.50 vs GT 26495.50), `tax_2_27` (pred=-6391.80 vs GT 17209.84), `tax_1_92` (sign wrong). These likely have fundamentally wrong filing_status or income fields.
- 12 bounded errors (2-45% rel error): wrong deduction amounts, missed credits, or schedule-level extraction errors. The calculator faithfully computes the wrong answer from slightly-wrong params.
- 3 borderline misses (<5%): `tax_0_24` (1.9%), `tax_1_47` (4.7%), `tax_2_4` (4.9%).

Level gradient is flatter than unstr: L0 65% → L1 62% → L2 53%. The calculator backstop normalizes difficulty across levels — when extraction succeeds, the answer is exact.

**Key shared-extraction evidence:** `tax_1_17` produces **identical** wrong predictions in both workflow (-3648.75) and pot (-3648.75). Both call the same `extract_tax_params`, get the same wrong params, and the calculator deterministically computes the same wrong answer. The extraction layer is shared and load-bearing.

#### PoT (24/50 = 48%)

20 calculation errors, 6 extraction failures.

**Extraction failure sub-shapes (6):**

| Shape | Count | Cases |
|---|---|---|
| pydantic_retry_exhausted | 3 | tax_0_37, tax_0_30, tax_1_82 |
| code_parsing_syntax (`<answer>` instead of Python) | 2 | tax_1_44, tax_2_56 |
| sandbox_import_blocked (`from typing`) | 1 | tax_0_85 |

**Zero dict-assignment-on-pydantic crashes.** Airline pot had 7/50 `params["X"] = Y` crashes (the canonical INFRA #2.C/D bug). Tax pot has none. With 75 fields, the LLM generates `params = extract_tax_params(forms_text)` → `result = compute_tax_calculator(params)` as wholesale function calls. The `inject_args=true` Makefile flag keeps `forms_text` in the sandbox, reinforcing this pattern. The dict-asymmetry bug's failure surface **depends on schema complexity**: small schema → LLM manipulates individual fields → crashes; large schema → LLM calls tools wholesale → no crash. INFRA #2.C/D is still the correct fix but is not blocking tax pot.

Calculation errors: 14/20 exceed 50% relative error, with 6 over 100%. PoT's error distribution is heavier-tailed than workflow's because the generated code can compound extraction mistakes with its own logic errors.

Cross-strategy complementarity with workflow: only 13 cases both get right, 9 both get wrong. 17 cases workflow-only, 11 cases pot-only. 5 cases pot uniquely gets right that both workflow and unstr miss (tax_2_59, tax_2_23, tax_2_77, tax_0_44, tax_1_47) — all because PoT's code execution is exact when extraction succeeds, recovering borderline cases where workflow's slightly-wrong params push it over tolerance.

#### React V3.1 (7/50 = 14%)

19 calculation errors, 24 extraction failures, 0 transport.

**The headline failure: 48% extraction failure rate, entirely from parser fragility on 75-field TaxParams.**

Extraction failure sub-shapes (24):

| Shape | Count | Description |
|---|---|---|
| `cannot find final answer` | 15 | No `<answer>` tag, no parseable fence block in simulate output |
| `expression expected after dictionary key and ':'` | 5 | `<answer>` found but dict syntax malformed |
| `invalid decimal literal` | 2 | `<answer>` found but number formatting invalid |
| `malformed node or string` | 1 | ast.literal_eval choked on constructor |
| `unterminated string literal` | 1 | LLM output has unclosed string |

**Root cause: `simulate` parser cannot reliably handle 75-field TaxParams.**

React overrides `extract_tax_params.method=simulate` (from `simulate_pydantic`) because pydantic-ai cannot nest agents — the outer `compute_tax_answer` agent calls extraction as a tool, and registering a `simulate_pydantic` interface as a pydantic-ai tool would create a nested `Agent.run_sync()` call (event loop collision). The `simulate` factory's parser relies on `<answer>` tags + json/literal_eval/constructor fallbacks. For airline's 5-field AirlineParams this works (airline react = 58%). For tax's 75-field TaxParams — where the LLM output is 2000+ chars of field/value pairs — the parser hits edge cases 48% of the time.

The 15 "cannot find final answer" cases include **easy L0 cases that every other strategy gets right** (tax_0_12, tax_0_22, tax_0_37, tax_0_85). The model likely produces correct params but formats them in a way the parser doesn't recognize. This is a pipeline failure, not a reasoning failure.

**Contrast with workflow:** In workflow, `extract_tax_params.method=simulate_pydantic` handles extraction natively through pydantic-ai's structured output with validation and retries → **extraction succeeds 50/50.** Same model, same schema, same F4 injection. The only difference is the parser. React's extraction success rate is 26/50 = 52%; among those 26 parseable cases, 7/26 = 27% get the right answer. The parser failure is the dominant loss channel.

**Fix candidates (not applied — pending discussion):**
- **(a) Two-phase react.** Extract params first via `simulate_pydantic`, then pass to the react agent which only has `compute_tax_calculator` as a tool. Eliminates the nested-agent constraint entirely. No framework change needed — just a different Makefile wiring.
- **(b) Structured-output factory.** New factory using litellm's native JSON-mode or function-calling for extraction, bypassing both simulate's parser and pydantic-ai nesting. Framework change, but broadly useful.
- **(c) Parser hardening.** Extend simulate's `parse_output` to try `{...}` block extraction (like the existing dict/list fallback at line 174-193 of `core.py`) for BaseModel return types when `<answer>` tags are missing. Incremental improvement; doesn't solve the format-diversity problem for very long outputs.

**Cost:** React is by far the most expensive at $0.040/case (4× workflow). Individual cases reach $0.10+ (tax_2_59: $0.104, 157K input tokens, 341s latency).

### What this confirms for the paper

1. **Schema complexity is a first-order variable.** The same framework + model + strategy produces dramatically different results on airline (5 fields) vs tax (75 fields). The gap is NOT uniform across strategies — it scales with parser fragility: unstr (no extraction) is comparable, workflow (pydantic-ai extraction) loses 34 pp, react (simulate extraction) loses 44 pp.

2. **The extraction layer is the universal bottleneck for pipeline strategies on tax.** Workflow, pot, and react all funnel through `extract_tax_params`. When extraction succeeds, the calculator is deterministic and exact. When extraction fails (wrong params or parser failure), no downstream step can recover. The 46/50 oracle ceiling confirms that the information is in the problem — the strategies just can't reliably extract it.

3. **Parser robustness matters more than we predicted.** The "Cross-domain Phase C lessons" section predicted F4 would be the primary lever. It was — for airline. For tax, the *parser* downstream of F4 became the bottleneck, because F4 gives the LLM the right field names but the parser must then handle a 75-field output. The simulate parser's regex-based approach doesn't scale.

4. **PoT dict-asymmetry is schema-size-dependent.** Airline's 7/50 dict-assignment crashes didn't reproduce on tax (0/50). The LLM's code generation strategy shifts from field-level manipulation to tool-level delegation when the schema is too complex to manipulate directly. INFRA #2.C/D is still correct but not the bottleneck here.

### Next interventions (post this measurement)

- **React fix (a) above** — two-phase react would be the cheapest test of whether react can approach workflow-level extraction quality on tax.
- **Extraction quality** — workflow's 20/50 wrong-params cases are the next ceiling after parser issues. Auditing the extracted TaxParams values (via `record_details=true` rerun) would reveal which fields are systematically wrong and whether domain-specific prompt engineering (field descriptions, examples) can help.
- **Tolerance analysis** — 3 workflow cases miss by <5% (tax_0_24 at 1.9%, tax_1_47 at 4.7%, tax_2_4 at 4.9%). A 5% tolerance threshold would flip these, pushing workflow to 33/50 = 66%.

Source data: `benchmarks/rulearena/tax/results/20260427.{154642.workflow,165952.pot,174646.react}_v31_followups/`, `../secretagent/benchmarks/rulearena/tax/results/20260426.{021836.unstructured_baseline,133847.structured_baseline}/`.
