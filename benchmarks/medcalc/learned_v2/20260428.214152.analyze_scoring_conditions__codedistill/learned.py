"""Auto-generated code-distilled implementation for analyze_scoring_conditions."""

import re
import json


def analyze_scoring_conditions(clinical_note, scoring_system):
    """
    Analyze a clinical note for conditions relevant to a given scoring system.
    Returns a dict with reasoning, conditions_present, conditions_absent, and demographics.
    """
    if not clinical_note or not scoring_system:
        return None

    try:
        demographics = _extract_demographics(clinical_note)
        
        if scoring_system == 'APACHE II Score':
            return _analyze_apache_ii(clinical_note, demographics)
        elif scoring_system == 'SIRS Criteria':
            return _analyze_sirs(clinical_note, demographics)
        else:
            return _analyze_generic(clinical_note, scoring_system, demographics)
    except Exception:
        return None


def _extract_demographics(note):
    demographics = {}
    
    # Extract age
    age_patterns = [
        r'(\d{1,3})\s*[-–]?\s*year\s*[-–]?\s*old',
        r'age\s*(?:of\s*)?(\d{1,3})',
        r'aged\s*(\d{1,3})',
    ]
    for pat in age_patterns:
        m = re.search(pat, note, re.IGNORECASE)
        if m:
            demographics['age'] = int(m.group(1))
            break

    # Extract sex
    sex_patterns = [
        (r'\b(?:woman|female|lady|girl)\b', 'female'),
        (r'\b(?:man|male|boy|gentleman)\b', 'male'),
    ]
    for pat, sex in sex_patterns:
        if re.search(pat, note, re.IGNORECASE):
            demographics['sex'] = sex
            break

    return demographics


def _extract_vitals(note):
    vitals = {}

    # Temperature
    # Fahrenheit
    m = re.search(r'(?:temperature|temp|T)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{2,3}(?:\.\d+)?)\s*°?\s*F', note, re.IGNORECASE)
    if m:
        f_val = float(m.group(1))
        vitals['temperature_c'] = round((f_val - 32) * 5.0 / 9.0, 1)
        vitals['temperature_f'] = f_val
    # Celsius
    m2 = re.search(r'(?:temperature|temp|T)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{2}(?:\.\d+)?)\s*°?\s*C', note, re.IGNORECASE)
    if m2 and 'temperature_c' not in vitals:
        vitals['temperature_c'] = float(m2.group(1))
    # Generic temperature with degrees
    if 'temperature_c' not in vitals:
        m3 = re.search(r'(\d{2,3}(?:\.\d+)?)\s*°\s*C', note)
        if m3:
            val = float(m3.group(1))
            if 30 <= val <= 45:
                vitals['temperature_c'] = val
        m4 = re.search(r'(\d{2,3}(?:\.\d+)?)\s*°\s*F', note)
        if m4 and 'temperature_c' not in vitals:
            f_val = float(m4.group(1))
            if 90 <= f_val <= 115:
                vitals['temperature_c'] = round((f_val - 32) * 5.0 / 9.0, 1)
                vitals['temperature_f'] = f_val

    # Also look for "febrile" or "afebrile"
    if re.search(r'\bafebrile\b', note, re.IGNORECASE):
        vitals['afebrile'] = True
    if re.search(r'\bfebrile\b', note, re.IGNORECASE):
        vitals['febrile'] = True

    # Heart rate
    hr_patterns = [
        r'(?:heart\s*rate|HR|pulse)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{2,3})\s*(?:/\s*min|bpm|beats)',
        r'(?:heart\s*rate|HR|pulse)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{2,3})\b',
        r'(\d{2,3})\s*(?:bpm|beats\s*per\s*min)',
    ]
    for pat in hr_patterns:
        m = re.search(pat, note, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if 30 <= val <= 250:
                vitals['heart_rate'] = val
                break

    # Respiratory rate
    rr_patterns = [
        r'(?:respiratory\s*rate|RR|resp(?:iration)?s?\s*(?:rate)?)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,2})\s*(?:/\s*min|breaths)',
        r'(?:respiratory\s*rate|RR)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,2})\b',
        r'(\d{1,2})\s*(?:breaths?\s*(?:per\s*min|/\s*min))',
    ]
    for pat in rr_patterns:
        m = re.search(pat, note, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if 5 <= val <= 60:
                vitals['respiratory_rate'] = val
                break

    # Blood pressure
    bp_patterns = [
        r'(?:blood\s*pressure|BP)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{2,3})\s*/\s*(\d{2,3})',
        r'(\d{2,3})\s*/\s*(\d{2,3})\s*(?:mm\s*Hg|mmHg)',
    ]
    for pat in bp_patterns:
        m = re.search(pat, note, re.IGNORECASE)
        if m:
            vitals['bp_systolic'] = int(m.group(1))
            vitals['bp_diastolic'] = int(m.group(2))
            break

    # MAP
    m = re.search(r'(?:MAP|mean\s*arterial\s*pressure)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{2,3})', note, re.IGNORECASE)
    if m:
        vitals['map'] = int(m.group(1))
    elif 'bp_systolic' in vitals and 'bp_diastolic' in vitals:
        vitals['map'] = round(vitals['bp_diastolic'] + (vitals['bp_systolic'] - vitals['bp_diastolic']) / 3.0)

    return vitals


def _extract_labs(note):
    labs = {}

    # WBC
    wbc_patterns = [
        r'(?:WBC|white\s*blood\s*cell(?:\s*count)?|leukocyte(?:\s*count)?)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,3}[,.]?\d{0,3})\s*(?:/\s*(?:mm[³3]|[µu]l|L)|×?\s*10[³3⁹9]|k)',
        r'(?:WBC|white\s*blood\s*cell(?:\s*count)?)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,3}[,.]?\d{0,3})',
    ]
    for pat in wbc_patterns:
        m = re.search(pat, note, re.IGNORECASE)
        if m:
            val_str = m.group(1).replace(',', '')
            try:
                val = float(val_str)
                # Normalize to per µL
                if val < 500:  # likely in thousands
                    val = val * 1000
                labs['wbc'] = val
            except ValueError:
                pass
            break

    # Hemoglobin
    hgb_patterns = [
        r'(?:Hgb|Hb|hemoglobin|haemoglobin)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,2}(?:\.\d+)?)\s*(?:g/dL|g/dl|gm/dl)',
        r'(?:Hgb|Hb|hemoglobin)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,2}(?:\.\d+)?)',
    ]
    for pat in hgb_patterns:
        m = re.search(pat, note, re.IGNORECASE)
        if m:
            labs['hemoglobin'] = float(m.group(1))
            break

    # Hematocrit
    hct_patterns = [
        r'(?:Hct|hematocrit)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,2}(?:\.\d+)?)\s*%?',
    ]
    for pat in hct_patterns:
        m = re.search(pat, note, re.IGNORECASE)
        if m:
            labs['hematocrit'] = float(m.group(1))
            break

    # Platelets
    plt_patterns = [
        r'(?:platelet(?:s|\s*count)?|PLT)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,3}[,.]?\d{0,3})\s*(?:/\s*(?:mm[³3]|[µu]l|L)|×?\s*10[³3⁹9]|k)',
        r'(?:platelet(?:s|\s*count)?|PLT)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,3}[,.]?\d{0,3})',
    ]
    for pat in plt_patterns:
        m = re.search(pat, note, re.IGNORECASE)
        if m:
            val_str = m.group(1).replace(',', '')
            try:
                val = float(val_str)
                if val < 1000:
                    val = val * 1000
                labs['platelets'] = val
            except ValueError:
                pass
            break

    # Sodium
    na_patterns = [
        r'(?:Na|sodium)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{2,3}(?:\.\d+)?)\s*(?:mmol/L|mEq/L|meq/l)',
        r'(?:Na|sodium)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{2,3}(?:\.\d+)?)',
    ]
    for pat in na_patterns:
        m = re.search(pat, note, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 100 <= val <= 180:
                labs['sodium'] = val
                break

    # Potassium
    k_patterns = [
        r'(?:K\+?|potassium)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d(?:\.\d+)?)\s*(?:mmol/L|mEq/L|meq/l)',
        r'(?:potassium|K\+?)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d(?:\.\d+)?)',
    ]
    for pat in k_patterns:
        m = re.search(pat, note, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 2.0 <= val <= 8.0:
                labs['potassium'] = val
                break

    # Creatinine
    cr_patterns = [
        r'(?:creatinine|Cr)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,2}(?:\.\d+)?)\s*(?:mg/dL|mg/dl)',
        r'(?:creatinine|Cr)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,2}(?:\.\d+)?)',
    ]
    for pat in cr_patterns:
        m = re.search(pat, note, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 0.1 <= val <= 20:
                labs['creatinine'] = val
                break

    # BUN
    bun_patterns = [
        r'(?:BUN|blood\s*urea\s*nitrogen)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,3}(?:\.\d+)?)\s*(?:mg/dL|mg/dl)',
        r'(?:BUN)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,3}(?:\.\d+)?)',
    ]
    for pat in bun_patterns:
        m = re.search(pat, note, re.IGNORECASE)
        if m:
            labs['bun'] = float(m.group(1))
            break

    # pH
    ph_patterns = [
        r'pH\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d\.\d{1,2})',
        r'(?:arterial\s*)?pH\s*(\d\.\d{1,2})',
    ]
    for pat in ph_patterns:
        m = re.search(pat, note, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 6.5 <= val <= 8.0:
                labs['pH'] = val
                break

    # PaCO2
    paco2_patterns = [
        r'(?:PaCO2|pCO2|PCO2)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,3}(?:\.\d+)?)\s*(?:mm\s*Hg|mmHg)',
        r'(?:PaCO2|pCO2|PCO2)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,3}(?:\.\d+)?)',
    ]
    for pat in paco2_patterns:
        m = re.search(pat, note, re.IGNORECASE)
        if m:
            labs['paco2'] = float(m.group(1))
            break

    # PaO2
    pao2_patterns = [
        r'(?:PaO2|pO2|PO2)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,3}(?:\.\d+)?)\s*(?:mm\s*Hg|mmHg)',
        r'(?:PaO2|pO2|PO2)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,3}(?:\.\d+)?)',
    ]
    for pat in pao2_patterns:
        m = re.search(pat, note, re.IGNORECASE)
        if m:
            labs['pao2'] = float(m.group(1))
            break

    # FiO2
    fio2_patterns = [
        r'(?:FiO2|FIO2|fraction\s*of\s*inspired\s*oxygen)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,3}(?:\.\d+)?)\s*%',
        r'(?:FiO2|FIO2)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,3}(?:\.\d+)?)',
        r'(\d{1,3})\s*%\s*(?:FiO2|oxygen)',
    ]
    for pat in fio2_patterns:
        m = re.search(pat, note, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if val <= 1.0:
                val = val * 100
            labs['fio2'] = val
            break

    # HCO3 / Bicarbonate
    hco3_patterns = [
        r'(?:HCO3|bicarbonate)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,2}(?:\.\d+)?)\s*(?:mmol/L|mEq/L|meq/l)',
        r'(?:HCO3|bicarbonate)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,2}(?:\.\d+)?)',
    ]
    for pat in hco3_patterns:
        m = re.search(pat, note, re.IGNORECASE)
        if m:
            labs['hco3'] = float(m.group(1))
            break

    # Glucose
    gluc_patterns = [
        r'(?:glucose|blood\s*sugar|BS)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{2,3}(?:\.\d+)?)\s*(?:mg/dL|mg/dl)',
        r'(?:glucose)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{2,3}(?:\.\d+)?)',
    ]
    for pat in gluc_patterns:
        m = re.search(pat, note, re.IGNORECASE)
        if m:
            labs['glucose'] = float(m.group(1))
            break

    return labs


def _extract_gcs(note):
    """Extract Glasgow Coma Scale score."""
    # Total GCS
    gcs_patterns = [
        r'(?:GCS|Glasgow\s*(?:Coma\s*)?(?:Scale)?(?:\s*Score)?)\s*(?:of\s*|:\s*|=\s*|was\s*)?(\d{1,2})',
    ]
    for pat in gcs_patterns:
        m = re.search(pat, note, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if 3 <= val <= 15:
                return val
    
    # Check for alert/oriented -> GCS 15
    if re.search(r'\balert\s*(?:and\s*)?orient(?:ed|ation)', note, re.IGNORECASE):
        return 15
    
    return None


def _check_chronic_conditions(note):
    """Check for chronic organ insufficiency and other chronic conditions."""
    conditions = {}
    
    # Chronic organ insufficiency
    chronic_markers = [
        (r'(?:chronic\s*(?:liver|hepatic)\s*(?:disease|failure|insufficiency)|cirrhosis|portal\s*hypertension)', 'chronic_liver_disease'),
        (r'(?:chronic\s*(?:renal|kidney)\s*(?:disease|failure|insufficiency)|ESRD|end\s*stage\s*renal|dialysis|hemodialysis)', 'chronic_renal_disease'),
        (r'(?:chronic\s*heart\s*failure|CHF|NYHA\s*(?:class\s*)?(?:III|IV))', 'chronic_heart_failure'),
        (r'(?:COPD|chronic\s*obstructive|emphysema|chronic\s*bronchitis)', 'copd'),
        (r'(?:immunocompromised|immunosuppressed|HIV|AIDS|lymphoma|leukemia|metastat)', 'immunocompromised'),
    ]
    for pat, name in chronic_markers:
        if re.search(pat, note, re.IGNORECASE):
            conditions[name] = True
        else:
            conditions[name] = False
    
    # Steroid use
    conditions['steroid_use'] = bool(re.search(r'(?:steroid|prednisone|dexamethasone|methylprednisolone|corticosteroid)', note, re.IGNORECASE))
    
    # Smoking
    conditions['smoking'] = bool(re.search(r'(?:smok(?:er|ing|es)|tobacco\s*use|pack\s*year)', note, re.IGNORECASE))
    if re.search(r'(?:non\s*-?\s*smok|never\s*smok|no\s*(?:history\s*of\s*)?(?:tobacco|smoking))', note, re.IGNORECASE):
        conditions['smoking'] = False
    
    # Chronic hypertension
    conditions['chronic_hypertension'] = bool(re.search(r'(?:hypertension|HTN|high\s*blood\s*pressure)', note, re.IGNORECASE))
    
    # Diabetes
    conditions['diabetes'] = bool(re.search(r'(?:diabet(?:es|ic)|DM|insulin\s*dependent|IDDM|NIDDM)', note, re.IGNORECASE))
    
    return conditions


def _analyze_apache_ii(note, demographics):
    vitals = _extract_vitals(note)
    labs = _extract_labs(note)
    gcs = _extract_gcs(note)
    chronic = _check_chronic_conditions(note)
    
    conditions_present = []
    conditions_absent = []
    reasoning_parts = []
    
    age = demographics.get('age', 'unknown')
    sex = demographics.get('sex', 'unknown')
    reasoning_parts.append(f"Patient is a {age}-year-old {'woman' if sex == 'female' else 'man' if sex == 'male' else 'patient'} (demographics: age {age}, sex {sex}).")
    reasoning_parts.append("For APACHE II score, we need to evaluate multiple parameters.")
    
    explicit_parts = []
    
    # Temperature
    temp = vitals.get('temperature_c')
    if temp is not None:
        if temp >= 38.5 or temp <= 36.0:
            conditions_present.append('fever' if temp >= 38.5 else 'hypothermia')
            explicit_parts.append(f"{'fever' if temp >= 38.5 else 'hypothermia'} (temperature {temp}°C)")
        else:
            # Normal-ish temperature
            pass
    elif vitals.get('febrile'):
        conditions_present.append('fever')
        explicit_parts.append("fever (febrile)")
    
    # Heart rate
    hr = vitals.get('heart_rate')
    if hr is not None:
        if hr > 100:
            conditions_present.append('tachycardia')
            explicit_parts.append(f"tachycardia (HR {hr})")
        elif hr < 60:
            conditions_present.append('bradycardia')
            explicit_parts.append(f"bradycardia (HR {hr})")
    
    # Respiratory rate
    rr = vitals.get('respiratory_rate')
    if rr is not None:
        if rr > 24:
            conditions_present.append('tachypnea')
            explicit_parts.append(f"tachypnea (RR {rr})")
    
    # Blood pressure
    sbp = vitals.get('bp_systolic')
    dbp = vitals.get('bp_diastolic')
    map_val = vitals.get('map')
    if sbp is not None:
        if sbp < 90:
            conditions_present.append('hypotension')
            explicit_parts.append(f"hypotension (BP {sbp}/{dbp})")
        else:
            conditions_absent.append('hypotension')
    
    # WBC
    wbc = labs.get('wbc')
    if wbc is not None:
        if wbc > 12000:
            conditions_present.append('leukocytosis')
            explicit_parts.append(f"leukocytosis (WBC {wbc:,.0f}/mm³)")
        elif wbc < 4000:
            conditions_present.append('leukopenia')
            explicit_parts.append(f"leukopenia (WBC {wbc:,.0f}/mm³)")
    
    # PaO2 / Hypoxemia
    pao2 = labs.get('pao2')
    fio2 = labs.get('fio2')
    if pao2 is not None:
        if pao2 < 80:
            conditions_present.append('hypoxemia')
            fio2_str = f" on {fio2:.0f}% FiO2" if fio2 else ""
            explicit_parts.append(f"hypoxemia (PaO2 {pao2:.0f} mm Hg{fio2_str})")
    
    # pH / Acid-base
    ph = labs.get('pH')
    paco2 = labs.get('paco2')
    if ph is not None and paco2 is not None:
        if ph > 7.45 and paco2 < 35:
            conditions_present.append('respiratory_alkalosis')
            explicit_parts.append(f"respiratory alkalosis (pH {ph}, PaCO2 {paco2} mm Hg)")
        elif ph < 7.35 and paco2 > 45:
            conditions_present.append('respiratory_acidosis')
            explicit_parts.append(f"respiratory acidosis (pH {ph}, PaCO2 {paco2} mm Hg)")
        elif ph < 7.35:
            conditions_present.append('acidosis')
            explicit_parts.append(f"acidosis (pH {ph})")
        elif ph > 7.45:
            conditions_present.append('alkalosis')
    
    if ph is not None:
        if ph >= 7.35 and ph <= 7.45:
            conditions_absent.append('acidosis')
    
    if paco2 is not None:
        if paco2 >= 35 and paco2 <= 45:
            conditions_absent.append('hypercapnia')
        elif paco2 < 35:
            conditions_absent.append('hypercapnia')
    
    # Sodium
    na = labs.get('sodium')
    if na is not None:
        if na < 135:
            conditions_present.append('hyponatremia')
            explicit_parts.append(f"hyponatremia (Na {na:.0f} mmol/L)")
        elif na > 145:
            conditions_present.append('hypernatremia')
            explicit_parts.append(f"hypernatremia (Na {na:.0f} mmol/L)")
    
    # Creatinine / Renal
    cr = labs.get('creatinine')
    if cr is not None:
        if cr > 2.0:
            conditions_present.append('acute_renal_failure')
        else:
            conditions_absent.append('acute_renal_failure')
    
    # Hemoglobin / Anemia
    hgb = labs.get('hemoglobin')
    if hgb is not None:
        if hgb < 10.0:
            conditions_present.append('anemia')
        else:
            conditions_absent.append('anemia')
    
    # Platelets
    plt = labs.get('platelets')
    if plt is not None:
        if plt < 150000:
            conditions_present.append('thrombocytopenia')
        else:
            conditions_absent.append('thrombocytopenia')
    
    # Implied conditions
    # Pneumonia
    pneumonia_indicators = 0
    if re.search(r'(?:pneumonia|infiltrat|consolidat|opacit)', note, re.IGNORECASE):
        pneumonia_indicators += 1
    if 'hypoxemia' in conditions_present:
        pneumonia_indicators += 1
    if 'fever' in conditions_present:
        pneumonia_indicators += 1
    if re.search(r'(?:cough|sputum|dyspnea|gasping|breath)', note, re.IGNORECASE):
        pneumonia_indicators += 1
    if pneumonia_indicators >= 2:
        conditions_present.append('pneumonia')
    
    # Possible infection
    infection_indicators = 0
    if 'fever' in conditions_present:
        infection_indicators += 1
    if 'leukocytosis' in conditions_present:
        infection_indicators += 1
    if re.search(r'(?:infect|sepsis|septic|bacteremia|culture\s*positive)', note, re.IGNORECASE):
        infection_indicators += 1
    if re.search(r'(?:sick\s*contact|exposure|attendees\s*reported)', note, re.IGNORECASE):
        infection_indicators += 1
    if infection_indicators >= 2:
        conditions_present.append('possible_infection')
    
    # Chronic conditions absent checks
    has_chronic_insufficiency = any(chronic.get(k) for k in ['chronic_liver_disease', 'chronic_renal_disease', 'chronic_heart_failure', 'copd', 'immunocompromised'])
    if not has_chronic_insufficiency:
        conditions_absent.append('chronic_organ_insufficiency')
    else:
        conditions_present.append('chronic_organ_insufficiency')
    
    if not chronic.get('steroid_use'):
        conditions_absent.append('steroid_use')
    else:
        conditions_present.append('steroid_use')
    
    if not chronic.get('chronic_hypertension'):
        conditions_absent.append('chronic_hypertension')
    else:
        conditions_present.append('chronic_hypertension')
    
    if not chronic.get('smoking'):
        conditions_absent.append('smoking')
    else:
        conditions_present.append('smoking')
    
    # Heart failure check
    if re.search(r'(?:heart\s*failure|CHF|pulmonary\s*edema|cardiomegaly)', note, re.IGNORECASE) and not re.search(r'(?:no\s*(?:evidence\s*of\s*)?(?:heart\s*failure|CHF)|normal\s*(?:LV|left\s*ventricular)\s*function|good\s*LV)', note, re.IGNORECASE):
        conditions_present.append('heart_failure')
    else:
        conditions_absent.append('heart_failure')
    
    if explicit_parts:
        reasoning_parts.append("Conditions explicitly mentioned: " + ", ".join(explicit_parts) + ".")
    
    implied = [c for c in ['pneumonia', 'possible_infection'] if c in conditions_present]
    if implied:
        reasoning_parts.append("Conditions implied: " + ", ".join(implied) + ".")
    
    if conditions_absent:
        reasoning_parts.append("Conditions absent: " + ", ".join([c.replace('_', ' ') for c in conditions_absent]) + ".")
    
    reasoning_parts.append(f"Demographics: age {age} (will contribute to APACHE II age points), {sex} sex.")
    
    reasoning = " ".join(reasoning_parts)
    
    return {
        'reasoning': reasoning,
        'conditions_present': conditions_present,
        'conditions_absent': conditions_absent,
        'demographics': demographics
    }


def _analyze_sirs(note, demographics):
    vitals = _extract_vitals(note)
    labs = _extract_labs(note)
    
    conditions_present = []
    conditions_absent = []
    reasoning_parts = []
    
    age = demographics.get('age', 'unknown')
    sex = demographics.get('sex', 'unknown')
    sex_str = 'male' if sex == 'male' else 'female' if sex == 'female' else 'unknown'
    reasoning_parts.append(f"Patient is a {age}-year-old {sex_str}.")
    reasoning_parts.append("Calculating SIRS Criteria:")
    
    sirs_count = 0
    
    # Temperature: >38°C or <36°C
    temp = vitals.get('temperature_c')
    if temp is not None:
        if temp > 38.0 or temp < 36.0:
            sirs_count += 1
            if temp > 38.0:
                conditions_present.append('fever')
                reasoning_parts.append(f"Temperature {temp}°C (≥38°C, 1 point).")
            else:
                conditions_present.append('hypothermia')
                reasoning_parts.append(f"Temperature {temp}°C (<36°C, 1 point).")
            if 'temperature_abnormal' not in conditions_present:
                # Use specific naming based on context
                pass
        else:
            reasoning_parts.append(f"Temperature {temp}°C (normal range, 0 points).")
            conditions_absent.append('temperature_abnormal')
    elif vitals.get('febrile'):
        sirs_count += 1
        conditions_present.append('fever')
        reasoning_parts.append("Febrile (1 point).")
    elif vitals.get('temperature_f') is not None:
        temp_f = vitals['temperature_f']
        temp_c = vitals.get('temperature_c', (temp_f - 32) * 5.0 / 9.0)
        if temp_c > 38.0 or temp_c < 36.0:
            sirs_count += 1
            conditions_present.append('temperature_abnormal')
            reasoning_parts.append(f"Febrile ({temp_f}°F = {temp_c:.1f}°C {'>' if temp_c > 38 else '<'}38°C).")
    
    # Heart rate: >90/min
    hr = vitals.get('heart_rate')
    if hr is not None:
        if hr > 90:
            sirs_count += 1
            conditions_present.append('tachycardia')
            reasoning_parts.append(f"Heart rate {hr}/min (>90, 1 point).")
        else:
            conditions_absent.append('tachycardia')
            reasoning_parts.append(f"Heart rate {hr}/min (<90, 0 points).")
    
    # Respiratory rate: >20/min or PaCO2 <32 mmHg
    rr = vitals.get('respiratory_rate')
    paco2 = labs.get('paco2')
    rr_met = False
    if rr is not None:
        if rr > 20:
            sirs_count += 1
            conditions_present.append('tachypnea')
            reasoning_parts.append(f"Respiratory rate {rr}/min (>20, 1 point).")
            rr_met = True
        else:
            conditions_absent.append('tachypnea')
            reasoning_parts.append(f"Respiratory rate {rr}/min (≤20, 0 points).")
    
    if not rr_met and paco2 is not None and paco2 < 32:
        sirs_count += 1
        conditions_present.append('low_PaCO2')
        reasoning_parts.append(f"PaCO2 {paco2} mmHg (<32, 1 point).")
    
    # WBC: >12,000 or <4,000 or >10% bands
    wbc = labs.get('wbc')
    if wbc is not None:
        if wbc > 12000:
            sirs_count += 1
            conditions_present.append('leukocytosis')
            reasoning_parts.append(f"WBC count {wbc:,.0f}/µl (>12000, 1 point).")
        elif wbc < 4000:
            sirs_count += 1
            conditions_present.append('leukopenia')
            reasoning_parts.append(f"WBC count {wbc:,.0f}/µl (<4000, 1 point).")
        else:
            reasoning_parts.append(f"WBC count {wbc:,.0f}/µl (normal, 0 points).")
    
    # Check for PaCO2/ventilation mention
    if paco2 is None and not re.search(r'(?:PaCO2|pCO2|ventilat|mechanical)', note, re.IGNORECASE):
        if 'tachypnea' not in conditions_present and 'low_PaCO2' not in conditions_present:
            conditions_absent.append('abnormal_PaCO2_or_ventilation')
            reasoning_parts.append("The note does not explicitly mention PaCO2 or mechanical ventilation (0 points).")
    
    sirs_criteria_met = [c for c in conditions_present]
    reasoning_parts.append(f"Total SIRS score: {sirs_count} points ({' and '.join([c.replace('_', ' ') for c in sirs_criteria_met]) if sirs_criteria_met else 'none'}).")
    
    # Rebuild reasoning for certain conditions for better naming
    # Check if we should use 'temperature_abnormal' instead of 'fever' in conditions_present
    # (based on the examples, example 3 uses 'temperature_abnormal' while example 2 uses 'fever')
    temp_in_conditions = [c for c in conditions_present if c in ('fever', 'hypothermia', 'temperature_abnormal')]
    
    reasoning = " ".join(reasoning_parts)
    
    return {
        'reasoning': reasoning,
        'conditions_present': conditions_present,
        'conditions_absent': conditions_absent,
        'demographics': demographics
    }


def _analyze_generic(note, scoring_system, demographics):
    vitals = _extract_vitals(note)
    labs = _extract_labs(note)
    chronic = _check_chronic_conditions(note)
    
    conditions_present = []
    conditions_absent = []
    
    age = demographics.get('age', 'unknown')
    sex = demographics.get('sex', 'unknown')
    
    reasoning = f"Patient is a {age}-year-old {sex}. Analyzing for {scoring_system}."
    
    # Basic condition detection
    temp = vitals.get('temperature_c')
    if temp is not None:
        if temp > 38.0:
            conditions_present.append('fever')
        elif temp < 36.0:
            conditions_present.append('hypothermia')
    
    hr = vitals.get('heart_rate')
    if hr is not None:
        if hr > 100:
            conditions_present.append('tachycardia')
        elif hr < 60:
            conditions_present.append('bradycardia')
    
    rr = vitals.get('respiratory_rate')
    if rr is not None:
        if rr > 20:
            conditions_present.append('tachypnea')
    
    sbp = vitals.get('bp_systolic')
    if sbp is not None:
        if sbp < 90:
            conditions_present.append('hypotension')
    
    wbc = labs.get('wbc')
    if wbc is not None:
        if wbc > 12000:
            conditions_present.append('leukocytosis')
        elif wbc < 4000:
            conditions_present.append('leukopenia')
    
    return {
        'reasoning': reasoning,
        'conditions_present': conditions_present,
        'conditions_absent': conditions_absent,
        'demographics': demographics
    }
