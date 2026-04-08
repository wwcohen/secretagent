"""Minimal helpers for Oolong two-phase pipeline.

Phase 1 (per context window): infer schema -> classify entries -> compact records (to save tokens).
Phase 2 (per question row): answer from cached compact records.
"""

from __future__ import annotations

import json
import re
import time
from math import ceil
from pathlib import Path
from typing import Any, Callable
from tqdm import tqdm

_RUN_WINDOW_PAYLOADS: dict[int, dict[str, Any]] | None = None


def install_run_window_payloads(by_cid: dict[int, dict[str, Any]]) -> None:
    """Install in-memory phase-1 payloads for this run."""
    global _RUN_WINDOW_PAYLOADS
    _RUN_WINDOW_PAYLOADS = by_cid


def get_run_window_payload(cid: int) -> dict[str, Any] | None:
    """Return an in-memory payload for context_window_id if available."""
    if _RUN_WINDOW_PAYLOADS is None:
        return None
    return _RUN_WINDOW_PAYLOADS.get(int(cid))


def clear_run_window_payloads() -> None:
    """Clear in-memory phase-1 payloads after run completion."""
    global _RUN_WINDOW_PAYLOADS
    _RUN_WINDOW_PAYLOADS = None


def unwrap_result(payload: Any) -> dict[str, Any]:
    """Return payload['result'] when present, else normalize to a dict."""
    if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
        return payload["result"]
    if isinstance(payload, dict):
        return payload
    return {"raw": payload}


def extract_final_answer(resp: Any) -> str:
    """Extract final answer string from answer_from_cached_records response."""
    if isinstance(resp, dict) and isinstance(resp.get("result"), dict):
        if "final_answer" in resp["result"]:
            return str(resp["result"]["final_answer"])
    if isinstance(resp, dict) and "final_answer" in resp:
        return str(resp["final_answer"])
    return str(resp)


def infer_schema_with_retry(
    infer_fn: Callable[..., Any],
    context: str,
    *,
    line_limit: int,
    retries: int,
    backoff: float,
) -> tuple[dict[str, Any], str | None]:
    """Call infer schema with retries; return (schema, error)."""
    head = "\n".join(context.split("\n")[:line_limit])
    for attempt in range(1, retries + 1):
        try:
            return unwrap_result(infer_fn(context_window_text=head)), None
        except Exception as e:
            if attempt == retries:
                return {}, f"{type(e).__name__}: {e}"
            time.sleep(backoff ** (attempt - 1))
    return {}, "unknown"


def extract_entry_lines(context: str, regex: str) -> tuple[list[str], bool, str | None]:
    """Return context lines matching regex; also report regex validity."""
    if not regex.strip():
        return [], True, None
    try:
        pat = re.compile(regex)
    except re.error as e:
        return [], False, str(e)
    lines = [ln for ln in context.split("\n") if ln.strip()]
    entries = [ln for ln in lines if pat.fullmatch(ln) or pat.search(ln)]
    return entries, True, None


def compute_batch_size(num_entries: int, context_len: int, token_budget_per_call: int) -> int:
    """Notebook-style heuristic for classify_entry_batch chunk size."""
    raw = max(1, ceil((num_entries / max(context_len, 1)) * token_budget_per_call))
    return max(1, round(raw / 5) * 5)


def _canonical_label(label: str, label_set: list[str]) -> str:
    """Map model label to canonical label from label_set when possible."""
    lbl = str(label).strip().lower()
    canon = {str(x).lower().replace(" ", "_"): str(x) for x in label_set}
    if lbl in canon:
        return canon[lbl]
    lbl2 = lbl.replace(" ", "_")
    return canon.get(lbl2, str(label))


_MAX_SPLIT_DEPTH = 32


def _records_from_classify_response(
    out: Any,
    b_start: int,
    batch: list[str],
    label_set: list[str],
) -> list[dict[str, Any]]:
    """Parse model JSON into record dicts or raise if count/idx/label invalid."""
    recs = unwrap_result(out).get("records", [])
    if len(recs) != len(batch):
        raise ValueError(f"count mismatch: {len(recs)} != {len(batch)}")
    allowed = {x.lower() for x in label_set}
    out_list: list[dict[str, Any]] = []
    for j, r in enumerate(recs):
        idx = int(r.get("idx", b_start + j))
        if idx != b_start + j:
            raise ValueError(f"idx mismatch at {j}")
        label = _canonical_label(r.get("label", ""), label_set)
        if str(label).lower() not in allowed:
            raise ValueError(f"invalid label: {label}")
        out_list.append(
            {"idx": idx, "entry_text": r.get("entry_text") or batch[j], "label": label}
        )
    return out_list


def _classify_chunk_divided(
    classify_fn: Callable[..., Any],
    b_start: int,
    batch: list[str],
    label_set: list[str],
    *,
    single_retries: int,
    backoff: float,
    depth: int,
    stats: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """|batch|>1: up to single_retries chunk calls then binary split; size-1: same retries (notebook parity)."""
    if not batch:
        return []
    if depth > _MAX_SPLIT_DEPTH:
        raise RuntimeError("classify split depth exceeded")

    if len(batch) == 1:
        last_err: Exception | None = None
        for attempt in range(single_retries):
            try:
                out = classify_fn(
                    entry_lines=batch,
                    label_set=label_set,
                    batch_start_idx=b_start,
                    num_entry_lines=1,
                )
                return _records_from_classify_response(out, b_start, batch, label_set)
            except Exception as e:
                last_err = e
                if stats is not None:
                    stats["classify_leaf_retries"] = stats.get("classify_leaf_retries", 0) + 1
            time.sleep(backoff**attempt)
        if last_err is not None:
            raise last_err
        raise RuntimeError("classify failed for single-line batch (no successful attempt)")

    for attempt in range(single_retries):
        try:
            out = classify_fn(
                entry_lines=batch,
                label_set=label_set,
                batch_start_idx=b_start,
                num_entry_lines=len(batch),
            )
            return _records_from_classify_response(out, b_start, batch, label_set)
        except Exception:
            if stats is not None:
                stats["classify_chunk_retries"] = stats.get("classify_chunk_retries", 0) + 1
        time.sleep(backoff**attempt)

    if stats is not None:
        stats["classify_splits"] = stats.get("classify_splits", 0) + 1
    m = len(batch) // 2
    left = _classify_chunk_divided(
        classify_fn,
        b_start,
        batch[:m],
        label_set,
        single_retries=single_retries,
        backoff=backoff,
        depth=depth + 1,
        stats=stats,
    )
    right = _classify_chunk_divided(
        classify_fn,
        b_start + m,
        batch[m:],
        label_set,
        single_retries=single_retries,
        backoff=backoff,
        depth=depth + 1,
        stats=stats,
    )
    return left + right


def classify_batches_with_retry(
    classify_fn: Callable[..., Any],
    entry_lines: list[str],
    label_set: list[str],
    *,
    batch_size: int,
    retries: int,
    backoff: float,
    classify_stats: dict[str, int] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Classify entry lines in coarse chunks; each chunk uses recursive split on failure.

    Optional ``classify_stats`` is incremented: classify_splits, classify_leaf_retries,
    classify_chunk_retries (mutated in place for this window).
    """
    merged: dict[int, dict[str, Any]] = {}
    errors: list[dict[str, Any]] = []

    chunks = [entry_lines[i : i + batch_size] for i in range(0, len(entry_lines), batch_size)]
    for i, chunk in enumerate(tqdm(chunks, desc="classify_batches", leave=False)):
        b_start = sum(len(c) for c in chunks[:i])
        try:
            recs = _classify_chunk_divided(
                classify_fn,
                b_start,
                chunk,
                label_set,
                single_retries=retries,
                backoff=backoff,
                depth=0,
                stats=classify_stats,
            )
            for r in recs:
                merged[r["idx"]] = r
        except Exception as e:
            errors.append({"b_start": b_start, "error": str(e)})

    records = [merged[k] for k in sorted(merged)]
    return records, errors


_GOLD_LABEL_LINE = re.compile(r"^(.*)\s+\|\|\s+Label:\s*([^\|]+?)\s*$")


def extract_gold_labels_in_order(context_with_labels: str) -> list[str]:
    """Gold label sequence from ``context_window_text_with_labels`` (notebook parity)."""
    gold_labels: list[str] = []
    for ln in str(context_with_labels).split("\n"):
        m = _GOLD_LABEL_LINE.match(ln.strip())
        if m:
            gold_labels.append(m.group(2).strip())
    return gold_labels


def classification_accuracy_vs_gold(
    compact_records: list[dict[str, Any]],
    context_with_labels: str,
) -> dict[str, Any]:
    """Per-window classification metrics vs gold ``|| Label:`` lines (oolong notebook)."""
    gold_labels = extract_gold_labels_in_order(context_with_labels)
    pred_by_idx: dict[int, str] = {}
    for r in compact_records:
        if r.get("idx") is None:
            continue
        pred_by_idx[int(r["idx"])] = str(r.get("label", ""))

    def norm(s: str) -> str:
        return str(s).strip().lower()

    matched_idxs = [i for i in range(len(gold_labels)) if i in pred_by_idx]
    correct = sum(
        1 for i in matched_idxs if norm(pred_by_idx[i]) == norm(gold_labels[i])
    )
    n_gold = len(gold_labels)
    n_matched = len(matched_idxs)
    return {
        "accuracy_on_matched": correct / n_matched if n_matched else 0.0,
        "accuracy_over_gold": correct / n_gold if n_gold else 0.0,
        "correct_on_matched": correct,
        "matched_records": n_matched,
        "gold_records": n_gold,
    }


def compact_records(records: list[dict[str, Any]], regex: str) -> list[dict[str, Any]]:
    """Convert records to compact {idx,date,user_id,label} schema for answer ptool."""
    out: list[dict[str, Any]] = []
    try:
        pat = re.compile(regex) if regex else None
    except re.error:
        pat = None

    for r in records:
        idx = r.get("idx")
        label = r.get("label", "")
        entry_text = r.get("entry_text", "")
        date = None
        user_id = None

        if pat:
            m = pat.match(entry_text)
            if m:
                gd = m.groupdict() if m.lastindex else {}
                if gd:
                    date = gd.get("date")
                    user_id = gd.get("user_id")
                else:
                    gs = m.groups()
                    date = gs[0] if len(gs) > 0 else None
                    user_id = gs[1] if len(gs) > 1 else None
                if user_id is not None and str(user_id).isdigit():
                    user_id = int(user_id)

        out.append({"idx": idx, "date": date, "user_id": user_id, "label": label})
    return out


def build_window_payload(
    *,
    context: str,
    dataset: str,
    context_len: int,
    infer_fn: Callable[..., Any],
    classify_fn: Callable[..., Any],
    token_budget_per_call: int,
    schema_line_limit: int,
    schema_retries: int,
    schema_backoff: float,
    classify_retries: int,
    classify_backoff: float,
) -> dict[str, Any]:
    """Build one cached window payload for phase-2 answering."""
    schema, schema_error = infer_schema_with_retry(
        infer_fn,
        context,
        line_limit=schema_line_limit,
        retries=schema_retries,
        backoff=schema_backoff,
    )
    label_set = schema.get("label_set", [])
    if not isinstance(label_set, list):
        label_set = []
    label_set = [str(x).strip().lower() for x in label_set]
    regex = str(schema.get("regular_expression", "") or "")

    entry_lines, regex_valid, regex_error = extract_entry_lines(context, regex)
    batch_size = 0
    batch_errors: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    classify_stats: dict[str, int] = {}

    if regex_valid and entry_lines:
        batch_size = compute_batch_size(len(entry_lines), context_len, token_budget_per_call)
        records, batch_errors = classify_batches_with_retry(
            classify_fn,
            entry_lines,
            label_set,
            batch_size=batch_size,
            retries=classify_retries,
            backoff=classify_backoff,
            classify_stats=classify_stats,
        )

    compact = compact_records(records, regex)
    return {
        "dataset": dataset,
        "schema": {"label_set": label_set, "regular_expression": regex},
        "classification": {
            "records": compact,
            "matched_line_count": len(entry_lines),
            "label_set_used": label_set,
            "batch_size": batch_size,
        },
        "debug": {
            "schema_error": schema_error,
            "regex_valid": regex_valid,
            "regex_error": regex_error,
            "entry_line_count": len(entry_lines),
            "batch_errors": batch_errors,
            "classify_splits": classify_stats.get("classify_splits", 0),
            "classify_leaf_retries": classify_stats.get("classify_leaf_retries", 0),
            "classify_chunk_retries": classify_stats.get("classify_chunk_retries", 0),
        },
    }


def filesystem_slug(model_id: str, *, max_len: int = 120) -> str:
    """Stable, path-safe directory name for an LLM id (per-model cache namespaces)."""
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(model_id).strip())
    s = re.sub(r"_+", "_", s).strip("_")
    return (s or "unknown_model")[:max_len]


def window_cache_path(
    cache_root: Path,
    split: str,
    context_len: int | None,
    cid: int,
    *,
    model_slug: str | None = None,
) -> Path:
    """Path for per-window cache JSON.

    When ``model_slug`` is set, namespaces cache by model so a new backend does not
    reuse another model's infer/classify artifacts.
    """
    shard = f"{context_len}" if context_len is not None else "flat"
    p = Path(cache_root)
    if model_slug:
        p = p / model_slug
    return p / split / shard / f"{cid}.json"


def load_window_cache(path: Path) -> dict[str, Any] | None:
    """Load cached window payload if present and valid."""
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_window_cache(path: Path, payload: dict[str, Any]) -> None:
    """Save per-window payload to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def label_set_and_records_for_answer(cached: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    """Extract (label_set, compact_records) from cached payload."""
    schema = cached.get("schema", {})
    classification = cached.get("classification", {})
    label_set = schema.get("label_set") or classification.get("label_set_used") or []
    records = classification.get("records") or []
    if not isinstance(label_set, list):
        label_set = []
    if not isinstance(records, list):
        records = []
    return label_set, records
