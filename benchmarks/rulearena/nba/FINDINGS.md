# NBA benchmark findings

Living document. Add findings as they're confirmed; update when stronger evidence arrives.

---

## Domain overview: NBA is binary classification, not numeric calculation

**What makes NBA different from airline and tax.** NBA asks "does any operation violate CBA salary cap rules?" — the answer is True/False, not a dollar amount. There is **no calculator**: the ground truth comes directly from the JSONL `answer` field. Evaluation is exact boolean match: `bool(predicted) == bool(expected)`. No tolerance threshold applies (unlike tax's 1% relative error).

This has structural implications for every strategy:
- **Workflow** is `extract_nba_params → float(result.verdict)` — extraction IS the answer. No calc step means extraction quality = final accuracy.
- **PoT** generates code but has no calculator tool to call. The LLM must reason about CBA rules in generated Python, not delegate arithmetic.
- **React** has only `extract_nba_params` as a tool (no calculator tool). The agent loop is simpler than airline/tax react.
- **Structured baseline** must one-shot the entire CBA analysis and return a float.

**NbaResult has 3 meaningful fields** (verdict, illegal_operation, problematic_team) + reasoning. Compare: AirlineParams has 5 fields, TaxParams has ~75. This is the simplest extraction target in RuleArena.

**97K rules text.** The CBA reference rules file is 98,208 bytes (461 lines). Every prompt includes the full rules text, yielding ~22K input tokens per call. This requires `timeout: 600` in conf.yaml (default 180s is insufficient).

**Class imbalance in valid split.** 36/42 (86%) are True (violation), 6/42 (14%) are False (compliant). A naive all-True baseline scores 86%. Any strategy below this threshold is worse than trivial.

---

## Data distribution

| Split | Total | L0 | L1 | L2 | True | False |
|---|---|---|---|---|---|---|
| train | 128 | 48 | 53 | 27 | 109 (85%) | 19 (15%) |
| valid | 42 | 16 | 17 | 9 | 36 (86%) | 6 (14%) |
| test | 46 | 17 | 19 | 10 | 34 (74%) | 12 (26%) |

Test split has more balanced class distribution (74/26) than train/valid (85/15). Level distribution is roughly 3:3:1.5 across all splits.

---

## Smoke test results (1 case, V3.1)

Single-case smoke tests on the first valid case. Model: `together_ai/deepseek-ai/DeepSeek-V3.1`, `cachier.enable_caching=false`.

| Strategy | Predicted | Expected | Correct | Latency | Input tokens | Cost | Diagnosis |
|---|---|---|---|---|---|---|---|
| unstructured | 1.0 | 1.0 | YES | 87s | 21925 | $0.016 | Clean: `<answer>True</answer>` parsed correctly |
| structured | exception | 1.0 | NO | ~1s | — | — | `cannot find final answer` — 4 output tokens, no visible reasoning |
| pot | function object | 1.0 | NO | — | — | — | Returned callable, not float |
| react | 0.0 | 1.0 | NO | — | — | — | Reasoning error: concluded no violation when one exists |
| workflow | — | — | — | — | — | — | Not yet tested (added after smoke batch) |

### Smoke observations

**Unstructured is the only clean pass.** The 87s latency on a single case (vs airline's ~10s) reflects the 97K rules text. Full n=42 runs will take ~60 min per strategy.

**Structured baseline's 4-token output** mirrors the pattern seen on tax: DeepSeek routes computation to `reasoning_content` and emits a terse hallucinated number (or nothing parseable). With NBA's binary output this is especially fragile — the model doesn't even produce a True/False, just an unparseable stub.

**PoT returned a function object, not a float.** The generated code likely defined a function but didn't call it or return a value. This is a code-generation bug, not a reasoning error.

**React concluded "no violation" on a violation case.** Unlike airline's react (which was 0% due to schema hallucination pre-F4), NBA react produced a parseable answer — it just reasoned incorrectly. This is a reasoning error, suggesting the CBA rules are genuinely hard to apply even with tool support.

---

## F4 schema injection: predicted lift for NBA

F4 (commit `fd84417`) injects `model_json_schema()` into simulate/simulate_pydantic prompts for BaseModel return types. Cross-domain evidence:

| Domain | Extraction target | Fields | F4 lift on workflow | F4 lift on react |
|---|---|---|---|---|
| airline | AirlineParams | 5 | +18 pp (76→94%) | +58 pp (0→58%) |
| tax | TaxParams | ~75 | measured at 60% (no pre-F4 baseline) | measured at 14% |
| **nba** | **NbaResult** | **3** | **prediction below** | **prediction below** |

**NBA prediction: F4 lift should be smaller than airline's.**

Reasoning: NbaResult has only 3 meaningful fields (verdict, illegal_operation, problematic_team). The field names are intuitive and unlikely to be hallucinated even without schema injection. Compare airline (5 fields, some ambiguous like `penalty_rate` vs `fee_amount`) and tax (75 fields with IRS-form-label names that invite hallucination). F4's value scales with schema complexity — NBA is at the low end.

However, F4 still helps by injecting the Field descriptions (e.g., "Letter of the first violating operation (e.g. 'A', 'B')"), which tell the LLM the expected format. This could prevent format errors (e.g., writing "Operation A" instead of just "A") even if field names would have been guessed correctly.

**Bottom line:** F4 is already baked into the current code. Any n=42 run will include F4. The interesting question is not "how much did F4 help" but "given F4, what is the remaining bottleneck" — and for NBA, that bottleneck is likely **CBA rule reasoning quality**, not extraction fidelity.

---

## Cross-domain predictions for NBA

Based on airline (n=50) and tax (n=50) Phase C results:

| Strategy | Airline | Tax | NBA prediction | Rationale |
|---|---|---|---|---|
| unstr | 60% | 58% | **60-70%** | Binary verdict is simpler than numeric; but 97K rules are harder to reason over than airline's short rules |
| struct | 42% | 10% | **40-50%** | 3-field NbaResult is closer to airline's complexity; but binary output may actually help (model can guess True/False more easily than a dollar amount) |
| workflow | 94% | 60% | **65-80%** | Extraction of 3 fields should be very reliable (like airline); the bottleneck shifts to whether the LLM gets the *verdict* right, not whether it extracts the right fields |
| pot | 62% | 48% | **50-65%** | No calculator means PoT must encode CBA logic in Python — hard. But no dict-asymmetry crash risk (NbaResult has only 3 fields) |
| react | 58% | 14% | **50-65%** | Only 1 tool (extract), simple 3-field schema → parser should handle it. But the smoke test showed reasoning error, not parser error — ceiling may be lower than airline |

**Key uncertainty: CBA rule complexity.** The 97K rules text contains dense legal language about salary cap exceptions, bird rights, mid-level exceptions, etc. The LLM must understand and correctly apply these rules to specific team situations. This is qualitatively different from airline (short, procedural rules) and tax (long but well-structured form-based rules). NBA's rules may be the hardest reasoning challenge in RuleArena even though its extraction target is the simplest.

**Class imbalance caveat.** With 86% True in valid, a strategy that always predicts "violation" scores 86%. Any strategy below ~60% is being actively harmed by its pipeline — it would be better off ignoring the input. This makes the naive-baseline threshold unusually high.

---

## Domain-specific configuration

```yaml
# conf/conf.yaml differences from airline/tax
llm:
  timeout: 600     # airline/tax use default 180s; NBA needs 600 for 97K rules text
  max_tokens: 8192 # same as airline/tax

# No calculator in ptools — workflow is extract→verdict, not extract→calc
# pot has inject_args=true but no tool calls — LLM must reason in code
# react has only extract_nba_params as tool (vs airline's extract+calc, tax's extract+calc)
```

---

## Open questions (pre n=42 run)

1. **Does the all-True baseline (86%) bound most strategies from above?** If unstr/workflow/react all cluster near 86%, the strategies are not reasoning — they're leveraging class imbalance. The 6 False cases are the discriminative signal.

2. **Per-level gradient.** Airline and tax both show steep L0→L1→L2 dropoff. NBA has fewer L2 cases (only 9 in valid), so per-level estimates will be noisy. Focus on L0+L1 (n=33) for reliable comparison.

3. **PoT code quality.** The smoke test returned a function object. If PoT systematically fails to produce callable code on NBA, it may score 0% regardless of reasoning quality.

4. **Workflow vs unstructured gap direction.** On airline, workflow >> unstr (94% vs 60%). On tax, workflow ≈ unstr (60% vs 58%). NBA could go either way: if extraction of 3 fields is trivial, workflow degenerates to "extract verdict + return it" which may not beat raw unstructured reasoning. The value of workflow depends on whether structured extraction forces more careful analysis.

---

Source: smoke tests run 2026-04-27 on branch `experiment/infra-fixes` at commits `f5ebbc7` through `9540772`. Cross-domain numbers from `benchmarks/rulearena/airline/FINDINGS.md` and `benchmarks/rulearena/tax/FINDINGS.md`.
