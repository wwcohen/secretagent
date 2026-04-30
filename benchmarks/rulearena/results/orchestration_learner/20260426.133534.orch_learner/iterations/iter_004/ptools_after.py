"""RuleArena benchmark tools and workflows.

Domains: airline (baggage fees), tax (US federal income tax), nba (CBA compliance).
Experiment levels:
  L0  - oracle: ground truth params fed directly to Python calculators
  L0F - CoT: single LLM call per domain with chain-of-thought prompt
  L1  - extract: LLM extracts structured params, Python computes answer
  L3  - ReAct: autonomous agent with extraction and calculator tools

Example CLI commands:
    uv run expt.py run --help
    uv run expt.py run evaluate.expt_name=l1_airline dataset.domain=airline \
        ptools.compute_rulearena_answer.method=direct \
        ptools.compute_rulearena_answer.fn=ptools.l1_extract_workflow
"""

import importlib.util
import json
# from math import e
import re
import sys
from pathlib import Path
from typing import Any
from pydantic import BaseModel

# from secretagent.benchmarks.rulearena.search_spaces import tax_space
from secretagent.core import interface, implement_via

_DATA_DIR = Path(__file__).parent / "data"

class BagItem(BaseModel):
    id: int
    name: str
    size: list[int]  # [length, width, height] in inches
    weight: int       # pounds

class AirlineParams(BaseModel):
    base_price: int         # ticket price in USD
    customer_class: str     # e.g "Main Cabin", "Business"
    routine: str            # destination region, e.g. "U.S", "Japan"
    direction: int          # 0 for departing from US, 1 for arriving to US
    bag_list: list[BagItem] 

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
    taxable_state_refunds: float = 0.0                 # Line 1
    alimony_income: float = 0.0                        # Line 2a
    sale_of_business: float = 0.0                      # Line 4
    rental_real_estate_sch1: float = 0.0               # Line 5
    farm_income: float = 0.0                           # Line 6
    unemployment_compensation: float = 0.0             # Line 7
    other_income: float = 0.0                          # Line 8
    educator_expenses: float = 0.0                     # Line 11
    hsa_deduction: float = 0.0                         # Line 13
    ira_deduction: float = 0.0                         # Line 20
    student_loan_interest_deduction: float = 0.0       # Line 21
    other_adjustments: float = 0.0                     # Line 24

    # Schedule 2
    amt_f6251: float = 0.0                            # Line 1
    credit_repayment: float = 0.0                     # Line 2
    other_additional_taxes: float = 0.0               # Line 17

    # Schedule 3
    foreign_tax_credit: float = 0.0                  # Line 1
    dependent_care: float = 0.0                     # Line 2
    retirement_savings: float = 0.0                 # Line 4
    elderly_disabled_credits: float = 0.0           # Line 6d
    plug_in_motor_vehicle: float = 0.0              # Line 6i
    alt_motor_vehicle: float = 0.0                 # Line 6j

    # Schedule A (when itemized=true) 
    medical_dental_expenses: float = 0.0            # Line 1
    state_local_income_or_sales_tax: float = 0.0   # Line 5a
    state_local_real_estate_tax: float = 0.0       # Line 5b
    state_local_personal_property_tax: float = 0.0 # Line 5c
    other_taxes_paid: float = 0.0                    # Line 5d
    home_mortgage_interest_and_points: float = 0.0 # Line 8a
    home_mortgage_interest_unreported: float = 0.0 # Line 8b
    home_mortgage_points_unreported: float = 0.0   # Line 8c
    investment_interest: float = 0.0                # Line 9
    charity_cash: float = 0.0                      # Line 11
    charity_non_cash: float = 0.0                  # Line 12
    casualty_and_theft_loss: float = 0.0           # Line 15
    other_itemized_deductions: float = 0.0        # Line 16

    # Schedule C (when self_employed=true)
    gross_receipts: float = 0.0                   # Line 1
    returns_and_allowances: float = 0.0           # Line 2
    cost_of_goods_sold: float = 0.0              # Line 4
    other_inc_sched_c: float = 0.0               # Line 5
    total_expenses: float = 0.0                          # Line 10
    expenses_of_home: float = 0.0                         # Line 30
    total_social_security_wages: float = 0.0              # Line 31

    # Form 8863 (when has_student_loans_or_education_expenses=true)
    student_list: list[StudentRecord] = []

class NbaResult(BaseModel):
    verdict: bool = False          # true if any operation violates rules
    illegal_operation: str = ""    # letter of the violating operation
    problematic_team: str = ""     # letter of the violating team
    reasoning: str = ""            # brief explanation


# ---------------------------------------------------------------------------
# LLM extraction interfaces
# ---------------------------------------------------------------------------

@interface
def extract_airline_params(query: str) -> AirlineParams:
    """Extract structured baggage parameters from an airline fee query."""
    ...


@interface
def extract_tax_params(query: str) -> TaxParams:
    """Extract taxpayer parameters from filled IRS forms.

    Extract the filled-in INPUT values from IRS forms. Skip computed
    fields marked [__]. Dollar values like "$1,234" become numeric (1234.0).
    """
    ...


@interface
def extract_nba_params(query: str) -> NbaResult:
    """Determine whether any NBA team operation violates CBA salary cap rules."""
    ...
# ---------------------------------------------------------------------------
# Calculator interfaces (always Python via direct method)
# ---------------------------------------------------------------------------

@interface
def compute_airline_calculator(params: dict) -> int:
    """Compute airline baggage fee and total ticket cost.

    Pass the dict returned by extract_airline_params directly as params.
    Required keys: base_price, customer_class, routine, direction, bag_list.

    Returns:
        Total cost (ticket price + baggage fees) as integer dollars.

    Examples:
    >>> compute_airline_calculator({"base_price": 500, "customer_class": "Main Cabin", "routine": "U.S.", "direction": 0, "bag_list": [{"id": 1, "name": "carry-on", "size": [22, 14, 9], "weight": 10}]})
    500
    """


@interface
def compute_tax_calculator(params: dict) -> float:
    """Compute federal tax amount from extracted TaxPayer fields.

    Pass the dict returned by extract_tax_params directly as params.
    Optional schedule fields are defaulted to 0 if absent.

    Returns:
        Amount owed (positive) or overpaid/refund (negative) as float.

    Examples:
    >>> compute_tax_calculator({"filing_status": "single", "age": 35, "wage_tip_compensation": 50000.0})
    5000.0
    """


# ---------------------------------------------------------------------------
# CoT prompt interfaces (always prompt_llm, bound at definition time)
# ---------------------------------------------------------------------------

@implement_via('prompt_llm', prompt_template_file='prompt_templates/airline_cot.txt')
def _cot_airline(problem_text: str, rules_text: str) -> str:
    ...


@implement_via('prompt_llm', prompt_template_file='prompt_templates/tax_cot.txt')
def _cot_tax(forms_text: str) -> str:
    ...


@implement_via('prompt_llm', prompt_template_file='prompt_templates/nba_cot.txt')
def _cot_nba(problem_text: str, rules_text: str) -> str:
    ...



@implement_via('simulate')
def _parse_numeric_answer(llm_output: str) -> float:
    """Extract the numeric dollar amount from LLM text output.

    The output may contain "The total cost is $1,234." or
    "The total tax owed is $567." or "The total tax overpaid is $89."
    For overpaid amounts, return the value as negative.
    """
    ...


@implement_via('simulate')
def _parse_bool_answer(llm_output: str) -> bool:
    """Extract True or False from LLM text output.

    The output contains either "Answer: True." or "Answer: False."
    """
    ...


# ---------------------------------------------------------------------------
# Python calculator implementations (called from workflows, not interfaces)
# ---------------------------------------------------------------------------

# Region normalization for airline extraction
_VALID_REGIONS = {
    "U.S.", "Puerto Rico", "Canada", "Mexico", "Cuba", "Haiti", "Panama",
    "Colombia", "Ecuador", "Peru", "South America", "Israel", "Qatar",
    "Europe", "India", "China", "Japan", "South Korea", "Hong Kong",
    "Australia", "New Zealand",
}

_REGION_FIXES = {
    "asia": "China",
    "north america": "U.S.",
    "us": "U.S.",
    "usa": "U.S.",
    "united states": "U.S.",
    "domestic": "U.S.",
    "tokyo": "Japan",
    "beijing": "China",
    "shanghai": "China",
    "seoul": "South Korea",
    "sydney": "Australia",
    "london": "Europe",
    "paris": "Europe",
    "berlin": "Europe",
}


def _normalize_region(routine: str) -> str:
    if routine in _VALID_REGIONS:
        return routine
    fixed = _REGION_FIXES.get(routine.lower().strip())
    return fixed if fixed else "U.S."


def _airline_calc_fn(params: dict) -> int:
    from calculators.airline import compute_airline_fee
    p = dict(params)
    p["routine"] = _normalize_region(p.get("routine", "U.S."))
    return compute_airline_fee(p)


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
    result = dict(params)
    for defaults in (_SCHED_C_DEFAULTS, _SCHED_A_DEFAULTS, _EDU_DEFAULTS):
        for k, v in defaults.items():
            result.setdefault(k, v)
    # Ensure student_list is always a list (LLM may return 0, false, etc.)
    if not isinstance(result.get("student_list"), list):
        result["student_list"] = []
    return result


def _tax_calc_fn(params: dict) -> float:
    from calculators.tax import compute_tax_fee
    result = compute_tax_fee({"pydantic": _apply_tax_defaults(params)})
    if result is None:
        raise RuntimeError("Tax calculator returned None")
    return result


# ---------------------------------------------------------------------------
# Tax forms query builder (needed for L0F and L1 tax domain)
# ---------------------------------------------------------------------------

_tax_prompt_module = None


def _get_tax_prompt_module():
    global _tax_prompt_module
    if _tax_prompt_module is not None:
        return _tax_prompt_module
    prompt_path = _DATA_DIR / "tax" / "prompt.py"
    spec = importlib.util.spec_from_file_location("tax_prompt", prompt_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _tax_prompt_module = mod
    return mod


_TAX_PROMPT_TEMPLATE = (
    "\nYou are given several forms used to report US income tax and the instructions "
    "or rules about how to fill the forms. Then you will be given the income and/or "
    "payment information about a tax payer According to the given information. You "
    "should calculate the income tax owed by this payer.\n\nIRS Forms for the tax "
    "payer:\n$forms\nCalculate the tax owed by the payer step-by-step according to "
    "the information provided by the forms. You should calculate all fields marked "
    "with [__]. DO NOT round numbers without explicit instructions. End your response "
    "with <answer>xxx</answer> where xxx is the total tax amount as a number "
    "(negative if overpaid/refunded).\nYour response:\n"
)


def build_tax_forms_query(metadata: dict) -> str:
    """Build the filled IRS forms prompt from taxpayer metadata dict.

    Replicates the logic from external/RuleArena/tax/auto_test.py.
    """
    mod = _get_tax_prompt_module()
    tax_payer = metadata["dict"]

    forms = [mod.basic_forms]
    if tax_payer["itemized"]:
        forms.append(mod.itemized_forms)
    if tax_payer["self_employed"]:
        forms.append(mod.self_employ_forms)
    if tax_payer["has_student_loans_or_education_expenses"]:
        forms.append(mod.edu_forms)
    if tax_payer["child_and_dependent"]:
        forms.append(mod.schedule_8812)
    forms = "".join(forms)

    for k, v in tax_payer["data"].items():
        if isinstance(v, str):
            forms = forms.replace("$" + k, v)
        else:
            forms = forms.replace("$" + k, "$" + f"{v:,}")

    forms = forms.replace("$TBD", "[__]")

    prompt = _TAX_PROMPT_TEMPLATE.replace("$forms", forms)
    prompt = prompt.replace("$name", tax_payer["name"])
    prompt = prompt.replace("$age", str(tax_payer["age"]))
    prompt = prompt.replace("$spouse_age", str(tax_payer["spouse_age"]))
    prompt = prompt.replace("$blind", str(tax_payer["blind"]))
    prompt = prompt.replace("$spouse_blind", str(tax_payer["spouse_blind"]))
    prompt = prompt.replace("$filing_status", tax_payer["filing_status"])
    prompt = prompt.replace("$itemized", str(tax_payer["itemized"]))
    prompt = prompt.replace("$num_qualifying_children", str(tax_payer["num_qualifying_children"]))
    prompt = prompt.replace("$num_other_dependents", str(tax_payer["num_other_dependents"]))
    return prompt


# ---------------------------------------------------------------------------
# NBA query builder
# ---------------------------------------------------------------------------

_NBA_ASSUMPTIONS = (
    "Assume:\n"
    "* the Salary Cap for the prior (2023-24) Salary Cap Year is $136,000,000;\n"
    "* the Average Player Salary for the prior (2023-24) Salary Cap Year is $9,700,000;\n"
    "* the Salary Cap for the current (2024-25) NBA Salary Cap Year is $140,588,000;\n"
    "* the Luxury Tax is $170,814,000;\n"
    "* the First Apron Level is $178,132,000;\n"
    "* the Second Apron Level is $188,931,000;\n"
    "* the Team Salary of each team listed under \"Team Situations:\" do not "
    "include the amount of contracts that expire at the end of 2023-2024 Salary Cap Year.\n"
)


def _build_nba_query(problem_text: str, rules_text: str, metadata: dict) -> str:
    team_info = "Team Situations:\n" + "\n".join(metadata.get("team_situations", []))
    player_info = "Player Situations:\n" + "\n".join(metadata.get("player_situations", []))
    operations = "Operations:\n" + "\n".join(metadata.get("operations", []))
    question = team_info + "\n\n" + player_info + "\n\n" + operations

    return (
        f"Reference Rules in NBA Collective Bargaining Agreement:\n\n"
        f"{rules_text}\n\n"
        f"{_NBA_ASSUMPTIONS}\n"
        f"Decide whether any operation by any team violates the rules:\n\n"
        f"{question}"
    )


# ---------------------------------------------------------------------------
# PoT interfaces (program_of_thought, bound at runtime via config)
# ---------------------------------------------------------------------------

@interface
def pot_airline(problem_text: str, rules_text: str) -> float:
    """Given a passenger's itinerary and baggage details, and the airline's
    fee rules, compute the total cost (ticket price + baggage fees) in dollars.
    """


@interface
def pot_nba(problem_text: str, rules_text: str) -> float:
    """Given NBA team situations, player situations, proposed operations, and
    CBA salary cap rules, determine if any operation violates the rules.
    Return 1.0 if any violation exists, 0.0 if all operations are compliant.
    """


@interface
def pot_tax(forms_text: str) -> float:
    """Given filled IRS forms with some fields marked [__] for computation,
    calculate all tax fields step by step and return the total tax owed
    (positive) or overpaid/refund (negative) as a dollar amount.
    """


# ---------------------------------------------------------------------------
# PoT workflow dispatcher
# ---------------------------------------------------------------------------

def pot_workflow(
    problem_text: str, domain: str, rules_text: str,
    metadata_json: str, forms_text: str
) -> float:
    """PoT workflow: LLM generates Python code, interpreter executes it."""
    if domain == "airline":
        return pot_airline(problem_text=problem_text, rules_text=rules_text)
    if domain == "nba":
        metadata = json.loads(metadata_json)
        nba_query = _build_nba_query(problem_text, rules_text, metadata)
        return pot_nba(problem_text=nba_query, rules_text="")
    if domain == "tax":
        return pot_tax(forms_text=forms_text)
    raise ValueError(f"PoT not yet implemented for domain: {domain!r}")


# ---------------------------------------------------------------------------
# Workflow functions
# ---------------------------------------------------------------------------

def l0_oracle_workflow(
    problem_text: str, domain: str, rules_text: str,
    metadata_json: str, forms_text: str
) -> float:
    """Oracle workflow: feed ground-truth params directly to Python calculators.

    Zero LLM calls. Establishes the accuracy ceiling for each domain.
    NBA returns 1.0 for violation, 0.0 for compliant.
    """
    metadata = json.loads(metadata_json)
    if domain == "airline":
        return float(_airline_calc_fn(metadata))
    if domain == "tax":
        return _tax_calc_fn(metadata.get("pydantic", metadata))
    if domain == "nba":
        return float(bool(metadata.get("answer", False)))
    raise ValueError(f"Unknown domain: {domain!r}")


def l0f_cot_workflow(
    problem_text: str, domain: str, rules_text: str,
    metadata_json: str, forms_text: str
) -> float:
    """CoT baseline: single LLM call per domain with structured prompt, then parse answer.

    Replicates the original RuleArena paper's CoT evaluation methodology.
    """
    if domain == "airline":
        raw = _cot_airline(problem_text=problem_text, rules_text=rules_text)
        return _parse_numeric_answer(raw)
    if domain == "tax":
        raw = _cot_tax(forms_text=forms_text)
        return _parse_numeric_answer(raw)
    if domain == "nba":
        metadata = json.loads(metadata_json)
        nba_query = _build_nba_query(problem_text, rules_text, metadata)
        raw = _cot_nba(problem_text=nba_query, rules_text="")
        return float(_parse_bool_answer(raw))
    raise ValueError(f"Unknown domain: {domain!r}")


def l1_extract_workflow(
    problem_text: str, domain: str, rules_text: str,
    metadata_json: str, forms_text: str
) -> float:
    """L1 PTool workflow: LLM extracts structured params, Python computes answer.

    LLM extracts structured params via simulate_pydantic, Python computes answer.
    """
    metadata = json.loads(metadata_json)
    if domain == "airline":
        query = f"RULES:\n{rules_text}\n\nQUERY:\n{problem_text}"
        params = extract_airline_params(query=query)
        return float(_airline_calc_fn(params.model_dump()))

    if domain == "tax":
        params = extract_tax_params(query=forms_text)
        return _tax_calc_fn(params.model_dump())

    if domain == "nba":
        query = _build_nba_query(problem_text, rules_text, metadata)
        result = extract_nba_params(query=query)
        return float(result.verdict)

    raise ValueError(f"Unknown domain: {domain!r}")


# ---------------------------------------------------------------------------
# Top-level interface
# ---------------------------------------------------------------------------

@interface
def compute_rulearena_answer(
    problem_text: str,
    domain: str,
    rules_text: str,
    metadata_json: str,
    forms_text: str,
) -> float:
    """Compute the answer for a RuleArena benchmark problem.

    Returns the numeric answer: dollar amount for airline and tax domains,
    or 1.0 (violation) / 0.0 (compliant) for the NBA domain.

    Args:
        problem_text: Natural language problem statement.
        domain: One of "airline", "tax", "nba".
        rules_text: Domain rules text provided to the model.
        metadata_json: JSON-encoded ground truth metadata (used by L0 oracle).
        forms_text: Pre-built IRS forms text for tax domain; empty for others.
    """
    ...


