"""RuleArena tax domain: US federal income tax calculation."""

import re
from pathlib import Path
from pydantic import BaseModel

from secretagent.core import interface, implement_via

_DATA_DIR = Path(__file__).parent / "data"


# -- Data models --

class StudentRecord(BaseModel):
    qualified_student_expenses: int = 0
    f8863_part_iii_23: str = "No"
    f8863_part_iii_24: str = "No"
    f8863_part_iii_25: str = "No"
    f8863_part_iii_26: str = "No"


class TaxParams(BaseModel):
    # Basic Info
    name: str = ""
    age: int = 0
    spouse_age: int = 0
    filing_status: str = "single"  # single/married filing jointly/married filing separately/head of household/qualifying surviving spouse
    blind: bool = False
    spouse_blind: bool = False
    itemized: bool = False
    self_employed: bool = False
    has_student_loans_or_education_expenses: bool = False
    num_qualifying_children: int = 0
    num_other_dependents: int = 0

    # Form 1040
    wage_tip_compensation: float = 0.0             # Line 1a
    household_employee_wage: float = 0.0           # Line 1b
    unreported_tip: float = 0.0                    # Line 1c
    nontaxable_combat_pay: float = 0.0             # Line 1d
    tax_exempt_interest: float = 0.0               # Line 2a
    taxable_interest: float = 0.0                  # Line 2b
    qualified_dividends: float = 0.0               # Line 3a
    ordinary_dividends: float = 0.0                # Line 3b
    ira_distributions: float = 0.0                 # Line 4a
    taxable_ira_distributions: float = 0.0         # Line 4b
    all_pensions: float = 0.0                      # Line 5a
    taxable_pensions: float = 0.0                  # Line 5b
    social_security_benefits: float = 0.0          # Line 6a
    taxable_social_security_benefits: float = 0.0  # Line 6b
    qualified_business_income: float = 0.0         # Line 13
    federal_income_tax_withheld: float = 0.0       # Line 25
    earned_income_credit: float = 0.0              # Line 27

    # Schedule 1
    taxable_state_refunds: float = 0.0
    alimony_income: float = 0.0
    sale_of_business: float = 0.0
    rental_real_estate_sch1: float = 0.0
    farm_income: float = 0.0
    unemployment_compensation: float = 0.0
    other_income: float = 0.0
    educator_expenses: float = 0.0
    hsa_deduction: float = 0.0
    ira_deduction: float = 0.0
    student_loan_interest_deduction: float = 0.0
    other_adjustments: float = 0.0

    # Schedule 2
    amt_f6251: float = 0.0
    credit_repayment: float = 0.0
    other_additional_taxes: float = 0.0

    # Schedule 3
    foreign_tax_credit: float = 0.0
    dependent_care: float = 0.0
    retirement_savings: float = 0.0
    elderly_disabled_credits: float = 0.0
    plug_in_motor_vehicle: float = 0.0
    alt_motor_vehicle: float = 0.0

    # Schedule A (when itemized=true)
    medical_dental_expenses: float = 0.0
    state_local_income_or_sales_tax: float = 0.0
    state_local_real_estate_tax: float = 0.0
    state_local_personal_property_tax: float = 0.0
    other_taxes_paid: float = 0.0
    home_mortgage_interest_and_points: float = 0.0
    home_mortgage_interest_unreported: float = 0.0
    home_mortgage_points_unreported: float = 0.0
    investment_interest: float = 0.0
    charity_cash: float = 0.0
    charity_non_cash: float = 0.0
    casualty_and_theft_loss: float = 0.0
    other_itemized_deductions: float = 0.0

    # Schedule C (when self_employed=true)
    gross_receipts: float = 0.0
    returns_and_allowances: float = 0.0
    cost_of_goods_sold: float = 0.0
    other_inc_sched_c: float = 0.0
    total_expenses: float = 0.0
    expenses_of_home: float = 0.0
    total_social_security_wages: float = 0.0

    # Form 8863 (when has_student_loans_or_education_expenses=true)
    student_list: list[StudentRecord] = []


# -- Unstructured (zero-shot) helpers: always bound --

@implement_via('prompt_llm',
               prompt_template_file='prompt_templates/unstructured.txt',
               answer_pattern=None)
def zeroshot_tax(forms_text: str) -> str:
    ...


def _parse_money_token(s: str) -> float:
    """Parse a money-like token: '1,234', '$500', '-$1,234.56', '$-500'."""
    s = s.strip().replace('$', '').replace(',', '').replace(' ', '')
    if not s or s in ('-', '+', '.'):
        raise ValueError(f'empty/degenerate money token: {s!r}')
    return float(s)


def _parse_numeric_answer(llm_output: str) -> float:
    """Extract a signed dollar amount from an unstructured LLM tax response.

    Primary: <answer>xxx</answer> (the format our prompt requests).
    Fallback 1: 'total tax owed/overpaid is $X' (the upstream RuleArena
        prompt format - negated on 'overpaid'/'refunded').
    Fallback 2: last $-prefixed amount anywhere in the text.
    Raises ValueError if no amount found.
    """
    # Primary
    m = re.search(r'<answer>\s*([-\$\d,.\s]+?)\s*</answer>', llm_output, re.IGNORECASE)
    if m:
        try:
            return _parse_money_token(m.group(1))
        except ValueError:
            pass  # malformed inside <answer>; fall through

    # Fallback 1: prose form
    m = re.search(
        r'total\s+tax\s+(owed|overpaid|refunded?)\s+is\s+(-?\$?\s*-?[\d,]+(?:\.\d+)?)',
        llm_output, re.IGNORECASE,
    )
    if m:
        word = m.group(1).lower()
        val = _parse_money_token(m.group(2))
        return -abs(val) if word.startswith(('over', 'refund')) else val

    # Fallback 2: last $-amount in text
    matches = re.findall(r'-?\$\s*-?[\d,]+(?:\.\d+)?', llm_output)
    if matches:
        return _parse_money_token(matches[-1])

    raise ValueError(f"no dollar amount found in LLM output: {llm_output!r}")


# -- Python helpers --

_SCHED_C_DEFAULTS = {
    "gross_receipts": 0.0, "returns_and_allowances": 0.0,
    "cost_of_goods_sold": 0.0, "other_inc_sched_c": 0.0,
    "total_expenses": 0.0, "expenses_of_home": 0.0,
    "total_social_security_wages": 0.0,
}
_SCHED_A_DEFAULTS = {
    "medical_dental_expenses": 0.0, "state_local_income_or_sales_tax": 0.0,
    "state_local_real_estate_tax": 0.0, "state_local_personal_property_tax": 0.0,
    "other_taxes_paid": 0.0, "home_mortgage_interest_and_points": 0.0,
    "home_mortgage_interest_unreported": 0.0, "home_mortgage_points_unreported": 0.0,
    "investment_interest": 0.0, "charity_cash": 0.0, "charity_non_cash": 0.0,
    "casualty_and_theft_loss": 0.0, "other_itemized_deductions": 0.0,
}
_EDU_DEFAULTS = {"student_list": []}


def _apply_tax_defaults(params: dict) -> dict:
    """Fill in zeros for optional Schedule A/C and Form 8863 fields the LLM omits."""
    result = dict(params)
    for defaults in (_SCHED_C_DEFAULTS, _SCHED_A_DEFAULTS, _EDU_DEFAULTS):
        for k, v in defaults.items():
            result.setdefault(k, v)
    if not isinstance(result.get("student_list"), list):
        result["student_list"] = []
    return result


_TAX_KEYS = list(TaxParams.model_fields.keys())


def _tax_calc_fn(*args, **kw) -> float:
    """Compute federal tax owed.

    Accepts four calling conventions because this function is invoked by
    code (positional dict, via tax_workflow), pydantic-ai tools (positional
    expansion of TaxParams fields), and pot-generated code (keyword
    `params=...` form). `params: dict` in the interface signature gives the
    framework no shape info, so we normalize here.
    """
    from calculators.tax import compute_tax_fee

    if 'params' in kw and not args:
        raw = kw['params']
    elif len(args) == 1 and not kw:
        raw = args[0]
    elif len(args) == len(_TAX_KEYS) and not kw:
        raw = dict(zip(_TAX_KEYS, args))
    elif set(kw) == set(_TAX_KEYS) and not args:
        raw = dict(kw)
    else:
        raise TypeError(
            f"unexpected arg shape: args={len(args)}, kw={sorted(kw)}")

    if hasattr(raw, 'model_dump'):
        raw = raw.model_dump()
    if not isinstance(raw, dict):
        raise TypeError(
            f"expected dict or pydantic model, got {type(raw).__name__}")

    result = compute_tax_fee({"pydantic": _apply_tax_defaults(dict(raw))})
    if result is None:
        raise RuntimeError("Tax calculator returned None")
    return result


# -- Interfaces bound via conf.yaml --

@interface
def extract_tax_params(query: str) -> TaxParams:
    """Extract taxpayer parameters from filled IRS forms.

    Extract the filled-in INPUT values from IRS forms. Skip computed
    fields marked [__]. Dollar values like "$1,234" become numeric (1234.0).
    """
    ...


@interface
def compute_tax_calculator(params: dict) -> float:
    """Compute federal tax amount from extracted TaxPayer fields.

    Pass the dict returned by extract_tax_params directly as params.
    Optional schedule fields are defaulted to 0 if absent.

    Returns:
        Amount owed (positive) or overpaid/refund (negative) as float.
    """


# -- Top-level interface --

@interface
def compute_tax_answer(forms_text: str) -> float:
    """Given filled IRS forms with some fields marked [__] for computation,
    calculate all tax fields step by step and return the total tax owed
    (positive) or overpaid/refund (negative) as a dollar amount.
    """
    ...


# -- Workflows (bound via conf.yaml as direct implementations) --

def tax_workflow(forms_text: str) -> float:
    """Handcoded workflow: LLM extracts params, Python computes tax."""
    params = extract_tax_params(query=forms_text)
    return float(compute_tax_calculator(params.model_dump()))


def unstructured_workflow(forms_text: str) -> float:
    """Zero-shot unstructured workflow: prompt LLM, parse numeric answer."""
    raw = zeroshot_tax(forms_text=forms_text)
    return _parse_numeric_answer(raw)
