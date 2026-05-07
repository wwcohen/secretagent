"""Pareto frontier visualization."""

from pathlib import Path

import matplotlib.pyplot as plt
from adjustText import adjust_text


# Color palette for methods — visually distinct, colorblind-friendly
_METHOD_COLORS = [
    "#1976D2",  # blue
    "#D32F2F",  # red
    "#388E3C",  # green
    "#F57C00",  # orange
    "#7B1FA2",  # purple
    "#0097A7",  # teal
    "#C2185B",  # deep pink
    "#5D4037",  # brown
]

# Marker shapes for models
_MODEL_MARKERS = ["o", "s", "D", "^", "v", "P", "X", "h"]


def _parse_label(label: str) -> tuple[str, str]:
    """Split 'method/model' label into (method, model). Falls back gracefully."""
    if "/" in label:
        method, model = label.split("/", 1)
        return method, model
    return label, ""


def plot_pareto_frontier(
    results: list[tuple[str, float, float]],
    title: str = "Pareto Frontier",
    output_path: str | Path = "pareto.png",
    metric_name: str = "Accuracy",
    show: bool = True,
):
    """Plot accuracy vs cost with frontier points highlighted.

    Labels should be in 'method/model' format for best results (color by
    method, shape by model). Plain labels also work.

    Args:
        results: list of (label, accuracy_or_metric, cost_per_q) tuples.
        title: plot title.
        output_path: where to save the PNG.
        metric_name: y-axis label (e.g. "Accuracy", "F1").
        show: if True, call plt.show() after saving.
    """
    if not results:
        print("No results to plot.")
        return

    # Deduplicate: NSGA-II re-evaluates configs on cache hits, producing
    # identical (label, acc, cost) tuples that pile up at one point on the
    # plot and clutter labels. Collapse to one entry per (label, acc, cost).
    seen = set()
    deduped = []
    for r in results:
        key = (r[0], round(r[1], 6), round(r[2], 8))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    results = deduped

    # Discover unique methods and models
    methods_seen: list[str] = []
    models_seen: list[str] = []
    for label, _, _ in results:
        method, model = _parse_label(label)
        if method not in methods_seen:
            methods_seen.append(method)
        if model and model not in models_seen:
            models_seen.append(model)

    method_color = {m: _METHOD_COLORS[i % len(_METHOD_COLORS)] for i, m in enumerate(methods_seen)}
    model_marker = {m: _MODEL_MARKERS[i % len(_MODEL_MARKERS)] for i, m in enumerate(models_seen)}

    # Identify Pareto-optimal points (non-dominated)
    frontier_mask = []
    for i, (_, acc_i, cost_i) in enumerate(results):
        dominated = False
        for j, (_, acc_j, cost_j) in enumerate(results):
            if i != j and acc_j >= acc_i and cost_j <= cost_i and (acc_j > acc_i or cost_j < cost_i):
                dominated = True
                break
        frontier_mask.append(not dominated)

    fig, ax = plt.subplots(figsize=(10, 7))

    # Plot dominated points first (behind)
    for idx, ((label, acc, cost), is_frontier) in enumerate(zip(results, frontier_mask)):
        if is_frontier:
            continue
        method, model = _parse_label(label)
        color = method_color.get(method, "#666666")
        marker = model_marker.get(model, "o") if model else "o"
        ax.scatter(
            cost, acc,
            marker=marker, c="none", edgecolors=color,
            linewidths=1.0, s=50, alpha=0.35, zorder=2,
        )

    # Plot frontier points on top
    frontier_texts = []
    for idx, ((label, acc, cost), is_frontier) in enumerate(zip(results, frontier_mask)):
        if not is_frontier:
            continue
        method, model = _parse_label(label)
        color = method_color.get(method, "#666666")
        marker = model_marker.get(model, "o") if model else "o"
        ax.scatter(
            cost, acc,
            marker=marker, c=color, edgecolors="white",
            linewidths=0.8, s=130, alpha=1.0, zorder=4,
        )
        txt = ax.text(
            cost, acc, f"  {label}",
            fontsize=8.5, fontweight="bold", color=color,
            zorder=5,
        )
        frontier_texts.append(txt)

    # Connect frontier points with a dashed line
    frontier_pts = sorted(
        [(c, a) for (_, a, c), on_f in zip(results, frontier_mask) if on_f],
        key=lambda x: x[0],
    )
    if len(frontier_pts) > 1:
        ax.plot(
            [c for c, _ in frontier_pts],
            [a for _, a in frontier_pts],
            "--", color="#BBBBBB", linewidth=1.0, alpha=0.6, zorder=1,
        )

    # De-overlap frontier labels only
    if frontier_texts:
        adjust_text(
            frontier_texts, ax=ax,
            arrowprops=dict(arrowstyle="-", color="#CCCCCC", lw=0.5, shrinkA=5, shrinkB=5),
            expand=(1.8, 1.8),
            force_text=(1.0, 1.0),
            force_points=(0.5, 0.5),
        )

    # Build legend: methods (color circles) + models (gray shapes)
    from matplotlib.lines import Line2D

    legend_handles = []
    # Method entries
    for m in methods_seen:
        legend_handles.append(
            Line2D([0], [0], marker="o", color="w", markerfacecolor=method_color[m],
                   markeredgecolor=method_color[m], markersize=9, label=m)
        )
    # Separator
    if models_seen:
        legend_handles.append(
            Line2D([0], [0], marker="None", color="w", label=" ")
        )
    # Model entries
    for m in models_seen:
        legend_handles.append(
            Line2D([0], [0], marker=model_marker[m], color="w", markerfacecolor="#555555",
                   markeredgecolor="#555555", markersize=7, label=m)
        )
    # Frontier / dominated indicator
    legend_handles.append(Line2D([0], [0], marker="None", color="w", label=" "))
    legend_handles.append(
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#1976D2",
               markeredgecolor="white", markersize=9, label="Pareto-optimal")
    )
    legend_handles.append(
        Line2D([0], [0], marker="o", color="w", markerfacecolor="none",
               markeredgecolor="#999999", markersize=7, label="Dominated")
    )

    ax.legend(
        handles=legend_handles, loc="lower right", fontsize=8,
        framealpha=0.92, handletextpad=0.5, borderpad=0.8,
        labelspacing=0.4,
    )

    # Axis styling. Use log-scale x when costs span more than ~20x, so 4 frontier
    # points spanning $0.002-$0.30 don't get crushed into a left-edge cluster.
    costs = [c for _, _, c in results if c > 0]
    if costs and max(costs) / min(costs) > 20:
        ax.set_xscale("log")
        ax.set_xlim(min(costs) * 0.7, max(costs) * 1.6)
    else:
        cost_range = max(costs) - min(costs) if len(costs) > 1 else max(costs)
        ax.set_xlim(
            max(0, min(costs) - cost_range * 0.08),
            max(costs) + cost_range * 0.20,
        )

    ax.set_xlabel("Cost per query ($)", fontsize=11)
    ax.set_ylabel(metric_name, fontsize=11)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.15, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=9)

    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Plot saved to {output_path}")

    if show:
        plt.show()
    plt.close(fig)
