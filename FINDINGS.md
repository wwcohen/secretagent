# Findings

## 2026-04-30: NBA Benchmark — Framework Bug Fixes and PoT Analysis

Three infrastructure bugs were identified from NBA benchmark analysis and fixed in `src/secretagent/implement/core.py`.

### Bug 1: PoT state poisoning (CRITICAL)

**Symptom**: PoT scored 2.2% (1/46) on NBA. 24/46 cases crashed with `'ellipsis' object has no attribute 'verdict'`.

**Root cause**: smolagents' `LocalPythonExecutor` shares mutable `custom_tools` dict and `state` dict across calls. When LLM-generated code redefines a tool as a stub (`def extract_nba_params(...): ...`), it permanently replaces the real tool wrapper. All subsequent calls then get `Ellipsis` instead of real results. 4/46 generated code blocks triggered this; once poisoned, all later cases broke.

**Fix**: Save/restore `custom_tools` via `finally` block and reset `state = {}` before each execution in `PoTFactory.__call__`. Three lines added. Verified via `smolagents` executor that `state = {}` is safe — smolagents re-populates internal tracking keys on each execution.

### Bug 2: SimulateFactory.parse_output missing numeric fallback (MODERATE)

**Symptom**: 5/46 structured_baseline cases failed with `ValueError: cannot find final answer`. The LLM returned bare `"1.0"` (4 output tokens) without `<answer>` tags.

**Root cause**: `parse_output` had fallbacks for dict/list/BaseModel and str return types, but no fallback for int/float when `<answer>` tags are missing.

**Fix**: Added numeric fallback after the str fallback: `_coerce_numeric(text.strip(), return_type)`. This only succeeds when the entire stripped output IS a number — no regex heuristic. Design rationale: digits are low-signal (appear in reasoning), unlike `{}`/`[]` delimiters used for dict/list extraction, so the numeric fallback must be strict to avoid silent wrong answers. Python's `float()`/`int()` rejects trailing periods, prose with numbers, etc.

### Bug 3: PoT prompt lacks tool return type schemas (MODERATE)

**Symptom**: 27/33 verdict usages in generated code misuse the type (e.g., `result.verdict == "violation"` — verdict is bool, not str). 8/46 hallucinated field names (`result.violating_operation` instead of `result.illegal_operation`).

**Root cause**: PoT's `create_prompt` included tool stubs but not their pydantic return type schemas. The LLM saw `-> NbaResult` but had to guess field names and types.

**Fix**: In `PoTFactory.create_prompt`, append `_format_pydantic_schema(return_type)` for each tool's return type. The function already existed (used by simulate prompts) and returns `""` for non-pydantic types.

### Post-fix results: NBA PoT

After all three fixes, PoT with DeepSeek V3.1 remained at 2.2% (1/46). Analysis of the 46 new (post-fix) cached responses showed three remaining failure categories:
- **21 cases**: dict-style access on pydantic (`result["verdict"]` instead of `result.verdict`) — smolagents interpreter doesn't support this
- **20 cases**: raw NbaResult returned instead of float — no verdict-to-float conversion
- **9 cases**: tool called with wrong argument count (2 args instead of 1)

These are model-level code generation failures, not framework bugs. Verification: running the same fixed pipeline with `gemini/gemini-2.5-flash` on 25 test cases yielded **44% correct** (11/25) vs 2.2% with V3.1. The 20x improvement from only changing the model confirms the framework is working correctly and the remaining gap is model capability.

**Implication for the paper**: PoT strategy effectiveness is highly model-dependent. Structured baseline achieves 58.7% with a cheap model; PoT needs a strong model to be competitive — a genuine Pareto tradeoff that the optimization framework can exploit.
