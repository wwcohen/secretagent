import sys
from pathlib import Path
from typing import Dict, Any, Optional

DATA_DIR = Path(__file__).parent.parent / "data"
TAX_DIR = str(DATA_DIR / "tax")

if TAX_DIR not in sys.path:
    sys.path.insert(0, TAX_DIR)

try:
    from structured_forms import TaxPayer, FilingStatus
    from micro_evaluation import compute_answer
except Exception as e:
    print(f"Warning: Could not load tax reference implementation: {e}")
    TaxPayer = None
    compute_answer = None


def _taxpayer_defaults() -> Dict[str, Any]:
    """Return sensible defaults for every required TaxPayer field."""
    if TaxPayer is None:
        return {}
    from pydantic_core import PydanticUndefined
    defaults: Dict[str, Any] = {}
    for name, field_info in TaxPayer.model_fields.items():
        annotation = field_info.annotation
        # Skip fields that already have a default value
        if field_info.default is not PydanticUndefined:
            continue
        # Determine type-appropriate zero value
        if annotation is float:
            defaults[name] = 0.0
        elif annotation is int:
            defaults[name] = 0
        elif annotation is bool:
            defaults[name] = False
        elif annotation is str:
            defaults[name] = ""
        elif annotation is FilingStatus:
            defaults[name] = FilingStatus.SINGLE
    return defaults


def compute_tax_fee(info: Dict[str, Any]) -> Optional[float]:
    """
    Compute tax amount from a RuleArena tax problem dict.

    Args:
        info: dict with a "pydantic" key whose value is the TaxPayer fields

    Returns:
        Amount owed (positive) or overpaid (negative), or None on failure
    """
    if TaxPayer is None or compute_answer is None:
        return None

    try:
        merged = {**_taxpayer_defaults(), **info["pydantic"]}
        tp = TaxPayer(**merged)
        amount, _ = compute_answer(tp)
        return float(amount)
    except Exception as e:
        print(f"Error computing tax fee: {e}")
        return None
