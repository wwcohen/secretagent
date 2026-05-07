#!/usr/bin/env python3
"""Aggregate Together AI costs by API key from an organization costs CSV.

Usage:
    python scripts/together_ai_costs_by_key.py COSTS.csv [--by-date]
"""

import argparse
import csv
import re
import sys
from collections import defaultdict


def parse_amount(s: str) -> float:
    """Parse a dollar amount like '$0.39' to a float."""
    return float(s.strip().lstrip("$"))


def extract_api_key(dimensions: str) -> str:
    """Extract api_key_id value from the Dimensions field."""
    m = re.search(r"api_key_id:(\S+?)(?:,|$)", dimensions)
    return m.group(1) if m else "unknown"


def main():
    parser = argparse.ArgumentParser(description="Aggregate Together AI costs by API key")
    parser.add_argument("csv_file", help="Path to the Together AI organization costs CSV")
    parser.add_argument("--by-date", action="store_true", help="Also break down costs by date")
    args = parser.parse_args()

    totals_by_key = defaultdict(float)
    totals_by_key_date = defaultdict(lambda: defaultdict(float))

    with open(args.csv_file, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            api_key = extract_api_key(row["Dimensions"])
            amount = parse_amount(row["Amount (USD)"])
            totals_by_key[api_key] += amount
            if args.by_date:
                totals_by_key_date[api_key][row["Date"]] += amount

    grand_total = sum(totals_by_key.values())

    print(f"{'API Key':<40s} {'Amount':>10s} {'%':>6s}")
    print("-" * 58)
    for key, total in sorted(totals_by_key.items(), key=lambda x: -x[1]):
        pct = 100.0 * total / grand_total if grand_total else 0
        print(f"{key:<40s} ${total:>9.2f} {pct:>5.1f}%")
        if args.by_date:
            for date, amt in sorted(totals_by_key_date[key].items()):
                print(f"  {date:<38s} ${amt:>9.2f}")
    print("-" * 58)
    print(f"{'TOTAL':<40s} ${grand_total:>9.2f}")


if __name__ == "__main__":
    main()
