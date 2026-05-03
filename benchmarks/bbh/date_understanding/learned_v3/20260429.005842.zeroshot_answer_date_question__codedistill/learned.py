"""Auto-generated code-distilled implementation for zeroshot_answer_date_question."""

import re
from datetime import datetime, timedelta
import calendar


def zeroshot_answer_date_question(question: str):
    """
    Answer date-related questions in a zero-shot manner.
    Returns a date string (MM/DD/YYYY) or None if the question cannot be handled confidently.
    """
    if not question or not isinstance(question, str):
        return None

    question = question.strip()
    
    # Common month mappings
    month_names = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
        'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9,
        'oct': 10, 'nov': 11, 'dec': 12
    }

    def parse_date(text):
        """Try to parse a date from text in various formats."""
        text = text.strip().rstrip('.')
        
        # Try MM/DD/YYYY
        m = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', text)
        if m:
            try:
                return datetime(int(m.group(3)), int(m.group(1)), int(m.group(2)))
            except ValueError:
                pass

        # Try "Month DD, YYYY"
        m = re.match(r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})', text)
        if m:
            month_str = m.group(1).lower()
            if month_str in month_names:
                try:
                    return datetime(int(m.group(3)), month_names[month_str], int(m.group(2)))
                except ValueError:
                    pass

        # Try "DD Month YYYY"
        m = re.match(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', text)
        if m:
            month_str = m.group(2).lower()
            if month_str in month_names:
                try:
                    return datetime(int(m.group(3)), month_names[month_str], int(m.group(1)))
                except ValueError:
                    pass

        return None

    def format_date(dt):
        return f"{dt.month:02d}/{dt.day:02d}/{dt.year}"

    def find_date_in_text(text):
        """Find a date mentioned in text."""
        # MM/DD/YYYY
        patterns = [
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'(\d{1,2}\s+[A-Za-z]+\s+\d{4})',
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                d = parse_date(m.group(1))
                if d:
                    return d
        return None

    lower_q = question.lower()

    # Extract the base date from the question
    base_date = find_date_in_text(question)

    if base_date is None:
        # Try to find today reference
        if 'today is' in lower_q:
            after_today = question[lower_q.index('today is') + 8:]
            base_date = find_date_in_text(after_today)

    if base_date is None:
        return None

    # Handle "X days/months/years ago/later/after/before/from today"
    delta_match = re.search(r'(\d+)\s+(day|days|month|months|year|years)\s+(ago|before|earlier|later|after|from)', lower_q)
    if delta_match:
        num = int(delta_match.group(1))
        unit = delta_match.group(2).rstrip('s')
        direction = delta_match.group(3)
        
        forward = direction in ('later', 'after', 'from')
        sign = 1 if forward else -1

        if unit == 'day':
            result = base_date + timedelta(days=sign * num)
        elif unit == 'month':
            new_month = base_date.month + sign * num
            new_year = base_date.year
            while new_month > 12:
                new_month -= 12
                new_year += 1
            while new_month < 1:
                new_month += 12
                new_year -= 1
            max_day = calendar.monthrange(new_year, new_month)[1]
            new_day = min(base_date.day, max_day)
            result = datetime(new_year, new_month, new_day)
        elif unit == 'year':
            new_year = base_date.year + sign * num
            max_day = calendar.monthrange(new_year, base_date.month)[1]
            new_day = min(base_date.day, max_day)
            result = datetime(new_year, base_date.month, new_day)
        else:
            return None
        
        return format_date(result)

    # Handle "yesterday/tomorrow/today"
    if 'yesterday' in lower_q:
        return format_date(base_date - timedelta(days=1))
    if 'tomorrow' in lower_q:
        return format_date(base_date + timedelta(days=1))
    if 'the day before yesterday' in lower_q:
        return format_date(base_date - timedelta(days=2))
    if 'the day after tomorrow' in lower_q:
        return format_date(base_date + timedelta(days=2))
    if re.search(r'what (is|was) the date', lower_q) and 'today' in lower_q:
        return format_date(base_date)

    # Default: return the found date
    return format_date(base_date)
