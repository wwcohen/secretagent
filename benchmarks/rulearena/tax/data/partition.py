"""Partition tax .jsonl files into Dataset-format .json files.

Reads:
    data/{train,valid,test}.jsonl
    data/prompt.py (form templates)

Writes:
    data/{train,valid,test}.json (aggregate, Dataset format)
    data/{valid,test}_l{N}.json (per-level stratified slices)

Run from tax/:
    uv run python data/partition.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

# Allow importing calculators.* from the parent directory (tax/)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# Allow importing prompt.py from data/ (this directory)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from calculators.tax import compute_tax_fee  # noqa: E402
from secretagent.dataset import Case, Dataset  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent


def _build_forms_text(taxpayer_dict: dict) -> str:
    """Assemble the filled IRS forms (no task wrapper).

    Returns just the substituted forms (basic + conditional Schedule A/C/8863
    + form 8812). Strategy-specific instructions (task description, output
    format) live in prompt_templates/* or in the simulate / pot / react
    scaffolds, so each strategy can frame the task as it actually needs.
    """
    import prompt as tax_prompt  # data/prompt.py

    forms = [tax_prompt.basic_forms]
    if taxpayer_dict["itemized"]:
        forms.append(tax_prompt.itemized_forms)
    if taxpayer_dict["self_employed"]:
        forms.append(tax_prompt.self_employ_forms)
    if taxpayer_dict["has_student_loans_or_education_expenses"]:
        forms.append(tax_prompt.edu_forms)
    if taxpayer_dict["child_and_dependent"]:
        forms.append(tax_prompt.schedule_8812)
    text = "".join(forms)

    for k, v in taxpayer_dict["data"].items():
        if isinstance(v, str):
            text = text.replace("$" + k, v)
        else:
            text = text.replace("$" + k, "$" + f"{v:,}")

    text = text.replace("$TBD", "[__]")

    text = text.replace("$name", taxpayer_dict["name"])
    text = text.replace("$age", str(taxpayer_dict["age"]))
    text = text.replace("$spouse_age", str(taxpayer_dict["spouse_age"]))
    text = text.replace("$blind", str(taxpayer_dict["blind"]))
    text = text.replace("$spouse_blind", str(taxpayer_dict["spouse_blind"]))
    text = text.replace("$filing_status", taxpayer_dict["filing_status"])
    text = text.replace("$itemized", str(taxpayer_dict["itemized"]))
    text = text.replace("$num_qualifying_children", str(taxpayer_dict["num_qualifying_children"]))
    text = text.replace("$num_other_dependents", str(taxpayer_dict["num_other_dependents"]))
    return text


def _ascii_safe(s: str) -> str:
    return s.encode("ascii", errors="replace").decode("ascii")


def _case_from_record(record: dict) -> tuple[Case, int | None]:
    level = record.get("level")
    orig_idx = record["orig_idx"]
    try:
        expected = compute_tax_fee({"pydantic": record["pydantic"]})
    except Exception as e:
        raise RuntimeError(
            f"calculator failed for orig_idx={orig_idx}, level={level}: {e}"
        ) from e
    if expected is None:
        raise RuntimeError(
            f"calculator returned None for orig_idx={orig_idx}, level={level}"
        )
    forms_text = _ascii_safe(_build_forms_text(record["dict"]))
    name = f"tax_{level}_{orig_idx}" if level is not None else f"tax_{orig_idx}"
    case = Case(
        name=name,
        input_args=(forms_text,),
        expected_output=expected,
    )
    return case, level


def _write(path: Path, split_name: str, cases: list[Case]):
    ds = Dataset(name="rulearena_tax", split=split_name, cases=cases)
    path.write_text(ds.model_dump_json(indent=2))


def _partition(split: str, stratify: bool):
    jsonl_path = DATA_DIR / f"{split}.jsonl"
    if not jsonl_path.exists():
        print(f"skip {split}: {jsonl_path.name} not found")
        return

    with jsonl_path.open(encoding="utf-8") as f:
        pairs = [_case_from_record(json.loads(line)) for line in f]
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
    _partition("train", stratify=False)
    _partition("valid", stratify=True)
    _partition("test", stratify=True)


if __name__ == "__main__":
    main()
