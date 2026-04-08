"""Interfaces for Oolong benchmark.

Replace this module with your tools from your previous experiment.
Each @interface stub should have a docstring and type hints.
"""

from pathlib import Path
from typing import Any, Dict, List

from secretagent import config
from secretagent.core import interface

import pipeline_helpers as ph

@interface
def answer_question(
    context: str,
    question: str,
    context_window_id: int | None = None,
    dataset: str = "",
    context_len: int | None = None,
) -> str:
    """Zero-shot baseline: answer directly from the raw context window.

    Inputs:
    - context: full context-window text (mixed data entries + instructions/metadata)
    - question: natural-language question about the context

    Behavior:
    - Read the context and return one final answer string.
    - Do not use external knowledge; rely only on context + question.
    - Follow the question's expected answer format when possible.
    """
    if context_window_id is None:
        raise ValueError("answer_question requires context_window_id for cached workflow")

    cid = int(context_window_id)
    payload = ph.get_run_window_payload(cid)

    split = str(config.require("dataset.split"))
    context_len_cfg = config.get("dataset.context_len")
    context_len_cfg = int(context_len_cfg) if context_len_cfg is not None else None
    use_window_cache = bool(config.get("oolong.enable_window_cache", True))
    cache_root = Path(__file__).resolve().parent / str(
        config.get("oolong.window_cache_dir") or "window_cache"
    )

    model_slug: str | None = None
    if bool(config.get("oolong.scope_caches_to_model", True)):
        model_slug = ph.filesystem_slug(str(config.require("llm.model")))

    cache_path = ph.window_cache_path(
        cache_root, split, context_len_cfg, cid, model_slug=model_slug
    )
    if payload is None and use_window_cache:
        payload = ph.load_window_cache(cache_path)

    if payload is None:
        effective_context_len = (
            int(context_len)
            if context_len is not None
            else int(config.get("oolong.assumed_context_len_for_batching") or 1024)
        )
        payload = ph.build_window_payload(
            context=context,
            dataset=str(dataset),
            context_len=effective_context_len,
            infer_fn=infer_context_schema,
            classify_fn=classify_entry_batch,
            token_budget_per_call=int(config.get("oolong.token_budget_per_call") or 1280),
            schema_line_limit=int(config.get("oolong.schema_infer_line_limit") or 20),
            schema_retries=int(config.get("oolong.schema_retries") or 4),
            schema_backoff=float(config.get("oolong.schema_backoff") or 1.7),
            classify_retries=int(config.get("oolong.classify_retries") or 10),
            classify_backoff=float(config.get("oolong.classify_backoff") or 1.5),
        )
        if use_window_cache:
            ph.save_window_cache(cache_path, payload)

    label_set, records = ph.label_set_and_records_for_answer(payload)
    # Positional call ensures PoT inject_args maps values into sandbox variables.
    resp = answer_from_cached_records(question, label_set, records)
    return ph.extract_final_answer(resp)

@interface
def infer_context_schema(
    context_window_text: str | List[str],
) -> Dict[str, Any]:
    """
    The input text has text similar to data entries in addition to the description of the data
    Infer the classification labels, they are explicity specified in the context
    Infer a regular expression which helps with the schema/metadata for this context
    CAPTURE GROUPS IN REGEX

    Return EXACT JSON:
    {
      "result": {
        "label_set": ["inferred_label_1", "inferred_label_2"], #classification labels
        "regular_expression": "regex string for parsing data-entry lines" #regex which captures schema groups for data entry lines (do not match anything with any description like lines)
      }
    }
    """
    ...

@interface
def classify_entry_batch(
    entry_lines: List[str],
    label_set: List[str],
    batch_start_idx: int = 0,
    num_entry_lines: int | None = None,
) -> Dict[str, Any]:
    """
    Classify each provided data-entry line into exactly one label from label_set.

    Inputs:
    - num_entry_lines: number of entry lines (must equal len(entry_lines)); use to ensure you output exactly this many records
    - entry_lines: list of data-entry lines (no headers/instructions)
    - label_set: allowed canonical labels (e.g., ["correct", "incorrect"])
    - batch_start_idx: global starting index for this batch

    Requirements:
    - Classify each entry line into exactly one label from label_set.
    - Preserve input order.
    - Output count MUST equal len(entry_lines), with no omissions.
    - Output one record per input line.
    - idx must be batch_start_idx + line_position for every record.
    - Every idx in [batch_start_idx, batch_start_idx + len(entry_lines) - 1] must appear exactly once.
    - Do not skip, merge, duplicate, or invent records.
    - label must be lowercase and one of label_set.
    - If uncertain, still return a valid label from label_set (do not drop the record).

    Return EXACT JSON:
    {
      "result": {
        "records": [
          {"idx": 44, "label": "positive"},
          {"idx": 45, "label": "negative"}
        ],
        "input_count": <MUST EQUAL len(entry_lines)>,
        "output_count": <MUST EQUAL len(entry_lines)>,
        "label_set_used": ["positive", "negative"]
      }
    }
    """
    ...

@interface
def answer_from_cached_records(
    question: str,
    label_set: List[str],
    records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Answer the question using only the provided classified records.

    Inputs:
    - question: The natural-language query to answer.
    - label_set: The allowed canonical labels for entries in this context.
    - records: A list of classified data entries. Each item has:
      - idx: integer index (order in context)
      - date: date string for the entry (e.g., "May 30, 2023"), or null if unavailable
      - user_id: integer user id, or null if unavailable
      - label: one canonical label assigned to that entry

    Important:
    - Each record corresponds to exactly one entry_text and exactly one label.
    - Each record.label must be one of label_set.
    - Use only information in question, records, label_set, and schema_metadata.
    - Do not use external knowledge or assumptions.
    - Respect record order when order matters for the question.

    Task:
    - Reason over the records (and labels) to compute the exact answer.
    - Follow question-specific formatting instructions if present.
  
    Code-execution constraints:
    - Do NOT use any `import ...` statements.
    - Do NOT use `sum(...)` (and avoid other built-in aggregators like `map`, `filter`).
    - Prefer explicit `for` loops and integer counters.
    - Avoid clever one-liners; write straightforward step-by-step code.

    Implementation hint (when the question asks for "most common" label):
    - Compute label frequencies by looping over `records`.
    - For each label in `label_set`, maintain a separate integer count.
    - Choose the label with the largest count.
    - If there is a tie, choose label_set[0].

    Output format rules:
    - ANSWER_TYPE.LABEL       -> "Label: <label>"
    - ANSWER_TYPE.NUMERIC     -> "Answer: <integer>"
    - ANSWER_TYPE.USER        -> "User: <integer>"
    - ANSWER_TYPE.DATE        -> "Date: YYYY-MM-DD" (or parseable date string)
    - ANSWER_TYPE.MONTH_YEAR  -> "Answer: <Month YYYY>"
    - ANSWER_TYPE.COMPARISON  -> "Answer: <more common than|less common than|same frequency as>"

    Return EXACT JSON:
    {
      "result": {
        "final_answer": "<formatted answer string>"
      }
    }
    """
    ...
