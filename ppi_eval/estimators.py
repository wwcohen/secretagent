"""PPI mean estimators with a pluggable rectifier interface.

Estimand: theta = E[Y], where Y is an EXPENSIVE per-case outcome of a candidate
workflow -- either accuracy (Y in {0,1}) or cost (Y in R). We observe Y on a
small labeled set of n cases and a cheap predictor f on a large pool: the same
n labeled cases (f_lab) plus N unlabeled cases (f_unlab). PPI combines them into
an estimate that is unbiased for theta while borrowing variance reduction from
the cheap predictor.

All estimators share the power-tuned PPI++ engine (Angelopoulos et al., PPI++;
delegated to the official `ppi_py`). They differ only in the RECTIFIER -- the
functional form of the cheap predictor h used inside PPI:

  R0  constant / PPI++        h = f                (ppi_py, power-tuned lambda)
  R1  stratified / StratPPI   piecewise per feature-bin; PPI++ within each bin,
                              combined by stratum weights (arxiv 2406.04291)
  R2  regression rectifier    (subclass hook) h = g(features), tree/linear
  R3  matrix-factorization    (subclass hook) h from per-case latent factors

Key behavior we are testing: the cheap predictor is anchored to the baseline
workflow, so corr(f, Y_candidate) decays as a candidate moves away from
baseline. R0 only rescales f globally; the smarter rectifiers recalibrate
locally and -- when they cannot -- widen the CI honestly, which is what should
stop the optimizer from trusting a far-from-baseline candidate.

Public API:
  ppi_estimate(y_lab, f_lab, f_unlab, rectifier="R0", ...) -> PPIResult
  naive_estimate(y_lab, alpha) -> PPIResult
  corr(y, f) -> float
"""

from dataclasses import dataclass, field

import numpy as np

try:
    from ppi_py import ppi_mean_ci, ppi_mean_pointestimate
    _HAVE_PPI = True
except Exception:  # pragma: no cover - ppi_py is a declared dependency
    _HAVE_PPI = False


def _z(alpha: float) -> float:
    try:
        from scipy.stats import norm

        return float(norm.ppf(1 - alpha / 2))
    except Exception:
        return 1.959963984540054  # alpha = 0.05


def _t(alpha: float, dof: int) -> float:
    """Two-sided t multiplier; falls back to z if scipy is unavailable."""
    if dof < 1:
        return _z(alpha)
    try:
        from scipy.stats import t

        return float(t.ppf(1 - alpha / 2, dof))
    except Exception:
        return _z(alpha)


@dataclass
class PPIResult:
    """Result of a (PPI or naive) mean estimate."""

    estimate: float
    ci_lo: float
    ci_hi: float
    method: str = "?"
    n_lab: int = 0
    n_unlab: int = 0
    extra: dict = field(default_factory=dict)

    @property
    def half_width(self) -> float:
        return (self.ci_hi - self.ci_lo) / 2.0

    @property
    def se(self) -> float:
        return self.half_width / _z(0.05)

    def as_tuple(self) -> tuple[float, float, float]:
        """The (estimate, ci_lo, ci_hi) triple promised by ppi_estimate."""
        return (self.estimate, self.ci_lo, self.ci_hi)


# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------

def _clean(*arrays):
    """Drop entries where any aligned array is non-finite. Arrays must align by
    index only across the FIRST argument's length (labeled arrays)."""
    arrs = [np.asarray(a, dtype=float) for a in arrays]
    mask = np.ones(len(arrs[0]), dtype=bool)
    for a in arrs:
        mask &= np.isfinite(a)
    return [a[mask] for a in arrs]


def naive_estimate(y_lab, alpha: float = 0.05) -> PPIResult:
    """Labeled-only mean with a normal-approx CI (works for binary or real Y)."""
    y = np.asarray(y_lab, dtype=float)
    y = y[np.isfinite(y)]
    n = len(y)
    if n == 0:
        return PPIResult(float("nan"), float("nan"), float("nan"), "naive", 0, 0)
    p = float(y.mean())
    sd = float(y.std(ddof=1)) if n > 1 else 0.0
    se = sd / np.sqrt(n)
    z = _z(alpha)
    return PPIResult(p, p - z * se, p + z * se, "naive", n, 0)


def _ppi_pp(y_lab, f_lab, f_unlab, alpha: float) -> tuple[float, float, float]:
    """Power-tuned PPI++ mean (estimate, ci_lo, ci_hi) via ppi_py."""
    y = np.asarray(y_lab, dtype=float)
    fl = np.asarray(f_lab, dtype=float)
    fu = np.asarray(f_unlab, dtype=float)
    est = float(np.ravel(ppi_mean_pointestimate(y, fl, fu))[0])
    lo, hi = ppi_mean_ci(y, fl, fu, alpha=alpha)
    return est, float(np.ravel(lo)[0]), float(np.ravel(hi)[0])


def _rectified_ppi(y_lab, h_lab, h_unlab, alpha: float, tune: bool = True):
    """Power-tuned rectified PPI mean for an ARBITRARY per-case predictor h.

        theta(lam) = mean_lab[Y] + lam * (mean_unlab[h] - mean_lab[h])
        Var        = Var_lab[Y - lam*h]/n + lam^2 * Var_unlab[h]/N

    lam is tuned to minimize Var (PPI++ tuning), clipped to [0, 1] so the
    estimator interpolates between naive (lam=0, when h is useless -> honest
    widening) and full rectification (lam=1). A t-multiplier on n-1 dof keeps
    small-n CIs from undercovering. Returns (estimate, ci_lo, ci_hi, lam, se).
    """
    y = np.asarray(y_lab, dtype=float)
    hl = np.asarray(h_lab, dtype=float)
    hu = np.asarray(h_unlab, dtype=float)
    n, N = len(y), len(hu)
    var_hu = float(np.var(hu, ddof=1)) if N > 1 else 0.0
    if tune and n > 1:
        cov = float(np.cov(y, hl)[0, 1])
        denom = float(np.var(hl, ddof=1)) + (n / max(N, 1)) * var_hu
        lam = cov / denom if denom > 0 else 0.0
        lam = float(min(1.0, max(0.0, lam)))
    else:
        lam = 1.0
    theta = float(y.mean() + lam * (hu.mean() - hl.mean()))
    resid_var = float(np.var(y - lam * hl, ddof=1)) if n > 1 else 0.0
    var = resid_var / n + (lam ** 2) * var_hu / max(N, 1)
    se = float(np.sqrt(max(var, 0.0)))
    mult = _t(alpha, n - 1)
    return theta, theta - mult * se, theta + mult * se, lam, se


# ---------------------------------------------------------------------------
# Rectifiers
# ---------------------------------------------------------------------------

class Rectifier:
    """Base class. A rectifier turns (labeled Y, cheap f, optional features)
    into a PPI mean estimate of E[Y]. Subclasses override `estimate`."""

    name = "base"

    def estimate(self, y_lab, f_lab, f_unlab, x_lab=None, x_unlab=None,
                 alpha: float = 0.05) -> PPIResult:
        raise NotImplementedError


class R0Constant(Rectifier):
    """R0: constant rectifier h = f, power-tuned (this IS PPI++ from ppi_py)."""

    name = "R0"

    def estimate(self, y_lab, f_lab, f_unlab, x_lab=None, x_unlab=None,
                 alpha: float = 0.05) -> PPIResult:
        y, fl = _clean(y_lab, f_lab)
        fu = np.asarray(f_unlab, dtype=float)
        fu = fu[np.isfinite(fu)]
        n, N = len(y), len(fu)
        # Degenerate guards: PPI needs labeled pairs, unlabeled f, and signal.
        if not _HAVE_PPI or n < 2 or N < 1 or np.std(fl) == 0 or np.std(y) == 0:
            r = naive_estimate(y, alpha)
            r.method, r.n_unlab = "R0(naive-fallback)", N
            return r
        est, lo, hi = _ppi_pp(y, fl, fu, alpha)
        return PPIResult(est, lo, hi, "R0", n, N)


class R1Stratified(Rectifier):
    """R1: stratified / piecewise rectifier (StratPPI flavor).

    Build a piecewise predictor h that recalibrates the cheap f WITHIN feature
    strata, then feed it to the single power-tuned rectified-PPI engine:

      - Bin cases by a feature into `n_strata` quantile bins (edges over the full
        labeled+unlabeled pool).
      - In each (bin, f-value) cell, h = mean of labeled Y in that cell -- i.e. a
        per-stratum recalibration of the binary cheap predictor. Empty cells fall
        back to the bin's labeled mean, then to the global labeled mean.
      - h is defined for every labeled and unlabeled case; rectified PPI then
        power-tunes lambda and forms one pooled-residual CI.

    Why this calibrates and widens honestly: h uses both the feature and f, so it
    can hold tighter than R0 when the feature carries signal; and if h stops
    predicting Y (decorrelation), the tuned lambda shrinks toward 0, collapsing
    the estimator back to the naive labeled mean with its (wide) CI. With no
    feature supplied we recalibrate on f alone (a global recalibration of R0).
    """

    name = "R1"

    def __init__(self, n_strata: int = 3):
        self.n_strata = n_strata

    def _bin(self, v_lab, v_unlab, K):
        pool = np.concatenate([v_lab, v_unlab])
        edges = np.quantile(pool, np.linspace(0, 1, K + 1))
        edges[0], edges[-1] = -np.inf, np.inf
        edges = np.unique(edges)  # collapse tied edges -> fewer, non-empty bins
        return np.digitize(v_lab, edges[1:-1]), np.digitize(v_unlab, edges[1:-1])

    def estimate(self, y_lab, f_lab, f_unlab, x_lab=None, x_unlab=None,
                 alpha: float = 0.05) -> PPIResult:
        # R1 stratifies on a single feature; take column 0 of a feature matrix.
        if x_lab is not None and np.asarray(x_lab).ndim > 1:
            x_lab = np.asarray(x_lab)[:, 0]
        if x_unlab is not None and np.asarray(x_unlab).ndim > 1:
            x_unlab = np.asarray(x_unlab)[:, 0]
        y, fl = _clean(y_lab, f_lab)
        xl = None
        if x_lab is not None:
            y, fl, xl = _clean(y_lab, f_lab, x_lab)
        fu = np.asarray(f_unlab, dtype=float)
        xu = None if x_unlab is None else np.asarray(x_unlab, dtype=float)
        if xu is not None:
            um = np.isfinite(fu) & np.isfinite(xu)
            fu, xu = fu[um], xu[um]
        else:
            fu = fu[np.isfinite(fu)]

        n, N = len(y), len(fu)
        if n < 4 or N < 2 or np.std(y) == 0:
            r = naive_estimate(y, alpha)
            r.method, r.n_unlab = "R1(naive-fallback)", N
            return r

        # Feature bins (degrade to a single bin if no usable feature).
        if xl is None or xu is None or np.std(np.concatenate([xl, xu])) == 0:
            lab_bin = np.zeros(n, dtype=int)
            unlab_bin = np.zeros(N, dtype=int)
        else:
            lab_bin, unlab_bin = self._bin(xl, xu, max(1, int(self.n_strata)))

        # Fit h on labeled cells keyed by (feature bin, cheap f value).
        global_mean = float(y.mean())
        cell_mean: dict[tuple, float] = {}
        bin_mean: dict[int, float] = {}
        for b in np.unique(lab_bin):
            m = lab_bin == b
            bin_mean[int(b)] = float(y[m].mean())
            for fv in np.unique(fl[m]):
                mm = m & (fl == fv)
                cell_mean[(int(b), float(fv))] = float(y[mm].mean())

        def predict(bins, fvals):
            out = np.empty(len(bins), dtype=float)
            for i, (b, fv) in enumerate(zip(bins, fvals)):
                out[i] = cell_mean.get(
                    (int(b), float(fv)),
                    bin_mean.get(int(b), global_mean),
                )
            return out

        # Unlabeled: predict with the full-data fit. Labeled: leave-one-out
        # cross-fit so Y - h is not optimistically small (the residual variance
        # stays honest, which is what keeps the CI calibrated).
        def predict_loo(bins, fvals, yvals):
            out = np.empty(len(bins), dtype=float)
            for i in range(len(bins)):
                keep = np.arange(len(bins)) != i
                b, fv = int(bins[i]), float(fvals[i])
                cell = keep & (bins == b) & (fvals == fv)
                binm = keep & (bins == b)
                if cell.any():
                    out[i] = float(yvals[cell].mean())
                elif binm.any():
                    out[i] = float(yvals[binm].mean())
                else:
                    out[i] = float(yvals[keep].mean()) if keep.any() else global_mean
            return out

        h_lab = predict_loo(lab_bin, fl, y)
        h_unlab = predict(unlab_bin, fu)

        theta, lo, hi, lam, se = _rectified_ppi(y, h_lab, h_unlab, alpha)
        return PPIResult(
            theta, lo, hi, "R1", n, N,
            extra=dict(n_strata=len(set(lab_bin.tolist())), lam=lam, se=se),
        )


def _ridge_predict(D_fit, y_fit, D_eval, alpha: float):
    """Standardized ridge regression: fit on (D_fit, y_fit), predict D_eval.

    Columns are z-scored by the fit set; the intercept is unpenalized. Returns
    predictions for D_eval. Robust to zero-variance columns.
    """
    D_fit = np.asarray(D_fit, dtype=float)
    D_eval = np.asarray(D_eval, dtype=float)
    mu = D_fit.mean(axis=0)
    sd = D_fit.std(axis=0, ddof=0)
    sd = np.where(sd < 1e-12, 1.0, sd)
    Zf = (D_fit - mu) / sd
    Ze = (D_eval - mu) / sd
    n, d = Zf.shape
    Xf = np.hstack([np.ones((n, 1)), Zf])
    Xe = np.hstack([np.ones((len(Ze), 1)), Ze])
    reg = alpha * np.eye(d + 1)
    reg[0, 0] = 0.0  # do not penalize intercept
    try:
        w = np.linalg.solve(Xf.T @ Xf + reg, Xf.T @ y_fit)
    except np.linalg.LinAlgError:
        w = np.linalg.lstsq(Xf.T @ Xf + reg, Xf.T @ y_fit, rcond=None)[0]
    return Xe @ w


class R2Regression(Rectifier):
    """R2: regression rectifier. h = ridge(features) predicting Y from the cheap
    predictor f plus per-case features (token counts, problem length).

    h is fit on labeled (Y, [f, X]) and predicts every case. Labeled predictions
    are K-fold cross-fit so the residual variance stays honest; unlabeled
    predictions use the full-data fit. The result feeds the power-tuned
    rectified-PPI engine -- so if the richer regression genuinely predicts Y
    better than f alone, lambda stays near 1 and the CI tightens; if it overfits
    noise, lambda shrinks and the CI widens back toward naive.
    """

    name = "R2"

    def __init__(self, n_folds: int = 5, alpha: float = 1.0):
        self.n_folds = n_folds
        self.alpha = alpha

    @staticmethod
    def _design(f, X):
        f = np.asarray(f, dtype=float).reshape(-1, 1)
        if X is None:
            return f
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        return np.hstack([f, X])

    def estimate(self, y_lab, f_lab, f_unlab, x_lab=None, x_unlab=None,
                 alpha: float = 0.05) -> PPIResult:
        y = np.asarray(y_lab, dtype=float)
        D_lab = self._design(f_lab, x_lab)
        # Drop labeled rows with any non-finite entry.
        good = np.isfinite(y) & np.isfinite(D_lab).all(axis=1)
        y, D_lab = y[good], D_lab[good]
        D_unlab = self._design(f_unlab, x_unlab)
        um = np.isfinite(D_unlab).all(axis=1)
        D_unlab = D_unlab[um]

        n, d = D_lab.shape
        N = len(D_unlab)
        if n < max(5, d + 2) or N < 2 or np.std(y) == 0:
            r = naive_estimate(y, alpha)
            r.method, r.n_unlab = "R2(naive-fallback)", N
            return r

        # Unlabeled predictions: full-data fit.
        h_unlab = _ridge_predict(D_lab, y, D_unlab, self.alpha)
        # Labeled predictions: K-fold cross-fit (fold = index % K).
        K = max(2, min(self.n_folds, n))
        h_lab = np.empty(n, dtype=float)
        fold = np.arange(n) % K
        for k in range(K):
            te = fold == k
            tr = ~te
            if tr.sum() < d + 1 or te.sum() == 0:
                h_lab[te] = float(y[tr].mean()) if tr.any() else float(y.mean())
            else:
                h_lab[te] = _ridge_predict(D_lab[tr], y[tr], D_lab[te], self.alpha)

        theta, lo, hi, lam, se = _rectified_ppi(y, h_lab, h_unlab, alpha)
        return PPIResult(theta, lo, hi, "R2", n, N,
                         extra=dict(n_features=d, lam=lam, se=se))


RECTIFIERS: dict[str, Rectifier] = {
    "R0": R0Constant(),
    "R1": R1Stratified(n_strata=3),
    "R2": R2Regression(),
}


def get_rectifier(spec) -> Rectifier:
    if isinstance(spec, Rectifier):
        return spec
    if spec in RECTIFIERS:
        return RECTIFIERS[spec]
    raise KeyError(f"unknown rectifier {spec!r}; have {list(RECTIFIERS)}")


def ppi_estimate(y_lab, f_lab, f_unlab, rectifier="R0",
                 x_lab=None, x_unlab=None, alpha: float = 0.05) -> PPIResult:
    """Estimate E[Y] via PPI with the chosen rectifier.

    Args:
      y_lab:    labeled true outcomes Y (n,)            -- accuracy or cost
      f_lab:    cheap predictor f on the labeled cases (n,)
      f_unlab:  cheap predictor f on the unlabeled cases (N,)
      rectifier: "R0", "R1", or a Rectifier instance
      x_lab/x_unlab: optional per-case feature (n,)/(N,) used by R1+ rectifiers
      alpha:    1 - confidence level (0.05 -> 95% CI)

    Returns a PPIResult; .as_tuple() gives (estimate, ci_lo, ci_hi).
    """
    return get_rectifier(rectifier).estimate(
        y_lab, f_lab, f_unlab, x_lab=x_lab, x_unlab=x_unlab, alpha=alpha
    )


def corr(y, f) -> float:
    """Pearson corr(Y, f) over aligned finite pairs; 0.0 if undefined."""
    y, f = _clean(y, f)
    if len(y) < 2 or np.std(y) == 0 or np.std(f) == 0:
        return 0.0
    return float(np.corrcoef(y, f)[0, 1])
