"""Auto-generated code-distilled implementation for perform_calculation."""

import re
import math

def perform_calculation(input_str):
    try:
        s = input_str.strip()
        
        # Handle absolute value notation |x| -> abs(x)
        abs_match = re.search(r'\|(-?\d+(?:\.\d+)?)\|', s)
        if abs_match:
            val = float(abs_match.group(1))
            result = abs(val)
            result_str = str(int(result)) if result == int(result) else str(result)
            return f'Calculation: abs({abs_match.group(1)}) = {result_str}'
        
        # Handle "Identify the largest/smallest value from..." with list of numbers
        max_identify = re.match(r'(?:Identify|Find)\s+the\s+(largest|smallest|maximum|minimum)\s+value\s+from.*?:\s*([\d,.\s]+)$', s, re.IGNORECASE)
        if max_identify:
            func = 'max' if max_identify.group(1).lower() in ('largest', 'maximum') else 'min'
            nums = [n.strip() for n in max_identify.group(2).split(',') if n.strip()]
            values = [float(n) for n in nums]
            result = max(values) if func == 'max' else min(values)
            result_str = str(int(result)) if result == int(result) else str(result)
            nums_str = ', '.join(str(int(float(n))) if float(n) == int(float(n)) else n for n in nums)
            return f'Calculation: {func}({nums_str}) = {result_str}'

        # Handle "Find the minimum/maximum value from: numbers"
        find_match = re.match(r'(?:Find|Identify)\s+the\s+(minimum|maximum|largest|smallest)\s+value\s+from.*?:\s*([\d,.\s]+)$', s, re.IGNORECASE)
        if find_match:
            func = 'max' if find_match.group(1).lower() in ('largest', 'maximum') else 'min'
            nums = [n.strip() for n in find_match.group(2).split(',') if n.strip()]
            values = [float(n) for n in nums]
            result = max(values) if func == 'max' else min(values)
            result_str = str(int(result)) if result == int(result) else str(result)
            nums_str = ', '.join(str(int(float(n))) if float(n) == int(float(n)) else n for n in nums)
            return f'Calculation: {func}({nums_str}) = {result_str}'

        # Handle "Find the maximum value from stem-and-leaf plot:..." with detailed description
        stem_max_match = re.search(r'(?:Find|Identify)\s+the\s+(maximum|minimum|largest|smallest)\s+value\s+from\s+stem', s, re.IGNORECASE)
        if stem_max_match:
            func = 'max' if stem_max_match.group(1).lower() in ('largest', 'maximum') else 'min'
            # Extract all standalone numbers that look like data values (2+ digits)
            all_nums = re.findall(r'\b(\d{2,3})\b', s)
            # Filter: remove stems (single conceptual digits) and keep reasonable values
            # Look for patterns like "so 90" or "so 80,87,87,88,89"
            so_nums = re.findall(r'so\s+([\d,\s]+?)(?:[;.]|$)', s)
            data_values = []
            for chunk in so_nums:
                for n in chunk.split(','):
                    n = n.strip()
                    if n and n.isdigit():
                        data_values.append(int(n))
            
            if not data_values:
                # Try extracting "The largest number is X"
                largest_match = re.search(r'largest number is (\d+)', s)
                if largest_match:
                    result = int(largest_match.group(1))
                    return f'Calculation: {func}({result}) = {result}'
                return None
            
            # Remove duplicates from display but keep for calculation
            result = max(data_values) if func == 'max' else min(data_values)
            # Remove consecutive duplicates for display
            seen = set()
            unique_ordered = []
            for v in data_values:
                if v not in seen:
                    seen.add(v)
                    unique_ordered.append(v)
            nums_str = ', '.join(str(v) for v in unique_ordered)
            return f'Calculation: {func}({nums_str}) = {result}'

        # Handle gcd(a, b)
        gcd_match = re.match(r'gcd\((\d+),\s*(\d+)\)', s)
        if gcd_match:
            a, b = int(gcd_match.group(1)), int(gcd_match.group(2))
            result = math.gcd(a, b)
            return f'Calculation: gcd({a}, {b}) = {result}'

        # Handle multiple calculations separated by comma: "680 ÷ 10 = 68, 2170 ÷ 10 = 217"
        if '÷' in s and ',' in s and '=' in s:
            # Check if it's a multi-calculation string
            parts = s.split(',')
            calcs = []
            for part in parts:
                part = part.strip()
                part = part.replace('÷', '/')
                calcs.append(part)
            expr_str = ', '.join(calcs).replace('/', ' ÷ ')
            return f'Calculation: {expr_str}'

        # Handle "÷" -> "/"
        s_work = s.replace('÷', '/')

        # Handle chained equality like "frequency(0) + frequency(1) = 4 + 20 = 24"
        # Look for pattern with = signs containing the final computation
        chain_match = re.search(r'([\w()]+\s*[+\-*/]\s*[\w()]+(?:\s*[+\-*/]\s*[\w()]+)*)\s*=\s*([\d.]+(?:\s*[+\-*/]\s*[\d.]+)+)\s*=\s*([\d.]+)', s_work)
        if chain_match:
            prefix = chain_match.group(1).strip()
            expr = chain_match.group(2).strip()
            given_result = chain_match.group(3).strip()
            try:
                computed = eval(expr)
                result_str = str(int(computed)) if computed == int(computed) else str(computed)
            except:
                result_str = given_result
            return f'Calculation: {prefix} = {expr} = {result_str}'

        # Handle word-problem multiplications like "6 packages * 10 apples per package"
        word_mult = re.match(r'(\d+(?:\.\d+)?)\s+\w+\s*\*\s*(\d+(?:\.\d+)?)\s+\w+.*', s_work)
        if word_mult:
            a, b = word_mult.group(1), word_mult.group(2)
            result = float(a) * float(b)
            result_str = str(int(result)) if result == int(result) else str(result)
            return f'Calculation: {a} * {b} = {result_str}'

        # Handle "$X per pound" type multiplications
        money_mult = re.match(r'(\d+(?:\.\d+)?)\s+\w*\s*\*\s*\$?(\d+(?:\.\d+)?)\s*.*', s_work)
        if money_mult:
            a, b = money_mult.group(1), money_mult.group(2)
            result = float(a) * float(b)
            result_str = str(int(result)) if result == int(result) else str(result)
            return f'Calculation: {a} * {b} = {result_str}'

        # Try to extract a mathematical expression from the string
        # First, try to find explicit "= result" at the end after an expression
        
        # Handle "Calculate the mean: (2 + 9 + ...) / 7" type
        calc_match = re.search(r'(?:Calculate|Compute|Find).*?:\s*(.+)', s_work, re.IGNORECASE)
        if calc_match:
            expr = calc_match.group(1).strip()
            # Remove trailing text
            expr = re.sub(r'\s*=\s*.*$', '', expr).strip() if '=' in expr and not re.search(r'=\s*[\d.]', expr) else expr
            try:
                result = eval(expr)
                if isinstance(result, float):
                    if result == int(result) and '/' not in expr and '.' not in expr:
                        result_str = str(int(result))
                    else:
                        # Round to avoid floating point issues
                        result_str = str(round(result, 10))
                        # Clean up trailing zeros but keep at least one decimal if float
                        if '.' in result_str:
                            result_str = result_str.rstrip('0').rstrip('.')
                            if '.' not in result_str and ('/' in expr or '.' in expr):
                                result_str = result_str + '.0'
                else:
                    result_str = str(result)
                return f'Calculation: {expr} = {result_str}'
            except:
                pass

        # Extract expression: try to find the core math expression
        # Remove common textual prefixes/suffixes
        expr = s_work
        
        # Remove leading text like "Total hours billed = " or "Sum of frequencies..."
        eq_match = re.match(r'.*?=\s*([\d.]+(?:\s*[+\-*/]\s*[\d.]+)+)\s*$', expr)
        if eq_match:
            expr = eq_match.group(1).strip()
        else:
            # Remove trailing text like "for total cost"
            # Try to find the longest valid arithmetic expression
            # Pattern: numbers with operators, possibly with parentheses
            arith_patterns = re.findall(r'(\([\d\s+\-*/.,]+\)\s*[+\-*/]\s*[\d.]+|[\d.]+(?:\s*[+\-*/]\s*[\d.]+)+)', expr)
            if arith_patterns:
                # Pick the longest one
                expr = max(arith_patterns, key=len).strip()
            else:
                # Try parenthesized expression
                paren_match = re.search(r'(\([^)]+\)\s*[/+\-*]\s*[\d.]+)', expr)
                if paren_match:
                    expr = paren_match.group(1).strip()

        # Remove trailing text after last number
        expr = re.sub(r'(\d)\s+[a-zA-Z].*$', r'\1', expr)
        # Remove leading text before first number/paren
        expr = re.sub(r'^.*?(?=[\d(])', '', expr)
        # Remove $ signs
        expr = expr.replace('$', '')
        
        # Clean the expression
        expr = expr.strip()
        
        if not expr:
            return None

        # Handle "expr = result" where result is already given
        if '=' in expr:
            parts = expr.split('=')
            # Check if last part is just a number (the result)
            last = parts[-1].strip()
            try:
                float(last)
                # The expression is everything before the last =
                expr = '='.join(parts[:-1]).strip()
            except:
                pass

        try:
            result = eval(expr)
            if isinstance(result, float):
                if result == int(result) and '/' not in expr and '.' not in expr:
                    result_str = str(int(result))
                else:
                    result_str = str(round(result, 10))
                    if '.' in result_str:
                        result_str = result_str.rstrip('0')
                        if result_str.endswith('.'):
                            if '/' in expr or '.' in expr:
                                result_str += '0'
                            else:
                                result_str = result_str.rstrip('.')
            else:
                result_str = str(result)
            return f'Calculation: {expr} = {result_str}'
        except:
            return None
    except:
        return None
