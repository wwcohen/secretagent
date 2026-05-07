#!/usr/bin/env python3
"""Download tau-bench retail data files.

Source: https://github.com/sierra-research/tau2-bench
License: MIT

Run from the project root:
    uv run benchmarks/tau_bench_retail/data/download.py
"""

import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent

BASE_URL = "https://raw.githubusercontent.com/sierra-research/tau2-bench/main"

FILES = {
    "db.json": f"{BASE_URL}/data/tau2/domains/retail/db.json",
    "tasks.json": f"{BASE_URL}/data/tau2/domains/retail/tasks.json",
    "policy.md": f"{BASE_URL}/data/tau2/domains/retail/policy.md",
}


def download(name: str, url: str) -> None:
    dest = DATA_DIR / name
    if dest.exists():
        print(f"  {name}: already exists, skipping")
        return
    print(f"  {name}: downloading...", end=" ", flush=True)
    urllib.request.urlretrieve(url, dest)
    size_kb = dest.stat().st_size / 1024
    print(f"done ({size_kb:.0f} KB)")


if __name__ == "__main__":
    print(f"Downloading tau-bench retail data to {DATA_DIR}/")
    for name, url in FILES.items():
        download(name, url)
    print("Done.")
