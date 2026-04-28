"""Partition NBA .jsonl files into Dataset-format .json files.

Reads:
    data/reference_rules.txt
    data/{train,valid,test}.jsonl

Writes:
    data/{train,valid,test}.json (aggregate, Dataset format)
    data/{valid,test}_l{N}.json (per-level stratified slices)

Run from nba/:
    uv run python data/partition.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ptools import _NBA_ASSUMPTIONS  # noqa: E402
from secretagent.dataset import Case, Dataset  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent


def _rules_text() -> str:
    return (DATA_DIR / "reference_rules.txt").read_text(encoding="utf-8")


def _build_problem_text(record: dict) -> str:
    """Assemble the NBA problem text from jsonl record fields.

    Includes team situations, player situations, operations, salary cap
    assumptions, and the task framing question. Does NOT include rules_text
    — that is a separate argument to the top-level interface.
    """
    team_info = "Team Situations:\n" + "\n".join(record.get("team_situations", []))
    player_info = "Player Situations:\n" + "\n".join(record.get("player_situations", []))
    operations = "Operations:\n" + "\n".join(record.get("operations", []))

    return (
        f"{_NBA_ASSUMPTIONS}\n"
        f"Decide whether any operation by any team violates the rules:\n\n"
        f"{team_info}\n\n{player_info}\n\n{operations}"
    )


def _case_from_record(record: dict, rules_text: str) -> tuple[Case, int | None]:
    level = record.get("level")
    orig_idx = record["orig_idx"]
    expected = float(bool(record["answer"]))
    problem_text = _build_problem_text(record)
    name = f"nba_{level}_{orig_idx}" if level is not None else f"nba_{orig_idx}"
    case = Case(
        name=name,
        input_args=(problem_text, rules_text),
        expected_output=expected,
    )
    return case, level


def _write(path: Path, split_name: str, cases: list[Case]):
    ds = Dataset(name="rulearena_nba", split=split_name, cases=cases)
    path.write_text(ds.model_dump_json(indent=2))


def _partition(split: str, rules_text: str, stratify: bool):
    jsonl_path = DATA_DIR / f"{split}.jsonl"
    if not jsonl_path.exists():
        print(f"skip {split}: {jsonl_path.name} not found")
        return

    with jsonl_path.open(encoding="utf-8") as f:
        pairs = [_case_from_record(json.loads(line), rules_text) for line in f]
    cases = [c for c, _ in pairs]
    levels = [lv for _, lv in pairs]

    aggregate_path = DATA_DIR / f"{split}.json"
    _write(aggregate_path, split, cases)
    counts = defaultdict(int)
    for lv in levels:
        if lv is not None:
            counts[lv] += 1
    detail = ", ".join(f"l{lv}: {counts[lv]}" for lv in sorted(counts))
    print(f"Wrote {aggregate_path.name}: {len(cases)} cases" + (f" [{detail}]" if detail else ""))

    if not stratify:
        return
    if not any(lv is not None for lv in levels):
        print("  skip per-level: no 'level' field on cases")
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
