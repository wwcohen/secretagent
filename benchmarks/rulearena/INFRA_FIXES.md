# RuleArena infrastructure fixes

Cross-domain framework-level changes encountered while building per-domain benchmarks. Living list — finalize with Prof.

Each entry: **What** (symptom) / **Where** (file:line) / **Fix** / **Risk** / **Evidence**.

## Status (as of 2026-04-27)

All on `experiment/infra-fixes` (single shipping branch; `experiment/infra-followups` was FF-merged in and deleted on 2026-04-27).

| Item | Status | Commit |
|---|---|---|
| #1 numeric coercion (commas/$) | **DONE** (Phase B) | `d29195c` |
| #2.A/B/C/D PoT pydantic/dict asymmetry | pending | — |
| **#2.E PoT/simulate schema injection** | **DONE** (Phase C, "F4") — load-bearing fix | `fd84417` |
| #3 simulate parser layered (constructor + fence) | **DONE** (Phase B base + Phase C followups) | `a08738f`, `863a259`, `1cc91fa` |
| #4 retry on 5xx/429 | **DONE** (Phase B) — but budget is thin for sustained outages, follow-on bump pending | `fec2ca7` |
| #5 `run_all_valid.sh` exit code bug | pending | — |
| #6 `cached(_llm_impl)` returns None | **DONE** (Phase B + Phase C "F1" extension to pydantic-ai path) | `6e53d6b`, `c850231` |

**Phase B / Phase C empirical impact** is documented in `benchmarks/rulearena/airline/FINDINGS.md` (Phase C postscript). Headline: V3.1 react 0% → 58%, gemini react 6% → 52%, workflow 76% → 94% on airline n=50. F4 (#2.E) is the lever for any pydantic-returning interface; #2.C/D remain the unblocker for PoT.

---

## 1. `simulate` / `prompt_llm` answer coercion fails on comma-formatted floats

**What.** LLM emits `<answer>-25,502.0</answer>` (natural for dollar amounts). Parser calls `float('-25,502.0')` → `ValueError: could not convert string to float`. Case is lost as `**exception raised**`. Affects any float-output domain.

**Where.** Two sites, same pattern:
- `src/secretagent/implement/core.py:159-160` — `simulate.parse_output`: `if return_type in [int, str, float]: return return_type(final_answer)`
- `src/secretagent/implement/core.py:274-275` — `_extract_answer` (used by `prompt_llm`): same line, same risk.

**Fix.** Add a numeric-normalization helper before coercion: strip commas and `$`, accept ` -123` etc. Apply at both call sites. ~3 lines + 1 helper.

```python
def _coerce_numeric(s: str, t):
    if t in (int, float):
        s = s.strip().replace(',', '').replace('$', '')
    return t(s)
```

**Risk.** Touches framework code currently in use by the live airline run; defer until airline finishes. Net safe: airline's outputs are integer dollars (no commas naturally emitted, no decimals); tax benefits; nba unaffected (verdict bool).

**Evidence.** `benchmarks/rulearena/tax/FINDINGS.md` § "simulate factory parser doesn't strip commas" + `tax/results/20260425.044520.structured_baseline/` (case `tax_0_95`).

---

## 2. PoT pydantic / dict type-asymmetry

**What.** `extract_*_params(query) -> *Params` returns a pydantic model; `compute_*_calculator(params: dict) -> ...` declares dict in its annotation. PoT prompts the LLM with both signatures, so generated code naturally writes `params["x"] = …` after extraction — which crashes on the pydantic instance (`TypeError: 'TaxParams' object does not support item assignment`). ~1/3 plumbing failures observed in airline n=3.

**Where.** Domain ptools (`airline/ptools.py`, `tax/ptools.py`, future `nba/ptools.py`). Mirrored intentionally for cross-domain parity; deferred for unified fix.

**Possible fixes (pick one cross-domain):**
- **A.** Type `compute_*_calculator(params: <DomainParams>)` so PoT code is generated against the pydantic API (e.g. `params.x` access, `model_copy(update=...)`). Cleanest API.
- **B.** Have `extract_*_params` return a dict (lose pydantic validation; cheapest at API surface).
- **C.** Inject `params = params.model_dump() if hasattr(params, 'model_dump') else params` preamble into the PoT sandbox before the generated code executes. Fix is in the `program_of_thought` factory, not in domain code. Most domain-agnostic.
- **D.** Strengthen `_*_calc_fn`'s 4-convention shim to short-circuit on pydantic instances earlier (already partly done via `hasattr(raw, 'model_dump')`) — but PoT's generated code may crash on `params["x"] = ...` *before* reaching the shim.
- **E. (NEW)** Inject the **pydantic schema (field names + types + descriptions)** into the PoT prompt explicitly. Without this, the LLM hallucinates dict keys based on the prompt's surface form (e.g. `"Schedule C (Form 1040)_Line 1 - Gross receipts or sales"` instead of the actual field `gross_receipts`). C alone doesn't fix this — the lookup would silently return defaults. See tax FINDINGS § "PoT: schema hallucination on rich pydantic models". Severity scales with schema size: airline (5 fields) ≪ tax (70 fields).

**Risk.** A and B change the API across all 3 domains; coordinated change. C touches the framework. D is safest but doesn't fully solve. E touches the framework and may also reduce fragility on unstructured prompts. C+E together is probably the right combo.

**Evidence.** Memory note `project_pot_pydantic_dict_asymmetry.md`; tax `results/20260425.045958.pot/` (case `tax_1_17` — has `self_employed=True`, triggers both `.get()` failure and hallucinated key); airline ~1/3 plumbing failures.

---

## 3. `simulate` parser rejects Pydantic constructor + code-block answers

**What.** For non-primitive `return_type` (e.g. a Pydantic model), `parse_output` chains `json.loads → ast.literal_eval`. DeepSeek-V3.1 frequently emits two unparseable shapes inside `<answer>…</answer>`:
- **Pydantic constructor syntax**: `AirlineParams(cabin_class='Business', items=[Item(...)…])` → `literal_eval` rejects as `<ast.Call object>`.
- **Multi-statement code block**: ```` ```python\nparams = extract_…(text)\n…``` ```` → `invalid syntax`.

Cache scan over the airline n=50 run: **78/118 `<answer>`-tagged responses unparseable (66%)** — 37 constructor-syntax, 40 code-block, 1 invalid-decimal. Drives `react=0/50` on airline (39 of 50 failures from this). Schema is also hallucinated (model invents `passenger_name`, `flight_class` instead of the real `customer_class`, `routine`, `bag_list`) — so a parser fix alone won't make react correct, but it will surface the real validation error instead of swallowing it.

**Where.** Two sites, same pattern:
- `src/secretagent/implement/core.py:147-185` — `SimulateFactory.parse_output`.
- `src/secretagent/implement/core.py:262-276` — `_extract_answer` (used by `prompt_llm`).

**Fix.** Layered parser, in order: (a) strip ```` ```python … ``` ```` fences; (b) if `return_type` is a Pydantic BaseModel and `final_answer` matches `ClassName(...)`, parse the AST `Call` node and feed kwargs to `return_type.model_validate(...)`; (c) fall back to current `json.loads → ast.literal_eval`. Combine with item #5 (schema injection) for the schema-hallucination side.

**Risk.** Framework-wide; test all 3 domains. Backward-compatible: existing JSON outputs hit (c) unchanged.

**Same failure family, different surface — pydantic-ai validation retry.** When the interface uses `method=simulate_pydantic` (e.g., the default `extract_airline_params` in `airline/conf/conf.yaml:18`), the same V3.1 bad-structured-output behavior surfaces as `Exceeded maximum retries (1) for output validation` from pydantic-ai's `Agent` retry loop instead of from `parse_output`. Airline workflow strategy: 2/50 cases (`airline_2_10`, `airline_2_43`). Fix considerations: (i) the proper parser fix above doesn't help here — the pydantic-ai path doesn't go through `parse_output`; (ii) raising `pydantic.retries` beyond 1 is a band-aid; (iii) the only durable fix is to also strengthen the *prompt* (item #2 sub-bullet E: inject the schema explicitly) so the model emits valid structured output more often.

**Evidence.** `airline/results/20260425.060426.react/` (50/50 extraction_failures); cache scan `benchmarks/rulearena/airline/llm_cache/.secretagent.llm_util._llm_impl`; trace `benchmarks/rulearena/airline/results/20260425.060426.react/results.jsonl` (case `airline_0_6` shows the failure shape end-to-end).

**Concrete examples.**

Constructor syntax (case `airline_0_6`, model emitted):
```
<answer>
AirlineParams(
    passenger_name="Elizabeth", flight_class="First Class", departure="Austin",
    destination="Mumbai", baggage_items=[BaggageItem(...), ...], ticket_price=471.0)
</answer>
```
→ `ast.literal_eval` raises `malformed node or string on line 1: <ast.Call object at 0x...>`. Note also the field names are hallucinated (real `AirlineParams` has `customer_class`, `routine`, `bag_list`, `base_price`).

Code-block answer (case `airline_1_65`, pot — same parser path):
```
<answer>
```python
params = extract_airline_params(problem_text)
result = compute_airline_calculator(params)
final_answer(result)
```
</answer>
```
→ `ast.literal_eval` raises `invalid syntax (<unknown>, line 1)`.

What the parser currently expects (would succeed): `<answer>{"customer_class": "First", "routine": "Austin to Mumbai", "base_price": 471, "bag_list": [...]}</answer>`.

---

## 4. No retry on litellm 5xx / 429 transient errors

**What.** TogetherAI returns 500 / 503 / 429 mid-run; the litellm call propagates as `litellm.ServiceUnavailableError / InternalServerError / RateLimitError`; SimulateFactory and SimulatePydanticFactory record `**exception**: …` and re-raise. Each affected case is lost as `extraction_failure` with NaN cost. Airline n=50 lost **35/250 case-runs (14%)** to this — distributed across all 5 strategies (unstr=2, struct=7, workflow=9, pot=6, react=11). Materially distorts headline % numbers.

**Where.** `src/secretagent/llm_util.py` (the litellm completion call); affects every factory that goes through `llm_util.llm`. `simulate_pydantic` goes through pydantic-ai's `agent.run_sync` (`src/secretagent/implement/pydantic.py:69`) — needs separate retry handling, since pydantic-ai owns the retry budget for tool-validation failures (`pydantic.retries`) but not for transport-level errors.

**Fix.** Wrap the litellm completion with retry-with-exponential-backoff (3 attempts, jitter, ~1s base) on `ServiceUnavailableError | InternalServerError | RateLimitError`. Do **not** retry other 4xx (auth, schema). For pydantic-ai, swap `LiteLLMModel(...)` for a wrapper that retries at the HTTP layer before pydantic-ai sees the error.

**Risk.** Slows runs that hit a sustained outage (3x latency on a dead endpoint); cap total wall-clock with `llm.timeout`. Don't retry inside a cachier-cached path (cache must store the *successful* response only — current cachier already only writes on return, so this is automatic).

**Evidence.** Cross-strategy clustering: `/tmp/a1_xref.py` reproduces from `airline/results/20260425.*` CSVs.

**Concrete example.** From `workflow/results.csv` (one of 9 cases in that strategy):
```
**exception raised**: status_code: 503, model_name: together_ai/deepseek-ai/DeepSeek-V3.1,
body: litellm.ServiceUnavailableError: Together_aiException - Service unavailable
```
The case was lost (`failure_mode=extraction_failure`, `cost=NaN`) on a transient outage. A 3-attempt retry with 1s base + jitter would have rescued ≥80% of the 35 such losses (assuming a typical 503 burst lasts <5s).

---

## 5. `run_all_valid.sh` reports wrong exit code (TODO — affects all rulearena domains)

**What.** The per-strategy log line `=== $s end: $(date) (exit=$?) ===` reads `$?` *after* `make` completes, but `$?` at that point reflects the previous shell command in the pipe-chain (an implicit `echo`/`tee` value of 0), not the make exit code. Result: the master log always reports `exit=0` for every strategy regardless of whether `make` actually succeeded. Discovered while auditing airline n=50 — both `workflow` (-1073741819 STATUS_ACCESS_VIOLATION) and `pot` (status 11 SIGSEGV) crashed during interpreter shutdown, but the wrapper logged `exit=0`.

**Where.** Same buggy line in both wrappers:
- `benchmarks/rulearena/airline/run_all_valid.sh:22`
- `benchmarks/rulearena/tax/run_all_valid.sh:22`
- (`nba/run_all_valid.sh` does not exist yet — apply the corrected pattern when authored.)

**Fix.** Capture `$?` immediately after `make`:
```bash
make "$s" DOTPAIRS="$DOTPAIRS"; rc=$?
echo "=== $s end:   $(date) (exit=$rc) ==="
```

**Risk.** None — script-only, no framework code changed. Trivial.

**Evidence.** `airline/logs/run_all_20260425_023133.log` lines 313–314 and 431–432 show `make: *** Error N` immediately followed by `exit=0`.

**Severity.** Cosmetic for clean runs but a real reproducibility hazard: a future genuine `make` failure (e.g. data-corrupting crash mid-write) would be silently logged as success.

---

## 6. `cached(_llm_impl)` occasionally returns `None` — caller crashes on tuple unpack

**What.** `llm_util.llm` (`src/secretagent/llm_util.py:158-166`) calls `cached(_llm_impl)(prompt, model)` and unpacks the result as `model_output, stats = …`. `_llm_impl` always returns a 2-tuple, but the cachier-wrapped version occasionally returns `None`, producing `TypeError: cannot unpack non-iterable NoneType object`. Affected case is recorded as `extraction_failure` with `rollout` length 0 (so no diagnostic info beyond the exception). Airline n=50 unstructured: 4 cases (`airline_0_40`, `airline_0_79`, `airline_2_3`, `airline_2_40`).

Likely root cause is cachier's race / observer behavior under heavy sequential access on Windows — `cache_util.py:18-29` already documents a related macOS deadlock and a watchdog-observer monkey-patch. The Windows-side equivalent appears to surface as a None return. Not yet bisected.

**Where.**
- Symptom: `src/secretagent/llm_util.py:163` (`model_output, stats = cached(_llm_impl)(prompt, model)`).
- Suspected origin: `src/secretagent/cache_util.py:51-78` (`cached()` wrapper) plus the cachier library's pickle-cache read path on Windows.

**Fix (defensive, while root cause is being chased).** Detect None and either retry once or raise a clean error:
```python
result = cached(_llm_impl)(prompt, model)
if result is None:
    result = _llm_impl(prompt, model)   # bypass cache once
model_output, stats = result
```
Do **not** swallow None silently — it would mask real cachier bugs.

**Risk.** Low. The defensive retry adds at most one extra LLM call per affected case (~4/250 in this run). Should also instrument with a warning so we can track frequency over time.

**Evidence.** `airline/results/20260425.023139.unstructured_baseline/results.csv` — 4 rows with `cannot unpack non-iterable NoneType object`; rollout length 0 confirms the failure is before any record.record() call.

---

## 7. (placeholder)

Add new entries here as further infra issues surface during smoke / production runs.
