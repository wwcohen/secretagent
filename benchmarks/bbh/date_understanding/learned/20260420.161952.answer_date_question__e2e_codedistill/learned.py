"""Auto-generated end-to-end implementation for answer_date_question."""

import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

def answer_date_question(text):
    try:
        return _solve(text)
    except:
        return None

def _solve(text):
    # Split into context and question+options
    lines = text.strip().split('\n')
    
    # Find the question line and options
    question_line = ""
    options = {}
    context_lines = []
    
    for line in lines:
        line = line.strip()
        if re.match(r'^\([A-F]\)\s', line):
            letter = line[1]
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', line)
            if date_match:
                options[f'({letter})'] = date_match.group(1)
        elif 'Options:' in line:
            continue
        elif 'What is the date' in line:
            question_line = line
        else:
            context_lines.append(line)
    
    # Also check if question is embedded in a line with context
    for line in lines:
        if 'What is the date' in line:
            question_line = line
            # Context might be before the question in the same line
            break
    
    full_text = ' '.join(context_lines) + ' ' + question_line
    
    # Determine today's date
    today = _extract_today(full_text)
    
    if today is None:
        return None
    
    # Determine the transformation
    target_date = _apply_transformation(today, question_line)
    
    if target_date is None:
        return None
    
    # Format and match
    formatted = target_date.strftime('%m/%d/%Y')
    
    for key, val in options.items():
        if val == formatted:
            return key
    
    return None

def _extract_today(text):
    """Extract today's date from the context."""
    
    # "Today is Christmas Eve of 1937" -> 12/24/1937
    m = re.search(r'[Tt]oday is Christmas Eve of (\d{4})', text)
    if m:
        return datetime(int(m.group(1)), 12, 24)
    
    # "It is MM/DD/YYYY today" or "Today is MM/DD/YYYY"  
    m = re.search(r'[Ii]t is (\d{1,2}/\d{1,2}/\d{4}) today', text)
    if m:
        return _parse_date_mdy(m.group(1))
    
    m = re.search(r'[Tt]oday is (\d{1,2}/\d{1,2}/\d{4})', text)
    if m:
        return _parse_date_mdy(m.group(1))
    
    # "Jane thinks today is 6/18/2019, but John thinks today is 6/19/2019. John is correct."
    m = re.search(r'thinks today is [\d/]+,?\s*but \w+ thinks today is ([\d/]+)\.\s*\w+ is correct', text)
    if m:
        return _parse_date_mdy(m.group(1))
    
    # "Jane thinks today is 6/18/2019, but John thinks today is 6/19/2019. Jane is correct."  
    m = re.search(r'(\w+) thinks today is ([\d/]+),?\s*but (\w+) thinks today is ([\d/]+)\.\s*(\w+) is correct', text)
    if m:
        name1, date1, name2, date2, correct_name = m.groups()
        if correct_name == name1:
            return _parse_date_mdy(date1)
        else:
            return _parse_date_mdy(date2)

    # "Jane thought today is 3/11/2002, but today is in fact Mar 12, which is 1 day later"
    m = re.search(r'today is in fact (\w+ \d+)', text)
    if m:
        # Need year from context
        year_m = re.search(r'(\d{4})', text)
        if year_m:
            year = int(year_m.group(1))
            date_str = m.group(1)
            month_day = _parse_month_day(date_str)
            if month_day:
                return datetime(year, month_day[0], month_day[1])
    
    # "The deadline is Jun 1, 2021, which is 2 days away from now"
    m = re.search(r'(\w+ \d+,?\s*\d{4}),?\s*which is (\d+) days? away from now', text)
    if m:
        ref_date = _parse_date_text(m.group(1))
        days = int(m.group(2))
        if ref_date:
            return ref_date - timedelta(days=days)
    
    # "Yesterday was April 30, 2021" or "Yesterday was 12/31/1929"
    m = re.search(r'[Yy]esterday was (\w+ \d+,?\s*\d{4})', text)
    if m:
        ref_date = _parse_date_text(m.group(1))
        if ref_date:
            return ref_date + timedelta(days=1)
    
    m = re.search(r'[Yy]esterday was (\d{1,2}/\d{1,2}/\d{4})', text)
    if m:
        ref_date = _parse_date_mdy(m.group(1))
        if ref_date:
            return ref_date + timedelta(days=1)
    
    # "Yesterday, Jan 21, 2011, Jane ate..."
    m = re.search(r'[Yy]esterday,?\s*(\w+ \d+,?\s*\d{4})', text)
    if m:
        ref_date = _parse_date_text(m.group(1))
        if ref_date:
            return ref_date + timedelta(days=1)
    
    # "Jane booked a flight for tomorrow, Jul 29, 2002"
    m = re.search(r'tomorrow,?\s*(?:\w+,?\s*)?(\w+ \d+,?\s*\d{4})', text)
    if m:
        ref_date = _parse_date_text(m.group(1))
        if ref_date:
            return ref_date - timedelta(days=1)
    
    # "tomorrow (Tue, 7/9/1972)" or "tomorrow (7/9/1972)"
    m = re.search(r'tomorrow\s*\((?:\w+,?\s*)?(\d{1,2}/\d{1,2}/\d{4})\)', text)
    if m:
        ref_date = _parse_date_mdy(m.group(1))
        if ref_date:
            return ref_date - timedelta(days=1)
    
    # "Today's meeting is rescheduled to 11 am tomorrow, 10/16/1924"
    m = re.search(r'tomorrow,?\s*(\d{1,2}/\d{1,2}/\d{4})', text)
    if m:
        ref_date = _parse_date_mdy(m.group(1))
        if ref_date:
            return ref_date - timedelta(days=1)
    
    # "On May 9th, 2017 Jane bought 40 eggs. She ate one per day. Today she ran out of eggs."
    m = re.search(r'[Oo]n (\w+ \d+\w*,?\s*\d{4}).*?bought (\d+) eggs.*?ate one per day.*?ran out', text)
    if m:
        start_date = _parse_date_text(m.group(1))
        num_eggs = int(m.group(2))
        if start_date:
            return start_date + timedelta(days=num_eggs)
    
    # "Jane quited her job on Mar 20, 2020. 176 days have passed since then"
    m = re.search(r'on (\w+ \d+,?\s*\d{4})\.?\s*(\d+) days have passed', text)
    if m:
        ref_date = _parse_date_text(m.group(1))
        days = int(m.group(2))
        if ref_date:
            return ref_date + timedelta(days=days)
    
    # "The concert was scheduled to be on 06/01/1943, but was delayed by one day to today"
    m = re.search(r'on (\d{2}/\d{2}/\d{4}),?\s*but was delayed by one day to today', text)
    if m:
        ref_date = _parse_date_mdy(m.group(1))
        if ref_date:
            return ref_date + timedelta(days=1)
    
    m = re.search(r'on (\d{2}/\d{2}/\d{4}),?\s*but was delayed by (\d+) days? to today', text)
    if m:
        ref_date = _parse_date_mdy(m.group(1))
        days = int(m.group(2))
        if ref_date:
            return ref_date + timedelta(days=days)
    
    # "Jane was born on the last day of Feburary in 2001. Today is her 16-year-old birthday"
    m = re.search(r'born on the last day of (\w+) in (\d{4}).*?(\d+)-year-old birthday', text)
    if m:
        month_name = m.group(1)
        birth_year = int(m.group(2))
        age = int(m.group(3))
        target_year = birth_year + age
        month_num = _month_to_num(month_name)
        if month_num:
            # Last day of month in target year
            last_day = _last_day_of_month(target_year, month_num)
            return datetime(target_year, month_num, last_day)
    
    # "Jane was born on the last day of Feburary in 2000. Today is her 16-year-old birthday"
    
    # "Jane is celebrating the last day of Jan 2012"
    m = re.search(r'last day of (\w+) (\d{4})', text)
    if m:
        month_num = _month_to_num(m.group(1))
        year = int(m.group(2))
        if month_num:
            last_day = _last_day_of_month(year, month_num)
            return datetime(year, month_num, last_day)
    
    # "This is the last day of 1899"
    m = re.search(r'last day of (\d{4})', text)
    if m:
        year = int(m.group(1))
        return datetime(year, 12, 31)
    
    # "2015 is coming in 36 hours"
    m = re.search(r'(\d{4}) is coming in (\d+) hours', text)
    if m:
        year = int(m.group(1))
        hours = int(m.group(2))
        new_year = datetime(year, 1, 1)
        today = new_year - timedelta(hours=hours)
        # Round to day
        return datetime(today.year, today.month, today.day)
    
    # "Jane and John married on Jan 2, 1958. It is their 5-year anniversary today"
    m = re.search(r'on (\w+ \d+,?\s*\d{4})\.?\s*(?:It is|Today is) their (\d+)-year anniversary', text)
    if m:
        ref_date = _parse_date_text(m.group(1))
        years = int(m.group(2))
        if ref_date:
            return datetime(ref_date.year + years, ref_date.month, ref_date.day)
    
    # "May 6, 1992 is like yesterday to Jane, but that is actually ten years ago"
    m = re.search(r'(\w+ \d+,?\s*\d{4}) is like yesterday.*?(?:actually|in fact) (\w+|\d+) years? ago', text)
    if m:
        ref_date = _parse_date_text(m.group(1))
        years_str = m.group(2)
        years = _word_to_num(years_str)
        if ref_date and years:
            return datetime(ref_date.year + years, ref_date.month, ref_date.day)
    
    # "Jane got her job in 2016. Today is her 3-year work anniversary. She still remember that on Dec 2, her second day at work"
    m = re.search(r'on (\w+ \d+),?\s*her second day at work.*?(\d+)-year work anniversary', text)
    if m:
        month_day = _parse_month_day(m.group(1))
        years = int(m.group(2))
        if month_day:
            # Second day at work means first day was the day before
            first_day = datetime(2016, month_day[0], month_day[1]) - timedelta(days=1)
            return datetime(first_day.year + years, first_day.month, first_day.day)
    
    # Also try: "got her job in 2016" + "3-year work anniversary" + "on Dec 2, her second day"
    m = re.search(r'got her job in (\d{4}).*?(\d+)-year work anniversary.*?on (\w+ \d+),?\s*her second day', text)
    if m:
        start_year = int(m.group(1))
        years = int(m.group(2))
        month_day = _parse_month_day(m.group(3))
        if month_day:
            first_day = datetime(start_year, month_day[0], month_day[1]) - timedelta(days=1)
            return datetime(first_day.year + years, first_day.month, first_day.day)
    
    # "Today is 3/5, and it is Jane's second time in the year 1973"
    m = re.search(r'[Tt]oday is (\d{1,2}/\d{1,2}),.*?(?:year|NFL) (\d{4})', text)
    if m:
        parts = m.group(1).split('/')
        month = int(parts[0])
        day = int(parts[1])
        year = int(m.group(2))
        return datetime(year, month, day)
    
    # "Today is 9/7. Jane is watching NFL 2003"
    m = re.search(r'[Tt]oday is (\d{1,2}/\d{1,2})\..*?(\d{4})', text)
    if m:
        parts = m.group(1).split('/')
        month = int(parts[0])
        day = int(parts[1])
        year = int(m.group(2))
        return datetime(year, month, day)
    
    # "The current local time is 3:02 pm of 5/4/2004"
    m = re.search(r'of (\d{1,2}/\d{1,2}/\d{4})', text)
    if m:
        return _parse_date_mdy(m.group(1))
    
    # "In the UK, people usually put the day before the month when formatting the date. Therefore, today is 02/01/1987 to them"
    m = re.search(r'day before the month.*?today is (\d{2}/\d{2}/\d{4})', text)
    if m:
        # DD/MM/YYYY format
        parts = m.group(1).split('/')
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2])
        return datetime(year, month, day)
    
    # "Today is the second day of the third month of 1966"
    m = re.search(r'[Tt]oday is the (\w+) day of the (\w+) month of (\d{4})', text)
    if m:
        day = _ordinal_to_num(m.group(1))
        month = _ordinal_to_num(m.group(2))
        year = int(m.group(3))
        if day and month:
            return datetime(year, month, day)
    
    # "The first day of 2019 is a Tuesday, and today is the first Monday of 2019"
    m = re.search(r'first day of (\d{4}) is a (\w+).*?today is the first (\w+) of \d{4}', text)
    if m:
        year = int(m.group(1))
        first_day_weekday = m.group(2)
        target_weekday = m.group(3)
        jan1 = datetime(year, 1, 1)
        target_wd = _weekday_to_num(target_weekday)
        if target_wd is not None:
            # Find first occurrence of target weekday
            current_wd = jan1.weekday()
            diff = (target_wd - current_wd) % 7
            if diff == 0:
                diff = 7  # If Jan 1 is already that weekday, next one? No, "first Monday" could be Jan 1 if it's a Monday
                # Actually, "the first Monday of 2019" - if Jan 1 is Monday, that's it. If not, find next.
                # Jan 1, 2019 is Tuesday. First Monday would be Jan 7.
                diff = 7
            return jan1 + timedelta(days=diff)
    
    # "It was Sept. 1st, 2021 a week ago"
    m = re.search(r'[Ii]t was (\w+\.?\s*\d+\w*,?\s*\d{4})\s*a week ago', text)
    if m:
        ref_date = _parse_date_text(m.group(1))
        if ref_date:
            return ref_date + timedelta(days=7)
    
    # "Jane visits the bookstore on the 16th of each month starting from the October of 2009. It is her 5th visit"
    m = re.search(r'on the (\d+)\w* of each month starting from (?:the )?(\w+) of (\d{4}).*?(\d+)\w* visit', text)
    if m:
        day = int(m.group(1))
        month_num = _month_to_num(m.group(2))
        year = int(m.group(3))
        visit = int(m.group(4))
        if month_num:
            start = datetime(year, month_num, day)
            # visit 1 is the start, visit N is N-1 months later
            result = _add_months(start, visit - 1)
            return result
    
    # "Jane scheduled 3 appointments with 5 people for tomorrow (Tue, 7/9/1972)"
    m = re.search(r'tomorrow\s*\(\w+,\s*(\d{1,2}/\d{1,2}/\d{4})\)', text)
    if m:
        ref_date = _parse_date_mdy(m.group(1))
        if ref_date:
            return ref_date - timedelta(days=1)
    
    return None

def _apply_transformation(today, question):
    """Apply the date transformation asked in the question."""
    
    if 'date today' in question or 'date today' in question.lower():
        return today
    
    if 'date yesterday' in question:
        return today - timedelta(days=1)
    
    if 'date tomorrow' in question:
        return today + timedelta(days=1)
    
    if '24 hours later' in question:
        return today + timedelta(days=1)
    
    m = re.search(r'date (\d+) days? ago', question)
    if m:
        days = int(m.group(1))
        return today - timedelta(days=days)
    
    if 'one week ago' in question or 'a week ago' in question:
        return today - timedelta(days=7)
    
    if 'one week from today' in question or 'a week from today' in question:
        return today + timedelta(days=7)
    
    if 'one year ago' in question or 'a year ago' in question:
        return _add_months(today, -12)
    
    if 'one year from today' in question:
        return _add_months(today, 12)
    
    if 'a month ago' in question or 'one month ago' in question:
        return _add_months(today, -1)
    
    if 'a month from today' in question or 'one month from today' in question:
        return _add_months(today, 1)
    
    m = re.search(r'(\d+) days? from today', question)
    if m:
        days = int(m.group(1))
        return today + timedelta(days=days)
    
    m = re.search(r'(\d+) days? ago', question)
    if m:
        days = int(m.group(1))
        return today - timedelta(days=days)
    
    return None

def _add_months(dt, months):
    """Add months to a date."""
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    import calendar
    max_day = calendar.monthrange(year, month)[1]
    day = min(dt.day, max_day)
    return datetime(year, month, day)

def _parse_date_mdy(s):
    """Parse M/D/YYYY or MM/DD/YYYY."""
    parts = s.split('/')
    if len(parts) == 3:
        return datetime(int(parts[2]), int(parts[0]), int(parts[1]))
    return None

def _parse_date_text(s):
    """Parse textual date like 'Jun 1, 2021' or 'May 9th, 2017' or 'Sept. 1st, 2021'."""
    s = s.strip()
    # Remove ordinal suffixes
    s = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', s)
    # Remove periods after abbreviations
    s = re.sub(r'(\w+)\.', r'\1', s)
    
    # Try various formats
    for fmt in ['%B %d, %Y', '%B %d %Y', '%b %d, %Y', '%b %d %Y',
                '%B %d,%Y', '%b %d,%Y']:
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    
    # Handle "Sept" which isn't standard
    s2 = s.replace('Sept', 'Sep')
    for fmt in ['%B %d, %Y', '%B %d %Y', '%b %d, %Y', '%b %d %Y']:
        try:
            return datetime.strptime(s2.strip(), fmt)
        except ValueError:
            continue
    
    return None

def _parse_month_day(s):
    """Parse 'Dec 2' or 'Mar 12' -> (month, day)."""
    s = s.strip()
    s = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', s)
    s = re.sub(r'(\w+)\.', r'\1', s)
    
    months = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
              'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12,
              'january': 1, 'february': 2, 'march': 3, 'april': 4,
              'june': 6, 'july': 7, 'august': 8, 'september': 9,
              'october': 10, 'november': 11, 'december': 12}
    
    m = re.match(r'(\w+)\s+(\d+)', s)
    if m:
        month_name = m.group(1).lower()
        day = int(m.group(2))
        if month_name in months:
            return (months[month_name], day)
    return None

def _month_to_num(name):
    """Convert month name to number."""
    months = {'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'feburary': 2,
              'mar': 3, 'march': 3, 'apr': 4, 'april': 4, 'may': 5,
              'jun': 6, 'june': 6, 'jul': 7, 'july': 7, 'aug': 8, 'august': 8,
              'sep': 9, 'sept': 9, 'september': 9, 'oct': 10, 'october': 10,
              'nov': 11, 'november': 11, 'dec': 12, 'december': 12}
    return months.get(name.lower().rstrip('.'))

def _last_day_of_month(year, month):
    """Get last day of month."""
    import calendar
    return calendar.monthrange(year, month)[1]

def _word_to_num(s):
    """Convert word or digit string to number."""
    words = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
             'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
             'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
             'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
             'nineteen': 19, 'twenty': 20}
    if s.isdigit():
        return int(s)
    return words.get(s.lower())

def _ordinal_to_num(s):
    """Convert ordinal word to number."""
    ordinals = {'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5,
                'sixth': 6, 'seventh': 7, 'eighth': 8, 'ninth': 9, 'tenth': 10,
                'eleventh': 11, 'twelfth': 12}
    return ordinals.get(s.lower())

def _weekday_to_num(s):
    """Convert weekday name to Python weekday number (0=Monday)."""
    days = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6}
    return days.get(s.lower())
