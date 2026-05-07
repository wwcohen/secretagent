# /// script
# dependencies = ["datasets"]
# ///
"""Download MUSR dataset from HuggingFace and save as JSON files."""

import json
from pathlib import Path
from datasets import load_dataset

SPLITS = ["murder_mysteries", "object_placements", "team_allocation"]

def main():
    out = Path(__file__).parent
    ds = load_dataset("TAUR-Lab/MuSR")
    for split in SPLITS:
        data = [dict(row) for row in ds[split]]
        path = out / f"{split}.json"
        with open(path, "w") as f:
            json.dump({"split": split, "examples": data}, f, indent=2)
        print(f"{split}: {len(data)} examples -> {path}")

if __name__ == "__main__":
    main()
