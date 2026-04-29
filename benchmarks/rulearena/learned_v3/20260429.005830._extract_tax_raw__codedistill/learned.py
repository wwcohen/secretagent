"""Auto-generated code-distilled implementation for _extract_tax_raw."""

import re
import json

def _extract_tax_raw(text):
    try:
        result = {}
        
        # Basic Information
        m = re.search(r'Name:\s*(\w+)', text)
        result['name'] = m.group(1) if m else "John"
        
        m = re.search(r'Age \(on January 2, 2024\):\s*(\d+)', text)
        result['age'] = int(m.group(1)) if m else 0
        
        m = re.search(r'Age \(on January 2, 2024\) of Your Spouse:\s*(\d+)', text)
        result['spouse_age'] = int(m.group(1)) if m else 0
        
        # Filing Status
        filing_status_patterns = [
            (r'Filing Status.*?:\s*\[?\s*[xX]\s*\]?\s*Single', 'single'),
            (r'Filing Status.*?Single.*?\[?\s*[xX]\s*\]', 'single'),
            (r'\[\s*[xX]\s*\]\s*Single', 'single'),
            (r'Filing Status.*?\[?\s*[xX]\s*\]?\s*Married filing jointly', 'married filing jointly'),
            (r'\[\s*[xX]\s*\]\s*Married filing jointly', 'married filing jointly'),
            (r'Filing Status.*?\[?\s*[xX]\s*\]?\s*Married filing separately', 'married filing separately'),
            (r'\[\s*[xX]\s*\]\s*Married filing separately', 'married filing separately'),
            (r'Filing Status.*?\[?\s*[xX]\s*\]?\s*Head of household', 'head of household'),
            (r'\[\s*[xX]\s*\]\s*Head of household', 'head of household'),
            (r'Filing Status.*?\[?\s*[xX]\s*\]?\s*Qualifying surviving spouse', 'qualifying surviving spouse'),
            (r'\[\s*[xX]\s*\]\s*Qualifying surviving spouse', 'qualifying surviving spouse'),
            (r'\[\s*[xX]\s*\]\s*Qualifying widow', 'qualifying surviving spouse'),
        ]
        
        result['filing_status'] = 'single'
        # More robust: find the Filing Status section and check each option
        fs_section = re.search(r'Filing Status(.*?)(?=\n#|\nLine\s*1|\n1[a-z]?\s)', text, re.DOTALL | re.IGNORECASE)
        if fs_section:
            fs_text = fs_section.group(1)
        else:
            fs_text = text
        
        filing_options = [
            ('Single', 'single'),
            ('Married filing jointly', 'married filing jointly'),
            ('Married filing separately', 'married filing separately'),
            ('Head of household', 'head of household'),
            ('Qualifying surviving spouse', 'qualifying surviving spouse'),
            ('Qualifying widow', 'qualifying surviving spouse'),
        ]
        
        for pattern, status in filing_options:
            # Check for [x] or [X] before the status text
            p = re.search(r'\[\s*[xX]\s*\]\s*' + re.escape(pattern), fs_text, re.IGNORECASE)
            if p:
                result['filing_status'] = status
                break
        
        # Blind status
        def check_blind(text):
            blind = False
            spouse_blind = False
            # Look for blind checkboxes
            blind_section = re.search(r'(?:Standard Deduction|Age/Blindness)(.*?)(?=\n#|\nLine|\n\d+[a-z]?\s+[A-Z])', text, re.DOTALL | re.IGNORECASE)
            bt = blind_section.group(1) if blind_section else text
            
            # Pattern: "You were born before..." or "Are blind" with [x]
            # Look for patterns like [x] You were born... / [x] Are blind / [x] Spouse... blind
            blind_matches = re.findall(r'\[\s*([xX ])\s*\].*?(?:blind|Blind)', bt, re.IGNORECASE)
            
            # More specific: look for taxpayer blind and spouse blind
            if re.search(r'\[\s*[xX]\s*\].*?(?:You|Yourself).*?(?:blind|Blind)', bt, re.IGNORECASE):
                blind = True
            if re.search(r'\[\s*[xX]\s*\]\s*(?:Are\s+)?[Bb]lind', bt, re.IGNORECASE):
                # Could be taxpayer blind
                pass
            if re.search(r'\[\s*[xX]\s*\].*?[Ss]pouse.*?(?:blind|Blind)', bt, re.IGNORECASE):
                spouse_blind = True
            
            return blind, spouse_blind
        
        # More robust blind detection
        result['blind'] = False
        result['spouse_blind'] = False
        
        # Look for Age/Blindness section patterns
        # Typical patterns: checkboxes for "You: Were born before January 2, 1960" "[x] Are blind"
        # "Spouse: Were born before..." "[x] Is blind"
        
        age_blind_section = re.search(r'(?:Age/Blindness|Standard Deduction)(.*?)(?:\n#|\nIncome|\n1[a-z]?\s)', text, re.DOTALL | re.IGNORECASE)
        if age_blind_section:
            ab_text = age_blind_section.group(1)
        else:
            ab_text = text[:5000]
        
        # Look for "You:" section then "Are blind" or just "[x] Are blind" near "You"
        # Pattern: You ... [x] Are blind  or You ... [ ] Are blind
        you_section = re.search(r'You\s*:?(.*?)(?:Spouse|$)', ab_text, re.DOTALL | re.IGNORECASE)
        if you_section:
            you_text = you_section.group(1)
            if re.search(r'\[\s*[xX]\s*\].*?[Bb]lind', you_text):
                result['blind'] = True
        
        spouse_section = re.search(r'Spouse\s*:?(.*?)(?:\n#|\nIncome|\n1[a-z]?\s|$)', ab_text, re.DOTALL | re.IGNORECASE)
        if spouse_section:
            sp_text = spouse_section.group(1)
            if re.search(r'\[\s*[xX]\s*\].*?[Bb]lind', sp_text):
                result['spouse_blind'] = True
        
        # Itemized deduction check
        result['itemized'] = False
        if re.search(r'Schedule A', text) and re.search(r'Itemized Deductions', text):
            # Check if Schedule A is present with actual content
            sched_a = re.search(r'Schedule A.*?Itemized Deductions(.*?)(?:\n#\s*(?:Schedule [B-Z]|Form)|$)', text, re.DOTALL | re.IGNORECASE)
            if sched_a:
                result['itemized'] = True
        
        # Self-employed check - look for Schedule SE or Schedule C
        result['self_employed'] = False
        if re.search(r'Schedule SE', text) or re.search(r'Schedule C', text):
            se_section = re.search(r'Schedule SE|Schedule C', text)
            if se_section:
                result['self_employed'] = True
        
        # Student loans or education expenses
        result['has_student_loans_or_education_expenses'] = False
        if re.search(r'Schedule 3.*?(?:education|8863|American opportunity|lifetime learning)', text, re.DOTALL | re.IGNORECASE):
            result['has_student_loans_or_education_expenses'] = True
        if re.search(r'Form 8863', text, re.IGNORECASE):
            result['has_student_loans_or_education_expenses'] = True
        
        # Dependents
        def extract_dependents(text):
            num_qc = 0
            num_od = 0
            
            # Look for dependent section
            dep_section = re.search(r'[Dd]ependent[s]?(.*?)(?:\n#|\nIncome)', text, re.DOTALL)
            if dep_section:
                dep_text = dep_section.group(1)
                # Count qualifying children and other dependents
                qc_matches = re.findall(r'\[\s*[xX]\s*\].*?(?:child tax credit|qualifying child)', dep_text, re.IGNORECASE)
                num_qc = len(qc_matches)
                od_matches = re.findall(r'\[\s*[xX]\s*\].*?(?:other dependent|credit for other)', dep_text, re.IGNORECASE)
                num_od = len(od_matches)
            
            # Alternative: look for specific line items
            m = re.search(r'(?:Number of|#)\s*(?:qualifying\s+)?children.*?(\d+)', text, re.IGNORECASE)
            if m:
                num_qc = int(m.group(1))
            
            return num_qc, num_od
        
        # More robust dependent extraction
        # Look for dependent table entries
        dep_section_match = re.search(r'Dependents(.*?)(?=\n#\s+(?:Form|Income|Standard)|\nIncome\b)', text, re.DOTALL | re.IGNORECASE)
        
        num_qc = 0
        num_od = 0
        
        if dep_section_match:
            dep_text = dep_section_match.group(1)
            # Count entries with "child tax credit" checked
            qc_lines = re.findall(r'\[\s*[xX]\s*\](?:\s*\[\s*\]\s*|\s+)|\[\s*\]\s*\[\s*[xX]\s*\]', dep_text)
            # Look for names in dependent section as rows
            dep_entries = re.findall(r'(?:^|\n)\s*(?:\d+\.)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s', dep_text)
            
            # Count checkboxes in child tax credit column vs other dependents column
            child_credit = re.findall(r'\[\s*[xX]\s*\]\s*\[\s*\]', dep_text)
            other_credit = re.findall(r'\[\s*\]\s*\[\s*[xX]\s*\]', dep_text)
            num_qc = len(child_credit)
            num_od = len(other_credit)
        
        # Try another pattern for dependents
        if num_qc == 0 and num_od == 0:
            # Look for pattern with dependent names and checkboxes
            dep_lines = re.findall(r'[A-Z][a-z]+\s+[A-Z][a-z]+.*?\|\s*.*?\|\s*.*?\|\s*\[([xX ])\]\s*\|\s*\[([xX ])\]', text)
            for child_check, other_check in dep_lines:
                if child_check.strip().lower() == 'x':
                    num_qc += 1
                if other_check.strip().lower() == 'x':
                    num_od += 1
        
        # Try yet another pattern
        if num_qc == 0 and num_od == 0:
            # Look for tabular dependent data
            dep_rows = re.findall(r'\|\s*[A-Z][\w\s]+\|\s*[\w\s]+\|\s*[\w\-]+\|\s*\[([xX ])\]\s*\|\s*\[([xX ])\]\s*\|', text)
            for child_check, other_check in dep_rows:
                if child_check.strip().lower() == 'x':
                    num_qc += 1
                if other_check.strip().lower() == 'x':
                    num_od += 1
        
        result['num_qualifying_children'] = num_qc
        result['num_other_dependents'] = num_od
        
        # Helper function to extract dollar amounts
        def extract_amount(pattern, text, default=0.0):
            m = re.search(pattern, text)
            if m:
                val = m.group(1).replace(',', '').replace('$', '').strip()
                try:
                    return float(val)
                except ValueError:
                    return default
            return default
        
        # Extract line items from Form 1040
        # Line patterns - need to match "Line X: description ... $amount" or similar
        
        def find_line_value(line_id, text, default=0.0):
            """Find value for a specific line like '1a', '1b', etc."""
            patterns = [
                r'(?:^|\n)\s*' + re.escape(line_id) + r'[\.\s:]+[^$\d\n]*?\$?\s*([\d,]+(?:\.\d+)?)\s*$',
                r'(?:^|\n)\s*' + re.escape(line_id) + r'[\.\s:]+.*?\$\s*([\d,]+(?:\.\d+)?)',
                r'(?:^|\n)\s*' + re.escape(line_id) + r'[^:\n]*?:\s*\$?\s*([\d,]+(?:\.\d+)?)',
                r'(?:Line\s+)?' + re.escape(line_id) + r'[^:\n]*?:\s*\$?\s*([\d,]+(?:\.\d+)?)',
            ]
            for p in patterns:
                m = re.search(p, text, re.MULTILINE)
                if m:
                    val = m.group(1).replace(',', '')
                    try:
                        return float(val)
                    except ValueError:
                        pass
            return default
        
        def find_form_line(form_text, line_id, default=0.0):
            """More robust line finder within a form section."""
            # Try various patterns
            patterns = [
                # "1a. Wages... $57,031" or "1a. Wages... 57031"
                r'(?:^|\n)\s*' + re.escape(str(line_id)) + r'[.\s)]*[^$\n]*?[\$]\s*([\d,]+(?:\.\d{1,2})?)',
                # "1a ... : $57,031"
                r'(?:^|\n)\s*' + re.escape(str(line_id)) + r'[^:\n]*?:\s*\$?\s*([\d,]+(?:\.\d{1,2})?)',
                # Line at end after dots or spaces
                r'(?:^|\n)\s*' + re.escape(str(line_id)) + r'[.\s)]+\D+?(\d[\d,]*(?:\.\d{1,2})?)\s*$',
            ]
            for p in patterns:
                m = re.search(p, form_text, re.MULTILINE)
                if m:
                    val = m.group(1).replace(',', '')
                    try:
                        return float(val)
                    except ValueError:
                        pass
            return default
        
        # Now let's extract all financial fields
        # We need to find specific sections and lines
        
        # Find Form 1040 section
        form1040_match = re.search(r'# Form 1040.*?(?=\n# (?:Schedule|Form (?!1040))|$)', text, re.DOTALL)
        f1040 = form1040_match.group(0) if form1040_match else text
        
        # Find Schedule 1 section
        sch1_match = re.search(r'# Schedule 1.*?(?=\n# (?:Schedule [^1]|Form)|$)', text, re.DOTALL)
        sch1 = sch1_match.group(0) if sch1_match else ""
        
        # Find Schedule 2 section
        sch2_match = re.search(r'# Schedule 2.*?(?=\n# (?:Schedule [^2]|Form)|$)', text, re.DOTALL)
        sch2 = sch2_match.group(0) if sch2_match else ""
        
        # Find Schedule 3 section
        sch3_match = re.search(r'# Schedule 3.*?(?=\n# (?:Schedule [^3]|Form)|$)', text, re.DOTALL)
        sch3 = sch3_match.group(0) if sch3_match else ""
        
        # Find Schedule A section
        schA_match = re.search(r'# Schedule A.*?(?=\n# (?:Schedule [^A]|Form)|$)', text, re.DOTALL)
        schA = schA_match.group(0) if schA_match else ""
        
        # Find Schedule C section
        schC_match = re.search(r'# Schedule C.*?(?=\n# (?:Schedule [^C]|Form)|$)', text, re.DOTALL)
        schC = schC_match.group(0) if schC_match else ""
        
        # Find Schedule SE section
        schSE_match = re.search(r'# Schedule SE.*?(?=\n# (?:Schedule [^S]|Form)|$)', text, re.DOTALL)
        schSE = schSE_match.group(0) if schSE_match else ""
        
        # General robust line extraction
        def get_val(section, line_label, default=0.0):
            """Extract numeric value from a line in a section.
            line_label could be like '1a', '2b', '10', etc.
            """
            if not section:
                return default
            
            # Escape the line label for regex
            escaped = re.escape(str(line_label))
            
            patterns = [
                # Pattern: "1a. Description ... $57,031"
                r'(?:^|\n)\s*' + escaped + r'[.\s)]+[^\n$]*?\$\s*([\d,]+(?:\.\d{1,2})?)',
                # Pattern: "1a. Description: $57,031" or "1a: $57,031"
                r'(?:^|\n)\s*' + escaped + r'[^:\n]*?:\s*\$?\s*([\d,]+(?:\.\d{1,2})?)',
                # Pattern: "1a. Description ... 57031" (number at end of line)
                r'(?:^|\n)\s*' + escaped + r'[.\s)]+[^\n]*?(?:\s|\.{2,})\s*([\d,]+(?:\.\d{1,2})?)\s*$',
                # Pattern with just the line and amount
                r'(?:^|\n)\s*' + escaped + r'\s*[.:)]\s*.*?([\d,]+(?:\.\d{1,2})?)\s*$',
            ]
            
            for p in patterns:
                m = re.search(p, section, re.MULTILINE)
                if m:
                    val_str = m.group(1).replace(',', '')
                    try:
                        return float(val_str)
                    except ValueError:
                        pass
            return default
        
        # Extract income fields from Form 1040
        result['wage_tip_compensation'] = get_val(f1040, '1a')
        result['household_employee_wage'] = get_val(f1040, '1b') if get_val(f1040, '1b') > 0 else get_val(sch2, '7') if sch2 else 0.0
        result['unreported_tip'] = get_val(f1040, '1c') if get_val(f1040, '1c') > 0 else get_val(sch2, '5')
        result['nontaxable_combat_pay'] = get_val(f1040, '1d')
        result['tax_exempt_interest'] = get_val(f1040, '2a')
        result['taxable_interest'] = get_val(f1040, '2b')
        result['qualified_dividends'] = get_val(f1040, '3a')
        result['ordinary_dividends'] = get_val(f1040, '3b')
        result['ira_distributions'] = get_val(f1040, '4a')
        result['taxable_ira_distributions'] = get_val(f1040, '4b')
        result['all_pensions'] = get_val(f1040, '5a')
        result['taxable_pensions'] = get_val(f1040, '5b')
        result['social_security_benefits'] = get_val(f1040, '6a')
        result['taxable_social_security_benefits'] = get_val(f1040, '6b')
        
        # Qualified business income (line 13 of 1040)
        result['qualified_business_income'] = get_val(f1040, '13')
        
        # Federal income tax withheld (line 25d of 1040)
        result['federal_income_tax_withheld'] = get_val(f1040, '25d')
        if result['federal_income_tax_withheld'] == 0.0:
            result['federal_income_tax_withheld'] = get_val(f1040, '25')
        
        # Earned income credit (line 27 of 1040)
        result['earned_income_credit'] = get_val(f1040, '27')
        
        # Schedule 1 items
        result['taxable_state_refunds'] = get_val(sch1, '1')  # Could be line 1 of schedule 1
        result['alimony_income'] = get_val(sch1, '2a')
        result['sale_of_business'] = get_val(sch1, '4')
        result['rental_real_estate_sch1'] = get_val(sch1, '5')
        result['farm_income'] = get_val(sch1, '6')
        result['unemployment_compensation'] = get_val(sch1, '7')
        result['other_income'] = get_val(sch1, '8')  # Could be 8a or 8z
        
        # Adjustments from Schedule 1
        result['educator_expenses'] = get_val(sch1, '11')
        result['hsa_deduction'] = get_val(sch1, '13')
        result['ira_deduction'] = get_val(sch1, '20')
        result['student_loan_interest_deduction'] = get_val(sch1, '21')
        result['other_adjustments'] = get_val(sch1, '24')  # or 26
        
        # Schedule 2 items
        result['amt_f6251'] = get_val(sch2, '1')
        if result['amt_f6251'] == 0.0:
            result['amt_f6251'] = get_val(sch2, '2')
        result['credit_repayment'] = get_val(sch2, '19') if get_val(sch2, '19') > 0 else get_val(sch2, '18')
        result['other_additional_taxes'] = get_val(sch2, '17') if get_val(sch2, '17') > 0 else get_val(sch2, '21')
        
        # Schedule 3 items
        result['foreign_tax_credit'] = get_val(sch3, '1')
        result['dependent_care'] = get_val(sch3, '2')
        result['retirement_savings'] = get_val(sch3, '4')
        result['elderly_disabled_credits'] = get_val(sch3, '6d') if get_val(sch3, '6d') > 0 else get_val(sch3, '6')
        result['plug_in_motor_vehicle'] = get_val(sch3, '6f') if get_val(sch3, '6f') > 0 else 0.0
        result['alt_motor_vehicle'] = get_val(sch3, '6g') if get_val(sch3, '6g') > 0 else 0.0
        
        # Schedule A (Itemized Deductions)
        result['medical_dental_expenses'] = get_val(schA, '1')
        result['state_local_income_or_sales_tax'] = get_val(schA, '5a')
        result['state_local_real_estate_tax'] = get_val(schA, '5b')
        result['state_local_personal_property_tax'] = get_val(schA, '5c')
        result['other_taxes_paid'] = get_val(schA, '6')
        result['home_mortgage_interest_and_points'] = get_val(schA, '8a')
        result['home_mortgage_interest_unreported'] = get_val(schA, '8b')
        result['home_mortgage_points_unreported'] = get_val(schA, '8c')
        result['investment_interest'] = get_val(schA, '9')
        result['charity_cash'] = get_val(schA, '12')
        result['charity_other_than_cash'] = get_val(schA, '13')  # or 12
        result['charity_carryover'] = get_val(schA, '14')
        result['casualty_loss'] = get_val(schA, '15')
        result['other_itemized_deductions'] = get_val(schA, '16')
        
        # For fields that might need special handling
        # household_employee_wage is actually Schedule H / Sch2 line 9 or similar
        # Let's re-check some fields
        
        # Now let me re-approach this more carefully by looking at the actual text structure
        # The text has sections like "# Form 1040", "# Schedule 1", etc.
        # Within each section, lines are formatted as "line_num. description ... $amount" or similar
        
        # Let me build a more general parser
        
        def parse_all_lines(section_text):
            """Parse all line:value pairs from a section."""
            results = {}
            if not section_text:
                return results
            
            # Find all lines with amounts
            # Pattern: line_id followed by text and then a dollar amount
            for m in re.finditer(r'(?:^|\n)\s*(\d+[a-z]?)[.\s:)]+(.+)', section_text):
                line_id = m.group(1)
                rest = m.group(2)
                # Find the last number in the line (likely the amount)
                nums = re.findall(r'[\$]?\s*([\d,]+(?:\.\d{1,2})?)', rest)
                if nums:
                    last_num = nums[-1].replace(',', '')
                    try:
                        results[line_id] = float(last_num)
                    except ValueError:
                        pass
            return results
        
        # Let me use a completely different approach - parse the text more carefully
        # looking at the actual structure of the input
        
        # Actually, let me re-examine the approach. The examples show very specific field mappings.
        # Let me try to extract values more carefully.
        
        # For now, let me refine by looking at what fields map to what lines
        
        # The key insight is we need to parse line items from the forms
        # Let me create a more robust extraction
        
        def extract_all_amounts(section):
            """Extract all line -> amount mappings from a section."""
            if not section:
                return {}
            amounts = {}
            lines = section.split('\n')
            for line in lines:
                # Match patterns like "1a. description ... $1,234" or "1a description ... 1234"
                m = re.match(r'\s*(\d+[a-z]{0,2})[.\s:)\]]+(.+)', line)
                if m:
                    line_id = m.group(1)
                    rest = m.group(2)
                    # Get the rightmost dollar amount
                    dollar_matches = re.findall(r'\$\s*([\d,]+(?:\.\d{1,2})?)', rest)
                    if dollar_matches:
                        val_str = dollar_matches[-1].replace(',', '')
                        try:
                            amounts[line_id] = float(val_str)
                        except ValueError:
                            pass
                    else:
                        # Try to find a number at the end
                        num_match = re.search(r'([\d,]+(?:\.\d{1,2})?)\s*$', rest)
                        if num_match:
                            val_str = num_match.group(1).replace(',', '')
                            try:
                                val = float(val_str)
                                if val > 0:
                                    amounts[line_id] = val
                            except ValueError:
                                pass
            return amounts
        
        f1040_amounts = extract_all_amounts(f1040)
        sch1_amounts = extract_all_amounts(sch1)
        sch2_amounts = extract_all_amounts(sch2)
        sch3_amounts = extract_all_amounts(sch3)
        schA_amounts = extract_all_amounts(schA)
        schC_amounts = extract_all_amounts(schC)
        schSE_amounts = extract_all_amounts(schSE)
        
        def g(amounts, key, default=0.0):
            return amounts.get(key, default)
        
        # Re-extract with parsed amounts
        result['wage_tip_compensation'] = g(f1040_amounts, '1a')
        result['household_employee_wage'] = g(sch2_amounts, '9') if g(sch2_amounts, '9') > 0 else g(f1040_amounts, '1b')
        result['unreported_tip'] = g(sch2_amounts, '5') if g(sch2_amounts, '5') > 0 else g(sch2_amounts, '6') if g(sch2_amounts, '6') > 0 else g(f1040_amounts, '1c')
        result['nontaxable_combat_pay'] = g(f1040_amounts, '1d')
        result['tax_exempt_interest'] = g(f1040_amounts, '2a')
        result['taxable_interest'] = g(f1040_amounts, '2b')
        result['qualified_dividends'] = g(f1040_amounts, '3a')
        result['ordinary_dividends'] = g(f1040_amounts, '3b')
        result['ira_distributions'] = g(f1040_amounts, '4a')
        result['taxable_ira_distributions'] = g(f1040_amounts, '4b')
        result['all_pensions'] = g(f1040_amounts, '5a')
        result['taxable_pensions'] = g(f1040_amounts, '5b')
        result['social_security_benefits'] = g(f1040_amounts, '6a')
        result['taxable_social_security_benefits'] = g(f1040_amounts, '6b')
        result['qualified_business_income'] = g(f1040_amounts, '13')
        result['federal_income_tax_withheld'] = g(f1040_amounts, '25d', g(f1040_amounts, '25'))
        result['earned_income_credit'] = g(f1040_amounts, '27', g(f1040_amounts, '27a'))
        
        # Schedule 1 - Income items (Part I)
        result['taxable_state_refunds'] = g(sch1_amounts, '1')
        result['alimony_income'] = g(sch1_amounts, '2a')
        result['sale_of_business'] = g(sch1_amounts, '4')
        result['rental_real_estate_sch1'] = g(sch1_amounts, '5')
        result['farm_income'] = g(sch1_amounts, '6')
        result['unemployment_compensation'] = g(sch1_amounts, '7')
        result['other_income'] = g(sch1_amounts, '8z', g(sch1_amounts, '8'))
        
        # Schedule 1 - Adjustments (Part II)
        result['educator_expenses'] = g(sch1_amounts, '11')
        result['hsa_deduction'] = g(sch1_amounts, '13')
        result['ira_deduction'] = g(sch1_amounts, '20')
        result['student_loan_interest_deduction'] = g(sch1_amounts, '21')
        result['other_adjustments'] = g(sch1_amounts, '24z', g(sch1_amounts, '24'))
        
        # Schedule 2 - Additional Taxes
        result['amt_f6251'] = g(sch2_amounts, '1', g(sch2_amounts, '2'))
        
        # Household employee wage: Schedule H line or Schedule 2 line 9
        if g(sch2_amounts, '9') > 0:
            result['household_employee_wage'] = g(sch2_amounts, '9')
        
        # Unreported tip: Schedule 2 line 5 or 6
        if g(sch2_amounts, '5') > 0:
            result['unreported_tip'] = g(sch2_amounts, '5')
        elif g(sch2_amounts, '6') > 0:
            result['unreported_tip'] = g(sch2_amounts, '6')
        
        result['credit_repayment'] = g(sch2_amounts, '19', g(sch2_amounts, '18'))
        result['other_additional_taxes'] = g(sch2_amounts, '17', g(sch2_amounts, '21'))
        
        # Schedule 3 - Additional Credits and Payments
        result['foreign_tax_credit'] = g(sch3_amounts, '1')
        result['dependent_care'] = g(sch3_amounts, '2')
        result['retirement_savings'] = g(sch3_amounts, '4')
        result['elderly_disabled_credits'] = g(sch3_amounts, '6d', g(sch3_amounts, '6'))
        result['plug_in_motor_vehicle'] = g(sch3_amounts, '6f')
        result['alt_motor_vehicle'] = g(sch3_amounts, '6g')
        
        # Schedule A - Itemized Deductions
        result['medical_dental_expenses'] = g(schA_amounts, '1')
        result['state_local_income_or_sales_tax'] = g(schA_amounts, '5a')
        result['state_local_real_estate_tax'] = g(schA_amounts, '5b')
        result['state_local_personal_property_tax'] = g(schA_amounts, '5c')
        result['other_taxes_paid'] = g(schA_amounts, '6')
        result['home_mortgage_interest_and_points'] = g(schA_amounts, '8a')
        result['home_mortgage_interest_unreported'] = g(schA_amounts, '8b')
        result['home_mortgage_points_unreported'] = g(schA_amounts, '8c')
        result['investment_interest'] = g(schA_amounts, '9')
        result['charity_cash'] = g(schA_amounts, '12')
        result['charity_other_than_cash'] = g(schA_amounts, '13')
        result['charity_carryover'] = g(schA_amounts, '14')
        result['casualty_loss'] = g(schA_amounts, '15')
        result['other_itemized_deductions'] = g(schA_amounts, '16')
        
        # Schedule C
        # Schedule SE
        # For self-employed: check Schedule SE and Schedule C presence
        if schSE or schC:
            result['self_employed'] = True
        
        # For education: check for Form 8863 or education credits in Schedule 3
        if re.search(r'Form 8863', text) or re.search(r'8863', text):
            result['has_student_loans_or_education_expenses'] = True
        if g(sch3_amounts, '3') > 0:
            result['has_student_loans_or_education_expenses'] = True
        
        # Schedule C fields for self-employed
        if schC:
            result['self_employed_income'] = g(schC_amounts, '7', g(schC_amounts, '1'))
            result['self_employed_expenses'] = g(schC_amounts, '28', g(schC_amounts, '27'))
            result['self_employed_net'] = g(schC_amounts, '31')
        
        # Schedule SE fields
        if schSE:
            result['se_tax'] = g(schSE_amounts, '12', g(schSE_amounts, '4'))
            result['se_deduction'] = g(schSE_amounts, '13', g(schSE_amounts, '6'))
        
        # Convert to JSON output
        output = json.dumps({"result": result}, indent=2)
        return output
        
    except Exception:
        return None
