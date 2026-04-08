# Code changes: Oolong `rollout` + PoT `step_info` (full prompt / LLM output)

This note documents edits that (1) persist per-case **rollout** recordings when `evaluate.record_details` is true for the Oolong benchmark, and (2) store **full PoT prompt and raw LLM completion** in each Program-of-Thought `record` entry.

Line numbers refer to the **current** tree after these changes (as of this file’s creation).

---

## 1. `benchmarks/oolong/expt.py` — `OolongEvaluator.measure`

### Removed (conceptual)

The method previously **returned a single `dict(...)` literal** in one shot and **never** attached `rollout`, so `evaluate.record_details` had no effect for Oolong (unlike the base `Evaluator.measure` in `src/secretagent/evaluate.py`).

Equivalent old tail was:

```python
        return dict(
            predicted_output=predicted_output,
            expected_output=example.expected_output,
            answer_attempts=answer_attempts,
            **metrics,
            **llm_usage_stats,
        )
```

### Added / replaced (current lines)

| Lines | Change |
|-------|--------|
| **179–185** | Build the result into a variable `row = dict(...)` with the same keys as before (`predicted_output`, `expected_output`, `answer_attempts`, merged `**metrics`, `**llm_usage_stats`). |
| **186–187** | If `config.get("evaluate.record_details")` is truthy, set `row["rollout"] = records` (the list from `record.recorder()` for that case). |
| **188** | `return row` instead of returning the dict literal directly. |

**Location:** class `OolongEvaluator`, method `measure`, immediately after the `metrics = ...` / `compare_predictions` branch and before `def measurements`.

---

## 2. `src/secretagent/implement/core.py` — `PoTFactory.__call__`

### Removed (conceptual)

**On exception** inside the `try` that parses code and runs the sandbox:

```python
                record.record(
                    func=interface.name, args=args, kw=kw,
                    output=f'**exception**: {ex}', stats=stats,
                    step_info=dict(generated_code=llm_output))
```

**On success:**

```python
            record.record(
                func=interface.name, args=args, kw=kw, output=answer, stats=stats,
                step_info=dict(generated_code=generated_code))
```

The key `generated_code` in `step_info` is **no longer used** for PoT (replaced by the structure below).

### Added / replaced (current lines)

| Lines | Change |
|-------|--------|
| **306–316** | **Exception path:** `record.record(..., step_info=dict(prompt=prompt, llm_output=llm_output, extracted_python=None, error=str(ex)))` |
| **320–327** | **Success path:** `record.record(..., step_info=dict(prompt=prompt, llm_output=llm_output, extracted_python=generated_code))` |

**Semantics:**

- `prompt` — full string passed to `llm_util.llm` for this PoT call.
- `llm_output` — raw model completion text.
- `extracted_python` — substring matched by the fenced-code regex (same value as former success `generated_code`); `None` on failure before extraction succeeds.
- `error` — only on the exception path (`str(ex)`).

**Location:** class `PoTFactory`, method `__call__`, after `llm_output, stats = llm_util.llm(...)` and around the `try` / `except` that calls `_extract_answer` and `self.python_executor`.

---

## 3. `tests/test_pot.py` — `test_pot_records_generated_code`

### Removed (conceptual)

```python
    assert 'inc' in pot_entries[0]['step_info']['generated_code']
    assert 'final_answer' in pot_entries[0]['step_info']['generated_code']
```

### Added / replaced (current lines)

| Lines | Change |
|-------|--------|
| **173–176** | Assign `si = pot_entries[0]['step_info']`, assert `'prompt'` and `'llm_output'` are present, assert `'inc'` and `'final_answer'` appear in `si['extracted_python']`. |

**Location:** function `test_pot_records_generated_code`, assertions after `assert 'step_info' in pot_entries[0]`.

---

## Summary

| File | Purpose |
|------|--------|
| `expt.py` | Oolong results rows gain a `rollout` key when `evaluate.record_details` is true, so `results.jsonl` can include full per-interface call lists for phase 2. |
| `implement/core.py` | PoT rollouts include reproducible **prompt + raw LLM text** on every call, not only extracted Python (and not only on failure). |
| `test_pot.py` | Tests updated for the new `step_info` field names. |

---

## Consumer hint

With `evaluate.record_details=true`, each line in `results.jsonl` may include `rollout`: a list of dicts. For phase-2 PoT, find entries with `func == "answer_from_cached_records"` and read `step_info["prompt"]`, `step_info["llm_output"]`, and `step_info["extracted_python"]`.
