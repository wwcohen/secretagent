# /// script
# dependencies = ["requests"]
# ///
"""Download TabMWP dataset from the PromptPG GitHub repository.

Source: https://github.com/lupantech/PromptPG/tree/main/data/tabmwp
License: CC BY-NC-SA 4.0

Usage:
    uv run benchmarks/tabmwp/data/download.py
"""

import json
from pathlib import Path

import requests

BASE_URL = "https://raw.githubusercontent.com/lupantech/PromptPG/main/data/tabmwp"

FILES = [
    "problems_train.json",
    "problems_dev.json",
    "problems_test.json",
    "problems_dev1k.json",
    "problems_test1k.json",
    "splits.json",
]


def download_file(url: str, dest: Path) -> None:
    """Download a file from a URL to a local path."""
    print(f"Downloading {url} ...")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    print(f"  -> {dest}")


def summarize(path: Path) -> None:
    """Print basic stats for a downloaded problems file."""
    with open(path) as f:
        data = json.load(f)
    n = len(data)
    ques_types = {}
    grades = {}
    for ex in data.values():
        qt = ex.get("ques_type", "unknown")
        gr = ex.get("grade", "unknown")
        ques_types[qt] = ques_types.get(qt, 0) + 1
        grades[gr] = grades.get(gr, 0) + 1
    print(f"  {path.name}: {n} examples")
    print(f"    question types: {ques_types}")
    print(f"    grades: {dict(sorted(grades.items()))}")


def main():
    out = Path(__file__).parent
    for filename in FILES:
        url = f"{BASE_URL}/{filename}"
        dest = out / filename
        if dest.exists():
            print(f"Already exists: {dest}, skipping")
        else:
            download_file(url, dest)

    # Print summaries for the main splits
    print("\n--- Dataset summaries ---")
    for filename in ["problems_train.json", "problems_dev.json", "problems_test.json"]:
        path = out / filename
        if path.exists():
            summarize(path)


if __name__ == "__main__":
    main()
