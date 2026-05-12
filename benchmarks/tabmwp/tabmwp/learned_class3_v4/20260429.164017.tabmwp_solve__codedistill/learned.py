"""Auto-generated code-distilled implementation for tabmwp_solve."""

import re
import math
import statistics

def tabmwp_solve(question, table, problem_id, choices):
    """Solve a TabMWP (Tabular Math Word Problem)."""
    
    # Parse the table
    lines = table.strip().split('\n')
    rows = []
    for line in lines:
        parts = [p.strip() for p in line.split('|')]
        rows.append(parts)
    
    header = rows[0] if rows else []
    data_rows = rows[1:] if len(rows) > 1 else []
    
    q = question.lower()
    
    # Detect stem-and-leaf plot
    is_stem_leaf = any('stem' in h.lower() for h in header) and any('leaf' in h.lower() for h in header)
    
    if is_stem_leaf:
        return solve_stem_leaf(question, q, header, data_rows, choices)
    
    # Detect if it's a frequency table
    is_frequency = any('frequency' in h.lower() for h in header)
    
    # Check for function/relation questions
    if 'is this relation a function' in q:
        return solve_is_function(data_rows, choices)
    
    if 'is the function linear or nonlinear' in q or 'linear or nonlinear' in q:
        return solve_linear_nonlinear(data_rows, choices)
    
    # Schedule lookup
    if 'schedule' in q or ('train' in q and ('next' in q or 'missed' in q)):
        return solve_schedule(question, q, header, data_rows, rows, choices)
    
    # Look at schedule - which event begins at
    if 'which event' in q and 'begin' in q:
        return solve_event_lookup(question, q, header, data_rows, choices)
    
    # Frequency table queries
    if is_frequency:
        return solve_frequency(question, q, header, data_rows, choices)
    
    # Extract numbers from table
    numbers = extract_numbers_from_table(header, data_rows, q)
    
    # Mean
    if 'mean' in q or 'average' in q:
        if numbers:
            mean_val = sum(numbers) / len(numbers)
            return format_number(mean_val)
    
    # Median
    if 'median' in q:
        if numbers:
            sorted_nums = sorted(numbers)
            n = len(sorted_nums)
            if n % 2 == 1:
                median_val = sorted_nums[n // 2]
            else:
                median_val = (sorted_nums[n // 2 - 1] + sorted_nums[n // 2]) / 2
            return format_number(median_val)
    
    # Mode
    if 'mode' in q:
        if numbers:
            from collections import Counter
            cnt = Counter(numbers)
            max_count = max(cnt.values())
            modes = [k for k, v in cnt.items() if v == max_count]
            if len(modes) == 1:
                return format_number(modes[0])
            else:
                # Return smallest or handle multiple modes
                return format_number(min(modes))
    
    # Range
    if 'range' in q and ('what is the range' in q or 'find the range' in q):
        if numbers:
            return format_number(max(numbers) - min(numbers))
    
    # Largest/greatest/most
    if 'largest' in q or 'greatest' in q or 'most' in q or 'highest' in q or 'maximum' in q or 'longest' in q or 'heaviest' in q or 'tallest' in q or 'expensive' in q or 'farthest' in q:
        return solve_extreme(question, q, header, data_rows, choices, find_max=True)
    
    # Smallest/fewest/least/lowest/shortest/cheapest
    if 'smallest' in q or 'fewest' in q or 'least' in q or 'lowest' in q or 'minimum' in q or 'shortest' in q or 'cheapest' in q or 'lightest' in q:
        return solve_extreme(question, q, header, data_rows, choices, find_max=False)
    
    # "How many more" / difference
    if 'how many more' in q or 'how many fewer' in q or 'how much more' in q or 'how much less' in q or 'how much fewer' in q or 'difference' in q:
        return solve_difference(question, q, header, data_rows, choices)
    
    # "How many" with a specific condition (e.g., "how many ... exactly")
    if 'how many' in q:
        result = solve_how_many(question, q, header, data_rows, choices)
        if result is not None:
            return result
    
    # "How much" / total cost / addition
    if 'how much' in q or 'total' in q:
        return solve_addition(question, q, header, data_rows, choices)
    
    # "How many [items] in [number]" - pattern/multiplication
    if 'how many' in q:
        result = solve_pattern(question, q, header, data_rows, choices)
        if result is not None:
            return result
    
    # Which day/which ... did ... the most/least (already handled above mostly)
    if 'which' in q and choices:
        return solve_which(question, q, header, data_rows, choices)
    
    # On which day
    if 'on which' in q and choices:
        return solve_which(question, q, header, data_rows, choices)
    
    # Pattern completion (table with ?)
    if '?' in table:
        return solve_pattern(question, q, header, data_rows, choices)
    
    # Fallback: try to figure out from choices
    if choices:
        return solve_with_choices_fallback(question, q, header, data_rows, choices)
    
    return None


def parse_number(s):
    """Parse a number from string, handling currency, commas, etc."""
    if s is None:
        return None
    s = s.strip()
    # Remove currency symbols
    s = s.replace('$', '').replace(',', '').replace('%', '')
    # Remove trailing units
    s = s.strip()
    try:
        if '/' in s:
            parts = s.split('/')
            return float(parts[0]) / float(parts[1])
        val = float(s)
        return val
    except (ValueError, ZeroDivisionError):
        return None


def format_number(val):
    """Format a number as string, removing unnecessary decimals."""
    if val is None:
        return None
    if isinstance(val, float):
        if val == int(val):
            return str(int(val))
        # Check if it has a reasonable decimal representation
        formatted = f"{val:.2f}"
        # Remove trailing zeros after decimal
        if '.' in formatted:
            # Keep .00 format for money-like values
            return formatted
        return formatted
    return str(val)


def format_number_smart(val, is_money=False):
    """Format number smartly."""
    if val is None:
        return None
    if isinstance(val, float):
        if val == int(val) and not is_money:
            return str(int(val))
        if is_money:
            return f"{val:.2f}"
        # Check precision needed
        rounded = round(val, 2)
        if rounded == int(rounded):
            return str(int(rounded))
        return f"{rounded:.2f}" if abs(rounded - round(rounded, 1)) > 1e-9 else f"{rounded:.1f}" if rounded != int(rounded) else str(int(rounded))
    return str(int(val)) if isinstance(val, int) else str(val)


def extract_numbers_from_table(header, data_rows, q):
    """Extract numeric values from the table's value column."""
    numbers = []
    if len(header) >= 2:
        # Try to get numbers from the last column or the numeric column
        for row in data_rows:
            if len(row) >= 2:
                val = parse_number(row[-1])
                if val is not None:
                    numbers.append(val)
    return numbers


def solve_stem_leaf(question, q, header, data_rows, choices):
    """Solve stem-and-leaf plot problems."""
    # Parse all values
    values = []
    for row in data_rows:
        if len(row) >= 2:
            stem_str = row[0].strip()
            leaf_str = row[1].strip()
            try:
                stem = int(stem_str)
            except ValueError:
                continue
            if not leaf_str or leaf_str == '':
                continue
            leaves = [l.strip() for l in leaf_str.split(',') if l.strip()]
            for leaf in leaves:
                try:
                    leaf_val = int(leaf)
                    values.append(stem * 10 + leaf_val)
                except ValueError:
                    continue
    
    if not values:
        return None
    
    # What is the largest number
    if 'largest' in q or 'greatest' in q or 'most' in q or 'maximum' in q:
        return str(max(values))
    
    # What is the smallest number
    if 'smallest' in q or 'fewest' in q or 'least' in q or 'minimum' in q:
        return str(min(values))
    
    # How many ... exactly X
    exactly_match = re.search(r'exactly\s+(\d+)', q)
    if exactly_match:
        target = int(exactly_match.group(1))
        count = values.count(target)
        return str(count)
    
    # How many ... at least X / X or more
    at_least_match = re.search(r'at least\s+(\d+)', q)
    if at_least_match:
        target = int(at_least_match.group(1))
        count = sum(1 for v in values if v >= target)
        return str(count)
    
    # How many ... fewer than X / less than X
    fewer_match = re.search(r'(?:fewer|less) than\s+(\d+)', q)
    if fewer_match:
        target = int(fewer_match.group(1))
        count = sum(1 for v in values if v < target)
        return str(count)
    
    # How many ... more than X / greater than X
    more_match = re.search(r'(?:more|greater) than\s+(\d+)', q)
    if more_match:
        target = int(more_match.group(1))
        count = sum(1 for v in values if v > target)
        return str(count)
    
    # How many ... at most X / X or fewer
    at_most_match = re.search(r'at most\s+(\d+)', q)
    if at_most_match:
        target = int(at_most_match.group(1))
        count = sum(1 for v in values if v <= target)
        return str(count)
    
    # How many ... between X and Y
    between_match = re.search(r'between\s+(\d+)\s+and\s+(\d+)', q)
    if between_match:
        lo = int(between_match.group(1))
        hi = int(between_match.group(2))
        count = sum(1 for v in values if lo <= v <= hi)
        return str(count)
    
    # Median
    if 'median' in q:
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        if n % 2 == 1:
            return str(sorted_vals[n // 2])
        else:
            med = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
            return format_number(med)
    
    # Mean
    if 'mean' in q or 'average' in q:
        mean_val = sum(values) / len(values)
        return format_number(mean_val)
    
    # Mode
    if 'mode' in q:
        from collections import Counter
        cnt = Counter(values)
        max_count = max(cnt.values())
        modes = sorted([k for k, v in cnt.items() if v == max_count])
        if len(modes) == 1:
            return str(modes[0])
        return str(modes[0])
    
    # Range
    if 'range' in q:
        return str(max(values) - min(values))
    
    # How many [items] were/are there
    if 'how many' in q:
        return str(len(values))
    
    return None


def solve_is_function(data_rows, choices):
    """Check if a relation is a function."""
    x_values = []
    for row in data_rows:
        if len(row) >= 2:
            x_val = row[0].strip()
            x_values.append(x_val)
    
    if len(x_values) != len(set(x_values)):
        answer = 'no'
    else:
        answer = 'yes'
    
    if choices:
        for c in choices:
            if c.lower() == answer:
                return c
    return answer


def solve_linear_nonlinear(data_rows, choices):
    """Determine if a function is linear or nonlinear."""
    points = []
    for row in data_rows:
        if len(row) >= 2:
            x = parse_number(row[0])
            y = parse_number(row[1])
            if x is not None and y is not None:
                points.append((x, y))
    
    if len(points) < 2:
        return None
    
    # Check if slopes are constant
    slopes = []
    for i in range(1, len(points)):
        dx = points[i][0] - points[i-1][0]
        dy = points[i][1] - points[i-1][1]
        if dx == 0:
            return 'nonlinear' if not choices else next((c for c in choices if c.lower() == 'nonlinear'), 'nonlinear')
        slopes.append(dy / dx)
    
    is_linear = all(abs(s - slopes[0]) < 1e-9 for s in slopes)
    answer = 'linear' if is_linear else 'nonlinear'
    
    if choices:
        for c in choices:
            if c.lower() == answer:
                return c
    return answer


def solve_schedule(question, q, header, data_rows, rows, choices):
    """Solve schedule/timetable problems."""
    # Find the station/location mentioned
    # Parse times for the relevant station
    
    # Try to find the station name and the missed time
    # Pattern: "missed the X:XX [A.M./P.M.] train at [Station]"
    missed_match = re.search(r'missed the\s+([\d.:]+)\s*(a\.?m\.?|p\.?m\.?)\s*(?:train|bus)?\s*(?:at|from)\s+(.+?)(?:\.|$|\?)', q)
    
    if missed_match:
        time_str = missed_match.group(1).replace('.', ':')
        ampm = missed_match.group(2).replace('.', '').upper()
        if len(ampm) == 2:
            ampm = ampm[0] + '.' + ampm[1] + '.'
        station = missed_match.group(3).strip()
        
        # Normalize the target time
        target_time = normalize_time_str(time_str + ' ' + ampm)
        
        # Find the station row
        station_row = None
        for row in rows:
            if len(row) >= 2 and station.lower() in row[0].strip().lower():
                station_row = row
                break
        
        if station_row is None:
            # Try partial match
            for row in rows:
                if len(row) >= 2:
                    if any(word in row[0].strip().lower() for word in station.lower().split()):
                        station_row = row
                        break
        
        if station_row:
            times = [t.strip() for t in station_row[1:]]
            # Convert times to minutes for comparison
            target_minutes = time_to_minutes(target_time)
            
            if target_minutes is not None:
                next_time = None
                next_minutes = float('inf')
                
                for t in times:
                    t_normalized = normalize_time_str(t)
                    t_min = time_to_minutes(t_normalized)
                    if t_min is not None and t_min > target_minutes:
                        if t_min < next_minutes:
                            next_minutes = t_min
                            next_time = t.strip()
                
                if next_time:
                    # Clean up the time format
                    next_time = next_time.strip()
                    if choices:
                        # Match to choices
                        for c in choices:
                            c_norm = normalize_time_str(c)
                            nt_norm = normalize_time_str(next_time)
                            if c_norm == nt_norm:
                                return c
                        # Try fuzzy match
                        for c in choices:
                            if similar_time(c, next_time):
                                return c
                    return next_time
    
    # Event begins at time
    if 'begin' in q or 'start' in q:
        return solve_event_lookup(question, q, header, data_rows, choices)
    
    # What time does event end
    if 'end' in q:
        return solve_event_end_lookup(question, q, header, data_rows, choices)
    
    return None


def normalize_time_str(s):
    """Normalize time string."""
    s = s.strip()
    s = s.replace('.', ':').replace('::',':')
    # Fix A:M: -> A.M.
    s = re.sub(r'(\d+:\d+)\s*([AaPp]):?([Mm]):?', r'\1 \2.\3.', s)
    s = re.sub(r'(\d+:\d+)\s*([AaPp])\.([Mm])\.?', r'\1 \2.\3.', s)
    return s.strip()


def time_to_minutes(time_str):
    """Convert time string to minutes since midnight for comparison."""
    time_str = time_str.strip()
    # Try to parse various formats
    match = re.search(r'(\d{1,2}):(\d{2})\s*([AaPp]\.?[Mm]\.?)', time_str)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        ampm = match.group(3).replace('.', '').upper()
        
        if ampm == 'PM' and hours != 12:
            hours += 12
        elif ampm == 'AM' and hours == 12:
            hours = 0
        
        return hours * 60 + minutes
    return None


def similar_time(t1, t2):
    """Check if two time strings represent the same time."""
    m1 = time_to_minutes(normalize_time_str(t1))
    m2 = time_to_minutes(normalize_time_str(t2))
    if m1 is not None and m2 is not None:
        return m1 == m2
    return False


def solve_event_lookup(question, q, header, data_rows, choices):
    """Find event that begins at a specific time."""
    # Extract time from question
    time_match = re.search(r'(\d{1,2})[.:](\d{2})\s*(a\.?m\.?|p\.?m\.?)', q)
    if time_match:
        target_time = f"{time_match.group(1)}:{time_match.group(2)} {time_match.group(3).upper().replace('.','')}"
        target_minutes = time_to_minutes(target_time)
        
        # Find "Begin" column index
        begin_idx = None
        for i, h in enumerate(header):
            if 'begin' in h.lower() or 'start' in h.lower():
                begin_idx = i
                break
        
        if begin_idx is not None:
            for row in data_rows:
                if len(row) > begin_idx:
                    row_time = row[begin_idx].strip()
                    row_minutes = time_to_minutes(normalize_time_str(row_time))
                    if row_minutes is not None and target_minutes is not None and row_minutes == target_minutes:
                        event = row[0].strip()
                        if choices:
                            for c in choices:
                                if c.lower() == event.lower():
                                    return c
                        return event
    return None


def solve_event_end_lookup(question, q, header, data_rows, choices):
    """Find when event ends."""
    # Extract event name from question
    # Find "End" column
    end_idx = None
    for i, h in enumerate(header):
        if 'end' in h.lower():
            end_idx = i
            break
    
    if end_idx is None:
        return None
    
    for row in data_rows:
        event = row[0].strip().lower()
        if event in q:
            if len(row) > end_idx:
                answer = row[end_idx].strip()
                if choices:
                    for c in choices:
                        if similar_time(c, answer):
                            return c
                return answer
    return None


def solve_frequency(question, q, header, data_rows, choices):
    """Solve frequency table problems."""
    # Parse the frequency table
    values = []
    freqs = []
    
    # Find frequency column
    freq_idx = None
    val_idx = None
    for i, h in enumerate(header):
        if 'frequency' in h.lower():
            freq_idx = i
        else:
            val_idx = i
    
    if freq_idx is None or val_idx is None:
        return None
    
    for row in data_rows:
        if len(row) > max(freq_idx, val_idx):
            v = parse_number(row[val_idx])
            f = parse_number(row[freq_idx])
            if v is not None and f is not None:
                values.append(v)
                freqs.append(int(f))
    
    # "How many ... fewer than X"
    fewer_match = re.search(r'fewer than\s+(\d+)', q)
    if fewer_match:
        target = int(fewer_match.group(1))
        count = sum(f for v, f in zip(values, freqs) if v < target)
        return str(count)
    
    # "How many ... more than X"
    more_match = re.search(r'more than\s+(\d+)', q)
    if more_match:
        target = int(more_match.group(1))
        count = sum(f for v, f in zip(values, freqs) if v > target)
        return str(count)
    
    # "How many ... at least X"
    at_least_match = re.search(r'at least\s+(\d+)', q)
    if at_least_match:
        target = int(at_least_match.group(1))
        count = sum(f for v, f in zip(values, freqs) if v >= target)
        return str(count)
    
    # "How many ... at most X"
    at_most_match = re.search(r'at most\s+(\d+)', q)
    if at_most_match:
        target = int(at_most_match.group(1))
        count = sum(f for v, f in zip(values, freqs) if v <= target)
        return str(count)
    
    # "How many ... exactly X"
    exactly_match = re.search(r'exactly\s+(\d+)', q)
    if exactly_match:
        target = int(exactly_match.group(1))
        count = sum(f for v, f in zip(values, freqs) if v == target)
        return str(count)
    
    # "How many ... between X and Y"
    between_match = re.search(r'between\s+(\d+)\s+and\s+(\d+)', q)
    if between_match:
        lo = int(between_match.group(1))
        hi = int(between_match.group(2))
        count = sum(f for v, f in zip(values, freqs) if lo <= v <= hi)
        return str(count)
    
    # Median
    if 'median' in q:
        expanded = []
        for v, f in zip(values, freqs):
            expanded.extend([v] * f)
        expanded.sort()
        n = len(expanded)
        if n % 2 == 1:
            return format_number(expanded[n // 2])
        else:
            return format_number((expanded[n // 2 - 1] + expanded[n // 2]) / 2)
    
    # Mean
    if 'mean' in q or 'average' in q:
        total = sum(v * f for v, f in zip(values, freqs))
        count = sum(freqs)
        if count > 0:
            return format_number(total / count)
    
    # Mode
    if 'mode' in q:
        max_freq = max(freqs)
        modes = [v for v, f in zip(values, freqs) if f == max_freq]
        if len(modes) == 1:
            return format_number(modes[0])
    
    # Range
    if 'range' in q:
        expanded = []
        for v, f in zip(values, freqs):
            expanded.extend([v] * f)
        if expanded:
            return format_number(max(expanded) - min(expanded))
    
    # How many total
    if 'how many' in q:
        total = sum(freqs)
        return str(total)
    
    return None


def solve_extreme(question, q, header, data_rows, choices, find_max=True):
    """Find the row with the largest/smallest value."""
    if len(header) < 2:
        return None
    
    # Determine which column has the values
    # Usually the last column or the numeric column
    val_idx = len(header) - 1
    label_idx = 0
    
    best_val = None
    best_label = None
    
    for row in data_rows:
        if len(row) >= 2:
            val = parse_number(row[val_idx])
            if val is not None:
                if best_val is None or (find_max and val > best_val) or (not find_max and val < best_val):
                    best_val = val
                    best_label = row[label_idx].strip()
    
    if best_val is None:
        return None
    
    # Determine what the question is asking for - the label or the value
    # If asking "what is the largest number" -> return value
    # If asking "which X had the most" -> return label
    
    asking_for_value = False
    if 'what is' in q and ('number' in q or 'amount' in q or 'value' in q or 'price' in q or 'cost' in q or 'temperature' in q or 'length' in q or 'weight' in q or 'distance' in q or 'participants' in q or 'items' in q or 'menu items' in q or 'pumpkins' in q):
        asking_for_value = True
    
    if choices:
        # Check if choices are labels or values
        choice_is_numeric = all(parse_number(c) is not None for c in choices)
        if choice_is_numeric:
            return format_number(best_val)
        else:
            # Match label to choices
            for c in choices:
                if c.lower() == best_label.lower():
                    return c
            # Try partial match
            for c in choices:
                if c.lower() in best_label.lower() or best_label.lower() in c.lower():
                    return c
            return best_label
    
    if asking_for_value:
        return format_number(best_val)
    
    # If the question uses "which" or "on which" or "in which", return label
    if 'which' in q or 'who' in q:
        return best_label
    
    return format_number(best_val)


def solve_difference(question, q, header, data_rows, choices):
    """Solve how many more/fewer questions."""
    # Build a lookup from the table
    lookup = {}
    for row in data_rows:
        if len(row) >= 2:
            key = row[0].strip().lower()
            val = parse_number(row[-1])
            if val is not None:
                lookup[key] = val
    
    # Try to extract two entity names from the question
    # Pattern: "how many more X did A verb than B"
    # or "how much more did A verb than B"
    
    # Find entity names that appear in the question and the table
    entities_in_q = []
    for key in lookup:
        if key in q:
            entities_in_q.append(key)
    
    if len(entities_in_q) >= 2:
        # Determine order from question
        # "how many more did A than B" -> A - B
        positions = [(q.index(e), e) for e in entities_in_q]
        positions.sort()
        
        # Usually the structure is "more X did [entity1] ... than [entity2]"
        # entity1 - entity2
        # But let's be more careful
        
        if 'more' in q:
            # A more than B -> A - B
            # Usually the first entity mentioned is A, and the one after "than" is B
            than_pos = q.find('than')
            if than_pos >= 0:
                before_than = [e for p, e in positions if p < than_pos]
                after_than = [e for p, e in positions if p >= than_pos]
                if before_than and after_than:
                    a = before_than[-1]
                    b = after_than[0]
                    diff = lookup[a] - lookup[b]
                    return format_number_smart(abs(diff))
        
        if 'fewer' in q or 'less' in q:
            than_pos = q.find('than')
            if than_pos >= 0:
                before_than = [e for p, e in positions if p < than_pos]
                after_than = [e for p, e in positions if p >= than_pos]
                if before_than and after_than:
                    a = before_than[-1]
                    b = after_than[0]
                    diff = lookup[b] - lookup[a]
                    return format_number_smart(abs(diff))
        
        # Default: absolute difference
        vals = [lookup[e] for e in entities_in_q[:2]]
        return format_number_smart(abs(vals[0] - vals[1]))
    
    # Try with case-insensitive partial matching
    entities_in_q2 = []
    for key in lookup:
        for word in key.split():
            if len(word) > 2 and word in q:
                entities_in_q2.append(key)
                break
    
    if len(entities_in_q2) >= 2:
        vals = [lookup[e] for e in entities_in_q2[:2]]
        return format_number_smart(abs(vals[0] - vals[1]))
    
    return None


def solve_how_many(question, q, header, data_rows, choices):
    """Solve 'how many' questions."""
    # Check for comparisons
    fewer_match = re.search(r'fewer than\s+(\d+)', q)
    more_match = re.search(r'more than\s+(\d+)', q)
    at_least_match = re.search(r'at least\s+(\d+)', q)
    at_most_match = re.search(r'at most\s+(\d+)', q)
    exactly_match = re.search(r'exactly\s+([\d.]+)', q)
    
    numbers = extract_numbers_from_table(header, data_rows, q)
    
    if fewer_match:
        target = float(fewer_match.group(1))
        return str(sum(1 for n in numbers if n < target))
    if more_match:
        target = float(more_match.group(1))
        return str(sum(1 for n in numbers if n > target))
    if at_least_match:
        target = float(at_least_match.group(1))
        return str(sum(1 for n in numbers if n >= target))
    if at_most_match:
        target = float(at_most_match.group(1))
        return str(sum(1 for n in numbers if n <= target))
    if exactly_match:
        target = float(exactly_match.group(1))
        return str(sum(1 for n in numbers if n == target))
    
    return None


def solve_addition(question, q, header, data_rows, choices):
    """Solve addition/total cost problems."""
    # Build lookup from table (single column tables like price lists)
    lookup = {}
    is_money = False
    
    for row in data_rows:
        if len(row) >= 2:
            key = row[0].strip().lower()
            val_str = row[-1].strip()
            if '$' in val_str:
                is_money = True
            val = parse_number(val_str)
            if val is not None:
                lookup[key] = val
    
    # Also handle headerless tables (where first row might not be header)
    # Try the original rows too
    lines = []
    for row in data_rows:
        if len(row) >= 2:
            lines.append((row[0].strip(), row[-1].strip()))
    
    # Find items mentioned in question
    items_found = []
    for key in lookup:
        # Check if key or significant parts appear in question
        if key in q:
            items_found.append((key, lookup[key]))
        else:
            # Check partial match
            key_words = key.split()
            match_count = sum(1 for w in key_words if len(w) > 2 and w in q)
            if match_count >= len(key_words) * 0.5 and match_count > 0:
                items_found.append((key, lookup[key]))
    
    if len(items_found) >= 2:
        total = sum(v for _, v in items_found)
        return format_number_smart(total, is_money)
    elif len(items_found) == 1:
        # Maybe looking for just one value
        if 'how much' in q and ('cost' in q or 'price' in q or 'need' in q or 'pay' in q or 'spend' in q):
            if 'and' in q or 'total' in q:
                pass  # Need more items
            else:
                return format_number_smart(items_found[0][1], is_money)
    
    # Try harder matching
    items_found2 = []
    q_words = set(q.split())
    for key in lookup:
        key_words = set(key.split())
        common = q_words & key_words
        if len(common) >= 1 and any(len(w) > 3 for w in common):
            items_found2.append((key, lookup[key]))
    
    if len(items_found2) >= 2:
        total = sum(v for _, v in items_found2)
        return format_number_smart(total, is_money)
    
    return None


def solve_pattern(question, q, header, data_rows, choices):
    """Solve pattern/multiplication table problems."""
    # Look for ? in data
    known_pairs = []
    unknown_row = None
    
    for row in data_rows:
        if len(row) >= 2:
            x = parse_number(row[0])
            y_str = row[-1].strip()
            if '?' in y_str:
                unknown_row = row
            else:
                y = parse_number(y_str)
                if x is not None and y is not None:
                    known_pairs.append((x, y))
    
    if unknown_row is not None and known_pairs:
        x_unknown = parse_number(unknown_row[0])
        if x_unknown is not None:
            # Check if it's a linear relationship y = mx + b
            if len(known_pairs) >= 2:
                # Try y = mx
                ratios = [y / x for x, y in known_pairs if x != 0]
                if ratios and all(abs(r - ratios[0]) < 1e-9 for r in ratios):
                    result = x_unknown * ratios[0]
                    return format_number(result)
                
                # Try y = mx + b
                x1, y1 = known_pairs[0]
                x2, y2 = known_pairs[1]
                if x2 != x1:
                    m = (y2 - y1) / (x2 - x1)
                    b = y1 - m * x1
                    result = m * x_unknown + b
                    return format_number(result)
    
    return None


def solve_which(question, q, header, data_rows, choices):
    """Solve 'which' questions with choices."""
    # Build lookup
    lookup = {}
    for row in data_rows:
        if len(row) >= 2:
            key = row[0].strip()
            val = parse_number(row[-1])
            if val is not None:
                lookup[key.lower()] = (key, val)
    
    # Check if asking for most/least
    if 'most' in q or 'longest' in q or 'highest' in q or 'greatest' in q or 'largest' in q or 'heaviest' in q or 'tallest' in q or 'farthest' in q or 'expensive' in q:
        best = None
        best_key = None
        for k, (orig, v) in lookup.items():
            if best is None or v > best:
                best = v
                best_key = orig
        if best_key and choices:
            for c in choices:
                if c.lower() == best_key.lower():
                    return c
        return best_key
    
    if 'fewest' in q or 'least' in q or 'shortest' in q or 'smallest' in q or 'lowest' in q or 'cheapest' in q or 'lightest' in q:
        best = None
        best_key = None
        for k, (orig, v) in lookup.items():
            if best is None or v < best:
                best = v
                best_key = orig
        if best_key and choices:
            for c in choices:
                if c.lower() == best_key.lower():
                    return c
        return best_key
    
    # Generic: try to match something from the table to the question and choices
    if choices:
        for c in choices:
            for row in data_rows:
                if len(row) >= 2:
                    if c.lower() in row[0].strip().lower() or row[0].strip().lower() in c.lower():
                        # Check if this row matches the condition in the question
                        pass
        
        # Fallback
        return solve_with_choices_fallback(question, q, header, data_rows, choices)
    
    return None


def solve_with_choices_fallback(question, q, header, data_rows, choices):
    """Fallback solver when we have choices."""
    # Try to find the answer by matching table data to the question
    
    # Build a mapping of all table cells
    lookup = {}
    for row in data_rows:
        if len(row) >= 2:
            key = row[0].strip()
            for i in range(1, len(row)):
                val = row[i].strip()
                lookup[key.lower()] = val
    
    # Check if question asks about a specific value in the table
    for row in data_rows:
        if len(row) >= 2:
            label = row[0].strip().lower()
            for c_lower_choice in choices:
                if c_lower_choice.lower() == label:
                    # This choice matches a row label
                    pass
    
    # Try matching values from table to choices  
    for c in choices:
        c_norm = normalize_time_str(c) if re.search(r'\d+:\d+', c) else c
        for row in data_rows:
            for cell in row[1:]:
                cell_norm = normalize_time_str(cell.strip()) if re.search(r'\d+:\d+', cell.strip()) else cell.strip()
                if c.lower() == cell.strip().lower():
                    pass  # Found a match but need context
    
    return None
