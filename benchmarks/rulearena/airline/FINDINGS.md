# Airline domain — findings

Domain-local issues surfaced while auditing `n=50` valid runs (`results/20260425.*`). Cross-domain framework issues are tracked in `../INFRA_FIXES.md`. Each entry: **What** / **Where** / **Fix** / **Risk** / **Evidence**.

---

## 1. `_normalize_region` silent U.S. fallback drops international routes

**What.** When the LLM extracts `routine` as a route description (`'Austin to Shanghai'`, `'Chengdu to Minneapolis'`), a generic descriptor (`'international'`, `'standard'`, `'US-Europe'`), or an airport code (`'CLT-YUL'`, `'BOS-ATH'`) instead of a canonical region (`'China'`, `'Europe'`), `_normalize_region` doesn't match the string in `_VALID_REGIONS` or `_REGION_FIXES`, and **silently falls back to `"U.S."`**. The calculator then computes a US-domestic fee instead of the correct international fee.

**Where.** `benchmarks/rulearena/airline/ptools.py:96-100`:
```python
def _normalize_region(routine: str) -> str:
    if routine in _VALID_REGIONS:   return routine
    fixed = _REGION_FIXES.get(routine.lower().strip())
    return fixed if fixed else "U.S."   # silent fallback
```

`_REGION_FIXES` (`ptools.py:87-93`) maps individual cities to countries (`"shanghai": "China"`, `"beijing": "China"`, …) using whole-string equality. Multi-word route descriptions like `"austin to shanghai"` don't match even though `"shanghai"` is a known token. Several cities are missing entirely (`"chengdu"`, `"busan"`, `"port-au-prince"`, `"buenos aires"`, `"helsinki"`, `"barcelona"`, `"stockholm"`, `"osaka"`, `"nagoya"`, `"wuhan"`, `"guangzhou"`).

**Quantified impact (n=50, audit 2026-04-25).**

| metric | workflow | pot |
|---|---|---|
| parseable extractions | 39/50 | 35/50 |
| silent-fallback hit rate | 28/39 (72%) | 25/35 (71%) |
| **silent-fallback hit rate when GT routine ≠ U.S.** | **28/28 (100%)** | **25/25 (100%)** |
| recoverable wins (routine-only-bug, currently wrong) | **13** | **6** |
| projected correct% post-fix | 24% → **50%** | 26% → 38% |

**The LLM never once emits a canonical `_VALID_REGIONS` member for non-U.S. routes** across all 50 cases. This is not statistical noise — it is a deterministic failure mode. The bug is the single largest extraction-bug lever in the airline benchmark.

**Fix candidates.**
- **(a) Loud failure.** `raise ValueError(f"unknown routine: {routine!r}")` instead of defaulting. Surfaces the issue at runtime; will turn 28 silent corruptions into 28 explicit `extraction_failure` rows (worse for headline numbers, better for diagnostics).
- **(b) Substring scan.** Tokenize `routine` and probe each token against `_REGION_FIXES` before falling back. Handles `'Austin to Shanghai' → 'China'` automatically. Won't help abstract descriptors (`'international'`, `'standard'`).
- **(c) Schema-level constraint.** Change `AirlineParams.routine` to `Literal["U.S.", "China", "Japan", …]` with a `field_validator`. Forces the LLM to pick from the closed set during extraction; pydantic-ai retries on validation failure. **(c)** is the structurally correct fix.

Combine with INFRA item #3 (parser) and INFRA item #2 sub-bullet E (schema injection) for full effect.

**Risk.** Touches a hot path used by both `airline_workflow` and `_airline_calc_fn` (pot via `compute_airline_calculator`). Will not flip cases that also have `direction` wrong (item #5) — H3.B cross-tab shows 8/11 routine-OK cases also have direction-wrong, so a routine-only fix gets ~13 wf wins, not all ~26 silent-fallback × wrong cases.

**Evidence.**
- H1: 11/11 wf and 7/7 pot all-wrong cases with parseable extraction hit the bug (`/c/tmp/h1_extraction_audit.py`, `/c/tmp/h1_diff.csv`).
- H2: full 50-case sweep, 100% hit rate on non-U.S. GT cases (`/c/tmp/h2_normalize_region_sweep.py`, `/c/tmp/h2_sweep.csv`).
- H4: bit-exact reproduction confirmed for 22/22 audited cases — extracted params + production normalizers + calculator → strategy's recorded prediction byte-for-byte (`/c/tmp/h4_bitexact_repro.py`, `/c/tmp/h4_repro.csv`).
- Per-strategy raw routine strings (H2 output): `'international'` × 9, `'Austin to Mumbai'` × 2, `'Chengdu to Minneapolis'` × 1, `'CLT-YUL'` × 1, …

---

## 2. `_normalize_customer_class` — confirmed clean (n=50)

**What.** `_normalize_customer_class` (`ptools.py:119-122`) shares the structure of `_normalize_region` but **does not have a silent fallback**: if the value isn't in `_VALID_CLASSES` or `_CLASS_FIXES`, it returns the original string unchanged.

**Quantified (H3.A audit, 2026-04-25).**

| strategy | canonical raw | normalized via fixes | passthrough unchanged | match-after-norm vs GT |
|---|---|---|---|---|
| workflow | 37/39 (95%) | 1/39 | 1/39 | **38/39 (97%)** |
| pot | 18/35 (51%) | 17/35 | 0/35 | **35/35 (100%)** |

`_CLASS_FIXES` covers all observed paraphrases: `'First Class'` → `'First'`, `'Business Class'` → `'Business'`, `'Main Plus Class'` → `'Main Plus'`, `'Main Cabin Class'` → `'Main Cabin'`, `'Premium Economy Class'` → `'Premium Economy'`. Pot tends to add the trailing `' Class'`; the existing fixes catch all variants seen in n=50.

**Single observed outlier:** workflow's `airline_0_35` extracted `customer_class='Main Cabin^'` (extra caret character — likely a rendering artifact in the model's output). Silently passes through → calculator KeyError → `failure_mode=extraction_failure` (mis-classified as extraction rather than calculation). 1/39 cases.

**Fix.** Class normalization is **not a priority lever** — it works correctly on 73/74 observed extractions across both strategies. If/when the schema-Literal fix from item #5 lands, this will be subsumed cleanly. The `'Main Cabin^'` case will likely vanish under stricter validation; if not, add an explicit fallback raise instead of silent passthrough.

**Risk.** Low. Lowered priority based on H3.A measurement.

**Evidence.** `/c/tmp/h3_other_fields.py` (H3.A breakdown). `airline/results/20260425.044344.workflow/results.csv` row for `airline_0_35`.

---

## 3. `AirlineParams` schema lacks semantic guidance

**What.** The pydantic model (`ptools.py:21-26`) declares `direction: int` and `routine: str` with no docstrings, no `Literal` types, and no field descriptions:
```python
class AirlineParams(BaseModel):
    base_price: int
    customer_class: str
    routine: str
    direction: int
    bag_list: list[BagItem]
```
The LLM-extractor sees this schema (via simulate / simulate_pydantic prompts) and has no way to know:
- `direction=0` means US departure, `direction=1` means US arrival.
- `routine` should be one of ~20 country/region names, not a route description.
- `customer_class` should be one of 6 specific strings.

Cache forensics shows the LLM consequently invents both the values *and* sometimes the field names (item #3 / INFRA item #3: `passenger_name`, `flight_class`, `baggage_items`).

**Where.** `ptools.py:14-26`.

**Fix.** Use `pydantic.Field(description=…)` and `typing.Literal` for closed-set fields. Augment with examples in the simulate prompt (already supported via `example_file=` in `SimulateFactory.setup`).

**Risk.** Low. Improving the schema is purely additive; existing extractions will continue to validate against the relaxed-then-strict version. Will improve all three strategies that go through extract (workflow, pot, react).

**Evidence.** Inner-LLM trace `/tmp/react_trace2.log:1219-1267` shows the prompt that the model is asked to satisfy — no semantic guidance present. Cache scan in `/tmp/a1_scan_cache.py` shows 78/118 unparseable responses.

---

## 4. `_parse_numeric_answer` regex misses `Total cost = X` form (1 case in n=50)

**What.** Unstructured baseline parses raw LLM text via `_parse_numeric_answer` (`ptools.py:58-75`): primary pattern `r'total\s+cost\s+is\s+\$?(...)'`, fallback `last $-prefixed amount`. The primary regex requires the literal token `is`. When the model writes `Total cost = ticket + baggage fees = 1333 + 3475 = 4808`, the primary regex fails, and the fallback grabs the *last `$`-prefixed* amount — which is `$1333` (the ticket price), not the un-prefixed `4808` final answer.

**Quantified (B1 LLM-as-judge audit, 2026-04-25, $0.0087 spent).** Of 28 unstructured `calculation_error` rows, **1/28 (`airline_1_65`)** is a real parser bug. **27/28 are genuine reasoning errors** — model never stated GT or stated it only as an intermediate value. Verdict distribution from Gemini-2.5-flash-lite judge: 24 NO, 2 YES_INTERMEDIATE (false positives on spot-check — model never stated GT), 2 YES_FINAL (one false positive `airline_2_98`, one true bug `airline_1_65`).

**Where.** `ptools.py:58-75`.

**Fix.** Extend the primary regex to also accept `=` and `:` separators with no `is`:
```python
m = re.search(r'total\s+cost\s*(?:is|=|:)\s*\$?([\d,]+(?:\.\d+)?)', llm_output, re.IGNORECASE)
```
Then prefer the LAST such match (in case the model writes "Total cost = X" multiple times during reasoning before its final). Recovers `airline_1_65`'s `4808` (off by 0% from GT — fully recovers the case).

**Risk.** Low — local change to the unstructured parser. Won't affect other strategies. Won't regress the 27/28 cases where the model is wrong regardless.

**Evidence.** `/c/tmp/b1_judge.py` + `/c/tmp/b1_judge_results.csv`. Spot-checked rollout: `airline_1_65` conclusion is `Total cost = ticket + baggage fees = 1333 + 3475 = 4808` — no `$` on `4808`, no `is`.

---

## 5. `direction` extraction defaults to `1` regardless of prompt

**What.** Across n=50 audit, **the LLM emits `direction=1` on 39/39 workflow extractions and 34/35 pot extractions** — regardless of whether the actual flight is US-departing or US-arriving. Ground-truth distribution is roughly balanced (workflow: 22 GT=0 vs 17 GT=1; pot: 23 GT=0 vs 12 GT=1). This is not statistical noise — it's a deterministic LLM default driven by the schema's lack of semantic guidance.

Direction encoding (per `calculators/rulearena_reference.py:83-84`): `direction=0` ⇒ US is departure (routine is destination); `direction=1` ⇒ US is arrival (routine is departure). The schema provides no documentation of this convention.

**Quantified (H3.B audit, 2026-04-25).**

| strategy | direction match | extracted distribution | gt distribution |
|---|---|---|---|
| workflow | **17/39 (44%)** | `{1: 39, 0: 0}` | `{0: 22, 1: 17}` |
| pot | **11/35 (31%)** | `{1: 34, 0: 1}` | `{0: 23, 1: 12}` |

Cross-tab routine_match × direction_match (workflow): only **3** cases have both right; 8 have routine OK but direction wrong; 14 have routine wrong but direction lucky-matched (gt=1); 14 have both wrong. **A `_normalize_region` fix alone won't recover the 8 cases where direction is also wrong** — those require the schema-level fix in this item.

**Where.** `ptools.py:21-26`:
```python
class AirlineParams(BaseModel):
    base_price: int
    customer_class: str
    routine: str
    direction: int      # ← no docstring, no Literal[0,1], no semantic hint
    bag_list: list[BagItem]
```

**Fix.** Two complementary changes:

(a) **Schema-level documentation.** Use `pydantic.Field` with a description that explains the convention:
```python
direction: int = Field(
    ...,
    description=(
        "0 if the U.S. city is the place of departure (passenger flies FROM the U.S.), "
        "1 if the U.S. city is the place of arrival (passenger flies TO the U.S.)."
    ),
)
```

(b) **Literal type for closed set.** `direction: Literal[0, 1]` rejects any other integer at validation time.

(c) **Best:** redesign as enum-like — `direction: Literal["from_us", "to_us"]` with a `field_validator` that converts to int internally. The current numeric encoding is the root cause of the LLM's confusion; making the field self-documenting eliminates the failure mode.

Combine with INFRA item #2 sub-bullet E (schema injection into PoT/simulate prompts) so the description actually reaches the model.

**Risk.** Low. Changing `direction: int` → `direction: Literal[0, 1]` is fully backward-compatible with `_airline_calc_fn` (which only checks `direction == 1` and `direction == 0`). The string-based redesign (option c) requires updating `_airline_calc_fn` to call a converter, but that's a 5-line change.

**Evidence.** H3.B output (`/c/tmp/h3_other_fields.py`). Cache forensics: every `AirlineParams` cache entry across both strategies has `direction=1` except 1 pot case. Direction match per case: `/c/tmp/h2_sweep.csv` (`direction_match` column).

---

# Audit synthesis (n=50 valid, 2026-04-25)

Triage of all findings from the H/E/D/B/C/F audit phases. See conversation handoff in `AUDIT_HANDOFF.md` for methodology and per-phase scripts (`/c/tmp/h*_*.py`, `b1_judge.py`, `c3_scattered_wrong.py`, `f_cost_pareto.py`, etc.).

## G1. Findings triage

**Plumbing bugs (with case-name evidence + counts).**
- `_normalize_region` silent fallback (item #1) — 28/28 wf, 25/25 pot non-U.S. cases hit. **Single largest lever.**
- `direction` schema gap (item #5) — 39/39 wf, 34/35 pot extractions emit `direction=1`. Compounds item #1.
- INFRA #4 (5xx retry) — 35/250 case-runs lost across 5 strategies (14% flakiness tax).
- INFRA #3 (parser_constructor) — 39 react extraction failures + 2 wf pydantic_max_retries + 3 pot syntax errors.
- INFRA #1 (parser_float_coerce) — 2 struct cases.
- INFRA #6 (cachier-None unpack) — 4 unstr cases (was 4 in airline n=50; tracked already).
- `_parse_numeric_answer` regex (item #4) — 1 unstr case (`airline_1_65`).
- `'Main Cabin^'` passthrough (item #2 outlier) — 1 wf case (`airline_0_35`).
- Empty-rollout harness gap — 7 struct + 5 pot extraction_failures have no captured rollout. Lower priority; doesn't block analysis.

**Data / calculator concerns.**
- **NONE.** Calculator confirmed correct via H4 bit-exact reproduction (22/22). Ground truth `info` in `data/valid.jsonl` matches calculator output for the 2 spot-checked cases (`airline_2_25`, `airline_2_40`). The benchmark data is sound.

**Reasoning-capability ceilings.**
- Unstructured baseline: median calc_err 7.1%, p90 32%, max 72%. The 2 hallucinations are off-by-1-rule (model applied wrong fee table). 27/28 calc_errs are real reasoning errors per B1.
- Structured baseline: **bimodal**. Median 20%, max 99% (`airline_0_20` predicted $8 vs $972). 5/23 calc_errs are >50% hallucinations. The "simulate compute_airline_answer" approach has no calculator backstop. Best on easy cases, catastrophic on hard.
- Workflow + pot: errors are tightly bounded (max 51% wf, 32% pot) because the calculator is correct; remaining errors are bug-driven, not reasoning-driven. **Pot has zero >50% errors** — safest by error-magnitude.
- React: 0/50. All extraction-failure (INFRA #3 parser_constructor + 5xx). No reasoning data.
- L2 ceiling claim is **falsified**. Per E1', wf's projected L0/L1/L2 post-fix is 53%/44%/53% — flat across levels. The aggregate "L2 hardest" pattern was an artifact of `_normalize_region` × non-U.S. route concentration in L2 (8/11 extractable L2 cases have non-U.S. GT).

## G2. Recommended fixes (ranked by paper impact × ease)

| rank | fix | strategies affected | est. wins | effort |
|---|---|---|---|---|
| **1** | item #1: `_normalize_region` schema-Literal (option c) + substring scan fallback | wf, pot | wf +13 (24% → 50%), pot +6 (26% → 38%) | **30 min** |
| **2** | item #5: `direction` schema docstring + `Literal[0, 1]` | wf, pot | wf +up to 8 more (cases with routine OK but dir wrong) | **15 min** |
| **3** | INFRA #4: 5xx retry with backoff | all | +5–7 cases (≥80% of 35 transient failures recoverable) | **1 hour** (framework-level) |
| 4 | INFRA #3: parser_constructor (`<answer>` syntax tolerance) | react primarily | enables react to score nonzero (currently 0/50) | **2 hours** (framework-level) |
| 5 | item #4: `_parse_numeric_answer` regex extension for `=` and `:` | unstr | +1 (`airline_1_65`) | **5 min** |
| 6 | INFRA #1: numeric coercion strip commas/`$` | struct | +2 (`parser_float_coerce`) | **5 min** (framework) |
| 7 | INFRA #6: cachier-None defensive retry | unstr | +up to 4 | **15 min** (framework) |
| 8 | INFRA #2 sub-bullet E: schema injection into PoT prompt | pot, react | improves extraction quality further; not quantified | **1 hour** (framework) |

**Top combined leverage:** items #1 + #5 + INFRA #4 should lift workflow from 24% → ~58% (50% from #1, +8 from #5, +~2 from #4). At fixed mean cost ($0.0093), workflow becomes the unique Pareto-optimal strategy.

## G3. Reproducibility checklist

- All 5 strategy results: `results/20260425.{023139,033502,044344,050457,060426}.{strategy}/` — each with `results.csv` (50 rows + header), `results.jsonl` (50 valid lines), `config.yaml`.
- Run log: `logs/run_all_20260425_023133.log` (pre-audit ground state).
- Cache files: `llm_cache/.secretagent.implement.pydantic._run_agent_impl` (pydantic-ai, 215 KB, 145 entries) and `llm_cache/.secretagent.llm_util._llm_impl` (raw LLM, 7.4 MB).
- Audit scripts: `/c/tmp/{h1_extraction_audit,h2_normalize_region_sweep,h3_other_fields,h4_bitexact_repro,e_per_level,d1_relative_error,b1_judge,b23_parser_audit,c3_scattered_wrong,f_cost_pareto}.py`.
- Audit data: `/c/tmp/{h1_diff,h2_sweep,h4_repro,b1_judge_results}.csv`.
- Plot: `results_plot.png` (current Pareto, bug-affected).

## G4. Deliberately not fixed (n=50 audit scope)

- **PoT pydantic/dict asymmetry** (INFRA #2 / `project_pot_pydantic_dict_asymmetry.md`): 4 pot cases hit `KeyError: 'size'` / `TypeError: AirlineParams object does not support item assignment`. Cross-domain framework decision; deferred to a unified fix coordinated across airline + tax + nba (see INFRA #2 options A–E).
- **Tear-down crashes** (workflow `-1073741819`, pot `2816`): post-write Windows DLL-unload segfaults. Confirmed no data loss in n=50 (CSV+JSONL+config.yaml all intact). Wrapper exit-code bug at INFRA #5; tear-down crashes themselves are interpreter-shutdown artifacts, not framework bugs.
- **Empty-rollout harness gap** (struct 7, pot 5): the eval wrapper records `failure_mode=extraction_failure` but doesn't capture a rollout step when the exception happens before any step is logged. Lower priority — CSV-level data is sufficient for analysis.
- **Direction in calculator semantics** (`direction=0` vs `direction=1`): the convention is established in `rulearena_reference.py` and is the upstream RuleArena encoding. Don't change it; document it via the schema fix in item #5.

## G5. Paper caveats

- The aggregate correctness numbers (unstr=32%, struct=36%, wf=24%, pot=26%, react=0%) reported in this audit run are **bug-affected** — biased downward for wf/pot/react by `_normalize_region` + INFRA #3, and biased downward across the board by the 14% INFRA #4 flakiness tax.
- The "structured > unstructured" claim is **unsupported** by the n=50 data when conditioned on level: struct only beats unstr at L0; ties at L1; weakly beats at L2. And struct has 5x more hallucinations (>50% errors). Phrase carefully.
- The "L2 hardest" claim is **artifact** of the `_normalize_region` bug interacting with L2's higher non-U.S.-route prevalence. Flat once item #1 lands.
- Final paper numbers should re-run after items #1 + #5 + INFRA #4 are merged. Expected post-fix headline: workflow ~58% (Pareto-optimal), struct ~40%, unstr ~35%, pot ~42%, react ≥30%.

---

# Phase B postscript — infra-fix measurement (2026-04-26)

Branch A (domain fixes, this audit's items #1, #4, #5) merged to main as `a9aa5e0` on 2026-04-25. Branch B (`experiment/infra-fixes`, NOT merged) layers the four cross-domain framework fixes on top to produce the third measurement point.

## Deliverables

- **Three-runs comparison table:** `/c/tmp/three_runs.md` (baseline / branchA / branchB across all 5 strategies, with failure-mode breakdown and per-fix attribution).
- **Framework diff:** `/c/tmp/infra_changes.diff` (250 lines; src-only diff between `main` and `experiment/infra-fixes`).
- **Branch B run logs:** `logs/run_branchB_20260426_0141.log` — sequential per-strategy run on Windows, total wall-clock ~22 min (most in unstructured_baseline; struct/workflow/pot were cache-warm from branch A).
- **Branch B result dirs:** `results/20260426.{014201,015405,015432,015445,015455}.{strategy}/`.
- **Memory note:** `~/.claude/projects/.../memory/project_react_schema_hallucination.md` — captures the diagnostic shift in react's failure shape.

## Branch B commits (on `experiment/infra-fixes`, off A's tip `37e51dd`)

| commit | INFRA # | description |
|---|---|---|
| `fec2ca7` | #4 | 5xx/429 retry with exponential backoff in `llm_util.py` and `pydantic.py` (`_retry_with_backoff`, 3 attempts, 1s base + jitter; only `ServiceUnavailableError | InternalServerError | RateLimitError` are retried). |
| `d29195c` | #1 | `_coerce_numeric` strips commas and `$` before `int()`/`float()` in both `simulate.parse_output` and `_extract_answer`. |
| `a08738f` | #3 | Layered parser: strip ```` ```python|json ```` fences, then for pydantic return types parse `ClassName(...)` AST `Call` and call `model_validate`, then fall through to existing `json.loads → ast.literal_eval`. |
| `6e53d6b` | #6 | Defensive `None`-check on `cached(_llm_impl)` return; bypass cache once with stderr warning. |

## Headline (n=50, airline)

| strategy | baseline | branchA | branchB | A−base | B−A | B−base |
|---|---|---|---|---|---|---|
| unstructured_baseline | 32% | 36% | **44%** | +4pp  | +8pp  | +12pp |
| structured_baseline   | 36% | 40% | 40%     | +4pp  | 0pp   | +4pp  |
| workflow              | 24% | 76% | 76%     | +52pp | 0pp   | +52pp |
| pot                   | 26% | 60% | 60%     | +34pp | 0pp   | +34pp |
| react                 |  0% |  0% |  0%     |  0pp  | 0pp   |  0pp  |

The +8pp branch-B lift on unstructured_baseline is consistent with INFRA #6 (cachier-`None` bypass) recovering 4 cases plus incidental cleanup. The struct/workflow/pot zero-deltas are cache-warm equivalence (branch A's already-successful outputs re-parsed identically through the new layered parser) — i.e., backward-compat preserved, not "infra fixes did nothing." Tax (where `parser_float_coerce` hits more often per `tax/FINDINGS.md`) is where INFRA #1 will manifest.

## Updated take on react (item #3 of this audit)

This audit predicted INFRA #3 would unblock react. **It did — but only the parsing layer.** Branch B's react ran fresh for 8.5 min (no cache hits) and still landed 0/50, but the failure shape changed in the diagnostically expected way:

| | baseline / branchA failure | branchB failure |
|---|---|---|
| | `**exception raised**: malformed node or string on line 1: <ast.Call object>` | `**exception raised**: 5 validation errors for AirlineParams\nbase_price\n  Field required [type=missing, input_value={'passenger_name': ...}]` |
| | (literal_eval choking on constructor syntax — root cause swallowed) | (model_validate surfacing the real error: hallucinated field names) |

The deepseek-V3.1 model is emitting `AirlineParams(passenger_name="...", flight_class="...", origin=..., destination=..., baggage_items=[...], ticket_price=...)` — INFRA #3 successfully extracts those kwargs and passes them to `model_validate`, which rejects them because the real fields are `base_price`, `customer_class`, `routine`, `direction`, `bag_list`. This was anticipated in `INFRA_FIXES.md` §3:

> "Schema is also hallucinated (model invents `passenger_name`, `flight_class` instead of the real `customer_class`, `routine`, `bag_list`) — so a parser fix alone won't make react correct, but it will surface the real validation error instead of swallowing it."

**Why this matters for the paper.** Item #3 of this FINDINGS.md ("schema lacks semantic guidance") and INFRA #2.E ("inject pydantic schema into simulate prompts") are now the only remaining unblockers for react. Both are prompt-template changes, not framework changes. The current `simulate.txt` and `simulate_pydantic.txt` only embed `interface.src` — the function signature and docstring — so the model never sees the `AirlineParams` field names + types + descriptions. The fix is a one-template change with cross-domain reach (airline + tax both go through this path; tax has 70 fields and will break harder).

## Cross-benchmark react inventory (2026-04-26)

For the paper's claims about react: only `airline/` and `tax/` define a `react` make target. Both wire it identically:

```
ptools.compute_*_answer.method=simulate_pydantic
ptools.compute_*_answer.tools=[ptools.extract_*_params, ptools.compute_*_calculator]
ptools.extract_*_params.method=simulate     # nested simulate (not simulate_pydantic)
```

`benchmarks/medcalc/Makefile` and `benchmarks/musr/Makefile` have no `react` target — medcalc has `baseline / simulate / distilled / pot / workflow`, musr has `murder_workflow / object / team`. So the airline+tax react result is the only "react via simulate_pydantic" datapoint in the codebase. If the schema-hallucination diagnosis holds, fixing INFRA #2.E should lift both airline and tax react simultaneously.

## What does NOT change in this audit

Items #1, #2, #4, #5 of this FINDINGS.md were already fixed in branch A and merged to main. The recommendations in G2 (ranks 1, 2, 5) are done. Items left for the next round:

- **G2 rank 8 (INFRA #2.E — schema injection into simulate prompt)** — now elevated from "improves further; not quantified" to "the only remaining unblocker for react." Recommended scope: edit `src/secretagent/implement/prompt_templates/simulate.txt` to include a serialized schema block when `return_type` is a pydantic BaseModel, mirroring what pydantic-ai already does at the agent layer.
- **G4 deferred items remain deferred** (PoT pydantic/dict asymmetry, tear-down crashes, empty-rollout harness gap, direction calculator semantics). None blocked by branch B.

---

## Phase C postscript: cross-model react re-runs + 5-strategy V3.1 sweep on followups (2026-04-26 / 2026-04-27)

Branch B's diagnosis ("react=0% root cause is schema hallucination, fixable only via INFRA #2.E") was confirmed in two stages: a gemini-2.5-flash re-run on branch B (which retained 6% — schema hallucination is universal across V3.1 and gemini, not a model-specific quirk) and then a four-commit Phase C followup that cured it.

### Phase C followup commits (on `experiment/infra-fixes`, after merging `experiment/infra-followups`)

| Sha | Tag | Summary |
|---|---|---|
| `c850231` | F1 | `infra(pydantic): defensive None bypass on _run_agent cache` — mirrors INFRA #6 into the pydantic-ai cache wrapper |
| `863a259` | F2 | `infra(parser): model_validate dicts when return_type is BaseModel` — ValidationError surfaces at parser boundary instead of much later as KeyError |
| `1cc91fa` | F3 | `infra(parser): fence-block fallback when <answer> tag missing` — recovers ` ```python ClassName(...) ``` ` shapes |
| `fd84417` | **F4** | `infra(prompt): inject pydantic schema for BaseModel return types` — **the load-bearing fix.** Embeds `model_json_schema()` into simulate / simulate_pydantic prompts. |

### Phase C V3.1 sweep (n=50 / seed=137 / `cachier.enable_caching=false` to bust F4 prompt change)

| strategy | baseline | branch A | branch B | **followups** | Δ vs B |
|---|---|---|---|---|---|
| unstr_baseline | 32% | 36% | 44% | **60%** (30/50) | **+16 pp** |
| structured_baseline | 36% | 40% | 40% | 42% (21/50) | +2 pp |
| **workflow** | 24% | 76% | 76% | **94%** (47/50) | **+18 pp** |
| pot | 26% | 60% | 60% | 62% (31/50) | +2 pp |
| **react (V3.1)** | 0% | 0% | 0% | **58%** (29/50) | **+58 pp** |
| react (gemini-2.5-flash) | — | — | 6% | **52%** (26/50) | **+46 pp** |

**Three strategies move materially**: workflow (→ near-data-ceiling 94%), unstr (+16 pp), and both react variants (+46–58 pp). struct and pot essentially flat (+2 pp). The pattern is consistent with F4 being the lever:
- workflow / react / unstr's `extract_*_params` calls return a pydantic BaseModel → F4 fires → schema visible to LLM → field-name hallucination cured.
- struct / pot top-level calls return primitive types — F4 doesn't fire on them. Their extraction-tool calls do benefit, but the bottleneck for these strategies is elsewhere (struct: numeric inaccuracy at calc layer; pot: dict-assignment-on-pydantic asymmetry — see below).

### Phase C residual failure shapes

**V3.1 react (21 fails, 29/50 correct):**
- 12 transport: 6× 500, 4× 503, 2× 429 — bursty TogetherAI window during this run; the other 4 V3.1 sweep runs that followed within 5 hours had **zero** 5xx hits, so this is environmental, not framework-side. INFRA #4's 3-attempt budget should still be bumped (the tax workflow run on 2026-04-26 15:05 lost 50/50 to a sustained TogetherAI 500-burst, confirming the budget is too thin).
- 4 schema-residual: 3× `KeyError 'size'` + 1× `KeyError 'weight'` — agent emitted a dict missing required fields despite F4 schema in prompt
- 3 parser tail: F3 fence regex didn't catch the shape
- 1 pydantic-ai output validation retry exhausted; 1 numeric-incorrect

**gemini react (24 fails, 26/50 correct):**
- 20 "cannot find final answer" — F3 doesn't catch gemini's verbose multi-fence chain-of-thought shape; rollouts have len=0 because pydantic-ai raises before record(). Needs single-case `echo.llm_output=true` audit.
- 3 numeric-incorrect (~5% off) — same shape as the 3 baseline tool-bypass cases; gemini sometimes answers without invoking tools (deferred as F6)
- 1 `No choices returned from LiteLLM` — gemini transport blip

**pot (19 fails, 31/50 correct):** ⭐ **PoT pydantic/dict asymmetry confirmed in flesh.** 7 cases are `Code execution failed at line 'params["customer_class"] = ...'` — F4 helped the LLM use *correct* field names, but the LLM still emits `params[X] = ...` style code that crashes on a pydantic instance. F4 made the bug visible by removing the field-name hallucination noise; **INFRA #2.C (sandbox preamble `params = params.model_dump()`) or #2.A (re-type `compute_*_calculator(params: <DomainParams>)`) is the next unblocker for pot.**

**struct (29 fails, 21/50 correct):** 25 numeric-incorrect (calc-layer accuracy bound) + 4 parser shapes where the LLM emitted `<answer>` text bleeding outside the tag. Not affected by F4 because struct's top-level return type is `int`. struct is now bound by *content quality at the compute layer*, not extraction.

**workflow (3 fails, 47/50 correct):** 2 numeric-incorrect + 1 pydantic-ai output validation retry. **Effectively at data ceiling.**

### Cost / token deltas

V3.1 react followups: mean cost $0.0241/case, mean output_tokens 591, mean latency 58.9s. workflow: $0.0090/case (cheapest of the lot — direct path with two simulate calls). gemini react: $0.0326/case, output_tokens 7,999 (verbose CoT vs. V3.1's terse 591).

### What this confirms for the paper

1. **Schema hallucination was the universal root cause for react=0%**, validated across two model families. F4 is the durable fix; F1–F3 are correct but secondary cleanup.
2. **F4's lever applies anywhere a pydantic BaseModel is returned through `simulate` or `simulate_pydantic`**. Cross-domain prediction: tax (TaxParams ≈ 75 fields) should see *larger* lift than airline (AirlineParams = 5 fields).
3. **Failure mix is now strategy- and model-specific** — the "extraction failure" bucket has fragmented into transport, parser-shape, calc-accuracy, and PoT-asymmetry sub-buckets, each with a different next intervention.
4. **Workflow at 94%** sets a real ceiling line: any strategy that doesn't reach it needs to explain why.

### Next interventions (post-prof meeting)

- **INFRA #2.C/D (PoT asymmetry)** — biggest pot lever after this round
- **INFRA #4 retry budget bump** — verify pydantic-ai path actually invokes `_retry_with_backoff` end-to-end (V3.1's 12 unrecovered 5xx + tax workflow's full 50/50 wipe-out on 2026-04-26 confirms the current budget is inadequate for sustained outages)
- **F3 regex broadening** — single-case audit on gemini's 20 unrecovered "cannot find final answer" cases
- **F6 (deferred)** — gemini-2.5 sometimes bypasses tool calls; behavioral, ~3 cases per gemini run

Source data: `benchmarks/rulearena/airline/results/20260426.034436.react_v31_followups/`, `20260426.034502.react_gemini25/`, `20260426.044824.unstructured_baseline_v31_followups/`, `20260426.060959.structured_baseline_v31_followups/`, `20260426.071133.workflow_v31_followups/`, `20260426.073138.pot_v31_followups/`. Working comparison sheet: `/c/tmp/react_followups.md`.

