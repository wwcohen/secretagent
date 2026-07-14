"""Regenerate the RESULTS figures from the collected truth + cheap cache.

    uv run python -m ppi_eval.plots

Writes:
  ppi_eval/fig_budget_sweep.png   -- optimizer layer: selection quality vs budget
  ppi_eval/fig_width_vs_corr.png  -- estimator layer: PPI tightens with corr(f,Y)
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import ppi_eval.ab_experiment as ab

OUT = Path(__file__).resolve().parent


def main():
    ns = [10, 15, 20, 25, 40]
    data = {n: ab.report(n_label=n, trials=600, alpha=0.05, seed=0,
                         rectifiers=["R0", "R1", "R2"])["optimizer"] for n in ns}

    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for m, style in [("naive", "k--o"), ("R0", "C0-o"), ("R1", "C1-s"), ("R2", "C2-^")]:
        ax[0].plot(ns, [data[n][m]["test_acc_selected"] for n in ns], style, label=m)
        ax[1].plot(ns, [data[n][m]["pick_freq"].get("wf_orch", 0) for n in ns], style, label=m)
    ax[0].set(xlabel="labeled budget n", ylabel="test acc of selected config",
              title="Selection quality vs budget")
    ax[1].set(xlabel="labeled budget n", ylabel="P(select true-best wf_orch)",
              title="Best-config recovery")
    for a in ax:
        a.legend()
        a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "fig_budget_sweep.png", dpi=130)

    rep = ab.report(n_label=25, trials=600, alpha=0.05, seed=0, rectifiers=["R0", "R1", "R2"])
    est, corrs = rep["estimator"], rep["corr_f_y"]
    cfgs = [c for c in est if est[c]["naive"]["width"] > 0]  # drop the 0%/zero-width config
    xs = [corrs[c] for c in cfgs]
    red = [(est[c]["naive"]["width"] - est[c]["R0"]["width"]) / est[c]["naive"]["width"] for c in cfgs]

    fig2, ax2 = plt.subplots(figsize=(6.2, 4.6))
    ax2.scatter(xs, red, s=70, c="C0")
    for c, x, y in zip(cfgs, xs, red):
        ax2.annotate(c, (x, y), fontsize=8, xytext=(4, 4), textcoords="offset points")
    ax2.axhline(0, color="grey", lw=0.8)
    ax2.set(xlabel="corr(f, Y) for the candidate workflow",
            ylabel="R0 CI-width reduction vs naive",
            title="PPI tightens in proportion to corr(f,Y)\n(honest widening as candidates decorrelate)")
    ax2.grid(alpha=0.3)
    fig2.tight_layout()
    fig2.savefig(OUT / "fig_width_vs_corr.png", dpi=130)
    print("saved fig_budget_sweep.png, fig_width_vs_corr.png")


if __name__ == "__main__":
    main()
