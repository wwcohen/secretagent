#!/usr/bin/env python3
"""Download official FinQA JSON splits from the czyssrs/FinQA repository.

Run from the repository root or from this directory::

    uv run python benchmarks/finqa/data/download.py

Files are written to ``benchmarks/finqa/data/raw/``:

- ``train.json``, ``dev.json``, ``test.json`` — labeled splits

Next step: ``uv run python benchmarks/finqa/data/build_datasets.py``
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/czyssrs/FinQA/main/dataset"
FILES = [
    "train.json",
    "dev.json",
    "test.json",
]


def main() -> None:
    raw_dir = Path(__file__).resolve().parent / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    for name in FILES:
        url = f"{BASE}/{name}"
        dest = raw_dir / name
        print(f"Downloading {url} -> {dest}")
        urllib.request.urlretrieve(url, dest)
        print(f"  wrote {dest.stat().st_size} bytes")

    print("Done. Run: uv run python benchmarks/finqa/data/build_datasets.py")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as e:
        print(f"Download failed: {e}", file=sys.stderr)
        sys.exit(1)
