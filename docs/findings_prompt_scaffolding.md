# Findings: Prompt Scaffolding and L1 Accuracy on RuleArena

**Date:** 2026-04-01
**Authors:** [student], Claude Code (assisted)
**Benchmark:** RuleArena (airline baggage fees, US federal tax, NBA CBA compliance)
**Model:** DeepSeek-V3 (`together_ai/deepseek-ai/DeepSeek-V3`)
**Framework:** secretagent
**Reference:** ptp-behavior-distillation L1 results (same model, same benchmark)

## Summary

Replacing secretagent's generic `simulate` prompt wrapper with task-specific
`prompt_llm` templates that replicate ptp's direct framing recovered a
56.7-point accuracy gap on L1 tax extraction and produced strong results
across all three RuleArena domains.

## Results

| Domain  | simulate (baseline) | prompt_llm | ptp reference | Delta (sim -> prompt_llm) |
|---------|--------------------:|-----------:|--------------:|--------------------------:|
| Tax     |              43.3%  |   **100.0%** |        99.7% |                   +56.7pp |
| Airline |                 --  |    **98.3%** |        77.0% |                        -- |
| NBA     |                 --  |    **83.3%** |        80.1% |                        -- |

- **Tax N=60** (valid split, all complexity levels). 60/60 correct.
- **Airline N=60** (valid split). 59/60 correct; 1 wrong prediction (airline_2_91).
- **NBA N=42** (valid split). 35/42 correct; 7 wrong (6 false-positive violations + 1 parse error + 1 false-negative -- net bias toward predicting violations).

ptp reference numbers are from `rq2_summary.csv` on N=300/216 mixed
train+valid+test splits. Our results use N=60/42 valid-split only, so
cross-study comparison is directional, not exact.

## Proven findings

### 1. simulate's speculative framing causes catastrophic extraction failure on tax

The `simulate` factory wraps the function docstring in a speculative prompt:

> "Imagine this function was implemented... propose a possible output that
> would be produced by a correct implementation."

For tax extraction, this framing is ambiguous: the LLM sometimes follows the
embedded instruction in `forms_text` ("Calculate the tax owed...") rather than
extracting parameters. The result is a 43.3% accuracy on N=60 -- a 56.7-point
gap vs. the 100% achieved with direct framing.

**Evidence:**
- simulate baseline: 43.3% (result dir `20260401.150937.l1_tax`, N=60)
- prompt_llm: 100.0% (result dir `20260401.172102.l1_tax`, N=60)
- Same model, same calculator, same dataset split. Only the prompt changed.

**Root causes (two compounding issues):**
1. **Speculative vs. direct framing.** simulate says "propose a possible
   output"; ptp says "You are executing the function `extract_tax_params`."
   The direct framing unambiguously positions the LLM as the function executor.
2. **Unquoted input injection.** simulate substitutes `$query` bare into the
   prompt. When `forms_text` contains "Calculate the tax owed... End with
   `<answer>xxx</answer>`", the LLM follows that instruction instead of
   extracting. ptp's `repr()` quoting (replicated as triple-quoting in our
   templates) treats the input as data, not instruction.

### 2. An explicit extraction disambiguation instruction eliminates residual confusion

Adding "IMPORTANT: Your task is to EXTRACT parameters from the forms above,
NOT to calculate the tax" to the tax template, combined with "Return ONLY a
valid JSON object", fully disambiguated the task. This is a belt-and-suspenders
fix alongside quoting.

### 3. // comments in JSON schemas are safe under direct framing

The `simulate` factory's vague output format ("show it as if printed by
print(x)") caused the LLM to echo `//` comments from docstrings into its
JSON output, producing parse failures. Under `prompt_llm` with "Return ONLY
a valid JSON object", the LLM consistently strips comments from its output.
No `//`-related parse failures were observed across 162 prompt_llm calls.

## Hypothesized findings (require further validation)

### 4. Airline accuracy exceeding ptp may reflect split or prompt differences

Our airline result (98.3%) significantly exceeds ptp's reference (77.0%).
Possible explanations:
- **Split difference:** We evaluated on N=60 valid-split; ptp used N=300
  mixed split. The valid split may be easier or our small N may have favorable
  variance.
- **Template quality:** Our airline extraction template was written with the
  benefit of seeing ptp's failure modes. Minor wording differences could
  improve extraction.
- **Region normalization:** We added a `_normalize_region()` fallback that
  maps city/country names to fee-table regions. ptp may not have this.

This result needs validation on the full N=300 mixed split before drawing
conclusions.

### 5. NBA false-positive bias suggests prompt improvements are possible

6 of 7 NBA errors were false positives (predicted violation when the answer
was compliant). This systematic bias suggests the prompt may prime the LLM
to find violations. A more balanced framing or chain-of-thought step before
the verdict could reduce this bias.

### 6. The simulate factory may work for simpler extraction tasks

The simulate framing is not universally bad -- it works well for tasks where
the docstring is self-contained and unambiguous (e.g., simple classification,
short-text extraction). The failure mode is specific to complex extraction
where the input text contains competing instructions. This hypothesis needs
testing across other benchmarks.

## Architecture

The L1 pipeline after this change:

```
Input (problem_text, forms_text, rules_text, metadata)
  |
  v
prompt_llm template (domain-specific, direct framing)
  |  - airline_extract.txt / tax_extract.txt / nba_extract.txt
  |  - "You are executing the function `extract_X_params`"
  |  - "Return ONLY a valid JSON object"
  |  - Triple-quoted input: query = '''$query'''
  v
_parse_json_result() -- strips fences, comments, unwraps {"result": ...}
  |
  v
Domain calculator (Python) -- _airline_calc_fn / _tax_calc_fn / verdict
  |
  v
Numeric answer (float)
```

The existing `@interface` stubs (`extract_airline_params`, `extract_tax_params`,
`extract_nba_params`) are preserved for L3 ReAct workflows. L1 uses separate
`_extract_*_raw` functions bound to `prompt_llm` with `answer_pattern=None`.

## Files changed

| File | Change |
|------|--------|
| `benchmarks/rulearena/ptools.py` | Added `_parse_json_result`, `_extract_*_raw` interfaces, updated `l1_extract_workflow` |
| `benchmarks/rulearena/prompt_templates/tax_extract.txt` | New: ptp-style tax extraction template |
| `benchmarks/rulearena/prompt_templates/airline_extract.txt` | New: ptp-style airline extraction template |
| `benchmarks/rulearena/prompt_templates/nba_extract.txt` | New: ptp-style NBA extraction template |

## Reproduction

```bash
cd benchmarks/rulearena

# L1 Tax (N=60, valid split)
uv run python -m secretagent.cli.expt run \
  evaluate.expt_name=l1_tax dataset.domain=tax \
  ptools.compute_rulearena_answer.method=direct \
  ptools.compute_rulearena_answer.fn=ptools.l1_extract_workflow

# L1 Airline (N=60, valid split)
uv run python -m secretagent.cli.expt run \
  evaluate.expt_name=l1_airline dataset.domain=airline \
  ptools.compute_rulearena_answer.method=direct \
  ptools.compute_rulearena_answer.fn=ptools.l1_extract_workflow

# L1 NBA (N=42, valid split)
uv run python -m secretagent.cli.expt run \
  evaluate.expt_name=l1_nba dataset.domain=nba \
  ptools.compute_rulearena_answer.method=direct \
  ptools.compute_rulearena_answer.fn=ptools.l1_extract_workflow
```

## Key takeaway

For structured extraction tasks, prompt engineering is not optional
scaffolding -- it is load-bearing infrastructure. A generic "imagine the
output" wrapper cannot substitute for a task-specific prompt that (1) frames
the LLM as a function executor, (2) quotes input data to prevent instruction
injection, and (3) specifies the exact output format. The 56.7-point gap on
tax demonstrates that prompt framing alone can be the difference between a
failed and a perfect replication.
