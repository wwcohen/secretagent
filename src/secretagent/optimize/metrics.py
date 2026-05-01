"""Pareto-frontier quality metrics.

The core metric is the *hypervolume indicator* — the area (2D) of the region
dominated by a Pareto frontier relative to a reference point.  Bigger is
better: a frontier with higher hypervolume Pareto-dominates more of the
search space.

We only need the 2D case here: (accuracy, cost) with accuracy maximized and
cost minimized.  The 2D algorithm is a single O(n log n) sweep — no pymoo
dependency required.

Example
-------
    from secretagent.optimize.metrics import compute_hypervolume, compare_hypervolumes

    frontier_a = [(0.97, 0.008), (0.85, 0.003), (0.72, 0.001)]  # airline, structured_baseline
    frontier_b = [(0.80, 0.015), (0.40, 0.002)]                 # airline, react
    ref = (0.0, 0.02)  # worst accuracy, worst cost we care about

    hv_a = compute_hypervolume(frontier_a, ref)
    print(compare_hypervolumes(frontier_a, frontier_b, ref, label_a="structured", label_b="react"))
"""

from __future__ import annotations


def compute_hypervolume(
    frontier: list[tuple[float, float]],
    ref_point: tuple[float, float],
) -> float:
    """2D hypervolume for the (maximize accuracy, minimize cost) setting.

    Args:
        frontier: iterable of ``(accuracy, cost)`` pairs.  Need not be
            strictly Pareto — dominated points are dropped internally.
        ref_point: ``(ref_accuracy, ref_cost)`` — the "worst" corner.  A point
            contributes to the hypervolume only if it beats the reference on
            both axes (accuracy > ref_accuracy AND cost < ref_cost).

    Returns:
        The dominated area (same units as ``accuracy * cost``).  A higher
        value means the frontier dominates more of the space.  Returns 0 if
        no point beats the reference.
    """
    ref_acc, ref_cost = ref_point

    # 1. Keep only points strictly better than the reference on both axes.
    valid = [
        (float(a), float(c))
        for a, c in frontier
        if a > ref_acc and c < ref_cost
    ]
    if not valid:
        return 0.0

    # 2. Extract the strict Pareto subset: sort by cost ascending, then sweep
    #    keeping only points whose accuracy is strictly greater than the best
    #    seen so far.  (Ties are resolved by keeping the lower-cost version.)
    valid.sort(key=lambda p: (p[1], -p[0]))
    pareto: list[tuple[float, float]] = []
    best_acc = ref_acc
    for acc, cost in valid:
        if acc > best_acc:
            pareto.append((acc, cost))
            best_acc = acc
    if not pareto:
        return 0.0

    # 3. Integrate right-to-left.  `pareto` is sorted by cost ascending with
    #    accuracy also ascending, so at any x in [c_i, c_{i+1}) the staircase
    #    height is a_i.  Walk from the rightmost point to the leftmost,
    #    accumulating strips of width (prev_cost - c_i) and height
    #    (a_i - ref_acc).
    hv = 0.0
    prev_cost = ref_cost
    for acc, cost in reversed(pareto):
        hv += (prev_cost - cost) * (acc - ref_acc)
        prev_cost = cost
    return hv


def compare_hypervolumes(
    frontier_a: list[tuple[float, float]],
    frontier_b: list[tuple[float, float]],
    ref_point: tuple[float, float],
    label_a: str = "A",
    label_b: str = "B",
) -> str:
    """Human-readable comparison of two frontiers by hypervolume.

    Returns a single-line summary like:

        "structured has 23.4% more hypervolume than react (0.00614 vs 0.00498)"

    If ``frontier_b`` has zero hypervolume, reports it explicitly instead of
    dividing by zero.
    """
    hv_a = compute_hypervolume(frontier_a, ref_point)
    hv_b = compute_hypervolume(frontier_b, ref_point)

    if hv_b == 0.0 and hv_a == 0.0:
        return f"{label_a} and {label_b} both have zero hypervolume (no point beats ref)"
    if hv_b == 0.0:
        return f"{label_a} dominates ref ({hv_a:.6f}); {label_b} has zero hypervolume"
    if hv_a == 0.0:
        return f"{label_b} dominates ref ({hv_b:.6f}); {label_a} has zero hypervolume"

    pct = (hv_a - hv_b) / hv_b * 100.0
    direction = "more" if pct >= 0 else "less"
    return (
        f"{label_a} has {abs(pct):.1f}% {direction} hypervolume than {label_b} "
        f"({hv_a:.6f} vs {hv_b:.6f})"
    )
