"""Oolong benchmark experiment (minimal two-phase flow).

Phase 1: infer + classify once per unique context_window_id.
Phase 2: answer each question row from cached compact records.
"""

from __future__ import annotations

import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterator

import pandas as pd
import typer
from tqdm import tqdm

from secretagent import config, record
from secretagent.core import implement_via_config
import secretagent.implement.pydantic  # noqa: F401
from secretagent.dataset import Dataset, Case
from secretagent.evaluate import Evaluator

# Notebook / OOLong official scoring (parse model output, literal_eval gold, numeric soft score).
_EVAL_DIR = Path(__file__).resolve().parent / "src" / "eval"
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
from eval_helpers import synth_process_response  # noqa: E402

import pipeline_helpers as ph
import ptools


def _write_summary_json(
    csv_path: Path,
    df: pd.DataFrame,
    *,
    classification_accuracies_filename: str | None = None,
    classification_results_filename: str | None = None,
) -> Path:
    """Persist phase-2 run aggregates next to results.csv."""
    out = csv_path.parent / "summary.json"
    pred = df["predicted_output"].astype(str)
    n_exc = int(pred.str.startswith("**exception").sum())

    def fnum(series: pd.Series, *, how: str) -> float | None:
        if how == "mean":
            v = series.mean(skipna=True)
        else:
            v = series.sum(skipna=True)
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        return float(v)

    payload: dict[str, Any] = {
        "n_cases": int(len(df)),
        "n_exceptions": n_exc,
        "mean_correct": fnum(df["correct"], how="mean"),
        "mean_latency_seconds": fnum(df["latency"], how="mean"),
        "sum_latency_seconds": fnum(df["latency"], how="sum"),
        "mean_cost_usd": fnum(df["cost"], how="mean"),
        "sum_cost_usd": fnum(df["cost"], how="sum"),
        "results_csv": csv_path.name,
        "expt_name": config.get("evaluate.expt_name"),
    }
    if classification_accuracies_filename:
        payload["classification_accuracies_json"] = classification_accuracies_filename
    if classification_results_filename:
        payload["classification_results_json"] = classification_results_filename
    with open(out, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2)
        fp.write("\n")
    return out


def _write_classification_accuracies_json(
    run_dir: Path,
    body: dict[str, Any],
) -> Path:
    """Phase-1 classification vs gold labels (per window + aggregates)."""
    out = run_dir / "classification_accuracies.json"
    with open(out, "w", encoding="utf-8") as fp:
        json.dump(body, fp, indent=2)
        fp.write("\n")
    return out


def _write_classification_results_json(
    run_dir: Path,
    body: dict[str, Any],
) -> Path:
    """Full phase-1 payload per window (schema, classification records, debug)."""
    out = run_dir / "classification_results.json"
    with open(out, "w", encoding="utf-8") as fp:
        json.dump(body, fp, indent=2, ensure_ascii=False)
        fp.write("\n")
    return out


def _row_for_cid(rows: list[dict[str, Any]], cid: int) -> dict[str, Any]:
    for r in rows:
        if int(r["context_window_id"]) == cid:
            return r
    raise KeyError(f"context_window_id not in rows: {cid}")


def _classification_accuracy_rows(
    rows: list[dict[str, Any]],
    cids: list[int],
    by_cid: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    """One row per window: gold vs predicted compact labels (notebook ``evaluate_context_by_idx``)."""
    out: list[dict[str, Any]] = []
    for cid in cids:
        r0 = _row_for_cid(rows, cid)
        with_labels = str(r0.get("context_window_text_with_labels", "") or "")
        payload = by_cid[cid]
        recs = (payload.get("classification") or {}).get("records") or []
        if not isinstance(recs, list):
            recs = []
        m = ph.classification_accuracy_vs_gold(recs, with_labels)
        m["context_window_id"] = cid
        out.append(m)
    return out


class OolongEvaluator(Evaluator):
    """Scores answers with ``synth_process_response`` (same as synth notebook), not raw string equality."""

    def compare_predictions(self, predicted_output: Any, expected_output: Any) -> dict[str, Any]:
        pred = str(predicted_output).strip() if predicted_output is not None else ""
        gold = str(expected_output).strip() if expected_output is not None else ""
        return {"correct": float(pred == gold)}

    def measure(self, example: Case, interface: Any) -> dict[str, Any]:
        try:
            n_att = max(1, int(config.get("oolong.answer_retries", 6) or 6))
        except (TypeError, ValueError):
            n_att = 6
        with record.recorder() as records:
            predicted_output: Any | None = None
            last_ex: BaseException | None = None
            answer_attempts = 0
            for _ in range(n_att):
                answer_attempts += 1
                try:
                    predicted_output = interface(*example.input_args)  # type: ignore[misc]
                    break
                except Exception as ex:
                    last_ex = ex
            if predicted_output is None:
                predicted_output = f"**exception raised**: {last_ex}"
        llm_usage_stats = self.aggregate_usage_stats(records)
        dp = (example.metadata or {}).get("datapoint")
        pred_s = str(predicted_output)
        if (
            dp is not None
            and not pred_s.startswith("**exception")
            and isinstance(dp, dict)
        ):
            try:
                model = str(config.get("llm.model") or "")
                ev = synth_process_response(dp, pred_s, model)
                metrics = {
                    "correct": float(ev["score"]),
                    "eval_attempted_parse": ev["attempted_parse"],
                    "eval_parse_confidence": ev["parse_confidence"],
                }
            except Exception:
                metrics = {
                    "correct": 0.0,
                    "eval_attempted_parse": "",
                    "eval_parse_confidence": "error",
                }
        else:
            metrics = self.compare_predictions(predicted_output, example.expected_output)
        result = dict(
            predicted_output=predicted_output,
            expected_output=example.expected_output,
            answer_attempts=answer_attempts,
            **metrics,
            **llm_usage_stats,
        )
        if config.get("evaluate.record_details"):
            result["rollout"] = records
        return result

    def measurements(self, dataset: Dataset, interface: Any) -> Iterator[dict[str, Any]]:
        """Phase 2: optional thread pool (``oolong.max_workers``) for concurrent LLM calls."""
        cases = list(dataset.cases)
        workers = _oolong_max_workers()
        if workers <= 1:
            for example in tqdm(cases, desc="phase2_answer"):
                row = self.measure(example, interface)
                row["case_name"] = example.name
                yield row
            return

        def measure_idx(i: int, example: Case) -> tuple[int, dict[str, Any]]:
            row = self.measure(example, interface)
            row["case_name"] = example.name
            return i, row

        ordered: dict[int, dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(measure_idx, i, cases[i]) for i in range(len(cases))]
            for fut in tqdm(as_completed(futs), total=len(futs), desc="phase2_answer"):
                i, row = fut.result()
                ordered[i] = row
        for i in range(len(cases)):
            yield ordered[i]


def bench_root() -> Path:
    return Path(__file__).resolve().parent


def _apply_model_scoped_caches() -> str | None:
    """Namespace window + LLM caches by ``llm.model`` (see meeting_notes / Cohen on separate cache dirs)."""
    if not bool(config.get("oolong.scope_caches_to_model", True)):
        return None
    model = str(config.require("llm.model"))
    slug = ph.filesystem_slug(model)
    cache_dir = config.get("cachier.cache_dir")
    if cache_dir:
        p = Path(str(cache_dir))
        config.configure(cfg={"cachier": {"cache_dir": str(p / slug)}})
    return slug


_LOGFIRE_INITIALIZED = False


def _maybe_configure_logfire() -> None:
    """Send pydantic-ai Agent traces to Pydantic Logfire when ``logfire.enable`` is true.

    One-time setup per process. Does not affect ``simulate`` / ``program_of_thought`` (non-Agent) paths.
    See https://ai.pydantic.dev/logfire/
    """
    global _LOGFIRE_INITIALIZED
    if not bool(config.get("logfire.enable", False)):
        return
    if _LOGFIRE_INITIALIZED:
        return
    try:
        import logfire
    except ImportError as e:
        raise ImportError(
            "logfire is required when logfire.enable is true. Install with: uv add logfire"
        ) from e
    lf_kw: dict[str, Any] = {}
    sn = config.get("logfire.service_name")
    if sn:
        lf_kw["service_name"] = str(sn)
    st = config.get("logfire.send_to_logfire")
    if st is not None:
        lf_kw["send_to_logfire"] = bool(st)
    cons = config.get("logfire.console")
    if cons is not None:
        lf_kw["console"] = bool(cons)
    logfire.configure(**lf_kw)
    logfire.instrument_pydantic_ai()
    _LOGFIRE_INITIALIZED = True
    print("logfire: instrument_pydantic_ai() active (see https://logfire.pydantic.dev/)", flush=True)


def resolve_examples_path(split: str, context_len: int | None) -> Path:
    """Find shard JSONL/JSON, with raw_folder fallback; else flat split JSON."""
    data = bench_root() / "data"
    if context_len is not None:
        for base in (data, data / "raw_folder"):
            for ext in ("jsonl", "json"):
                p = base / split / f"{context_len}.{ext}"
                if p.is_file():
                    return p
        raise FileNotFoundError(
            f"Missing shard for split={split!r}, context_len={context_len!r}."
        )

    flat = data / f"{split}.json"
    if flat.is_file():
        return flat
    raise FileNotFoundError(f"Missing flat split file: {flat}")


def load_rows(split: str, context_len: int | None) -> list[dict[str, Any]]:
    """Load examples from JSONL or JSON."""
    path = resolve_examples_path(split, context_len)
    if path.suffix == ".jsonl":
        rows: list[dict[str, Any]] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    ex = data.get("examples", data)
    if isinstance(ex, list):
        return ex
    raise ValueError(f"Unsupported data format in {path}")


def prepare_rows(ctx: typer.Context) -> list[dict[str, Any]]:
    """Load config, read rows, then apply shuffle/subset."""
    config_file = bench_root() / "conf" / "conf.yaml"
    config.configure(yaml_file=config_file, dotlist=ctx.args)
    config.set_root(bench_root())

    split = str(config.require("dataset.split"))
    context_len = config.get("dataset.context_len")
    context_len = int(context_len) if context_len is not None else None

    rows = load_rows(split, context_len)

    seed = config.get("dataset.shuffle_seed")
    if seed is not None:
        rng = random.Random(int(seed))
        rng.shuffle(rows)

    n = config.get("dataset.n")
    if n is not None:
        rows = rows[: int(n)]

    return rows


def unique_cids(rows: list[dict[str, Any]]) -> list[int]:
    """Unique context_window_id values in first-seen order."""
    seen: set[int] = set()
    out: list[int] = []
    for r in rows:
        cid = int(r["context_window_id"])
        if cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


def context_for_cid(rows: list[dict[str, Any]], cid: int) -> tuple[str, str, int | None]:
    """Return (context_text, dataset_name, context_len) for a context window id."""
    for r in rows:
        if int(r["context_window_id"]) == cid:
            context = str(r.get("context_window_text", r.get("context", "")))
            dataset = str(r.get("dataset", ""))
            clen = r.get("context_len")
            clen = int(clen) if clen is not None else None
            return context, dataset, clen
    raise KeyError(f"context_window_id not found: {cid}")


def _oolong_max_workers() -> int:
    """Concurrent LLM workers for one run (phase 1 + phase 2). Default 1 = sequential."""
    try:
        n = int(config.get("oolong.max_workers", 1) or 1)
    except (TypeError, ValueError):
        n = 1
    return max(1, n)


def _phase2_enable_llm_cache() -> bool:
    """Whether phase-2 answer calls should use cachier (LLM cache)."""
    return bool(config.get("oolong.phase2_enable_llm_cache", True))


def _run_phase1(rows: list[dict[str, Any]]) -> tuple[str, list[int], dict[int, dict[str, Any]]]:
    """Run phase-1 window infer/classify and return payloads keyed by context_window_id."""
    split = str(config.require("dataset.split"))
    context_len_cfg = config.get("dataset.context_len")
    context_len_cfg = int(context_len_cfg) if context_len_cfg is not None else None
    model_slug = _apply_model_scoped_caches()
    implement_via_config(ptools, config.require("ptools"))

    cache_root = bench_root() / str(config.get("oolong.window_cache_dir") or "window_cache")
    use_cache = bool(config.get("oolong.enable_window_cache", True))
    token_budget = int(config.get("oolong.token_budget_per_call") or 1280)
    schema_line_limit = int(config.get("oolong.schema_infer_line_limit") or 20)
    schema_retries = int(config.get("oolong.schema_retries") or 4)
    schema_backoff = float(config.get("oolong.schema_backoff") or 1.7)
    classify_retries = int(config.get("oolong.classify_retries") or 10)
    classify_backoff = float(config.get("oolong.classify_backoff") or 1.5)
    default_context_len = int(config.get("oolong.assumed_context_len_for_batching") or 1024)
    max_workers = _oolong_max_workers()

    by_cid: dict[int, dict[str, Any]] = {}
    cids = unique_cids(rows)
    print(f"Phase 1 windows={len(cids)} rows={len(rows)} max_workers={max_workers}")

    def phase1_one(cid: int) -> tuple[int, dict[str, Any]]:
        cache_path = ph.window_cache_path(
            cache_root, split, context_len_cfg, cid, model_slug=model_slug
        )
        if use_cache:
            cached = ph.load_window_cache(cache_path)
            if cached is not None:
                return cid, cached

        context, dataset, row_context_len = context_for_cid(rows, cid)
        context_len = row_context_len if row_context_len is not None else default_context_len
        payload = ph.build_window_payload(
            context=context,
            dataset=dataset,
            context_len=context_len,
            infer_fn=ptools.infer_context_schema,
            classify_fn=ptools.classify_entry_batch,
            token_budget_per_call=token_budget,
            schema_line_limit=schema_line_limit,
            schema_retries=schema_retries,
            schema_backoff=schema_backoff,
            classify_retries=classify_retries,
            classify_backoff=classify_backoff,
        )
        if use_cache:
            ph.save_window_cache(cache_path, payload)
        return cid, payload

    if max_workers <= 1:
        for cid in tqdm(cids, desc="phase1"):
            c, payload = phase1_one(cid)
            by_cid[c] = payload
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(phase1_one, cid) for cid in cids]
            for fut in tqdm(as_completed(futures), total=len(futures), desc="phase1"):
                cid, payload = fut.result()
                by_cid[cid] = payload
    return split, cids, by_cid


def run_two_phase(rows: list[dict[str, Any]]) -> Path:
    """Execute full benchmark with phase-1 dedupe and phase-2 per-row answering."""
    _maybe_configure_logfire()
    context_len_cfg = config.get("dataset.context_len")
    context_len_cfg = int(context_len_cfg) if context_len_cfg is not None else None

    rd = Path(str(config.require("evaluate.result_dir")))
    config.configure(
        cfg={
            "evaluate": {
                "result_dir": str(rd / (str(context_len_cfg) if context_len_cfg is not None else "flat")),
            }
        },
    )

    split, cids, by_cid = _run_phase1(rows)

    ph.install_run_window_payloads(by_cid)
    cases: list[Case] = []
    for r in rows:
        cid = int(r["context_window_id"])
        cases.append(
            Case(
                name=str(r.get("id", f"{split}.{cid}")),
                input_args=(
                    str(r.get("context_window_text", r.get("context", ""))),
                    str(r.get("question", "")),
                    cid,
                    str(r.get("dataset", "")),
                    (int(r["context_len"]) if r.get("context_len") is not None else None),
                ),
                expected_output=r.get("answer", ""),
                metadata={
                    "context_window_id": cid,
                    "dataset": r.get("dataset"),
                    "datapoint": r,
                },
            )
        )

    dataset = Dataset(name="oolong", split=split, cases=cases)
    print("dataset:", dataset.summary())

    evaluator = OolongEvaluator()
    phase2_cache = _phase2_enable_llm_cache()
    print(f"Phase 2 llm cache enabled={phase2_cache}")
    try:
        with config.configuration(cachier={"enable_caching": phase2_cache}):
            csv_path = evaluator.evaluate(dataset, ptools.answer_question)
    finally:
        ph.clear_run_window_payloads()

    df = pd.read_csv(csv_path)
    print(df)
    print()
    print(df[["correct", "latency", "cost"]].mean())

    class_rows = _classification_accuracy_rows(rows, cids, by_cid)
    class_df = pd.DataFrame(class_rows)
    class_acc_json_name: str | None = None
    class_results_json_name: str | None = None
    if len(class_df):
        run_dir = csv_path.parent
        acc_csv = run_dir / "classification_accuracy.csv"
        class_df.to_csv(acc_csv, index=False)
        print()
        print("classification (per context_window_id):")
        print(class_df)

        sorted_df = class_df.sort_values("context_window_id")
        per_window: list[dict[str, Any]] = []
        for _, row in sorted_df.iterrows():
            per_window.append(
                {
                    "context_window_id": int(row["context_window_id"]),
                    "accuracy_on_matched": float(row["accuracy_on_matched"]),
                    "accuracy_over_gold": float(row["accuracy_over_gold"]),
                    "correct_on_matched": int(row["correct_on_matched"]),
                    "matched_records": int(row["matched_records"]),
                    "gold_records": int(row["gold_records"]),
                }
            )

        total_correct = int(class_df["correct_on_matched"].sum())
        total_gold = int(class_df["gold_records"].sum())
        total_matched = int(class_df["matched_records"].sum())
        class_body: dict[str, Any] = {
            "expt_name": config.get("evaluate.expt_name"),
            "llm_model": config.get("llm.model"),
            "n_windows": int(len(class_df)),
            "mean_accuracy_on_matched": float(class_df["accuracy_on_matched"].mean()),
            "mean_accuracy_over_gold": float(class_df["accuracy_over_gold"].mean()),
            "micro_accuracy_on_matched": float(total_correct / total_matched)
            if total_matched
            else 0.0,
            "micro_accuracy_over_gold": float(total_correct / total_gold)
            if total_gold
            else 0.0,
            "total_correct_on_matched": total_correct,
            "total_matched_records": total_matched,
            "total_gold_records": total_gold,
            "per_context_window": per_window,
            "classification_accuracy_csv": acc_csv.name,
        }
        class_acc_path = _write_classification_accuracies_json(run_dir, class_body)
        class_acc_json_name = class_acc_path.name

        if bool(config.get("oolong.write_classification_results_json", True)):
            results_body: dict[str, Any] = {
                "expt_name": config.get("evaluate.expt_name"),
                "llm_model": config.get("llm.model"),
                "dataset_split": split,
                "n_windows": len(cids),
                "classification_accuracies_json": class_acc_path.name,
                "per_context_window": [
                    {"context_window_id": int(cid), "phase1": by_cid[cid]}
                    for cid in sorted(cids, key=int)
                ],
            }
            class_results_path = _write_classification_results_json(run_dir, results_body)
            class_results_json_name = class_results_path.name
            print(f"classification results (full phase-1) written to {class_results_path}")

        print()
        print(
            "mean_accuracy_on_matched",
            class_body["mean_accuracy_on_matched"],
            "mean_accuracy_over_gold",
            class_body["mean_accuracy_over_gold"],
        )
        print(
            "micro_accuracy_on_matched",
            class_body["micro_accuracy_on_matched"],
            "micro_accuracy_over_gold",
            class_body["micro_accuracy_over_gold"],
        )
        print(f"classification accuracies written to {class_acc_path}")

    summary_path = _write_summary_json(
        csv_path,
        df,
        classification_accuracies_filename=class_acc_json_name,
        classification_results_filename=class_results_json_name,
    )
    print(f"summary written to {summary_path}")
    return csv_path


def _load_phase1_payloads_from_cache(
    rows: list[dict[str, Any]],
    split: str,
    context_len_cfg: int | None,
    model_slug: str | None,
) -> tuple[list[int], dict[int, dict[str, Any]]]:
    """Load per-window phase-1 payloads from window cache."""
    cache_root = bench_root() / str(config.get("oolong.window_cache_dir") or "window_cache")
    by_cid: dict[int, dict[str, Any]] = {}
    cids = unique_cids(rows)
    missing: list[int] = []
    for cid in cids:
        cache_path = ph.window_cache_path(
            cache_root, split, context_len_cfg, cid, model_slug=model_slug
        )
        payload = ph.load_window_cache(cache_path)
        if payload is None:
            missing.append(cid)
            continue
        by_cid[cid] = payload
    if missing:
        raise FileNotFoundError(
            f"Missing window cache payloads for context_window_id(s): {missing[:10]}"
            + (" ..." if len(missing) > 10 else "")
        )
    return cids, by_cid


def rebuild_outputs_from_cache(rows: list[dict[str, Any]], run_dir: Path) -> None:
    """Rebuild classification outputs + summary from existing run + window cache."""
    split = str(config.require("dataset.split"))
    context_len_cfg = config.get("dataset.context_len")
    context_len_cfg = int(context_len_cfg) if context_len_cfg is not None else None
    model_slug = _apply_model_scoped_caches()

    cids, by_cid = _load_phase1_payloads_from_cache(rows, split, context_len_cfg, model_slug)
    class_rows = _classification_accuracy_rows(rows, cids, by_cid)
    class_df = pd.DataFrame(class_rows)

    class_acc_json_name: str | None = None
    class_results_json_name: str | None = None
    if len(class_df):
        acc_csv = run_dir / "classification_accuracy.csv"
        class_df.to_csv(acc_csv, index=False)

        sorted_df = class_df.sort_values("context_window_id")
        per_window: list[dict[str, Any]] = []
        for _, row in sorted_df.iterrows():
            per_window.append(
                {
                    "context_window_id": int(row["context_window_id"]),
                    "accuracy_on_matched": float(row["accuracy_on_matched"]),
                    "accuracy_over_gold": float(row["accuracy_over_gold"]),
                    "correct_on_matched": int(row["correct_on_matched"]),
                    "matched_records": int(row["matched_records"]),
                    "gold_records": int(row["gold_records"]),
                }
            )

        total_correct = int(class_df["correct_on_matched"].sum())
        total_gold = int(class_df["gold_records"].sum())
        total_matched = int(class_df["matched_records"].sum())
        class_body: dict[str, Any] = {
            "expt_name": config.get("evaluate.expt_name"),
            "llm_model": config.get("llm.model"),
            "n_windows": int(len(class_df)),
            "mean_accuracy_on_matched": float(class_df["accuracy_on_matched"].mean()),
            "mean_accuracy_over_gold": float(class_df["accuracy_over_gold"].mean()),
            "micro_accuracy_on_matched": float(total_correct / total_matched)
            if total_matched
            else 0.0,
            "micro_accuracy_over_gold": float(total_correct / total_gold)
            if total_gold
            else 0.0,
            "total_correct_on_matched": total_correct,
            "total_matched_records": total_matched,
            "total_gold_records": total_gold,
            "per_context_window": per_window,
            "classification_accuracy_csv": acc_csv.name,
        }
        class_acc_path = _write_classification_accuracies_json(run_dir, class_body)
        class_acc_json_name = class_acc_path.name

        if bool(config.get("oolong.write_classification_results_json", True)):
            results_body: dict[str, Any] = {
                "expt_name": config.get("evaluate.expt_name"),
                "llm_model": config.get("llm.model"),
                "dataset_split": split,
                "n_windows": len(cids),
                "classification_accuracies_json": class_acc_path.name,
                "per_context_window": [
                    {"context_window_id": int(cid), "phase1": by_cid[cid]}
                    for cid in sorted(cids, key=int)
                ],
            }
            class_results_path = _write_classification_results_json(run_dir, results_body)
            class_results_json_name = class_results_path.name

    csv_path = run_dir / "results.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(f"Missing results.csv in run dir: {run_dir}")
    df = pd.read_csv(csv_path)
    _write_summary_json(
        csv_path,
        df,
        classification_accuracies_filename=class_acc_json_name,
        classification_results_filename=class_results_json_name,
    )


app = typer.Typer()


@app.callback()
def callback():
    """Oolong benchmark."""


@app.command(context_settings={"allow_extra_args": True, "allow_interspersed_args": False})
def run(ctx: typer.Context):
    """Run two-phase Oolong evaluation."""
    rows = prepare_rows(ctx)
    run_two_phase(rows)


@app.command(context_settings={"allow_extra_args": True, "allow_interspersed_args": False})
def quick_test(ctx: typer.Context):
    """Run first row only with the same two-phase logic."""
    rows = prepare_rows(ctx)
    if not rows:
        raise SystemExit("No rows loaded.")
    run_two_phase(rows[:1])


@app.command(context_settings={"allow_extra_args": True, "allow_interspersed_args": False})
def phase1_only(ctx: typer.Context):
    """Run only phase-1 (infer/classify/cache) and stop before answering."""
    rows = prepare_rows(ctx)
    _maybe_configure_logfire()
    split, cids, by_cid = _run_phase1(rows)
    print(
        f"phase1_only done split={split} windows={len(cids)} "
        f"cached_payloads={len(by_cid)}"
    )


@app.command(context_settings={"allow_extra_args": True, "allow_interspersed_args": False})
def repair_outputs(
    ctx: typer.Context,
    run_dir: str = typer.Option(..., help="Existing run directory containing results.csv"),
):
    """Rebuild classification files + summary from window cache and existing results."""
    rows = prepare_rows(ctx)
    rd = Path(run_dir)
    if not rd.is_absolute():
        rd = bench_root() / rd
    rebuild_outputs_from_cache(rows, rd)
    print(f"repair_outputs done: {rd}")


if __name__ == "__main__":
    app()
