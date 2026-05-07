"""
Simplified Medical Calculators with Explicit Type Signatures.

Each calculator is a pure function with typed arguments.
Auto-generates CALCULATOR_REGISTRY for L4 pipeline.

Categories (55 total):
- Physical/Anthropometric (7): BMI, IBW, ABW, BSA, MAP, Target Weight, Maintenance Fluids
- Renal Function (3): Creatinine Clearance, CKD-EPI GFR, MDRD GFR
- Electrolytes/Metabolic (10): Anion Gap, Delta Gap, Osmolality, Corrections, LDL, FENa
- Cardiac (9): QTc (5 formulas), CHA2DS2-VASc, HEART Score, RCRI, Wells PE
- Hepatic (4): FIB-4, MELD-Na, Child-Pugh, Steroid Conversion
- Pulmonary (4): CURB-65, PSI, PERC, SOFA
- Infectious/Inflammatory (4): Centor, FeverPAIN, SIRS, GBS
- Hematologic/Coagulation (4): HAS-BLED, Wells DVT, Caprini, MME
- ICU Scoring (2): APACHE II, Charlson Comorbidity Index
- Obstetric (3): Gestational Age, Due Date, Conception Date
- Other (3): GCS, HOMA-IR, Framingham Risk
"""

import math
import inspect
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass


# =============================================================================
# Calculator Registry Infrastructure
# =============================================================================

@dataclass
class CalculatorSpec:
    """Calculator specification with signature info."""
    name: str                    # Formal name
    func: Callable              # The compute function
    required: List[str]         # Required parameters
    optional: List[str]         # Optional parameters with defaults
    formula: str                # Formula description
    aliases: List[str]          # Alternative names for identification


# Registry populated by @calculator decorator
CALCULATOR_REGISTRY: Dict[str, CalculatorSpec] = {}


def calculator(name: str, aliases: List[str] = None):
    """Decorator to register a calculator with its signature."""
    def decorator(func):
        sig = inspect.signature(func)
        required = []
        optional = []
        for param_name, param in sig.parameters.items():
            # Skip *args and **kwargs — they aren't real calculator params
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
            else:
                optional.append(param_name)

        # Extract formula from docstring if present
        formula = ""
        if func.__doc__:
            for line in func.__doc__.split('\n'):
                line = line.strip()
                if line.startswith('Formula:'):
                    formula = line.replace('Formula:', '').strip()
                    break

        spec = CalculatorSpec(
            name=name,
            func=func,
            required=required,
            optional=optional,
            formula=formula,
            aliases=aliases or []
        )
        CALCULATOR_REGISTRY[name] = spec
        # Also register aliases
        for alias in (aliases or []):
            CALCULATOR_REGISTRY[alias.lower()] = spec
        return func
    return decorator


# =============================================================================
# Physical/Anthropometric Calculators (7)
# =============================================================================

@calculator(
    name="Body Mass Index (BMI)",
    aliases=["bmi"]
)
def bmi(weight_kg: float, height_cm: float) -> float:
    """Calculate Body Mass Index.

    Formula: BMI = weight_kg / (height_m)^2

    Input:
        weight_kg: Patient weight in kilograms (e.g., 80.0)
            - If given in lbs, convert: lbs * 0.453592 = kg
        height_cm: Patient height in centimeters (e.g., 175.0)
            - If given in feet/inches, convert: (feet * 12 + inches) * 2.54 = cm
            - If given in meters, convert: meters * 100 = cm

    Output:
        float: BMI value (e.g., 26.12)
            - Underweight: < 18.5
            - Normal: 18.5-24.9
            - Overweight: 25-29.9
            - Obese: >= 30

    Example:
        >>> bmi(weight_kg=80.0, height_cm=175.0)
        26.122
    """
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 3)


@calculator(
    name="Mean Arterial Pressure (MAP)",
    aliases=["map"]
)
def mean_arterial_pressure(systolic: float, diastolic: float) -> float:
    """Calculate Mean Arterial Pressure.

    Formula: MAP = (2 * DBP + SBP) / 3

    Input:
        systolic: Systolic blood pressure in mmHg (e.g., 120.0)
            - Extract from "BP: 120/80" or "blood pressure 120/80 mmHg"
            - The first number in the blood pressure reading
        diastolic: Diastolic blood pressure in mmHg (e.g., 80.0)
            - The second number in the blood pressure reading

    Output:
        float: MAP value in mmHg (e.g., 93.333)
            - Normal range: 70-100 mmHg
            - Low: < 65 mmHg (concern for organ perfusion)

    Example:
        >>> mean_arterial_pressure(systolic=120.0, diastolic=80.0)
        93.333
    """
    return round((2 * diastolic + systolic) / 3, 3)


@calculator(
    name="Ideal Body Weight (Devine)",
    aliases=["ibw", "ideal body weight"]
)
def ideal_body_weight(sex: str, height_cm: float) -> float:
    """Calculate Ideal Body Weight using Devine formula.

    Formula: Male: IBW = 50 + 2.3 * (height_in - 60), Female: IBW = 45.5 + 2.3 * (height_in - 60)

    Input:
        sex: Patient sex ("male" or "female")
            - Infer from pronouns: he/him/man/gentleman -> "male"
            - Infer from pronouns: she/her/woman/lady -> "female"
        height_cm: Patient height in centimeters (e.g., 170.0)
            - Convert feet/inches: (feet * 12 + inches) * 2.54 = cm

    Output:
        float: Ideal body weight in kg (e.g., 65.91)
            - Used as reference for drug dosing
            - Compare with actual weight for obesity assessment

    Example:
        >>> ideal_body_weight(sex="male", height_cm=175.0)
        70.455
    """
    height_in = height_cm / 2.54
    if sex.lower() == 'male':
        return round(50 + 2.3 * (height_in - 60), 3)
    else:
        return round(45.5 + 2.3 * (height_in - 60), 3)


@calculator(
    name="Adjusted Body Weight",
    aliases=["abw"]
)
def adjusted_body_weight(weight_kg: float, sex: str, height_cm: float) -> float:
    """Calculate Adjusted Body Weight for obese patients.

    Formula: ABW = IBW + 0.4 * (actual_weight - IBW)

    Input:
        weight_kg: Actual patient weight in kilograms (e.g., 100.0)
        sex: Patient sex ("male" or "female")
        height_cm: Patient height in centimeters (e.g., 170.0)

    Output:
        float: Adjusted body weight in kg (e.g., 78.5)
            - Used for drug dosing in obese patients
            - Better reflects lean body mass than actual weight

    Example:
        >>> adjusted_body_weight(weight_kg=100.0, sex="male", height_cm=175.0)
        82.182
    """
    ibw = ideal_body_weight(sex, height_cm)
    return round(ibw + 0.4 * (weight_kg - ibw), 3)


@calculator(
    name="Body Surface Area (Mosteller)",
    aliases=["bsa", "body surface area"]
)
def body_surface_area(weight_kg: float, height_cm: float) -> float:
    """Calculate Body Surface Area using Mosteller formula.

    Formula: BSA = sqrt((height_cm * weight_kg) / 3600)

    Input:
        weight_kg: Patient weight in kilograms (e.g., 70.0)
        height_cm: Patient height in centimeters (e.g., 170.0)

    Output:
        float: BSA in m^2 (e.g., 1.82)
            - Average adult: 1.7-2.0 m^2
            - Used for chemotherapy dosing

    Example:
        >>> body_surface_area(weight_kg=70.0, height_cm=170.0)
        1.814
    """
    return round(math.sqrt((height_cm * weight_kg) / 3600), 3)


@calculator(
    name="Target Weight",
    aliases=["target weight"]
)
def target_weight(height_cm: float, target_bmi: float = 21.75) -> float:
    """Calculate target weight for a given BMI.

    Formula: Target Weight = target_bmi * (height_m)^2

    Input:
        height_cm: Patient height in centimeters (e.g., 170.0)
        target_bmi: Target BMI value (default 21.75 for healthy weight)
            - Extract from "target BMI of 22" or "BMI goal: 25"

    Output:
        float: Target weight in kg (e.g., 62.8)

    Example:
        >>> target_weight(height_cm=170.0, target_bmi=22.0)
        63.58
    """
    height_m = height_cm / 100
    return round(target_bmi * (height_m ** 2), 3)


@calculator(
    name="Maintenance Fluids (4-2-1 Rule)",
    aliases=["maintenance fluids"]
)
def maintenance_fluids(weight_kg: float) -> float:
    """Calculate maintenance fluid rate using 4-2-1 rule.

    Formula: First 10kg: 4ml/kg/hr, Next 10kg: 2ml/kg/hr, Remaining: 1ml/kg/hr

    Input:
        weight_kg: Patient weight in kilograms (e.g., 70.0)

    Output:
        float: Fluid rate in ml/hr (e.g., 110.0)
            - For 24-hour volume, multiply by 24

    Example:
        >>> maintenance_fluids(weight_kg=70.0)
        110.0
    """
    if weight_kg <= 10:
        return round(weight_kg * 4, 3)
    elif weight_kg <= 20:
        return round(40 + (weight_kg - 10) * 2, 3)
    else:
        return round(60 + (weight_kg - 20) * 1, 3)


# =============================================================================
# Renal Function Calculators (3)
# =============================================================================

@calculator(
    name="Creatinine Clearance (Cockcroft-Gault)",
    aliases=["crcl", "creatinine clearance", "cockcroft-gault"]
)
def creatinine_clearance(
    age: float,
    sex: str,
    weight_kg: float,
    creatinine_mg_dl: float,
    height_cm: float = None
) -> float:
    """Calculate Creatinine Clearance using Cockcroft-Gault equation.

    Formula: CrCl = ((140 - age) * adjusted_weight * gender_coef) / (Cr * 72)

    Input:
        age: Patient age in years (e.g., 65)
            - Must be >= 18 for valid calculation
        sex: Patient sex ("male" or "female")
            - Infer from: he/him/man/gentleman -> "male"
            - Infer from: she/her/woman/lady -> "female"
        weight_kg: Patient weight in kilograms (e.g., 70.0)
            - Convert lbs to kg: lbs * 0.453592
        creatinine_mg_dl: Serum creatinine in mg/dL (e.g., 1.2)
            - If given in umol/L, convert: umol/L / 88.4 = mg/dL
            - Look for "creatinine: 1.2 mg/dL" or "Cr: 1.2"
        height_cm: (Optional) Patient height in cm (e.g., 170.0)
            - Needed for weight adjustment in obese patients
            - If provided, calculates IBW and adjusts weight based on BMI

    Output:
        float: Creatinine Clearance in mL/min (e.g., 45.5)
            - Normal: 90-120 mL/min
            - Mild decrease: 60-89 mL/min
            - Moderate decrease: 30-59 mL/min
            - Severe decrease: 15-29 mL/min
            - Kidney failure: < 15 mL/min

    Example:
        >>> creatinine_clearance(age=70, sex="male", weight_kg=80, creatinine_mg_dl=1.5)
        64.815
    """
    weight_to_use = weight_kg

    if height_cm is not None:
        height_m = height_cm / 100
        bmi_val = weight_kg / (height_m ** 2)
        height_in = height_cm / 2.54

        # Calculate IBW
        if sex.lower() == 'male':
            ibw = 50 + 2.3 * (height_in - 60)
        else:
            ibw = 45.5 + 2.3 * (height_in - 60)

        # Adjust weight based on BMI
        if bmi_val >= 30:  # Obese
            weight_to_use = ibw + 0.4 * (weight_kg - ibw)
        elif bmi_val >= 25:  # Overweight
            weight_to_use = ibw + 0.4 * (weight_kg - ibw)
        elif bmi_val < 18.5:  # Underweight
            weight_to_use = weight_kg
        else:  # Normal BMI
            weight_to_use = min(ibw, weight_kg)

    gender_coef = 1.0 if sex.lower() == 'male' else 0.85
    crcl = ((140 - age) * weight_to_use * gender_coef) / (creatinine_mg_dl * 72)
    return round(crcl, 3)


@calculator(
    name="CKD-EPI GFR (2021)",
    aliases=["ckd-epi", "gfr", "glomerular filtration rate"]
)
def ckd_epi_gfr(age: float, sex: str, creatinine_mg_dl: float) -> float:
    """Calculate GFR using CKD-EPI 2021 equation (race-free).

    Formula: 142 * min(Cr/kappa,1)^alpha * max(Cr/kappa,1)^-1.200 * 0.9938^age * sex_coef

    Input:
        age: Patient age in years (e.g., 65)
        sex: Patient sex ("male" or "female")
        creatinine_mg_dl: Serum creatinine in mg/dL (e.g., 1.2)
            - If given in umol/L, convert: umol/L / 88.4 = mg/dL

    Output:
        float: GFR in mL/min/1.73m^2 (e.g., 65.3)
            - G1 (Normal): >= 90
            - G2 (Mild): 60-89
            - G3a (Mild-Moderate): 45-59
            - G3b (Moderate-Severe): 30-44
            - G4 (Severe): 15-29
            - G5 (Kidney failure): < 15

    Example:
        >>> ckd_epi_gfr(age=65, sex="male", creatinine_mg_dl=1.2)
        62.847
    """
    if sex.lower() == 'female':
        kappa = 0.7
        alpha = -0.241
        sex_coef = 1.012
    else:
        kappa = 0.9
        alpha = -0.302
        sex_coef = 1.0

    cr_ratio = creatinine_mg_dl / kappa
    if creatinine_mg_dl <= kappa:
        gfr = 142 * (cr_ratio ** alpha) * (0.9938 ** age) * sex_coef
    else:
        gfr = 142 * (cr_ratio ** -1.200) * (0.9938 ** age) * sex_coef

    return round(gfr, 3)


@calculator(
    name="MDRD GFR",
    aliases=["mdrd"]
)
def mdrd_gfr(age: float, sex: str, creatinine_mg_dl: float) -> float:
    """Calculate GFR using MDRD equation.

    Formula: 175 * (Cr)^-1.154 * (age)^-0.203 * sex_coef

    Input:
        age: Patient age in years (e.g., 65)
        sex: Patient sex ("male" or "female")
        creatinine_mg_dl: Serum creatinine in mg/dL (e.g., 1.2)

    Output:
        float: GFR in mL/min/1.73m^2 (e.g., 60.5)

    Example:
        >>> mdrd_gfr(age=65, sex="male", creatinine_mg_dl=1.2)
        60.879
    """
    sex_coef = 0.742 if sex.lower() == 'female' else 1.0
    gfr = 175 * (creatinine_mg_dl ** -1.154) * (age ** -0.203) * sex_coef
    return round(gfr, 3)


# =============================================================================
# Electrolytes/Metabolic Calculators (10)
# =============================================================================

@calculator(
    name="Anion Gap",
    aliases=["anion gap"]
)
def anion_gap(sodium: float, chloride: float, bicarbonate: float) -> float:
    """Calculate Anion Gap.

    Formula: AG = Na - (Cl + HCO3)

    Input:
        sodium: Serum sodium in mEq/L (e.g., 140)
        chloride: Serum chloride in mEq/L (e.g., 100)
        bicarbonate: Serum bicarbonate/CO2 in mEq/L (e.g., 24)
            - May be labeled as HCO3, CO2, or bicarb

    Output:
        float: Anion gap in mEq/L (e.g., 12)
            - Normal: 8-12 mEq/L
            - Elevated (>12): Consider MUDPILES causes

    Example:
        >>> anion_gap(sodium=140, chloride=100, bicarbonate=24)
        16.0
    """
    return round(sodium - (chloride + bicarbonate), 3)


@calculator(
    name="Delta Gap",
    aliases=["delta gap"]
)
def delta_gap(sodium: float, chloride: float, bicarbonate: float, **kwargs) -> float:
    """Calculate Delta Gap (change from normal anion gap).

    Formula: Delta Gap = AG - 12 (where 12 is normal AG)

    Input:
        sodium: Serum sodium in mEq/L (e.g., 140)
        chloride: Serum chloride in mEq/L (e.g., 100)
        bicarbonate: Serum bicarbonate in mEq/L (e.g., 24)

    Output:
        float: Delta gap in mEq/L
            - Positive: Indicates high AG metabolic acidosis
            - Used with delta ratio to identify mixed disorders

    Example:
        >>> delta_gap(sodium=140, chloride=100, bicarbonate=18)
        10.0
    """
    ag = sodium - (chloride + bicarbonate)
    return round(ag - 12, 3)


@calculator(
    name="Delta Ratio",
    aliases=["delta ratio"]
)
def delta_ratio(sodium: float, chloride: float, bicarbonate: float, **kwargs) -> float:
    """Calculate Delta Ratio for mixed acid-base disorders.

    Formula: Delta Ratio = Delta Gap / (24 - HCO3)

    Input:
        sodium: Serum sodium in mEq/L (e.g., 140)
        chloride: Serum chloride in mEq/L (e.g., 100)
        bicarbonate: Serum bicarbonate in mEq/L (e.g., 18)

    Output:
        float: Delta ratio
            - < 1: Mixed HAGMA + NAGMA
            - 1-2: Pure HAGMA
            - > 2: HAGMA + metabolic alkalosis

    Example:
        >>> delta_ratio(sodium=140, chloride=100, bicarbonate=18)
        1.667
    """
    d_gap = delta_gap(sodium, chloride, bicarbonate)
    delta_hco3 = 24 - bicarbonate
    if delta_hco3 == 0:
        return 0.0
    return round(d_gap / delta_hco3, 3)


@calculator(
    name="Albumin Corrected Anion Gap",
    aliases=["albumin corrected anion gap", "corrected anion gap"]
)
def albumin_corrected_anion_gap(sodium: float, chloride: float, bicarbonate: float, albumin: float) -> float:
    """Calculate Albumin-Corrected Anion Gap.

    Formula: Corrected AG = AG + 2.5 * (4 - albumin)

    Input:
        sodium: Serum sodium in mEq/L (e.g., 140)
        chloride: Serum chloride in mEq/L (e.g., 100)
        bicarbonate: Serum bicarbonate in mEq/L (e.g., 24)
        albumin: Serum albumin in g/dL (e.g., 3.5)
            - Normal: 3.5-5.0 g/dL

    Output:
        float: Corrected anion gap in mEq/L
            - Accounts for hypoalbuminemia which lowers measured AG

    Example:
        >>> albumin_corrected_anion_gap(sodium=140, chloride=100, bicarbonate=24, albumin=2.5)
        19.75
    """
    ag = anion_gap(sodium, chloride, bicarbonate)
    return round(ag + 2.5 * (4 - albumin), 3)


@calculator(
    name="Serum Osmolality",
    aliases=["serum osmolality", "osmolality"]
)
def serum_osmolality(sodium: float, bun: float, glucose: float) -> float:
    """Calculate Serum Osmolality.

    Formula: Osm = 2*Na + BUN/2.8 + Glucose/18

    Input:
        sodium: Serum sodium in mEq/L (e.g., 140)
        bun: Blood urea nitrogen in mg/dL (e.g., 20)
            - If given in mmol/L, convert: mmol/L * 2.8 = mg/dL
        glucose: Serum glucose in mg/dL (e.g., 100)
            - If given in mmol/L, convert: mmol/L * 18 = mg/dL

    Output:
        float: Osmolality in mOsm/kg (e.g., 290)
            - Normal: 275-295 mOsm/kg
            - Hyperosmolar: > 295

    Example:
        >>> serum_osmolality(sodium=140, bun=20, glucose=100)
        292.698
    """
    return round(2 * sodium + bun / 2.8 + glucose / 18, 3)


@calculator(
    name="Free Water Deficit",
    aliases=["free water deficit"]
)
def free_water_deficit(weight_kg: float, sodium: float, age: float, sex: str) -> float:
    """Calculate Free Water Deficit for hypernatremia correction.

    Formula: FWD = TBW% * weight * (Na/140 - 1)

    Input:
        weight_kg: Patient weight in kg (e.g., 70)
        sodium: Serum sodium in mEq/L (e.g., 150)
        age: Patient age in years (e.g., 65)
        sex: Patient sex ("male" or "female")

    Output:
        float: Free water deficit in liters (e.g., 3.5)
            - Represents water needed to correct hypernatremia

    Example:
        >>> free_water_deficit(weight_kg=70, sodium=150, age=65, sex="male")
        2.5
    """
    # Total body water percentage
    if age < 18:
        tbw_pct = 0.6
    elif sex.lower() == 'male':
        tbw_pct = 0.5 if age >= 65 else 0.6
    else:
        tbw_pct = 0.45 if age >= 65 else 0.5

    deficit = tbw_pct * weight_kg * (sodium / 140 - 1)
    return round(deficit, 3)


@calculator(
    name="Sodium Correction for Hyperglycemia",
    aliases=["sodium correction", "corrected sodium"]
)
def sodium_correction(sodium: float, glucose: float) -> float:
    """Calculate Sodium Correction for Hyperglycemia.

    Formula: Corrected Na = Na + 0.024 * (glucose - 100)

    Input:
        sodium: Measured serum sodium in mEq/L (e.g., 130)
        glucose: Serum glucose in mg/dL (e.g., 400)

    Output:
        float: Corrected sodium in mEq/L (e.g., 137.2)
            - Accounts for dilutional effect of hyperglycemia

    Example:
        >>> sodium_correction(sodium=130, glucose=400)
        137.2
    """
    return round(sodium + 0.024 * (glucose - 100), 3)


@calculator(
    name="Calcium Correction for Hypoalbuminemia",
    aliases=["calcium correction", "corrected calcium"]
)
def calcium_correction(calcium: float, albumin: float) -> float:
    """Calculate Calcium Correction for Hypoalbuminemia.

    Formula: Corrected Ca = Ca + 0.8 * (4 - albumin)

    Input:
        calcium: Measured serum calcium in mg/dL (e.g., 8.0)
        albumin: Serum albumin in g/dL (e.g., 2.5)

    Output:
        float: Corrected calcium in mg/dL (e.g., 9.2)
            - Normal total calcium: 8.5-10.5 mg/dL

    Example:
        >>> calcium_correction(calcium=8.0, albumin=2.5)
        9.2
    """
    return round(calcium + 0.8 * (4 - albumin), 3)


@calculator(
    name="LDL Calculated (Friedewald)",
    aliases=["ldl", "ldl calculated"]
)
def ldl_calculated(total_cholesterol: float, hdl: float, triglycerides: float) -> float:
    """Calculate LDL using Friedewald equation.

    Formula: LDL = Total Cholesterol - HDL - (Triglycerides / 5)

    Input:
        total_cholesterol: Total cholesterol in mg/dL (e.g., 200)
        hdl: HDL cholesterol in mg/dL (e.g., 50)
        triglycerides: Triglycerides in mg/dL (e.g., 150)
            - Only valid if TG < 400 mg/dL

    Output:
        float: LDL cholesterol in mg/dL (e.g., 120)
            - Optimal: < 100 mg/dL
            - Near optimal: 100-129 mg/dL
            - Borderline high: 130-159 mg/dL
            - High: 160-189 mg/dL
            - Very high: >= 190 mg/dL

    Example:
        >>> ldl_calculated(total_cholesterol=200, hdl=50, triglycerides=150)
        120.0
    """
    return round(total_cholesterol - hdl - (triglycerides / 5), 3)


@calculator(
    name="Fractional Excretion of Sodium (FENa)",
    aliases=["fena", "fractional excretion of sodium"]
)
def fena(urine_sodium: float, serum_sodium: float, urine_creatinine: float, serum_creatinine: float) -> float:
    """Calculate Fractional Excretion of Sodium.

    Formula: FENa = (UNa * SCr) / (SNa * UCr) * 100

    Input:
        urine_sodium: Urine sodium in mEq/L (e.g., 20)
        serum_sodium: Serum sodium in mEq/L (e.g., 140)
        urine_creatinine: Urine creatinine in mg/dL (e.g., 100)
        serum_creatinine: Serum creatinine in mg/dL (e.g., 1.5)

    Output:
        float: FENa as percentage (e.g., 0.9)
            - < 1%: Pre-renal azotemia (volume depletion)
            - > 2%: Intrinsic renal disease (ATN)
            - 1-2%: Indeterminate

    Example:
        >>> fena(urine_sodium=20, serum_sodium=140, urine_creatinine=100, serum_creatinine=1.5)
        0.214
    """
    return round((urine_sodium * serum_creatinine) / (serum_sodium * urine_creatinine) * 100, 3)


# =============================================================================
# Cardiac Calculators (9)
# =============================================================================

@calculator(
    name="QTc (Bazett)",
    aliases=["qtc bazett", "bazett"]
)
def qtc_bazett(qt_msec: float, heart_rate: float) -> float:
    """Calculate QTc using Bazett formula.

    Formula: QTc = QT / sqrt(RR) where RR = 60/HR in seconds

    Input:
        qt_msec: QT interval in milliseconds (e.g., 400)
        heart_rate: Heart rate in bpm (e.g., 75)

    Output:
        float: Corrected QT interval in msec (e.g., 434)
            - Normal: < 450 ms (males), < 460 ms (females)
            - Prolonged: > 500 ms (risk of torsades)

    Example:
        >>> qtc_bazett(qt_msec=400, heart_rate=75)
        436.719
    """
    rr = 60 / heart_rate
    return round(qt_msec / math.sqrt(rr), 3)


@calculator(
    name="QTc (Fridericia)",
    aliases=["qtc fridericia", "fridericia"]
)
def qtc_fridericia(qt_msec: float, heart_rate: float) -> float:
    """Calculate QTc using Fridericia formula.

    Formula: QTc = QT / RR^(1/3) where RR = 60/HR in seconds

    Input:
        qt_msec: QT interval in milliseconds (e.g., 400)
        heart_rate: Heart rate in bpm (e.g., 75)

    Output:
        float: Corrected QT interval in msec

    Example:
        >>> qtc_fridericia(qt_msec=400, heart_rate=75)
        423.228
    """
    rr = 60 / heart_rate
    return round(qt_msec / (rr ** (1/3)), 3)


@calculator(
    name="QTc (Framingham)",
    aliases=["qtc framingham"]
)
def qtc_framingham(qt_msec: float, heart_rate: float) -> float:
    """Calculate QTc using Framingham formula.

    Formula: QTc = QT + 154 * (1 - RR) where RR = 60/HR in seconds

    Input:
        qt_msec: QT interval in milliseconds (e.g., 400)
        heart_rate: Heart rate in bpm (e.g., 75)

    Output:
        float: Corrected QT interval in msec

    Example:
        >>> qtc_framingham(qt_msec=400, heart_rate=75)
        431.0
    """
    rr = 60 / heart_rate
    return round(qt_msec + 154 * (1 - rr), 3)


@calculator(
    name="QTc (Hodges)",
    aliases=["qtc hodges", "hodges"]
)
def qtc_hodges(qt_msec: float, heart_rate: float) -> float:
    """Calculate QTc using Hodges formula.

    Formula: QTc = QT + 1.75 * (HR - 60)

    Input:
        qt_msec: QT interval in milliseconds (e.g., 400)
        heart_rate: Heart rate in bpm (e.g., 75)

    Output:
        float: Corrected QT interval in msec

    Example:
        >>> qtc_hodges(qt_msec=400, heart_rate=75)
        426.25
    """
    return round(qt_msec + 1.75 * (heart_rate - 60), 3)


@calculator(
    name="QTc (Rautaharju)",
    aliases=["qtc rautaharju", "rautaharju"]
)
def qtc_rautaharju(qt_msec: float, heart_rate: float) -> float:
    """Calculate QTc using Rautaharju formula.

    Formula: QTc = QT + 154 * (1 - RR) where RR = 60/HR in seconds

    Input:
        qt_msec: QT interval in milliseconds (e.g., 400)
        heart_rate: Heart rate in bpm (e.g., 75)

    Output:
        float: Corrected QT interval in msec

    Example:
        >>> qtc_rautaharju(qt_msec=400, heart_rate=75)
        431.0
    """
    rr = 60 / heart_rate
    return round(qt_msec + 154 * (1 - rr), 3)


@calculator(
    name="CHA2DS2-VASc Score",
    aliases=["cha2ds2-vasc", "chads2", "cha2ds2"]
)
def cha2ds2_vasc(
    age: float,
    sex: str,
    has_chf: bool = False,
    has_hypertension: bool = False,
    has_diabetes: bool = False,
    has_stroke_tia: bool = False,
    has_vascular_disease: bool = False
) -> float:
    """Calculate CHA2DS2-VASc Score for Atrial Fibrillation Stroke Risk.

    Formula: Sum of: CHF(+1), HTN(+1), Age>=75(+2)/65-74(+1), DM(+1), Stroke/TIA(+2), Vascular(+1), Female(+1)

    Input:
        age: Patient age in years (e.g., 72)
        sex: Patient sex ("male" or "female")
        has_chf: History of congestive heart failure (True/False)
        has_hypertension: History of hypertension (True/False)
        has_diabetes: History of diabetes mellitus (True/False)
        has_stroke_tia: History of stroke or TIA (True/False)
        has_vascular_disease: History of vascular disease - MI, PAD, aortic plaque (True/False)

    Output:
        float: CHA2DS2-VASc score (0-9)
            - 0 (male) or 1 (female): Low risk
            - 1 (male) or 2 (female): Intermediate risk
            - >= 2 (male) or >= 3 (female): High risk, anticoagulation recommended

    Example:
        >>> cha2ds2_vasc(age=72, sex="male", has_hypertension=True, has_diabetes=True)
        3.0
    """
    score = 0

    # Age points
    if age >= 75:
        score += 2
    elif age >= 65:
        score += 1

    # Sex (female = 1 point)
    if sex.lower() == 'female':
        score += 1

    # Conditions
    if has_chf:
        score += 1
    if has_hypertension:
        score += 1
    if has_diabetes:
        score += 1
    if has_stroke_tia:
        score += 2
    if has_vascular_disease:
        score += 1

    return float(score)


@calculator(
    name="HEART Score",
    aliases=["heart score", "heart", "heart score for major cardiac events"]
)
def heart_score(
    age: float,
    history_suspicious: int = 0,
    ecg_findings: int = 0,
    risk_factors: int = 0,
    troponin: int = 0,
    **kwargs
) -> float:
    """Calculate HEART Score for Major Cardiac Events.

    Formula: Sum of History + ECG + Age + Risk factors + Troponin (each 0-2 points)

    Input:
        age: Patient age in years (e.g., 55)
        history_suspicious: 0=slightly, 1=moderately, 2=highly suspicious
        ecg_findings: 0=normal, 1=non-specific, 2=significant ST deviation
        risk_factors: 0=none, 1=1-2 factors, 2=3+ factors
            - Factors: HTN, DM, smoking, obesity, family hx, hyperlipidemia
        troponin: 0=normal, 1=1-3x normal, 2=>3x normal

    Output:
        float: HEART score (0-10)
            - 0-3: Low risk (1.6% MACE)
            - 4-6: Moderate risk (12% MACE)
            - 7-10: High risk (50%+ MACE)

    Example:
        >>> heart_score(age=55, history_suspicious=1, ecg_findings=0, risk_factors=1, troponin=0)
        3.0
    """
    score = 0

    # Map descriptive strings to numeric scores (LLM may send text instead of ints)
    def _map_heart(val, mapping):
        if val is None:
            return 0
        if isinstance(val, str):
            val_l = val.lower().strip()
            for keywords, score_val in mapping:
                if any(kw in val_l for kw in keywords):
                    return score_val
            # Try numeric parse
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return 0
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    history_suspicious = _map_heart(history_suspicious, [
        (['highly', 'typical', 'classic', 'high'], 2),
        (['moderately', 'moderate', 'somewhat'], 1),
        (['slightly', 'atypical', 'low', 'non-specific', 'vague'], 0),
    ])
    ecg_findings = _map_heart(ecg_findings, [
        (['st elevation', 'st depression', 'significant', 'deviation', 'stemi'], 2),
        (['non-specific', 'nonspecific', 'repolarization', 'minor', 't wave'], 1),
        (['normal', 'unremarkable', 'sinus'], 0),
    ])
    risk_factors = _map_heart(risk_factors, [
        (['3', 'three', '3+', 'many', 'multiple', 'several'], 2),
        (['1', '2', 'one', 'two', 'few', 'some'], 1),
        (['0', 'none', 'no', 'zero'], 0),
    ])
    troponin = _map_heart(troponin, [
        (['>3', 'greater than three', 'more than 3', 'markedly', 'high'], 2),
        (['1-3', 'one to three', 'slightly', 'mildly', 'elevated'], 1),
        (['normal', 'negative', 'less than', 'within normal', 'not elevated'], 0),
    ])

    # Age
    if age >= 65:
        score += 2
    elif age >= 45:
        score += 1

    # Other components
    score += history_suspicious
    score += ecg_findings
    score += risk_factors
    score += troponin

    return float(score)


@calculator(
    name="Revised Cardiac Risk Index (RCRI)",
    aliases=["rcri", "revised cardiac risk index"]
)
def rcri(
    high_risk_surgery: bool = False,
    ischemic_heart_disease: bool = False,
    congestive_heart_failure: bool = False,
    cerebrovascular_disease: bool = False,
    insulin_diabetes: bool = False,
    creatinine_elevated: bool = False
) -> float:
    """Calculate Revised Cardiac Risk Index for Pre-Operative Risk.

    Formula: Sum of 6 risk factors (0-6 points)

    Input:
        high_risk_surgery: Intraperitoneal, intrathoracic, or suprainguinal vascular surgery
        ischemic_heart_disease: History of MI, positive stress test, angina, nitrate use, Q waves
        congestive_heart_failure: History of CHF, pulmonary edema, PND, bilateral rales, S3, CXR with pulmonary edema
        cerebrovascular_disease: History of stroke or TIA
        insulin_diabetes: Insulin-dependent diabetes mellitus
        creatinine_elevated: Preoperative creatinine > 2.0 mg/dL

    Output:
        float: RCRI score (0-6)
            - 0: 0.4% risk of major cardiac event
            - 1: 0.9% risk
            - 2: 6.6% risk
            - >= 3: 11% risk

    Example:
        >>> rcri(high_risk_surgery=True, ischemic_heart_disease=True)
        2.0
    """
    score = 0
    if high_risk_surgery:
        score += 1
    if ischemic_heart_disease:
        score += 1
    if congestive_heart_failure:
        score += 1
    if cerebrovascular_disease:
        score += 1
    if insulin_diabetes:
        score += 1
    if creatinine_elevated:
        score += 1
    return float(score)


@calculator(
    name="Wells' Criteria for PE",
    aliases=["wells pe", "wells criteria for pulmonary embolism"]
)
def wells_pe(
    dvt_signs: bool = False,
    pe_likely: bool = False,
    heart_rate_over_100: bool = False,
    immobilization_surgery: bool = False,
    prior_pe_dvt: bool = False,
    hemoptysis: bool = False,
    malignancy: bool = False
) -> float:
    """Calculate Wells' Criteria for Pulmonary Embolism.

    Formula: Sum of weighted criteria

    Input:
        dvt_signs: Clinical signs/symptoms of DVT (+3 points)
        pe_likely: PE is #1 diagnosis or equally likely (+3 points)
        heart_rate_over_100: Heart rate > 100 bpm (+1.5 points)
        immobilization_surgery: Immobilization >= 3 days or surgery within 4 weeks (+1.5 points)
        prior_pe_dvt: Previous PE or DVT (+1.5 points)
        hemoptysis: Hemoptysis (+1 point)
        malignancy: Active cancer (treatment within 6 months or palliative) (+1 point)

    Output:
        float: Wells score
            - <= 4: PE unlikely
            - > 4: PE likely

    Example:
        >>> wells_pe(dvt_signs=True, heart_rate_over_100=True)
        4.5
    """
    score = 0.0
    if dvt_signs:
        score += 3
    if pe_likely:
        score += 3
    if heart_rate_over_100:
        score += 1.5
    if immobilization_surgery:
        score += 1.5
    if prior_pe_dvt:
        score += 1.5
    if hemoptysis:
        score += 1
    if malignancy:
        score += 1
    return round(score, 1)


# =============================================================================
# Hepatic Calculators (4)
# =============================================================================

@calculator(
    name="FIB-4 Index",
    aliases=["fib-4", "fib4", "fibrosis-4", "fib-4 index for liver fibrosis", "fibrosis 4 index"]
)
def fib4(age: float = 0, ast: float = 0, alt: float = 0, platelets: float = 0, **kwargs) -> float:
    """Calculate FIB-4 Index for Liver Fibrosis.

    Formula: FIB-4 = (Age * AST) / (Platelets * sqrt(ALT))

    Input:
        age: Patient age in years (e.g., 55)
        ast: AST in U/L (e.g., 45)
        alt: ALT in U/L (e.g., 50)
        platelets: Platelet count in 10^9/L (e.g., 150)
            - If given as thousands (e.g., 150,000), divide by 1000

    Output:
        float: FIB-4 index
            - < 1.45: Low probability of advanced fibrosis
            - 1.45-3.25: Indeterminate
            - > 3.25: High probability of advanced fibrosis

    Example:
        >>> fib4(age=55, ast=45, alt=50, platelets=150)
        1.852
    """
    # Handle uppercase aliases from LLM
    if ast == 0:
        ast = kwargs.get('AST', kwargs.get('aspartate_aminotransferase', kwargs.get('sgot', 0)))
    if alt == 0:
        alt = kwargs.get('ALT', kwargs.get('alanine_aminotransferase', kwargs.get('sgpt', 0)))
    if platelets == 0:
        platelets = kwargs.get('Platelets', kwargs.get('platelet_count', kwargs.get('plt', 0)))
    age = float(age or 0)
    ast = float(ast or 0)
    alt = float(alt or 0)
    platelets = float(platelets or 0)
    if platelets == 0 or alt == 0:
        return 0.0
    return round((age * ast) / (platelets * math.sqrt(alt)), 3)


@calculator(
    name="MELD-Na Score",
    aliases=["meld-na", "meld na", "meld sodium"]
)
def meld_na(bilirubin: float, inr: float, creatinine: float, sodium: float) -> float:
    """Calculate MELD-Na Score (UNOS/OPTN).

    Formula: MELD = 10 * (0.957*ln(Cr) + 0.378*ln(Bili) + 1.120*ln(INR) + 0.643)
             MELD-Na = MELD + 1.32*(137-Na) - 0.033*MELD*(137-Na)

    Input:
        bilirubin: Total bilirubin in mg/dL (e.g., 2.5), minimum 1.0
        inr: INR (e.g., 1.5), minimum 1.0
        creatinine: Serum creatinine in mg/dL (e.g., 1.5), 1.0-4.0 range
        sodium: Serum sodium in mEq/L (e.g., 135), 125-137 range

    Output:
        float: MELD-Na score (6-40)
            - Used for liver transplant prioritization
            - Higher scores = higher mortality

    Example:
        >>> meld_na(bilirubin=2.5, inr=1.5, creatinine=1.5, sodium=135)
        15.0
    """
    # Apply minimum/maximum bounds
    bili = max(1.0, bilirubin)
    cr = max(1.0, min(4.0, creatinine))
    na = max(125, min(137, sodium))
    inr_val = max(1.0, inr)

    # MELD calculation
    meld = 10 * (0.957 * math.log(cr) + 0.378 * math.log(bili) + 1.120 * math.log(inr_val) + 0.643)
    meld = round(meld)

    # MELD-Na adjustment
    meld_na_score = meld + 1.32 * (137 - na) - 0.033 * meld * (137 - na)
    return round(max(6, min(40, meld_na_score)))


@calculator(
    name="Child-Pugh Score",
    aliases=["child-pugh", "child pugh", "child-pugh score", "child pugh score",
             "child-pugh classification"]
)
def child_pugh(
    bilirubin: float,
    albumin: float,
    inr: float,
    ascites_grade: int = 0,
    encephalopathy_grade: int = 0,
    **kwargs
) -> float:
    """Calculate Child-Pugh Score for Cirrhosis Mortality.

    Formula: Sum of points for bilirubin, albumin, INR, ascites, encephalopathy

    Input:
        bilirubin: Total bilirubin in mg/dL (e.g., 2.5)
        albumin: Serum albumin in g/dL (e.g., 3.0)
        inr: INR (e.g., 1.5)
        ascites_grade: 0=none, 1=mild/controlled, 2=moderate-severe
        encephalopathy_grade: 0=none, 1=grade I-II, 2=grade III-IV

    Output:
        float: Child-Pugh score (5-15)
            - Class A (5-6): 100% 1-year survival
            - Class B (7-9): 80% 1-year survival
            - Class C (10-15): 45% 1-year survival

    Example:
        >>> child_pugh(bilirubin=2.5, albumin=3.0, inr=1.5, ascites_grade=1, encephalopathy_grade=0)
        7.0
    """
    # Helper to convert string descriptions to integer grades (0, 1, 2)
    def _parse_grade(val, grade_type="ascites"):
        if val is None:
            return 0
        if isinstance(val, (int, float)):
            return int(val)
        if isinstance(val, str):
            val_l = val.lower().strip()
            # Try numeric parse first
            try:
                return int(float(val_l))
            except (ValueError, TypeError):
                pass
            # Map common string descriptions to grade scores (0=none, 1=mild, 2=moderate-severe)
            if any(kw in val_l for kw in ['none', 'absent', 'no ', 'not present']):
                return 0
            if grade_type == "ascites":
                if any(kw in val_l for kw in ['mild', 'slight', 'small', 'controlled', 'grade 1', 'grade i']):
                    return 1
                if any(kw in val_l for kw in ['moderate', 'severe', 'large', 'tense', 'refractory',
                                                'grade 2', 'grade ii', 'grade 3', 'grade iii']):
                    return 2
            else:  # encephalopathy
                if any(kw in val_l for kw in ['mild', 'grade 1', 'grade i', 'grade 2', 'grade ii',
                                               '1-2', 'i-ii', 'stage 1', 'stage 2', 'minimal']):
                    return 1
                if any(kw in val_l for kw in ['moderate', 'severe', 'grade 3', 'grade iii', 'grade 4',
                                               'grade iv', '3-4', 'iii-iv', 'stage 3', 'stage 4',
                                               'coma', 'obtunded']):
                    return 2
            # Default: if it has some content but we can't parse, assume mild (1)
            if val_l and val_l not in ('0', 'false'):
                return 1
            return 0
        return 0

    # Coerce types — LLM may send strings
    bilirubin = float(bilirubin)
    albumin = float(albumin)
    inr = float(inr)
    ascites_grade = _parse_grade(ascites_grade, "ascites")
    encephalopathy_grade = _parse_grade(encephalopathy_grade, "encephalopathy")

    score = 0

    # Bilirubin points
    if bilirubin < 2:
        score += 1
    elif bilirubin <= 3:
        score += 2
    else:
        score += 3

    # Albumin points
    if albumin > 3.5:
        score += 1
    elif albumin >= 2.8:
        score += 2
    else:
        score += 3

    # INR points
    if inr < 1.7:
        score += 1
    elif inr <= 2.3:
        score += 2
    else:
        score += 3

    # Ascites
    score += ascites_grade + 1

    # Encephalopathy
    score += encephalopathy_grade + 1

    return float(score)


@calculator(
    name="Steroid Conversion",
    aliases=["steroid conversion", "prednisone equivalent"]
)
def steroid_conversion(steroid_name: str, dose_mg: float, **kwargs) -> float:
    """Calculate Prednisone Equivalent dose for steroids.

    Formula: Prednisone equivalent = dose * conversion_factor

    Input:
        steroid_name: Name of steroid (e.g., "dexamethasone", "hydrocortisone")
        dose_mg: Dose in mg (e.g., 4.0)

    Output:
        float: Prednisone equivalent dose in mg
            - Useful for comparing potency across steroids

    Conversion factors (dose = X mg for 5mg prednisone equivalent):
        - Hydrocortisone: 20mg (factor 0.25)
        - Cortisone: 25mg (factor 0.2)
        - Prednisone: 5mg (factor 1.0)
        - Prednisolone: 5mg (factor 1.0)
        - Methylprednisolone: 4mg (factor 1.25)
        - Dexamethasone: 0.75mg (factor 6.67)
        - Betamethasone: 0.75mg (factor 6.67)

    Example:
        >>> steroid_conversion(steroid_name="dexamethasone", dose_mg=4.0)
        26.68
    """
    factors = {
        'hydrocortisone': 0.25,
        'cortisone': 0.2,
        'prednisone': 1.0,
        'prednisolone': 1.0,
        'methylprednisolone': 1.25,
        'triamcinolone': 1.25,
        'dexamethasone': 6.67,
        'betamethasone': 6.67,
    }

    name_lower = steroid_name.lower()
    factor = factors.get(name_lower, 1.0)
    return round(dose_mg * factor, 3)


# =============================================================================
# Pulmonary Calculators (4)
# =============================================================================

@calculator(
    name="CURB-65 Score",
    aliases=["curb-65", "curb65"]
)
def curb65(
    confusion: bool = False,
    bun_elevated: bool = False,
    respiratory_rate_elevated: bool = False,
    hypotension: bool = False,
    age_65_plus: bool = False
) -> float:
    """Calculate CURB-65 Score for Pneumonia Severity.

    Formula: C + U + R + B + 65 (0-5 points)

    Input:
        confusion: New-onset confusion (True/False)
        bun_elevated: BUN > 19 mg/dL or urea > 7 mmol/L (True/False)
        respiratory_rate_elevated: Respiratory rate >= 30 (True/False)
        hypotension: SBP < 90 or DBP <= 60 mmHg (True/False)
        age_65_plus: Age >= 65 years (True/False)

    Output:
        float: CURB-65 score (0-5)
            - 0-1: Low risk, outpatient treatment
            - 2: Moderate risk, consider admission
            - 3-5: High risk, hospitalize (4-5 consider ICU)

    Example:
        >>> curb65(confusion=True, bun_elevated=True, age_65_plus=True)
        3.0
    """
    score = 0
    if confusion:
        score += 1
    if bun_elevated:
        score += 1
    if respiratory_rate_elevated:
        score += 1
    if hypotension:
        score += 1
    if age_65_plus:
        score += 1
    return float(score)


@calculator(
    name="PSI/PORT Score",
    aliases=["psi score", "port score", "pneumonia severity index",
             "psi/port score", "psi/port", "psi port score", "psi port"]
)
def psi_score(
    age: float,
    sex: str,
    nursing_home: bool = False,
    neoplastic_disease: bool = False,
    liver_disease: bool = False,
    chf: bool = False,
    cerebrovascular: bool = False,
    renal_disease: bool = False,
    altered_mental: bool = False,
    respiratory_rate_high: bool = False,
    hypotension: bool = False,
    temperature_abnormal: bool = False,
    tachycardia: bool = False,
    ph_low: bool = False,
    bun_high: bool = False,
    sodium_low: bool = False,
    glucose_high: bool = False,
    hematocrit_low: bool = False,
    pao2_low: bool = False,
    pleural_effusion: bool = False,
    **kwargs
) -> float:
    """Calculate Pneumonia Severity Index (PSI/PORT Score).

    Formula: Demographics + Comorbidities + Physical Exam + Labs

    Input:
        age: Patient age in years
        sex: Patient sex ("male" or "female", females get -10)
        nursing_home: Nursing home resident (+10)
        neoplastic_disease: Neoplastic disease (+30)
        liver_disease: Liver disease (+20)
        chf: Congestive heart failure (+10)
        cerebrovascular: Cerebrovascular disease (+10)
        renal_disease: Renal disease (+10)
        altered_mental: Altered mental status (+20)
        respiratory_rate_high: RR >= 30 (+20)
        hypotension: SBP < 90 (+20)
        temperature_abnormal: Temp < 35C or >= 40C (+15)
        tachycardia: HR >= 125 (+10)
        ph_low: pH < 7.35 (+30)
        bun_high: BUN >= 30 mg/dL (+20)
        sodium_low: Na < 130 mEq/L (+20)
        glucose_high: Glucose >= 250 mg/dL (+10)
        hematocrit_low: Hct < 30% (+10)
        pao2_low: PaO2 < 60 mmHg (+10)
        pleural_effusion: Pleural effusion (+10)

    Output:
        float: PSI score
            - Class I: <= 50 (use clinical judgment)
            - Class II: 51-70 (0.6% mortality)
            - Class III: 71-90 (2.8% mortality)
            - Class IV: 91-130 (8.2% mortality)
            - Class V: > 130 (29.2% mortality)

    Example:
        >>> psi_score(age=75, sex="male", chf=True, bun_high=True)
        105.0
    """
    # Handle aliases — LLM may send alternative parameter names
    if not chf:
        chf = bool(kwargs.get('congestive_heart_failure', kwargs.get('heart_failure', False)))
    if not respiratory_rate_high:
        respiratory_rate_high = bool(kwargs.get('respiratory_rate', kwargs.get('rr_high', False)))
    if not hypotension:
        hypotension = bool(kwargs.get('systolic_bp', kwargs.get('systolic_bp_low', kwargs.get('low_bp', False))))
    if not cerebrovascular:
        cerebrovascular = bool(kwargs.get('cerebrovascular_disease', kwargs.get('stroke', False)))
    if not renal_disease:
        renal_disease = bool(kwargs.get('renal', kwargs.get('kidney_disease', False)))
    if not neoplastic_disease:
        neoplastic_disease = bool(kwargs.get('cancer', kwargs.get('neoplasm', False)))
    if not altered_mental:
        altered_mental = bool(kwargs.get('altered_mental_status', kwargs.get('confusion', False)))
    if not temperature_abnormal:
        temperature_abnormal = bool(kwargs.get('temperature', kwargs.get('temp_abnormal', False)))
    if not tachycardia:
        tachycardia = bool(kwargs.get('heart_rate_high', kwargs.get('hr_high', False)))

    # Start with age
    score = age if sex.lower() == 'male' else age - 10

    # Nursing home
    if nursing_home:
        score += 10

    # Comorbidities
    if neoplastic_disease:
        score += 30
    if liver_disease:
        score += 20
    if chf:
        score += 10
    if cerebrovascular:
        score += 10
    if renal_disease:
        score += 10

    # Physical exam
    if altered_mental:
        score += 20
    if respiratory_rate_high:
        score += 20
    if hypotension:
        score += 20
    if temperature_abnormal:
        score += 15
    if tachycardia:
        score += 10

    # Labs
    if ph_low:
        score += 30
    if bun_high:
        score += 20
    if sodium_low:
        score += 20
    if glucose_high:
        score += 10
    if hematocrit_low:
        score += 10
    if pao2_low:
        score += 10
    if pleural_effusion:
        score += 10

    return float(score)


@calculator(
    name="PERC Rule",
    aliases=["perc", "perc rule"]
)
def perc_rule(
    age_50_plus: bool = False,
    heart_rate_100_plus: bool = False,
    spo2_below_95: bool = False,
    leg_swelling: bool = False,
    hemoptysis: bool = False,
    surgery_trauma: bool = False,
    prior_pe_dvt: bool = False,
    hormone_use: bool = False
) -> float:
    """Calculate PERC Rule for Pulmonary Embolism.

    Formula: 8 criteria; PERC negative if all 0

    Input:
        age_50_plus: Age >= 50 years
        heart_rate_100_plus: HR >= 100 bpm
        spo2_below_95: SpO2 < 95% on room air
        leg_swelling: Unilateral leg swelling
        hemoptysis: Hemoptysis
        surgery_trauma: Recent surgery or trauma (within 4 weeks)
        prior_pe_dvt: Prior PE or DVT
        hormone_use: Oral contraceptives or hormone replacement

    Output:
        float: Number of positive criteria (0-8)
            - 0: PERC negative, PE can be ruled out (in low-risk patients)
            - >= 1: PERC positive, further workup needed

    Example:
        >>> perc_rule(age_50_plus=True, heart_rate_100_plus=True)
        2.0
    """
    score = 0
    if age_50_plus:
        score += 1
    if heart_rate_100_plus:
        score += 1
    if spo2_below_95:
        score += 1
    if leg_swelling:
        score += 1
    if hemoptysis:
        score += 1
    if surgery_trauma:
        score += 1
    if prior_pe_dvt:
        score += 1
    if hormone_use:
        score += 1
    return float(score)


@calculator(
    name="SOFA Score",
    aliases=["sofa", "sequential organ failure assessment",
             "sofa score", "sequential organ failure assessment score"]
)
def sofa_score(
    pao2_fio2_ratio: float = None,
    platelets: float = None,
    bilirubin: float = None,
    map_or_vasopressors: int = 0,
    gcs: int = 15,
    creatinine: float = None,
    **kwargs
) -> float:
    """Calculate Sequential Organ Failure Assessment (SOFA) Score.

    Formula: Sum of 6 organ system scores (0-24)

    Input:
        pao2_fio2_ratio: PaO2/FiO2 ratio (e.g., 350)
            - 0 pts: >= 400
            - 1 pt: 300-399
            - 2 pts: 200-299
            - 3 pts: 100-199 with respiratory support
            - 4 pts: < 100 with respiratory support
        platelets: Platelet count in 10^9/L (e.g., 150)
        bilirubin: Total bilirubin in mg/dL (e.g., 1.0)
        map_or_vasopressors: 0=MAP>=70, 1=MAP<70, 2=low dose dopamine, 3=high dose dopamine, 4=norepinephrine
        gcs: Glasgow Coma Scale (3-15)
        creatinine: Serum creatinine in mg/dL (e.g., 1.2)

    Output:
        float: SOFA score (0-24)
            - 0-1: ~0% mortality
            - 2-3: ~6% mortality
            - 4-5: ~20% mortality
            - 6-7: ~22% mortality
            - 8-9: ~33% mortality
            - 10-11: ~50% mortality
            - >= 12: ~80%+ mortality

    Example:
        >>> sofa_score(pao2_fio2_ratio=300, platelets=100, gcs=14)
        3.0
    """
    # Handle aliases — LLM may send alternative parameter names
    if pao2_fio2_ratio is None:
        pao2_fio2_ratio = kwargs.get('pf_ratio', kwargs.get('pao2_fio2', kwargs.get('p_f_ratio', None)))
    if map_or_vasopressors == 0:
        # LLM may send vasopressor info under different names
        v = kwargs.get('norepinephrine_mcg_kg_min', kwargs.get('vasopressors', kwargs.get('map', kwargs.get('cardiovascular', None))))
        if v is not None:
            if isinstance(v, dict):
                # Extract a numeric value from a dict — try 'score', 'value', or first numeric value
                v = v.get('score', v.get('value', next((val for val in v.values() if isinstance(val, (int, float))), 0)))
            try:
                map_or_vasopressors = int(float(v))
            except (ValueError, TypeError):
                map_or_vasopressors = 0

    # Coerce map_or_vasopressors if it's a dict (LLM sometimes sends dict instead of int)
    if isinstance(map_or_vasopressors, dict):
        map_or_vasopressors = map_or_vasopressors.get('score', map_or_vasopressors.get('value',
            next((val for val in map_or_vasopressors.values() if isinstance(val, (int, float))), 0)))
        try:
            map_or_vasopressors = int(float(map_or_vasopressors))
        except (ValueError, TypeError):
            map_or_vasopressors = 0

    # Coerce gcs if it's a dict (LLM sometimes sends dict instead of int)
    if isinstance(gcs, dict):
        gcs = gcs.get('total', gcs.get('score', gcs.get('value',
            next((val for val in gcs.values() if isinstance(val, (int, float))), 15))))
        try:
            gcs = int(float(gcs))
        except (ValueError, TypeError):
            gcs = 15

    score = 0

    # Respiration
    if pao2_fio2_ratio is not None:
        if pao2_fio2_ratio >= 400:
            score += 0
        elif pao2_fio2_ratio >= 300:
            score += 1
        elif pao2_fio2_ratio >= 200:
            score += 2
        elif pao2_fio2_ratio >= 100:
            score += 3
        else:
            score += 4

    # Coagulation
    if platelets is not None:
        if platelets >= 150:
            score += 0
        elif platelets >= 100:
            score += 1
        elif platelets >= 50:
            score += 2
        elif platelets >= 20:
            score += 3
        else:
            score += 4

    # Liver
    if bilirubin is not None:
        if bilirubin < 1.2:
            score += 0
        elif bilirubin < 2.0:
            score += 1
        elif bilirubin < 6.0:
            score += 2
        elif bilirubin < 12.0:
            score += 3
        else:
            score += 4

    # Cardiovascular
    score += min(4, map_or_vasopressors)

    # CNS
    if gcs >= 15:
        score += 0
    elif gcs >= 13:
        score += 1
    elif gcs >= 10:
        score += 2
    elif gcs >= 6:
        score += 3
    else:
        score += 4

    # Renal
    if creatinine is not None:
        if creatinine < 1.2:
            score += 0
        elif creatinine < 2.0:
            score += 1
        elif creatinine < 3.5:
            score += 2
        elif creatinine < 5.0:
            score += 3
        else:
            score += 4

    return float(score)


# =============================================================================
# Infectious/Inflammatory Calculators (4)
# =============================================================================

@calculator(
    name="Centor Score (McIsaac)",
    aliases=["centor", "mcisaac", "strep pharyngitis"]
)
def centor_score(
    tonsillar_exudate: bool = False,
    tender_lymphadenopathy: bool = False,
    fever: bool = False,
    absence_of_cough: bool = False,
    age: float = None
) -> float:
    """Calculate Centor Score (Modified/McIsaac) for Strep Pharyngitis.

    Formula: Sum with age modifier

    Input:
        tonsillar_exudate: Tonsillar exudates/swelling (+1)
        tender_lymphadenopathy: Tender anterior cervical lymphadenopathy (+1)
        fever: Temperature > 38C/100.4F (+1)
        absence_of_cough: Absence of cough (+1)
        age: Patient age for McIsaac modifier
            - < 15: +1
            - 15-44: 0
            - >= 45: -1

    Output:
        float: Centor/McIsaac score (0-5)
            - 0-1: No testing or antibiotics
            - 2-3: Rapid strep test
            - 4-5: Empiric antibiotics reasonable

    Example:
        >>> centor_score(tonsillar_exudate=True, fever=True, absence_of_cough=True, age=25)
        3.0
    """
    score = 0

    if tonsillar_exudate:
        score += 1
    if tender_lymphadenopathy:
        score += 1
    if fever:
        score += 1
    if absence_of_cough:
        score += 1

    # McIsaac age modifier
    if age is not None:
        if age < 15:
            score += 1
        elif age >= 45:
            score -= 1

    return float(max(0, score))


@calculator(
    name="FeverPAIN Score",
    aliases=["feverpain"]
)
def feverpain(
    fever: bool = False,
    purulence: bool = False,
    attend_rapidly: bool = False,
    inflamed_tonsils: bool = False,
    no_cough_coryza: bool = False,
    **kwargs
) -> float:
    """Calculate FeverPAIN Score for Strep Pharyngitis.

    Formula: Fever + Purulence + Attend rapidly + Inflamed tonsils + No cough/coryza (0-5)

    Input:
        fever: Fever in last 24 hours (+1)
        purulence: Pharyngeal/tonsillar exudate (+1)
        attend_rapidly: Attend within 3 days of symptom onset (+1)
        inflamed_tonsils: Severely inflamed tonsils (+1)
        no_cough_coryza: No cough or coryza (+1)

    Output:
        float: FeverPAIN score (0-5)
            - 0-1: 13-18% strep, no antibiotics
            - 2-3: 34-40% strep, consider delayed antibiotics
            - 4-5: 62-65% strep, consider immediate antibiotics

    Example:
        >>> feverpain(fever=True, purulence=True, no_cough_coryza=True)
        3.0
    """
    score = 0
    if fever:
        score += 1
    if purulence:
        score += 1
    if attend_rapidly:
        score += 1
    if inflamed_tonsils:
        score += 1
    if no_cough_coryza:
        score += 1
    return float(score)


@calculator(
    name="SIRS Criteria",
    aliases=["sirs"]
)
def sirs_criteria(
    temperature_abnormal: bool = False,
    heart_rate_elevated: bool = False,
    respiratory_abnormal: bool = False,
    wbc_abnormal: bool = False
) -> float:
    """Calculate SIRS Criteria count.

    Formula: Count of criteria met (>= 2 = SIRS positive)

    Input:
        temperature_abnormal: Temp > 38C or < 36C (+1)
        heart_rate_elevated: HR > 90 bpm (+1)
        respiratory_abnormal: RR > 20 or PaCO2 < 32 mmHg (+1)
        wbc_abnormal: WBC > 12,000 or < 4,000 or > 10% bands (+1)

    Output:
        float: Number of SIRS criteria met (0-4)
            - >= 2: SIRS positive

    Example:
        >>> sirs_criteria(temperature_abnormal=True, heart_rate_elevated=True)
        2.0
    """
    score = 0
    if temperature_abnormal:
        score += 1
    if heart_rate_elevated:
        score += 1
    if respiratory_abnormal:
        score += 1
    if wbc_abnormal:
        score += 1
    return float(score)


@calculator(
    name="Glasgow-Blatchford Score (GBS)",
    aliases=["gbs", "glasgow-blatchford", "blatchford"]
)
def gbs(
    bun_score: int = 0,
    hemoglobin_score: int = 0,
    systolic_bp_score: int = 0,
    tachycardia: bool = False,
    melena: bool = False,
    syncope: bool = False,
    liver_disease: bool = False,
    cardiac_failure: bool = False,
    **kwargs
) -> float:
    """Calculate Glasgow-Blatchford Bleeding Score.

    Formula: Sum of clinical and lab criteria (0-23)

    Input:
        bun_score: BUN points
            - 6.5-8: 2 pts, 8-10: 3 pts, 10-25: 4 pts, >25: 6 pts
        hemoglobin_score: Hemoglobin points (varies by sex)
            - Men: 12-13: 1 pt, 10-12: 3 pts, <10: 6 pts
            - Women: 10-12: 1 pt, <10: 6 pts
        systolic_bp_score: SBP points
            - 100-109: 1 pt, 90-99: 2 pts, <90: 3 pts
        tachycardia: HR >= 100 (+1)
        melena: Melena present (+1)
        syncope: Syncope (+2)
        liver_disease: Known liver disease (+2)
        cardiac_failure: Known cardiac failure (+2)

    Output:
        float: GBS score (0-23)
            - 0: Very low risk, outpatient management
            - 1-6: Low risk
            - >= 7: High risk, requires intervention

    Example:
        >>> gbs(bun_score=4, hemoglobin_score=3, melena=True, syncope=True)
        10.0
    """
    # Convert raw values to scores if LLM sends raw clinical values
    raw_bun = kwargs.get('bun', kwargs.get('blood_urea_nitrogen', None))
    if bun_score == 0 and raw_bun is not None:
        raw_bun = float(raw_bun)
        # BUN in mmol/L scoring
        if raw_bun >= 25:
            bun_score = 6
        elif raw_bun >= 10:
            bun_score = 4
        elif raw_bun >= 8:
            bun_score = 3
        elif raw_bun >= 6.5:
            bun_score = 2

    raw_hb = kwargs.get('hemoglobin', kwargs.get('hgb', kwargs.get('hb', None)))
    sex = kwargs.get('sex', kwargs.get('gender', 'male'))
    if hemoglobin_score == 0 and raw_hb is not None:
        raw_hb = float(raw_hb)
        is_male = isinstance(sex, str) and sex.lower().startswith('m')
        if raw_hb < 10:
            hemoglobin_score = 6
        elif raw_hb < 12:
            hemoglobin_score = 3 if is_male else 1
        elif raw_hb < 13 and is_male:
            hemoglobin_score = 1

    raw_sbp = kwargs.get('systolic_bp', kwargs.get('sbp', kwargs.get('systolic_blood_pressure', None)))
    if systolic_bp_score == 0 and raw_sbp is not None:
        raw_sbp = float(raw_sbp)
        if raw_sbp < 90:
            systolic_bp_score = 3
        elif raw_sbp < 100:
            systolic_bp_score = 2
        elif raw_sbp < 110:
            systolic_bp_score = 1

    raw_hr = kwargs.get('heart_rate', kwargs.get('hr', kwargs.get('pulse', None)))
    if not tachycardia and raw_hr is not None:
        tachycardia = float(raw_hr) >= 100

    score = int(bun_score) + int(hemoglobin_score) + int(systolic_bp_score)
    if tachycardia:
        score += 1
    if melena:
        score += 1
    if syncope:
        score += 2
    if liver_disease:
        score += 2
    if cardiac_failure:
        score += 2
    return float(score)


# =============================================================================
# Hematologic/Coagulation Calculators (4)
# =============================================================================

@calculator(
    name="HAS-BLED Score",
    aliases=["has-bled", "hasbled"]
)
def has_bled(
    hypertension: bool = False,
    abnormal_renal: bool = False,
    abnormal_liver: bool = False,
    stroke: bool = False,
    bleeding: bool = False,
    labile_inr: bool = False,
    elderly: bool = False,
    drugs: bool = False,
    alcohol: bool = False
) -> float:
    """Calculate HAS-BLED Score for Major Bleeding Risk.

    Formula: H-A-S-B-L-E-D criteria (0-9 points)

    Input:
        hypertension: Uncontrolled HTN (SBP > 160) (+1)
        abnormal_renal: Dialysis, transplant, Cr > 2.26 mg/dL (+1)
        abnormal_liver: Cirrhosis, bilirubin > 2x normal (+1)
        stroke: Prior stroke (+1)
        bleeding: Prior bleeding or predisposition (+1)
        labile_inr: Labile INR (TTR < 60%) (+1)
        elderly: Age > 65 (+1)
        drugs: Antiplatelet or NSAID use (+1)
        alcohol: >= 8 drinks/week (+1)

    Output:
        float: HAS-BLED score (0-9)
            - 0-2: Low bleeding risk
            - >= 3: High bleeding risk, caution with anticoagulation

    Example:
        >>> has_bled(hypertension=True, elderly=True, drugs=True)
        3.0
    """
    score = 0
    if hypertension:
        score += 1
    if abnormal_renal:
        score += 1
    if abnormal_liver:
        score += 1
    if stroke:
        score += 1
    if bleeding:
        score += 1
    if labile_inr:
        score += 1
    if elderly:
        score += 1
    if drugs:
        score += 1
    if alcohol:
        score += 1
    return float(score)


@calculator(
    name="Wells' Criteria for DVT",
    aliases=["wells dvt", "wells criteria for dvt"]
)
def wells_dvt(
    active_cancer: bool = False,
    paralysis: bool = False,
    bedridden: bool = False,
    localized_tenderness: bool = False,
    leg_swelling: bool = False,
    calf_swelling_3cm: bool = False,
    pitting_edema: bool = False,
    collateral_veins: bool = False,
    previous_dvt: bool = False,
    alternative_diagnosis: bool = False
) -> float:
    """Calculate Wells' Criteria for DVT.

    Formula: Sum of clinical criteria points

    Input:
        active_cancer: Active cancer (treatment within 6 months) (+1)
        paralysis: Paralysis, paresis, or recent leg cast (+1)
        bedridden: Bedridden > 3 days or major surgery within 12 weeks (+1)
        localized_tenderness: Localized tenderness along deep venous system (+1)
        leg_swelling: Entire leg swollen (+1)
        calf_swelling_3cm: Calf swelling > 3cm compared to asymptomatic leg (+1)
        pitting_edema: Pitting edema confined to symptomatic leg (+1)
        collateral_veins: Collateral superficial veins (+1)
        previous_dvt: Previously documented DVT (+1)
        alternative_diagnosis: Alternative diagnosis at least as likely (-2)

    Output:
        float: Wells DVT score
            - <= 0: Low probability (5%)
            - 1-2: Moderate probability (17%)
            - >= 3: High probability (53%)

    Example:
        >>> wells_dvt(active_cancer=True, leg_swelling=True, calf_swelling_3cm=True)
        3.0
    """
    score = 0
    if active_cancer:
        score += 1
    if paralysis:
        score += 1
    if bedridden:
        score += 1
    if localized_tenderness:
        score += 1
    if leg_swelling:
        score += 1
    if calf_swelling_3cm:
        score += 1
    if pitting_edema:
        score += 1
    if collateral_veins:
        score += 1
    if previous_dvt:
        score += 1
    if alternative_diagnosis:
        score -= 2
    return float(score)


@calculator(
    name="Caprini VTE Score",
    aliases=["caprini", "vte score", "caprini vte score", "caprini score",
             "caprini risk assessment", "caprini vte"]
)
def caprini(
    age_score: int = 0,
    surgery_score: int = 0,
    mobility_score: int = 0,
    condition_scores: int = 0,
    **kwargs
) -> float:
    """Calculate Caprini Score for Venous Thromboembolism Risk.

    Formula: Sum of weighted risk factors

    Input:
        age_score: Age points
            - 41-60: 1 pt
            - 61-74: 2 pts
            - >= 75: 3 pts
        surgery_score: Surgery type points
            - Minor: 1 pt
            - Major (> 45 min): 2 pts
            - Elective lower extremity arthroplasty: 5 pts
        mobility_score: Mobility restriction points
            - Currently on bed rest: 1 pt
            - Confined to bed > 72 hrs: 2 pts
        condition_scores: Sum of condition points (varies by condition)

    Output:
        float: Caprini score
            - 0-1: Very low risk
            - 2: Low risk
            - 3-4: Moderate risk
            - >= 5: High risk

    Example:
        >>> caprini(age_score=2, surgery_score=2, condition_scores=1)
        5.0
    """
    # Coerce all score params to int (LLM may send strings)
    def _to_int(v):
        if v is None:
            return 0
        if isinstance(v, str):
            try:
                return int(float(v))
            except (ValueError, TypeError):
                return 0
        try:
            return int(v)
        except (ValueError, TypeError):
            return 0

    age_score = _to_int(age_score)
    surgery_score = _to_int(surgery_score)
    mobility_score = _to_int(mobility_score)

    # Handle condition_scores being a dict (sum True values) or list (sum items)
    if isinstance(condition_scores, dict):
        condition_scores = sum(1 for v in condition_scores.values() if v)
    elif isinstance(condition_scores, list):
        condition_scores = sum(_to_int(x) for x in condition_scores)
    else:
        condition_scores = _to_int(condition_scores)

    return float(age_score + surgery_score + mobility_score + condition_scores)


@calculator(
    name="Morphine Milligram Equivalents (MME)",
    aliases=["mme", "morphine equivalents"]
)
def mme(morphine_mg: float = 0, oxycodone_mg: float = 0, hydrocodone_mg: float = 0,
        hydromorphone_mg: float = 0, fentanyl_mcg_hr: float = 0, methadone_mg: float = 0,
        codeine_mg: float = 0, tramadol_mg: float = 0, **kwargs) -> float:
    """Calculate total Morphine Milligram Equivalents.

    Formula: Sum of (opioid dose * conversion factor)

    Input:
        morphine_mg: Morphine dose in mg (factor: 1)
        oxycodone_mg: Oxycodone dose in mg (factor: 1.5)
        hydrocodone_mg: Hydrocodone dose in mg (factor: 1)
        hydromorphone_mg: Hydromorphone dose in mg (factor: 4)
        fentanyl_mcg_hr: Fentanyl transdermal in mcg/hr (factor: 2.4)
        methadone_mg: Methadone dose in mg (factor: varies, using 3)
        codeine_mg: Codeine dose in mg (factor: 0.15)
        tramadol_mg: Tramadol dose in mg (factor: 0.1)

    Output:
        float: Total MME per day
            - < 50: Lower risk
            - 50-90: Moderate risk, caution
            - >= 90: High risk, avoid if possible

    Example:
        >>> mme(oxycodone_mg=30, hydrocodone_mg=20)
        65.0
    """
    # Guard against None values — LLM may send None for omitted opioids
    morphine_mg = float(morphine_mg or 0)
    oxycodone_mg = float(oxycodone_mg or 0)
    hydrocodone_mg = float(hydrocodone_mg or 0)
    hydromorphone_mg = float(hydromorphone_mg or 0)
    fentanyl_mcg_hr = float(fentanyl_mcg_hr or 0)
    methadone_mg = float(methadone_mg or 0)
    codeine_mg = float(codeine_mg or 0)
    tramadol_mg = float(tramadol_mg or 0)

    # Handle alternative param names from LLM extraction
    if 'tapentadol_mg' in kwargs:
        tap_val = kwargs['tapentadol_mg']
        tramadol_mg += float(tap_val or 0) * 0.1  # tapentadol ≈ 0.1 MME factor

    total = 0.0
    total += morphine_mg * 1.0
    total += oxycodone_mg * 1.5
    total += hydrocodone_mg * 1.0
    total += hydromorphone_mg * 4.0
    total += fentanyl_mcg_hr * 2.4
    total += methadone_mg * 3.0
    total += codeine_mg * 0.15
    total += tramadol_mg * 0.1
    return round(total, 1)


# =============================================================================
# ICU Scoring Calculators (2)
# =============================================================================

@calculator(
    name="APACHE II Score",
    aliases=["apache ii", "apache 2", "apache ii score", "apache-ii", "apache 2 score"]
)
def apache_ii(
    temperature_score: int = 0,
    map_score: int = 0,
    heart_rate_score: int = 0,
    respiratory_rate_score: int = 0,
    oxygenation_score: int = 0,
    ph_score: int = 0,
    sodium_score: int = 0,
    potassium_score: int = 0,
    creatinine_score: int = 0,
    hematocrit_score: int = 0,
    wbc_score: int = 0,
    gcs_score: int = 0,
    age_score: int = 0,
    chronic_health_score: int = 0,
    **kwargs
) -> float:
    """Calculate APACHE II Score for ICU mortality prediction.

    Formula: Acute Physiology Score + Age Points + Chronic Health Points

    Input:
        temperature_score: Temperature points (0-4)
        map_score: Mean arterial pressure points (0-4)
        heart_rate_score: Heart rate points (0-4)
        respiratory_rate_score: Respiratory rate points (0-4)
        oxygenation_score: A-aDO2 or PaO2 points (0-4)
        ph_score: Arterial pH points (0-4)
        sodium_score: Serum sodium points (0-4)
        potassium_score: Serum potassium points (0-4)
        creatinine_score: Serum creatinine points (0-4, doubled for ARF)
        hematocrit_score: Hematocrit points (0-4)
        wbc_score: WBC points (0-4)
        gcs_score: GCS points (15 - GCS, so 0-12)
        age_score: Age points
            - < 45: 0
            - 45-54: 2
            - 55-64: 3
            - 65-74: 5
            - >= 75: 6
        chronic_health_score: Chronic health points
            - Nonoperative/emergency: 5
            - Elective postoperative: 2

    Output:
        float: APACHE II score (0-71)
            - 0-4: ~4% mortality
            - 5-9: ~8% mortality
            - 10-14: ~15% mortality
            - 15-19: ~25% mortality
            - 20-24: ~40% mortality
            - 25-29: ~55% mortality
            - 30-34: ~73% mortality
            - >= 35: ~85% mortality

    Example:
        >>> apache_ii(temperature_score=1, map_score=2, gcs_score=3, age_score=5)
        11.0
    """
    # ---- APACHE II raw-value-to-score conversion helpers ----
    # When the LLM sends raw clinical values instead of pre-computed scores,
    # convert them using the standard APACHE II scoring tables.

    def _detect_raw_values(kw):
        """Check if kwargs contain raw clinical values (not _score params)."""
        raw_keys = {'temperature', 'temp', 'temp_c', 'map', 'mean_arterial_pressure',
                    'heart_rate', 'hr', 'pulse', 'respiratory_rate', 'rr',
                    'ph', 'arterial_ph', 'sodium', 'na', 'potassium', 'k',
                    'creatinine', 'cr', 'hematocrit', 'hct', 'wbc',
                    'white_blood_cells', 'gcs', 'glasgow_coma_scale',
                    'pao2', 'a_a_gradient', 'a_ado2', 'fio2', 'age'}
        return bool(raw_keys & set(kw.keys()))

    def _temp_score(temp_c):
        """APACHE II temperature score (0-4)."""
        if temp_c is None:
            return 0
        temp_c = float(temp_c)
        if temp_c >= 41.0:
            return 4
        if temp_c >= 39.0:
            return 3
        if temp_c >= 38.5:
            return 1
        if temp_c >= 36.0:
            return 0
        if temp_c >= 34.0:
            return 1
        if temp_c >= 32.0:
            return 2
        if temp_c >= 30.0:
            return 3
        return 4

    def _map_score_conv(m):
        """APACHE II MAP score (0-4)."""
        if m is None:
            return 0
        m = float(m)
        if m >= 160:
            return 4
        if m >= 130:
            return 3
        if m >= 110:
            return 2
        if m >= 70:
            return 0
        if m >= 50:
            return 2
        return 4

    def _hr_score(hr):
        """APACHE II heart rate score (0-4)."""
        if hr is None:
            return 0
        hr = float(hr)
        if hr >= 180:
            return 4
        if hr >= 140:
            return 3
        if hr >= 110:
            return 2
        if hr >= 70:
            return 0
        if hr >= 55:
            return 2
        if hr >= 40:
            return 3
        return 4

    def _rr_score(rr):
        """APACHE II respiratory rate score (0-4)."""
        if rr is None:
            return 0
        rr = float(rr)
        if rr >= 50:
            return 4
        if rr >= 35:
            return 3
        if rr >= 25:
            return 1
        if rr >= 12:
            return 0
        if rr >= 10:
            return 1
        if rr >= 6:
            return 2
        return 4

    def _oxygenation_score_conv(kw):
        """APACHE II oxygenation score (0-4) from FiO2, PaO2, or A-a gradient."""
        fio2 = kw.get('fio2', None)
        pao2 = kw.get('pao2', None)
        a_a = kw.get('a_a_gradient', kw.get('a_ado2', None))
        if fio2 is not None:
            fio2 = float(fio2)
            # Normalize if given as percentage (e.g., 70 -> 0.70)
            if fio2 > 1:
                fio2 = fio2 / 100
        if fio2 is not None and fio2 >= 0.5 and a_a is not None:
            a_a = float(a_a)
            if a_a >= 500:
                return 4
            if a_a >= 350:
                return 3
            if a_a >= 200:
                return 2
            return 0
        elif pao2 is not None:
            pao2 = float(pao2)
            if pao2 > 70:
                return 0
            if pao2 >= 61:
                return 1
            if pao2 >= 55:
                return 3
            return 4
        return 0

    def _ph_score_conv(ph):
        """APACHE II pH score (0-4)."""
        if ph is None:
            return 0
        ph = float(ph)
        if ph >= 7.7:
            return 4
        if ph >= 7.6:
            return 3
        if ph >= 7.5:
            return 1
        if ph >= 7.33:
            return 0
        if ph >= 7.25:
            return 2
        if ph >= 7.15:
            return 3
        return 4

    def _sodium_score_conv(na):
        """APACHE II sodium score (0-4)."""
        if na is None:
            return 0
        na = float(na)
        if na >= 180:
            return 4
        if na >= 160:
            return 3
        if na >= 155:
            return 2
        if na >= 150:
            return 1
        if na >= 130:
            return 0
        if na >= 120:
            return 2
        if na >= 111:
            return 3
        return 4

    def _potassium_score_conv(k):
        """APACHE II potassium score (0-4)."""
        if k is None:
            return 0
        k = float(k)
        if k >= 7.0:
            return 4
        if k >= 6.0:
            return 3
        if k >= 5.5:
            return 1
        if k >= 3.5:
            return 0
        if k >= 3.0:
            return 1
        if k >= 2.5:
            return 2
        return 4

    def _creatinine_score_conv(cr):
        """APACHE II creatinine score (0-4). Doubled for ARF not handled here."""
        if cr is None:
            return 0
        cr = float(cr)
        if cr >= 3.5:
            return 4
        if cr >= 2.0:
            return 3
        if cr >= 1.5:
            return 2
        if cr >= 0.6:
            return 0
        return 2

    def _hematocrit_score_conv(hct):
        """APACHE II hematocrit score (0-4)."""
        if hct is None:
            return 0
        hct = float(hct)
        if hct >= 60:
            return 4
        if hct >= 50:
            return 2
        if hct >= 46:
            return 1
        if hct >= 30:
            return 0
        if hct >= 20:
            return 2
        return 4

    def _wbc_score_conv(wbc):
        """APACHE II WBC score (0-4). WBC in thousands (10^3/uL)."""
        if wbc is None:
            return 0
        wbc = float(wbc)
        # If given as absolute count (e.g., 9800), convert to thousands
        if wbc > 300:
            wbc = wbc / 1000
        if wbc >= 40:
            return 4
        if wbc >= 20:
            return 2
        if wbc >= 15:
            return 1
        if wbc >= 3:
            return 0
        if wbc >= 1:
            return 2
        return 4

    def _gcs_to_score(gcs_val):
        """APACHE II GCS component = 15 - GCS (so GCS 15 -> 0, GCS 3 -> 12)."""
        if gcs_val is None:
            return 0
        gcs_val = int(float(gcs_val))
        return max(0, 15 - gcs_val)

    def _age_to_score(age_val):
        """APACHE II age score."""
        if age_val is None:
            return 0
        age_val = float(age_val)
        if age_val >= 75:
            return 6
        if age_val >= 65:
            return 5
        if age_val >= 55:
            return 3
        if age_val >= 45:
            return 2
        return 0

    # If raw clinical values are present in kwargs, convert to scores
    if _detect_raw_values(kwargs):
        raw_temp = kwargs.get('temperature', kwargs.get('temp', kwargs.get('temp_c', kwargs.get('body_temperature', None))))
        raw_map = kwargs.get('map', kwargs.get('mean_arterial_pressure', None))
        raw_hr = kwargs.get('heart_rate', kwargs.get('hr', kwargs.get('pulse', None)))
        raw_rr = kwargs.get('respiratory_rate', kwargs.get('rr', None))
        raw_ph = kwargs.get('ph', kwargs.get('arterial_ph', None))
        raw_na = kwargs.get('sodium', kwargs.get('na', None))
        raw_k = kwargs.get('potassium', kwargs.get('k', None))
        raw_cr = kwargs.get('creatinine', kwargs.get('cr', None))
        raw_hct = kwargs.get('hematocrit', kwargs.get('hct', None))
        raw_wbc = kwargs.get('wbc', kwargs.get('white_blood_cells', None))
        raw_gcs = kwargs.get('gcs', kwargs.get('glasgow_coma_scale', None))
        raw_age = kwargs.get('age', None)
        raw_chronic = kwargs.get('chronic_health', kwargs.get('chronic_health_points', None))

        # Only override a score param if caller didn't also provide a _score param
        if temperature_score == 0 and raw_temp is not None:
            temperature_score = _temp_score(raw_temp)
        if map_score == 0 and raw_map is not None:
            map_score = _map_score_conv(raw_map)
        if heart_rate_score == 0 and raw_hr is not None:
            heart_rate_score = _hr_score(raw_hr)
        if respiratory_rate_score == 0 and raw_rr is not None:
            respiratory_rate_score = _rr_score(raw_rr)
        if oxygenation_score == 0:
            oxygenation_score = _oxygenation_score_conv(kwargs)
        if ph_score == 0 and raw_ph is not None:
            ph_score = _ph_score_conv(raw_ph)
        if sodium_score == 0 and raw_na is not None:
            sodium_score = _sodium_score_conv(raw_na)
        if potassium_score == 0 and raw_k is not None:
            potassium_score = _potassium_score_conv(raw_k)
        if creatinine_score == 0 and raw_cr is not None:
            creatinine_score = _creatinine_score_conv(raw_cr)
        if hematocrit_score == 0 and raw_hct is not None:
            hematocrit_score = _hematocrit_score_conv(raw_hct)
        if wbc_score == 0 and raw_wbc is not None:
            wbc_score = _wbc_score_conv(raw_wbc)
        if gcs_score == 0 and raw_gcs is not None:
            gcs_score = _gcs_to_score(raw_gcs)
        if age_score == 0 and raw_age is not None:
            age_score = _age_to_score(raw_age)
        if chronic_health_score == 0 and raw_chronic is not None:
            chronic_health_score = int(float(raw_chronic))

    # Coerce all score values to numeric (LLM may send dicts/strings)
    def _ensure_num(v):
        if isinstance(v, dict):
            return int(v.get('score', v.get('value', v.get('points', 0))) or 0)
        if isinstance(v, str):
            try:
                return int(float(v))
            except (ValueError, TypeError):
                return 0
        try:
            return int(v)
        except (ValueError, TypeError):
            return 0

    score = (_ensure_num(temperature_score) + _ensure_num(map_score) +
             _ensure_num(heart_rate_score) + _ensure_num(respiratory_rate_score) +
             _ensure_num(oxygenation_score) + _ensure_num(ph_score) +
             _ensure_num(sodium_score) + _ensure_num(potassium_score) +
             _ensure_num(creatinine_score) + _ensure_num(hematocrit_score) +
             _ensure_num(wbc_score) + _ensure_num(gcs_score) +
             _ensure_num(age_score) + _ensure_num(chronic_health_score))
    return float(score)


@calculator(
    name="Charlson Comorbidity Index (CCI)",
    aliases=["cci", "charlson", "charlson comorbidity"]
)
def charlson(
    age: float,
    mi: bool = False,
    chf: bool = False,
    pvd: bool = False,
    cva: bool = False,
    dementia: bool = False,
    copd: bool = False,
    connective_tissue: bool = False,
    pud: bool = False,
    mild_liver: bool = False,
    diabetes: bool = False,
    hemiplegia: bool = False,
    moderate_renal: bool = False,
    diabetes_complications: bool = False,
    malignancy: bool = False,
    moderate_liver: bool = False,
    metastatic: bool = False,
    aids: bool = False,
    **kwargs
) -> float:
    """Calculate Charlson Comorbidity Index.

    Formula: Sum of weighted comorbidity points + age points

    Input:
        age: Patient age (1 pt per decade over 40, max 4)
        mi: Myocardial infarction (+1)
        chf: Congestive heart failure (+1)
        pvd: Peripheral vascular disease (+1)
        cva: Cerebrovascular disease/TIA (+1)
        dementia: Dementia (+1)
        copd: COPD (+1)
        connective_tissue: Connective tissue disease (+1)
        pud: Peptic ulcer disease (+1)
        mild_liver: Mild liver disease (+1)
        diabetes: Diabetes without complications (+1)
        hemiplegia: Hemiplegia (+2)
        moderate_renal: Moderate/severe renal disease (+2)
        diabetes_complications: Diabetes with complications (+2)
        malignancy: Any malignancy (+2)
        moderate_liver: Moderate/severe liver disease (+3)
        metastatic: Metastatic solid tumor (+6)
        aids: AIDS (+6)

    Output:
        float: CCI score
            - 0: 12% 10-year mortality
            - 1-2: 26% 10-year mortality
            - 3-4: 52% 10-year mortality
            - >= 5: 85% 10-year mortality

    Example:
        >>> charlson(age=65, diabetes=True, chf=True, copd=True)
        5.0
    """
    score = 0

    # Age points (1 per decade over 40, max 4)
    if age >= 50:
        score += min(4, int((age - 40) // 10))

    # 1 point conditions
    if mi:
        score += 1
    if chf:
        score += 1
    if pvd:
        score += 1
    if cva:
        score += 1
    if dementia:
        score += 1
    if copd:
        score += 1
    if connective_tissue:
        score += 1
    if pud:
        score += 1
    if mild_liver:
        score += 1
    if diabetes:
        score += 1

    # 2 point conditions
    if hemiplegia:
        score += 2
    if moderate_renal:
        score += 2
    if diabetes_complications:
        score += 2
    if malignancy:
        score += 2

    # 3 point conditions
    if moderate_liver:
        score += 3

    # 6 point conditions
    if metastatic:
        score += 6
    if aids:
        score += 6

    return float(score)


# =============================================================================
# Obstetric Calculators (3)
# =============================================================================

@calculator(
    name="Gestational Age",
    aliases=["gestational age", "estimated gestational age"]
)
def gestational_age(weeks: float, days: float = 0) -> float:
    """Calculate Gestational Age in weeks.

    Formula: weeks + days/7

    Input:
        weeks: Gestational weeks (e.g., 32)
        days: Additional days (0-6, e.g., 4)

    Output:
        float: Gestational age in weeks (e.g., 32.57)

    Example:
        >>> gestational_age(weeks=32, days=4)
        32.571
    """
    return round(weeks + days / 7, 3)


@calculator(
    name="Estimated Due Date",
    aliases=["due date", "edd", "estimated due date"]
)
def estimated_due_date(gestational_weeks: float = None, **kwargs) -> float:
    """Calculate weeks remaining until due date.

    Formula: 40 - current_gestational_age

    Input:
        gestational_weeks: Current gestational age in weeks (e.g., 28)

    Output:
        float: Weeks remaining until EDD (e.g., 12)
            - Full term: 37-42 weeks
            - Due date is 40 weeks from LMP

    Example:
        >>> estimated_due_date(gestational_weeks=28)
        12.0
    """
    # Handle aliases
    if gestational_weeks is None:
        gestational_weeks = kwargs.get('last_menstrual_period', kwargs.get('lmp',
            kwargs.get('gestational_age', kwargs.get('weeks', None))))
    if gestational_weeks is None:
        gestational_weeks = 0
    # If it's a date string (from last_menstrual_period), compute gestational age
    if isinstance(gestational_weeks, str):
        try:
            gestational_weeks = float(gestational_weeks)
        except (ValueError, TypeError):
            from datetime import datetime, date
            cycle_length = float(kwargs.get('cycle_length_days', kwargs.get('cycle_length', 28)) or 28)
            for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%B %d, %Y'):
                try:
                    lmp_date = datetime.strptime(gestational_weeks.strip(), fmt).date()
                    today = date.today()
                    days_diff = (today - lmp_date).days
                    gestational_weeks = days_diff / 7.0
                    break
                except ValueError:
                    continue
            else:
                gestational_weeks = 0
    gestational_weeks = float(gestational_weeks)
    return round(40 - gestational_weeks, 3)


@calculator(
    name="Date of Conception",
    aliases=["conception date", "estimated of conception"]
)
def conception_date(gestational_weeks: float = None, **kwargs) -> float:
    """Calculate weeks since conception.

    Formula: gestational_weeks - 2 (conception ~2 weeks after LMP)

    Input:
        gestational_weeks: Current gestational age in weeks (e.g., 28)

    Output:
        float: Weeks since conception (e.g., 26)

    Example:
        >>> conception_date(gestational_weeks=28)
        26.0
    """
    # Handle aliases — LLM may send last_menstrual_period or lmp instead of gestational_weeks
    if gestational_weeks is None:
        gestational_weeks = kwargs.get('last_menstrual_period', kwargs.get('lmp',
            kwargs.get('gestational_age', kwargs.get('weeks', None))))
    if gestational_weeks is None:
        gestational_weeks = 0
    # If it's a date string (from last_menstrual_period), try to compute weeks from LMP
    if isinstance(gestational_weeks, str):
        try:
            gestational_weeks = float(gestational_weeks)
        except (ValueError, TypeError):
            # Try parsing as a date — compute weeks from LMP to today
            from datetime import datetime, date
            for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%B %d, %Y'):
                try:
                    lmp_date = datetime.strptime(gestational_weeks.strip(), fmt).date()
                    today = date.today()
                    days_diff = (today - lmp_date).days
                    gestational_weeks = days_diff / 7.0
                    break
                except ValueError:
                    continue
            else:
                gestational_weeks = 0
    gestational_weeks = float(gestational_weeks)
    return round(gestational_weeks - 2, 3)


# =============================================================================
# Other Calculators (3)
# =============================================================================

@calculator(
    name="Glasgow Coma Scale (GCS)",
    aliases=["gcs", "glasgow coma"]
)
def gcs(eye: int, verbal: int, motor: int, **kwargs) -> float:
    """Calculate Glasgow Coma Scale total score.

    Formula: Eye + Verbal + Motor (3-15)

    Input:
        eye: Eye response (1-4)
            - 1: No response
            - 2: Opens to pain
            - 3: Opens to voice
            - 4: Opens spontaneously
        verbal: Verbal response (1-5)
            - 1: No response
            - 2: Incomprehensible sounds
            - 3: Inappropriate words
            - 4: Confused
            - 5: Oriented
        motor: Motor response (1-6)
            - 1: No response
            - 2: Extension to pain
            - 3: Flexion to pain
            - 4: Withdraws from pain
            - 5: Localizes to pain
            - 6: Obeys commands

    Output:
        float: GCS total score (3-15)
            - 3-8: Severe brain injury (coma)
            - 9-12: Moderate brain injury
            - 13-15: Minor brain injury

    Example:
        >>> gcs(eye=4, verbal=5, motor=6)
        15.0
    """
    # Map descriptive strings to GCS scores (LLM may send text descriptions)
    _eye_map = {
        'no response': 1, 'none': 1, 'no eye': 1, 'no eye opening': 1,
        'pain': 2, 'to pain': 2, 'pressure': 2, 'eye opening to pain': 2,
        'voice': 3, 'to voice': 3, 'to speech': 3, 'command': 3, 'eye opening to voice': 3,
        'spontaneous': 4, 'spontaneously': 4, 'eye opening spontaneous': 4,
    }
    _verbal_map = {
        'no response': 1, 'none': 1, 'no verbal': 1, 'intubated': 1,
        'incomprehensible': 2, 'sounds': 2, 'moaning': 2,
        'inappropriate': 3, 'words': 3,
        'confused': 4, 'disoriented': 4,
        'oriented': 5, 'normal': 5, 'conversant': 5,
    }
    _motor_map = {
        'no response': 1, 'none': 1, 'no motor': 1,
        'extension': 2, 'decerebrate': 2, 'extensor': 2,
        'flexion': 3, 'abnormal flexion': 3, 'decorticate': 3,
        'withdrawal': 4, 'withdraws': 4, 'withdraw': 4,
        'localizes': 5, 'localising': 5, 'localize': 5,
        'obeys': 6, 'obey': 6, 'commands': 6, 'normal': 6,
    }

    def _gcs_parse(val, mapping, default=1):
        if val is None:
            return default
        if isinstance(val, str):
            val_l = val.lower().strip()
            # Try numeric parse first
            try:
                return int(float(val_l))
            except (ValueError, TypeError):
                pass
            for kw, score in mapping.items():
                if kw in val_l:
                    return score
            return default
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return default

    eye = _gcs_parse(eye, _eye_map, 1)
    verbal = _gcs_parse(verbal, _verbal_map, 1)
    motor = _gcs_parse(motor, _motor_map, 1)

    return float(eye + verbal + motor)


@calculator(
    name="HOMA-IR",
    aliases=["homa-ir", "homa ir", "insulin resistance"]
)
def homa_ir(fasting_glucose: float, fasting_insulin: float) -> float:
    """Calculate HOMA-IR for Insulin Resistance.

    Formula: HOMA-IR = (Glucose * Insulin) / 405

    Input:
        fasting_glucose: Fasting glucose in mg/dL (e.g., 100)
        fasting_insulin: Fasting insulin in uU/mL (e.g., 10)

    Output:
        float: HOMA-IR value
            - < 1.0: Normal insulin sensitivity
            - 1.0-2.0: Early insulin resistance
            - 2.0-2.9: Significant insulin resistance
            - >= 3.0: Severe insulin resistance

    Example:
        >>> homa_ir(fasting_glucose=100, fasting_insulin=10)
        2.469
    """
    return round((fasting_glucose * fasting_insulin) / 405, 3)


@calculator(
    name="Framingham Risk Score",
    aliases=["framingham risk", "framingham heart"]
)
def framingham_risk(
    age: float,
    sex: str,
    total_cholesterol: float,
    hdl: float,
    systolic: float,
    smoker: bool = False,
    treated_bp: bool = False,
    **kwargs
) -> float:
    """Calculate Framingham 10-Year CHD Risk.

    Formula: Complex multivariate equation based on age, sex, lipids, BP, smoking

    Input:
        age: Patient age in years (30-79)
        sex: Patient sex ("male" or "female")
        total_cholesterol: Total cholesterol in mg/dL (e.g., 200)
        hdl: HDL cholesterol in mg/dL (e.g., 50)
        systolic: Systolic blood pressure in mmHg (e.g., 130)
        smoker: Current smoker (True/False)
        treated_bp: On blood pressure medication (True/False)

    Output:
        float: 10-year CHD risk as percentage (e.g., 8.5)
            - < 10%: Low risk
            - 10-20%: Intermediate risk
            - > 20%: High risk

    Example:
        >>> framingham_risk(age=55, sex="male", total_cholesterol=220, hdl=45, systolic=140, smoker=True)
        18.2
    """
    if sex.lower() == 'male':
        ln_age = math.log(age) * 52.00961
        ln_chol = math.log(total_cholesterol) * 20.014077
        ln_hdl = math.log(hdl) * -0.905964
        ln_sbp = math.log(systolic) * (1.916 if treated_bp else 1.809)
        smoking_pts = 7.837 if smoker else 0
        base = -172.300168

        s = ln_age + ln_chol + ln_hdl + ln_sbp + smoking_pts + base
        risk = 1 - 0.9402 ** math.exp(s)
    else:
        ln_age = math.log(age) * 31.764001
        ln_chol = math.log(total_cholesterol) * 22.465206
        ln_hdl = math.log(hdl) * -1.187731
        ln_sbp = math.log(systolic) * (2.019 if treated_bp else 1.957)
        smoking_pts = 7.574 if smoker else 0
        base = -146.5933061

        s = ln_age + ln_chol + ln_hdl + ln_sbp + smoking_pts + base
        risk = 1 - 0.98767 ** math.exp(s)

    return round(risk * 100, 1)


# =============================================================================
# Registry Access Functions
# =============================================================================

def get_all_calculators() -> Dict[str, CalculatorSpec]:
    """Return all registered calculators."""
    return CALCULATOR_REGISTRY


def get_calculator_signatures() -> Dict[str, Dict]:
    """Return signatures in format compatible with L4 pipeline."""
    signatures = {}
    seen = set()
    for name, spec in CALCULATOR_REGISTRY.items():
        if spec.name not in seen:
            signatures[spec.name] = {
                "required": spec.required,
                "optional": spec.optional,
                "formula": spec.formula,
                "aliases": spec.aliases,
                "docstring": spec.func.__doc__
            }
            seen.add(spec.name)
    return signatures


def get_calculator_names() -> List[str]:
    """Return list of all unique calculator names."""
    seen = set()
    names = []
    for spec in CALCULATOR_REGISTRY.values():
        if spec.name not in seen:
            names.append(spec.name)
            seen.add(spec.name)
    return sorted(names)


def get_calculator_docstring(calculator_name: str) -> Optional[str]:
    """Get the docstring for a calculator, for use in extraction prompts.

    Args:
        calculator_name: Name or alias of the calculator

    Returns:
        The function's docstring, or None if not found
    """
    calc_lower = calculator_name.lower()

    # First try exact match
    if calc_lower in CALCULATOR_REGISTRY:
        spec = CALCULATOR_REGISTRY[calc_lower]
        return spec.func.__doc__

    # Then try matching against formal names
    for name, spec in CALCULATOR_REGISTRY.items():
        if calc_lower == spec.name.lower():
            return spec.func.__doc__
        if any(calc_lower == a.lower() for a in spec.aliases):
            return spec.func.__doc__
        if calc_lower in spec.name.lower():
            return spec.func.__doc__

    return None


def get_extraction_hints(calculator_name: str) -> str:
    """Get extraction hints from calculator docstring for LLM prompting.

    Extracts the 'Input:' section from the docstring which contains
    detailed guidance on how to extract each value.

    Args:
        calculator_name: Name or alias of the calculator

    Returns:
        The Input section of the docstring, or empty string if not found
    """
    docstring = get_calculator_docstring(calculator_name)
    if not docstring:
        return ""

    # Extract the Input section
    lines = docstring.split('\n')
    input_lines = []
    in_input_section = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('Input:'):
            in_input_section = True
            continue
        elif stripped.startswith('Output:') or stripped.startswith('Example:'):
            in_input_section = False
        elif in_input_section:
            input_lines.append(line)

    base_hints = '\n'.join(input_lines).strip()

    # Add supplementary extraction guidance for complex calculators where
    # the docstring Input section alone is insufficient for LLM extraction.
    calc_lower = calculator_name.lower()
    extra_hints = _COMPLEX_CALCULATOR_HINTS.get(calc_lower, "")

    if extra_hints:
        return f"{base_hints}\n\nExtraction guidance:\n{extra_hints}" if base_hints else extra_hints

    return base_hints


# Supplementary extraction hints for calculators whose parameters require
# non-obvious mapping from clinical note text to function arguments.
_COMPLEX_CALCULATOR_HINTS: Dict[str, str] = {
    "steroid conversion": (
        "Extract the steroid name (e.g., dexamethasone, prednisone, hydrocortisone) "
        "and the dose in mg. The steroid_name should be just the drug name as a "
        "lowercase string, and dose_mg should be the numeric dose value."
    ),
    "prednisone equivalent": (
        "Extract the steroid name (e.g., dexamethasone, prednisone, hydrocortisone) "
        "and the dose in mg. The steroid_name should be just the drug name as a "
        "lowercase string, and dose_mg should be the numeric dose value."
    ),
    "mme": (
        "Extract each opioid medication and its dose separately. Use parameter names: "
        "morphine_mg, oxycodone_mg, hydrocodone_mg, hydromorphone_mg, fentanyl_mcg_hr, "
        "methadone_mg, codeine_mg, tramadol_mg. Only include opioids that are actually "
        "mentioned in the patient note. Set unmentioned opioids to 0 or omit them."
    ),
    "morphine equivalents": (
        "Extract each opioid medication and its dose separately. Use parameter names: "
        "morphine_mg, oxycodone_mg, hydrocodone_mg, hydromorphone_mg, fentanyl_mcg_hr, "
        "methadone_mg, codeine_mg, tramadol_mg. Only include opioids that are actually "
        "mentioned in the patient note. Set unmentioned opioids to 0 or omit them."
    ),
}


def compute(calculator_name: str, values: Dict[str, Any]) -> Optional[float]:
    """Compute a calculation using the registered calculator.

    Args:
        calculator_name: Name or alias of calculator
        values: Dictionary of parameter values

    Returns:
        Calculated result, or None if calculator not found or computation fails
    """
    import re

    # Find calculator by name or alias (case-insensitive)
    calc_lower = calculator_name.lower().strip()
    spec = None

    # First try exact match on registered names (aliases stored lowercased)
    if calc_lower in CALCULATOR_REGISTRY:
        spec = CALCULATOR_REGISTRY[calc_lower]
    else:
        # Then try matching against formal names and aliases
        for name, s in CALCULATOR_REGISTRY.items():
            if calc_lower == s.name.lower():
                spec = s
                break
            if any(calc_lower == a.lower() for a in s.aliases):
                spec = s
                break
            # Partial match: input contained in formal name
            if calc_lower in s.name.lower():
                spec = s
                break
            # Reverse partial match: formal name contained in input
            if s.name.lower() in calc_lower:
                spec = s
                break

    # If still not found, try stripping common suffixes and retry
    if spec is None:
        stripped = re.sub(r'\s+(score|calculator|index)\s*$', '', calc_lower, flags=re.IGNORECASE).strip()
        if stripped != calc_lower:
            if stripped in CALCULATOR_REGISTRY:
                spec = CALCULATOR_REGISTRY[stripped]
            else:
                for name, s in CALCULATOR_REGISTRY.items():
                    s_stripped = re.sub(r'\s+(score|calculator|index)\s*$', '', s.name.lower()).strip()
                    if stripped == s_stripped:
                        spec = s
                        break
                    if any(stripped == re.sub(r'\s+(score|calculator|index)\s*$', '', a.lower()).strip()
                           for a in s.aliases):
                        spec = s
                        break

    if spec is None:
        return None

    # Call the function with provided values
    try:
        return spec.func(**values)
    except (TypeError, KeyError, ValueError):
        return None


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Testing calculator_simple.py")
    print("=" * 60)

    # Test a few calculators
    print(f"\nBMI: {bmi(weight_kg=80, height_cm=175)}")
    print(f"MAP: {mean_arterial_pressure(systolic=120, diastolic=80)}")
    print(f"CrCl: {creatinine_clearance(age=70, sex='male', weight_kg=80, creatinine_mg_dl=1.5)}")
    print(f"CKD-EPI: {ckd_epi_gfr(age=65, sex='male', creatinine_mg_dl=1.2)}")
    print(f"Anion Gap: {anion_gap(sodium=140, chloride=100, bicarbonate=24)}")

    # Test registry
    print(f"\nTotal calculators registered: {len(get_calculator_names())}")
    print("\nCalculator names:")
    for name in get_calculator_names()[:10]:
        print(f"  - {name}")
    print("  ...")

    # Test compute function
    print("\nTest compute function:")
    result = compute("bmi", {"weight_kg": 80, "height_cm": 175})
    print(f"  compute('bmi', ...): {result}")

    result = compute("creatinine clearance", {"age": 70, "sex": "male", "weight_kg": 80, "creatinine_mg_dl": 1.5})
    print(f"  compute('creatinine clearance', ...): {result}")
