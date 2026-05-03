"""Auto-generated workflow-distilled implementation for tabmwp_solve.

Calls existing tools from ptools.
"""

from ptools import *

import re

def tabmwp_solve(question: str, table: str, table_id: str, choices: list | None) -> str:
    """
    Solves a tabular math word problem by orchestrating existing workflows.
    Uses Python-based tool execution (PoT) as the primary engine to compute exact
    answers, and robustly formats the outputs to match exact formatting expectations.
    """
    def evaluate_and_format(ans):
        if ans is None:
            return None
            
        ans_str = str(ans).strip()
        if not ans_str or ans_str.lower() in ['none', 'null', 'nan']:
            return None
            
        # Reject common error messages directly
        if "unsupported" in ans_str.lower() or "error" in ans_str.lower() or "traceback" in ans_str.lower():
            return None

        # 1. Exact string match with available choices
        if choices:
            for c in choices:
                if str(c).strip().lower() == ans_str.lower():
                    return str(c)
                    
        # 2. Try to parse directly as a number
        try:
            has_percent = False
            temp_str = ans_str
            if temp_str.endswith('%'):
                has_percent = True
                temp_str = temp_str[:-1]
                
            val_str = temp_str.replace(',', '').replace('$', '').strip()
            val = float(val_str)
            
            # Smooth out floating point arithmetic inaccuracies
            val = round(val, 10)
            
            # If choices exist, try to match numerically
            if choices:
                for c in choices:
                    c_str = str(c).strip().replace(',', '').replace('$', '').replace('%', '')
                    try:
                        c_val = round(float(c_str), 10)
                        if c_val == val:
                            return str(c)
                    except ValueError:
                        continue
                # If there are choices but no numeric match, consider this a failure so we can fallback
                return None
                
            # No choices provided, format the extracted number correctly
            if val.is_integer():
                formatted = f"{int(val):,}"
            else:
                # Retain two decimal places for money-related questions
                money_words = ['cost', 'spend', 'pay', 'price', 'taxes', 'earnings', 'budget', '$', 'how much money']
                is_money = any(word in question.lower() for word in money_words)
                if is_money:
                    formatted = f"{val:,.2f}"
                else:
                    formatted = f"{val:,}"
                    
            if has_percent:
                formatted += "%"
                
            return formatted
            
        except ValueError:
            # 3. If standard parsing fails and we have choices, attempt a fuzzy textual match
            if choices:
                cleaned_ans = re.sub(r'[^a-zA-Z0-9]', '', ans_str.lower())
                for c in choices:
                    cleaned_c = re.sub(r'[^a-zA-Z0-9]', '', str(c).lower())
                    if cleaned_c == cleaned_ans and cleaned_ans != '':
                        return str(c)
                return None
                
            # 4. Final Fallback: try to extract a single number embedded in the output string
            temp_for_re = ans_str.replace('$', '')
            matches = re.findall(r'-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?', temp_for_re)
            if len(matches) == 1:
                try:
                    val_str = matches[0].replace(',', '')
                    val = float(val_str)
                    val = round(val, 10)
                    
                    if val.is_integer():
                        formatted = f"{int(val):,}"
                    else:
                        money_words = ['cost', 'spend', 'pay', 'price', 'taxes', 'earnings', 'budget', '$', 'how much money']
                        is_money = any(word in question.lower() for word in money_words)
                        if is_money:
                            formatted = f"{val:,.2f}"
                        else:
                            formatted = f"{val:,}"
                            
                    if ans_str.endswith('%'):
                        formatted += "%"
                        
                    return formatted
                except ValueError:
                    return None
                    
            # If nothing parses sensibly, return None to trigger the zero-shot fallback
            return None

    # Prioritize pot_workflow (Program of Thoughts) since computing math with Python scripts
    # solves multi-step arithmetic drastically better than extraction workflows.
    workflows_to_try = [pot_workflow, incontext_workflow, rich_workflow]
    
    for wf in workflows_to_try:
        try:
            raw_ans = wf(question, table, table_id, choices)
            final_ans = evaluate_and_format(raw_ans)
            if final_ans is not None:
                return final_ans
        except Exception:
            continue
            
    return None
