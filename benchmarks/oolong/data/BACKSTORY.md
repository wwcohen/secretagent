# Oolong-Synth Dataset: Context & Reference

A summary for agents and developers working with the Oolong benchmark.

---

## What is Oolong?

**Oolong** is a benchmark for evaluating long-context reasoning and aggregation capabilities of large language models (Bertsch et al., 2025). It tests whether models can aggregate information across very long contexts—counting, comparing, and reasoning—rather than guessing or approximating.

**Paper:** [arxiv.org/abs/2511.02817](https://arxiv.org/abs/2511.02817)

---

## Oolong-Synth Overview

Oolong-synth is the main synthetic benchmark. It uses data from 10 NLP datasets, each with labeled examples formatted as in-context lines. Models must answer questions about aggregate statistics across these examples.

**Source datasets:** IMDB, AgNews, Yahoo, MultiNLI, TREC, spam, metaphors, formality, negation, app_reviews

---

## Data Splits

| Split      | Total Examples | Per Context Length |
|-----------|----------------|---------------------|
| Training  | 0              | N/A (evaluation-only benchmark) |
| Validation| 1,300          | 100 per length      |
| Test      | 5,200          | 400 per length      |

**Total:** 6,500 examples across validation and test.

---

## Context Lengths

13 context lengths: **1K, 2K, 4K, 8K, 16K, 32K, 64K, 128K, 256K, 512K, 1M, 2M, 4M** tokens.

---

## Schema (Per Example)

| Field                          | Type   | Description |
|--------------------------------|--------|-------------|
| `id`                           | int64  | Unique example ID |
| `context_window_id`            | int64  | ID of the context window (shared across multiple questions) |
| `context_len`                  | int64  | Token length (e.g., 16384) |
| `dataset`                      | string | Source dataset (imdb, metaphors, negation, etc.) |
| `context_window_text`          | string | Full context **without** labels |
| `context_window_text_with_labels` | string | Same context with `\|\| Label: <label>` appended to each data line |
| `question`                     | string | Question to answer |
| `answer`                       | string | Gold answer (e.g., `"['correct']"`, `"['42']"`) |
| `task_group`                   | string | `counting`, `user`, or `timeline` |
| `task`                         | string | e.g., `TASK_TYPE.MOST_FREQ`, `TASK_TYPE.RELATIVE_FREQ` |
| `answer_type`                  | string | e.g., `ANSWER_TYPE.LABEL`, `ANSWER_TYPE.NUMERIC` |
| `input_subset`                 | string | `"True"` or `"False"` |
| `num_labels`                   | int64  | Number of label classes in the context |

---

## Context Text Formats

**`context_window_text`** (no labels):
```
Date: May 30, 2023 || User: 81306 || Instance: See the sun far off...
```

**`context_window_text_with_labels`** (with labels):
```
Date: May 30, 2023 || User: 81306 || Instance: See the sun far off... || Label: incorrect
```

Use `context_window_text` for the harder setting; use `context_window_text_with_labels` when labels are allowed.

---

## Label Sets

Each `context_window_id` has a fixed set of labels (e.g., `['correct', 'incorrect']`, `['positive', 'negative']`).

**To extract labels** from `context_window_text_with_labels`:
```python
labels = set()
for line in text.split("\n"):
    if "|| Label: " in line:
        label = line.split("|| Label: ")[-1].strip()
        if label:
            labels.add(label)
label_set = sorted(labels)
```

---

## Task Types

- **Counting:** Most/least common label, counts, relative frequency
- **Temporal:** Dates, before/after, month-level patterns
- **User-based:** User frequency, subsets, per-user stats

---

## Evaluation

- Official scoring compares model output to the `answer` field (exact match, numeric partial credit, date parsing)
- There is no standalone scoring script that accepts pre-generated predictions

---

## Notes

- Same `context_window_id` → multiple questions over the same context.
- **Oolong-real** is a separate D&D (Critical Role) benchmark; this document covers **Oolong-synth** only.
- JSONL files can be large (GB for full test); use HuggingFace format or stream line-by-line for memory efficiency.
