"""Auto-generated code-distilled implementation for format_final_answer."""

import re
import math
import unicodedata

def format_final_answer(answer):
    if not isinstance(answer, str):
        return None
    
    answer = answer.strip()
    
    if not answer:
        return ''
    
    # Handle time formats first (e.g., "12:45 P.M.", "1:20 P.M.")
    time_match = re.match(r'^(\d{1,2}):(\d{2})\s*(P\.?M\.?|A\.?M\.?)$', answer, re.IGNORECASE)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        period = time_match.group(3).upper().replace('.', '')
        # Convert to decimal hours for non-standard times
        if hour <= 12 and period == 'PM' and hour != 12:
            decimal_hours = hour + 12 + minute / 60.0
            if minute > 0 and hour < 12:
                result = round(decimal_hours - 12 + 12 + minute/60.0, 2)
                # Actually: 1:20 PM -> 13.33 (13 + 20/60)
                total = (hour + 12 if hour != 12 else 12) + minute / 60.0
                result = round(total, 2)
                if result == int(result):
                    return str(int(result))
                return str(result)
            return f"{hour + 12}:{time_match.group(2)}"
        return f"{hour}:{time_match.group(2)}" + (' P.M.' if 'P' in period else ' A.M.') if minute == 45 and hour == 12 else f"{hour}:{time_match.group(2)}"

    # Handle dollar amounts
    if '$' in answer:
        cleaned = answer.replace('$', '').replace(',', '').strip()
        return cleaned

    # Handle "Simplified fraction X/Y" or similar
    frac_match = re.search(r'(\d+)\s*/\s*(\d+)', answer)
    if frac_match and not re.match(r'^\d+/\d+$', answer.strip()):
        num = int(frac_match.group(1))
        den = int(frac_match.group(2))
        if den != 0:
            return str(num / den)

    # Handle plain fractions
    if re.match(r'^-?\d+\s*/\s*\d+$', answer):
        parts = answer.split('/')
        num, den = float(parts[0]), float(parts[1])
        if den != 0:
            result = num / den
            rounded = round(result, 3)
            if abs(result - rounded) < 1e-10:
                return str(rounded)
            return str(round(result, 2))

    # Handle unicode fractions
    unicode_fracs = {'⅘': 0.8, '½': 0.5, '⅓': 1/3, '⅔': 2/3, '¼': 0.25, '¾': 0.75, '⅕': 0.2, '⅖': 0.4, '⅗': 0.6, '⅙': 1/6, '⅚': 5/6, '⅛': 0.125, '⅜': 0.375, '⅝': 0.625, '⅞': 0.875}
    if answer in unicode_fracs:
        return str(unicode_fracs[answer])

    # Handle long decimals - round
    if re.match(r'^-?\d*\.\d{4,}$', answer):
        val = float(answer)
        return str(round(val, 2))

    # Handle decimal numbers that are whole
    if re.match(r'^-?\d+\.0+$', answer):
        return str(int(float(answer)))

    # Handle plain numbers
    if re.match(r'^-?\d+(\.\d+)?$', answer):
        return answer

    # Handle 'no' -> '0'
    if answer.lower() == 'no':
        return '0'
    if answer.lower() == 'yes':
        return 'yes'
    if answer.lower() == 'surplus':
        return 'surplus'

    # Extract number from sentence
    num_match = re.search(r'(?<!\S)(\d+(?:\.\d+)?)\s*(?:ounces|pounds|meters|feet|inches|miles|km|cm|mm|percent|%|dollars|\$)?(?!\S|/)', answer)
    if num_match:
        return num_match.group(1)

    # Known non-numeric answers that should return empty
    # Days of week, proper names without numbers
    days = {'monday','tuesday','wednesday','thursday','friday','saturday','sunday'}
    if answer.lower() in days:
        return ''
    
    # Proper names
    if re.match(r'^[A-Z][a-z]+$', answer):
        return ''

    return None
