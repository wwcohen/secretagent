"""PPI hook for the NSGA-II inner loop (pareto.EvalCache).

`maybe_ppi(df, metric, naive_accuracy, naive_cost)` is called from pareto.py
right after the per-case results.csv is read. When `optimize.use_ppi` is off it
returns the naive means unchanged (zero behavior change). When on, it replaces
the two .mean() objectives with PPI estimates that join the candidate's small
labeled set (the rows actually run, keyed by case_name) to the cached cheap
predictions over the full pool (the unlabeled set).

Config keys (read via secretagent.config; env fallbacks in parens):
  optimize.use_ppi        bool   enable PPI scoring            (SECRETAGENT_USE_PPI)
  optimize.ppi_cache      path   cheap_preds_*.json           (SECRETAGENT_PPI_CACHE)
  optimize.ppi_rectifier  str    R0 | R1 (default R0)         (SECRETAGENT_PPI_RECTIFIER)
  optimize.ppi_feature    str    cache feature for R1 strata  (default narrative_chars)
  optimize.ppi_acc_pred   str    cache field predicting y     (default: f_score|f_correct)
  optimize.ppi_cost_pred  str    cache field predicting cost  (default f_cost)

The estimand for the accuracy objective is E[Y], Y = the metric column (correct);
for the cost objective it is E[C], C = the cost column. Both reuse the cheap
predictor in the cache: f_correct for accuracy, f_cost (or another field) for
cost. The cheap pool and the labeled rows align on case_name (deterministic
case sampling guarantees the labeled names are a subset of the cached pool).
"""

import json
import os
from functools import lru_cache
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[1]
_DEFAULT_CACHE = _REPO / "ppi_eval" / "cache" / "cheap_preds_musr_team.json"


def _cfg(key, default=None):
    try:
        from secretagent import config

        return config.get(key, default)
    except Exception:
        return default


def _flag(cfg_key, env_key, default=None):
    val = _cfg(cfg_key, None)
    if val is None:
        val = os.environ.get(env_key)
    return default if val is None else val


def ppi_enabled() -> bool:
    val = _flag("optimize.use_ppi", "SECRETAGENT_USE_PPI", None)
    if val is None:
        return False
    return str(val).strip().lower() not in ("0", "false", "no", "off", "")


@lru_cache(maxsize=4)
def _load_cache(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _coerce_correct(v):
    s = str(v).strip().lower()
    if s in ("true", "1", "1.0"):
        return 1.0
    if s in ("false", "0", "0.0", ""):
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return np.nan


def _acc_field(cobj, configured):
    """Cache field holding the cheap accuracy/metric predictor f.

    Honors an explicit `optimize.ppi_acc_pred` if set; otherwise accepts the new
    contract name `f_score`, falling back to the legacy `f_correct`. Keeps old
    caches working while new (possibly continuous-metric) providers write
    `f_score`. Returns the field's value, or None if absent.
    """
    if configured:
        return cobj.get(configured)
    if "f_score" in cobj:
        return cobj.get("f_score")
    return cobj.get("f_correct")


def maybe_ppi(df, metric, naive_accuracy, naive_cost):
    """Return (accuracy, cost) objectives, PPI-adjusted iff optimize.use_ppi is on.

    Falls back to the naive means on any missing data so the optimizer never
    breaks; raises only if PPI is explicitly enabled and the cache is unusable.
    """
    if not ppi_enabled():
        return naive_accuracy, naive_cost
    if "case_name" not in getattr(df, "columns", []):
        return naive_accuracy, naive_cost

    from ppi_eval.estimators import ppi_estimate

    cache_path = str(_flag("optimize.ppi_cache", "SECRETAGENT_PPI_CACHE", str(_DEFAULT_CACHE)))
    rectifier = str(_flag("optimize.ppi_rectifier", "SECRETAGENT_PPI_RECTIFIER", "R0"))
    feature = str(_cfg("optimize.ppi_feature", "narrative_chars"))
    acc_pred = _cfg("optimize.ppi_acc_pred", None)  # None -> f_score|f_correct
    cost_pred = str(_cfg("optimize.ppi_cost_pred", "f_cost"))

    cache = _load_cache(cache_path)["cases"]

    labeled_names = set(str(n) for n in df["case_name"]) & set(cache)
    if len(labeled_names) < 2:
        return naive_accuracy, naive_cost
    unlab_names = [n for n in cache if n not in labeled_names]

    # Per-case labeled outcomes from the candidate run.
    row_by_name = {str(r["case_name"]): r for _, r in df.iterrows()}

    y_acc, f_acc, x_lab = [], [], []
    y_cost, f_cost = [], []
    for name in labeled_names:
        row = row_by_name[name]
        cobj = cache[name]
        # accuracy
        y_acc.append(_coerce_correct(row.get(metric)))
        f_acc.append(_acc_field(cobj, acc_pred))
        x_lab.append(cobj.get(feature))
        # cost
        c = row.get("cost")
        y_cost.append(float(c) if c is not None and np.isfinite(float(c)) else np.nan)
        f_cost.append(cobj.get(cost_pred))

    f_acc_unlab = [_acc_field(cache[n], acc_pred) for n in unlab_names]
    f_cost_unlab = [cache[n].get(cost_pred) for n in unlab_names]
    x_unlab = [cache[n].get(feature) for n in unlab_names]

    acc = ppi_estimate(
        np.array(y_acc, float), np.array(f_acc, float), np.array(f_acc_unlab, float),
        rectifier=rectifier, x_lab=np.array(x_lab, float), x_unlab=np.array(x_unlab, float),
    ).estimate
    cost = ppi_estimate(
        np.array(y_cost, float), np.array(f_cost, float), np.array(f_cost_unlab, float),
        rectifier=rectifier, x_lab=np.array(x_lab, float), x_unlab=np.array(x_unlab, float),
    ).estimate

    acc = float(acc) if np.isfinite(acc) else naive_accuracy
    cost = float(cost) if np.isfinite(cost) else naive_cost
    return acc, cost
