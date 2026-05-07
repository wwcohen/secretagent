"""Airline baggage fee calculator.

Thin wrapper around the vendored RuleArena reference implementation in
calculators/rulearena_reference.py. Loads fee tables from
airline/data/fee_tables/ and invokes compute_answer unchanged.
"""

from pathlib import Path
from typing import Dict, Any

import pandas as pd

from . import rulearena_reference

DATA_DIR = Path(__file__).parent.parent / "data"


def _load_fee_tables():
    """Load baggage fee CSVs from airline/data/fee_tables/bag_[1-4]/[0|1].csv.

    The vendored rulearena_reference.load_checking_fee() expects an extra
    /airline/ segment in the path that existed in the upstream repo layout
    but not here — so we load the CSVs directly and pass the result into
    compute_answer.
    """
    check_base = []
    for bag_num in range(1, 5):
        us_departure = pd.read_csv(
            DATA_DIR / f"fee_tables/bag_{bag_num}/0.csv", index_col=0
        )
        us_arrival = pd.read_csv(
            DATA_DIR / f"fee_tables/bag_{bag_num}/1.csv", index_col=0
        )
        check_base.append({0: us_departure, 1: us_arrival})
    return check_base


try:
    FEE_TABLES = _load_fee_tables()
except Exception as e:
    print(f"Warning: Could not load airline fee tables: {e}")
    FEE_TABLES = None


def compute_airline_fee(info: Dict[str, Any]) -> int:
    """Compute airline baggage fee from problem info dict.

    Args:
        info: dict with keys base_price, direction, routine, customer_class, bag_list.

    Returns:
        Total cost (ticket price + baggage fees) as int.
    """
    if FEE_TABLES is None:
        raise RuntimeError("Fee tables not loaded - check airline/data/fee_tables/")

    total_cost, _ = rulearena_reference.compute_answer(
        base_price=info['base_price'],
        direction=info['direction'],
        routine=info['routine'],
        customer_class=info['customer_class'],
        bag_list=info['bag_list'],
        check_base_tables=FEE_TABLES,
    )
    return int(total_cost)
