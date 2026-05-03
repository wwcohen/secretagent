"""Auto-generated workflow-distilled implementation for answer_date_question.

Calls existing tools from ptools.
"""

from ptools import *

import re
from datetime import datetime, timedelta
from typing import List, Tuple, Optional


def _parse_date_mmddyyyy(s: str) -> Optional[datetime]:
    """Try to parse MM/DD/YYYY from a string."""
    m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', s)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        except ValueError:
            return None
    return None


def _format_date(d: datetime) -> str:
    return f"{d.month:02d}/{d.day:02d}/{d.year:04d}"


def _extract_options_pure(input_str: str) -> List[Tuple[str, str]]:
    """Extract options using regex."""
    options = []
    for m in re.finditer(r'\(([A-F])\)\s*(\d{1,2}/\d{1,2}/\d{4})', input_str):
        options.append((m.group(1), m.group(2)))
    return options


def _subtract_months(d: datetime, months: int) -> datetime:
    """Subtract months from a date."""
    month = d.month - months
    year = d.year
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    # Handle day overflow
    import calendar
    max_day = calendar.monthrange(year, month)[1]
    day = min(d.day, max_day)
    return datetime(year, month, day)


def _add_months(d: datetime, months: int) -> datetime:
    """Add months to a date."""
    return _subtract_months(d, -months)


def _compute_target_date(today: datetime, question: str) -> Optional[datetime]:
    """Given today's date and the question, compute the target date."""
    q = question.lower()
    
    # "yesterday"
    if 'yesterday' in q and 'date yesterday' in q:
        return today - timedelta(days=1)
    
    # "tomorrow"
    if 'tomorrow' in q and 'date tomorrow' in q:
        return today + timedelta(days=1)
    
    # "24 hours later"
    if '24 hours later' in q:
        return today + timedelta(days=1)
    
    # "one week from today" or "a week from today"
    m = re.search(r'(?:one|a|1)\s+week\s+from\s+today', q)
    if m:
        return today + timedelta(weeks=1)
    
    # "one week ago"
    m = re.search(r'(?:one|a|1)\s+week\s+ago', q)
    if m:
        return today - timedelta(weeks=1)
    
    # "N days ago"
    m = re.search(r'(\d+)\s+days?\s+ago', q)
    if m:
        return today - timedelta(days=int(m.group(1)))
    
    # "N days later" or "in N days"
    m = re.search(r'(\d+)\s+days?\s+later', q)
    if m:
        return today + timedelta(days=int(m.group(1)))
    m = re.search(r'in\s+(\d+)\s+days?', q)
    if m:
        return today + timedelta(days=int(m.group(1)))
    
    # "a month ago" or "one month ago"
    if re.search(r'(?:one|a|1)\s+month\s+ago', q):
        return _subtract_months(today, 1)
    
    # "one year ago" or "a year ago"
    if re.search(r'(?:one|a|1)\s+year\s+ago', q):
        return _subtract_months(today, 12)
    
    # "today" at end
    if re.search(r'date\s+today', q):
        return today
    
    # "N days from today"
    m = re.search(r'(\d+)\s+days?\s+from\s+today', q)
    if m:
        return today + timedelta(days=int(m.group(1)))
    
    return None


def _find_best_option(target: datetime, options: List[Tuple[str, str]]) -> Optional[str]:
    """Find the option that matches the target date."""
    target_str = _format_date(target)
    for letter, date_str in options:
        if date_str == target_str:
            return f'({letter})'
    # Try parsing each option date and comparing
    for letter, date_str in options:
        d = _parse_date_mmddyyyy(date_str)
        if d and d == target:
            return f'({letter})'
    return None


def _determine_today_from_text(input_str: str) -> Optional[datetime]:
    """Try to determine 'today' from the input text using Python heuristics
    combined with LLM extraction."""
    text = input_str.split('Options:')[0] if 'Options:' in input_str else input_str
    text_lower = text.lower()
    
    # Direct date mentions: "Today is MM/DD/YYYY" or "Today is Sep 9, 1909"
    # Try: "today is <date>"
    
    # Pattern: "Today is the second day of the third month of 1966"
    # We'll use LLM for complex cases, but try simple patterns first
    
    # Pattern: yesterday was MM/DD/YYYY
    m = re.search(r'yesterday\s+was\s+(\d{1,2})/(\d{1,2})/(\d{4})', text_lower)
    if m:
        yesterday = datetime(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        return yesterday + timedelta(days=1)
    
    # Pattern: "yesterday was <Month> <day>, <year>"
    m = re.search(r'yesterday\s+was\s+(\w+)\s+(\d{1,2}),?\s+(\d{4})', text, re.IGNORECASE)
    if m:
        try:
            yesterday = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%B %d %Y")
            return yesterday + timedelta(days=1)
        except ValueError:
            pass
    
    # Pattern: "yesterday, <Month> <day>, <year>"
    m = re.search(r'yesterday,?\s+(\w+)\s+(\d{1,2}),?\s+(\d{4})', text, re.IGNORECASE)
    if m:
        try:
            yesterday = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%b %d %Y")
            return yesterday + timedelta(days=1)
        except ValueError:
            try:
                yesterday = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%B %d %Y")
                return yesterday + timedelta(days=1)
            except ValueError:
                pass
    
    # Pattern: "Today is Sep 9, 1909" or "Today is January 1, 2020"
    m = re.search(r'today\s+is\s+(\w+)\s+(\d{1,2}),?\s+(\d{4})', text, re.IGNORECASE)
    if m:
        for fmt in ["%B %d %Y", "%b %d %Y"]:
            try:
                return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", fmt)
            except ValueError:
                continue
    
    # Pattern: "Today is MM/DD" or "Today is MM/DD/YYYY"
    m = re.search(r'today\s+is\s+(\d{1,2})/(\d{1,2})/(\d{4})', text_lower)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        except ValueError:
            pass
    
    m = re.search(r'today\s+is\s+(\d{1,2})/(\d{1,2})', text_lower)
    if m:
        # Need year from context
        year_m = re.search(r'year\s+(\d{4})', text_lower)
        if year_m:
            try:
                return datetime(int(year_m.group(1)), int(m.group(1)), int(m.group(2)))
            except ValueError:
                pass
    
    # Pattern: "tomorrow (Tue, 7/9/1972)" - today is the day before
    m = re.search(r'tomorrow\s*\([^)]*?(\d{1,2})/(\d{1,2})/(\d{4})\)', text)
    if m:
        try:
            tomorrow = datetime(int(m.group(3)), int(m.group(1)), int(m.group(2)))
            return tomorrow - timedelta(days=1)
        except ValueError:
            pass
    
    # "for tomorrow" with date
    m = re.search(r'for\s+tomorrow\s*\([^)]*?(\d{1,2})/(\d{1,2})/(\d{4})\)', text)
    if m:
        try:
            tomorrow = datetime(int(m.group(3)), int(m.group(1)), int(m.group(2)))
            return tomorrow - timedelta(days=1)
        except ValueError:
            pass
    
    return None


def answer_date_question(input_str: str) -> str:
    """Workflow for date understanding questions."""
    
    # Step 1: Extract options
    options = _extract_options_pure(input_str)
    if not options:
        try:
            options = extract_options(input_str)
        except Exception:
            return None
    
    if not options:
        return None
    
    # Step 2: Extract question
    q_match = re.search(r'What is the date\s+.*?\s+in\s+MM/DD/YYYY\s*\?', input_str)
    question_text = q_match.group(0) if q_match else None
    
    # Step 3: Try pure-Python approach first
    today = _determine_today_from_text(input_str)
    
    if today is None:
        # Use LLM tools to determine today's date
        try:
            facts = extract_date_facts(input_str)
            if facts:
                context = []
                inferences = []
                for fact in facts:
                    inf = make_inference(fact, context)
                    inferences.append(inf)
                    context.append(fact)
                    context.append(inf)
                
                # Try to extract today's date from inferences
                for inf in reversed(inferences):
                    # Look for "today's date is MM/DD/YYYY" pattern
                    m = re.search(r"today'?s?\s+date\s+is\s+(\d{1,2}/\d{1,2}/\d{4})", inf, re.IGNORECASE)
                    if m:
                        today = _parse_date_mmddyyyy(m.group(1))
                        if today:
                            break
                
                if today is None:
                    # Fallback: use full LLM pipeline
                    if question_text is None:
                        try:
                            question_text = extract_question(input_str)
                        except Exception:
                            return None
                    
                    try:
                        answer_text = answer_question(question_text, inferences)
                        result = match_option(answer_text, options)
                        if result:
                            letter, _ = result
                            return f'({letter})'
                    except Exception:
                        return None
                    return None
        except Exception:
            return None
    
    if today is not None and question_text is not None:
        target = _compute_target_date(today, question_text)
        if target is not None:
            result = _find_best_option(target, options)
            if result is not None:
                return result
            # If no exact match, maybe our today is wrong
            # Fall through to LLM approach
    
    # If we have today but couldn't compute target, or no match found
    # Use LLM pipeline as fallback
    try:
        facts = extract_date_facts(input_str)
        if question_text is None:
            question_text = extract_question(input_str)
        
        context = []
        inferences = []
        for fact in facts:
            inf = make_inference(fact, context)
            inferences.append(inf)
            context.append(fact)
            context.append(inf)
        
        # If we have a Python-computed today, inject it
        if today is not None:
            today_str = _format_date(today)
            inferences.append(f"Today's date is {today_str}.")
        
        answer_text = answer_question(question_text, inferences)
        
        # Try to extract a date from the answer and match
        answer_date = _parse_date_mmddyyyy(answer_text)
        if answer_date:
            result = _find_best_option(answer_date, options)
            if result:
                return result
        
        result = match_option(answer_text, options)
        if result:
            letter, _ = result
            return f'({letter})'
    except Exception:
        pass
    
    return None
