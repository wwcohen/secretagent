"""Partition airline .jsonl files into Dataset-format .json files.
                                                                                                                                               
Reads:                                                                           
data/reference_rules_textual.txt                                                                                                           
data/{train,valid,test}.jsonl                                                                                                              
                                                            
Writes:                                                                                                                                      
data/{train,valid,test}.json (aggregate, Dataset format)                                                                                 
data/{valid,test}_l{N}.json (per-level stratified slices, if `level` field present)                                                        
                                                                                
Run from airline/:
    uv run python data/partition.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

# Allow importing calculators.* from the parent directory (airline/)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calculators.airline import compute_airline_fee
from secretagent.dataset import Case, Dataset

DATA_DIR = Path(__file__).resolve().parent

def _rules_text() -> str:
    return (DATA_DIR / "reference_rules_textual.txt").read_text(encoding="utf-8")

def _case_from_record(record: dict, rules_text: str) -> tuple[Case, int | None]:
    level = record.get("level")  # optional: tax/nba may not carry a level field
    orig_idx = record["orig_idx"]
    # TODO(Phase 3): if tax/nba jsonl ships an 'answer' field, use upstream as
    # primary ground truth and make the calculator a verification step (warn
    # loudly on mismatch). For airline, no such field exists - calculator is
    # necessarily the source of truth.
    try:
        expected = compute_airline_fee(record["info"])
    except Exception as e:
        raise RuntimeError(
            f"calculator failed for orig_idx={orig_idx}, level={level}: {e}"
        ) from e
    name = f"airline_{level}_{orig_idx}" if level is not None else f"airline_{orig_idx}"
    case = Case(
        name=name,
        input_args=(record["prompt"], rules_text),
        expected_output=expected,
    )
    return case, level

def _write(path: Path, split_name: str, cases: list[Case]):
    ds = Dataset(name="rulearena_airline", split=split_name, cases=cases)
    path.write_text(ds.model_dump_json(indent=2), encoding="utf-8")

def _partition(split: str, rules_text: str, stratify: bool):
    jsonl_path = DATA_DIR / f"{split}.jsonl"
    if not jsonl_path.exists():
        print(f"skip {split}: {jsonl_path.name} not found")
        return 

    with jsonl_path.open(encoding="utf-8") as f:
        pairs = [_case_from_record(json.loads(line), rules_text) for line in f]
    cases = [c for c, _ in pairs]
    levels = [lv for _, lv in pairs]

    # Aggregate file
    aggregate_path = DATA_DIR / f"{split}.json"
    _write(aggregate_path, split, cases)
    counts = defaultdict(int)
    for lv in levels:
        if lv is not None:
            counts[lv] += 1
    detail = ", ".join(f"l{lv}: {counts[lv]}" for lv in sorted(counts))
    print(f"Wrote {aggregate_path.name}: {len(cases)} cases" + (f" [{detail}]" if detail else ""))

    # Per-level slices (opt-in via `stratify`, and only if level field present)
    if not stratify:
        return
    if not any(lv is not None for lv in levels):
        print(f"  skip per-level: no 'level' field on cases")
        return
    per_level: dict[int, list[Case]] = defaultdict(list)
    for case, lv in zip(cases, levels):
        if lv is not None:
            per_level[lv].append(case)
    for lv in sorted(per_level):
        path = DATA_DIR / f"{split}_l{lv}.json"
        _write(path, f"{split}_l{lv}", per_level[lv])
        print(f"  -> {path.name}: {len(per_level[lv])} cases")

def main():
    rules_text = _rules_text()
    print(f"Loaded rules ({len(rules_text)} chars)")
    _partition("train", rules_text, stratify=False)
    _partition("valid", rules_text, stratify=True)
    _partition("test",  rules_text, stratify=True)


if __name__ == "__main__":
    main()
    