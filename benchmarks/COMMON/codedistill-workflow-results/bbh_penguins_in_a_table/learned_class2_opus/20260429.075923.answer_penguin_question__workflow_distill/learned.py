"""Auto-generated workflow-distilled implementation for answer_penguin_question.

Calls existing tools from ptools.
"""

from ptools import *

import re
from typing import List, Tuple, Optional


def answer_penguin_question(input_str: str) -> str:
    """Solve a penguins-in-a-table multiple-choice question."""
    
    # --- Parse the input ourselves in pure Python for reliability ---
    
    try:
        result = _solve_penguin_question(input_str)
        if result is not None:
            return result
    except Exception:
        pass
    
    # Fallback to the LLM-based workflow
    try:
        table, actions, question, options = analyze_input(input_str)
        if table and options and question:
            for action in actions:
                table = table_operation(table, action)
            answer = answer_question(table, question)
            if answer:
                resp = choose_response(answer, options)
                if resp and resp[0]:
                    return f'({resp[0]})'
    except Exception:
        pass
    
    return None


def _solve_penguin_question(input_str: str) -> Optional[str]:
    """Pure-Python approach to parse and answer the question."""
    
    # Extract options
    options = _extract_options(input_str)
    if not options:
        return None
    
    # Extract question line
    question = _extract_question(input_str)
    if not question:
        return None
    
    # Parse all tables and actions
    penguin_table, giraffe_table, actions = _parse_tables_and_actions(input_str)
    
    # Apply actions to penguin table
    for action in actions:
        penguin_table = _apply_action(penguin_table, action)
    
    # Try to answer the question
    answer = _answer_question(penguin_table, giraffe_table, question)
    if answer is None:
        return None
    
    # Match answer to option
    matched = _match_option(answer, options)
    if matched:
        return f'({matched})'
    
    return None


def _extract_options(text: str) -> List[Tuple[str, str]]:
    """Extract (letter, value) pairs from Options section."""
    options = []
    pattern = r'\(([A-Z])\)\s*(.+?)(?=\n|\([A-Z]\)|$)'
    # Find the Options: section
    opts_match = re.search(r'Options:\s*\n(.*)', text, re.DOTALL)
    if not opts_match:
        return []
    opts_text = opts_match.group(1)
    for m in re.finditer(r'\(([A-Z])\)\s*([^\n(]+)', opts_text):
        letter = m.group(1)
        value = m.group(2).strip()
        options.append((letter, value))
    return options


def _extract_question(text: str) -> Optional[str]:
    """Extract the question being asked."""
    # The question is typically the line before Options:
    opts_idx = text.find('Options:')
    if opts_idx < 0:
        opts_idx = text.find('\nOptions')
    if opts_idx < 0:
        return None
    
    before_opts = text[:opts_idx].rstrip()
    # Find lines that end with ?
    lines = before_opts.split('\n')
    for line in reversed(lines):
        line = line.strip()
        if line.endswith('?'):
            return line
    return None


def _parse_tables_and_actions(text: str) -> Tuple[List[dict], List[dict], List[str]]:
    """Parse penguin table, giraffe table, and actions from the input."""
    
    actions = []
    
    # Split the text to find different sections
    # First, extract the penguin table from the initial description
    penguin_table = []
    
    # The initial table is embedded in the first paragraph
    # Pattern: "name, age, height (cm), weight (kg) Name1, val, val, val Name2, ..."
    # It's space-separated in the original format
    
    # Find the header and data in the initial block
    header_match = re.search(r'name,\s*age,\s*height\s*\(cm\),\s*weight\s*\(kg\)\s*', text)
    if not header_match:
        return [], [], []
    
    # Get text after the first header up to "For example" or end markers
    after_header = text[header_match.end():]
    
    # Find where the data ends (before "For example" line)
    for_example_idx = after_header.find('For example')
    if for_example_idx < 0:
        for_example_idx = after_header.find('We now')
        if for_example_idx < 0:
            for_example_idx = after_header.find('And here')
            if for_example_idx < 0:
                for_example_idx = len(after_header)
    
    data_text = after_header[:for_example_idx].strip()
    
    # The data rows might be space-separated on one line or newline-separated
    # Try to parse: "Louis, 7, 50, 11 Bernard, 5, 80, 13 ..."
    # Each row is: Name, number, number, number
    row_pattern = r'([A-Z][a-z]+),\s*(\d+),\s*(\d+),\s*(\d+)'
    for m in re.finditer(row_pattern, data_text):
        penguin_table.append({
            'name': m.group(1).strip(),
            'age': int(m.group(2)),
            'height': int(m.group(3)),
            'weight': int(m.group(4))
        })
    
    # Check for "We now add a penguin" actions
    add_patterns = re.findall(
        r'We now add a penguin to the table:\s*\n\s*([A-Z][a-z]+),\s*(\d+),\s*(\d+),\s*(\d+)',
        text
    )
    for m in add_patterns:
        actions.append(('add', {
            'name': m[0].strip(),
            'age': int(m[1]),
            'height': int(m[2]),
            'weight': int(m[3])
        }))
    
    # Check for delete actions
    del_patterns = re.findall(r'delete the penguin named (\w+)', text)
    for name in del_patterns:
        actions.append(('delete', name))
    
    # Check for giraffe table
    giraffe_table = []
    giraffe_header = re.search(r'listing giraffes:\s*\n\s*name,\s*age,\s*height\s*\(cm\),\s*weight\s*\(kg\)', text)
    if giraffe_header:
        giraffe_text = text[giraffe_header.end():]
        # Extract up to the question
        question_idx = giraffe_text.find('?')
        if question_idx > 0:
            # Go back to find the start of the question line
            line_start = giraffe_text.rfind('\n', 0, question_idx)
            if line_start > 0:
                giraffe_data = giraffe_text[:line_start]
            else:
                giraffe_data = giraffe_text[:question_idx]
        else:
            giraffe_data = giraffe_text
        
        for m in re.finditer(row_pattern, giraffe_data):
            giraffe_table.append({
                'name': m.group(1).strip(),
                'age': int(m.group(2)),
                'height': int(m.group(3)),
                'weight': int(m.group(4))
            })
    
    return penguin_table, giraffe_table, actions


def _apply_action(table: List[dict], action) -> List[dict]:
    """Apply an add or delete action to a table."""
    op, data = action
    if op == 'add':
        return table + [data]
    elif op == 'delete':
        return [row for row in table if row['name'] != data]
    return table


def _answer_question(penguin_table: List[dict], giraffe_table: List[dict], question: str) -> Optional[str]:
    """Try to answer the question using parsed tables."""
    
    q = question.lower()
    
    # Determine which table(s) to use
    # If question mentions giraffes specifically, use giraffe table
    # If question mentions "animals", use both
    # Otherwise use penguin table
    
    if 'how many animals' in q:
        count = len(penguin_table) + len(giraffe_table)
        return str(count)
    
    if 'how many giraffes' in q:
        return str(len(giraffe_table))
    
    if 'how many penguins are there' in q or ('how many penguins' in q and 'are there' in q):
        return str(len(penguin_table))
    
    # Determine the target table based on question context
    use_giraffe = 'giraffe' in q
    use_both = 'animal' in q
    
    if use_both:
        target = penguin_table + giraffe_table
    elif use_giraffe:
        target = giraffe_table
    else:
        target = penguin_table
    
    if not target:
        return None
    
    # "How many penguins are more than X years old"
    m = re.search(r'how many (?:penguins|giraffes|animals) are more than (\d+) years old and weigh?t? (?:more|less) than (\d+)', q)
    if m:
        age_threshold = int(m.group(1))
        weight_threshold = int(m.group(2))
        more_weight = 'more than' in q.split('weigh')[0] if 'weigh' in q else ('more' in q[q.find(m.group(2)):])
        # Re-check: "more than X years old and weight more than Y kg" vs "weight less than Y kg"
        after_and = q[q.find('and'):]
        if 'more than' in after_and:
            count = sum(1 for r in target if r['age'] > age_threshold and r['weight'] > weight_threshold)
        else:
            count = sum(1 for r in target if r['age'] > age_threshold and r['weight'] < weight_threshold)
        return str(count)
    
    m = re.search(r'how many (?:penguins|giraffes|animals) are more than (\d+) years old', q)
    if m:
        age_threshold = int(m.group(1))
        count = sum(1 for r in target if r['age'] > age_threshold)
        return str(count)
    
    # "How many penguins are less than X years old"
    m = re.search(r'how many (?:penguins|giraffes|animals) are less than (\d+) years old', q)
    if m:
        age_threshold = int(m.group(1))
        count = sum(1 for r in target if r['age'] < age_threshold)
        return str(count)
    
    # Which penguin is taller/shorter/heavier/lighter/older/younger than the other ones?
    m = re.search(r'which (?:penguin|giraffe|animal) is (tall|short|heav|light|old|young)(?:er|est)', q)
    if m:
        attr_prefix = m.group(1)
        if attr_prefix in ('tall',):
            key = 'height'
            return max(target, key=lambda r: r[key])['name']
        elif attr_prefix in ('short',):
            key = 'height'
            return min(target, key=lambda r: r[key])['name']
        elif attr_prefix in ('heav',):
            key = 'weight'
            return max(target, key=lambda r: r[key])['name']
        elif attr_prefix in ('light',):
            key = 'weight'
            return min(target, key=lambda r: r[key])['name']
        elif attr_prefix in ('old',):
            key = 'age'
            return max(target, key=lambda r: r[key])['name']
        elif attr_prefix in ('young',):
            key = 'age'
            return min(target, key=lambda r: r[key])['name']
    
    # "Which is the oldest/youngest/tallest/shortest/heaviest/lightest penguin/giraffe?"
    m = re.search(r'which is the (oldest|youngest|tallest|shortest|heaviest|lightest) (penguin|giraffe|animal)', q)
    if m:
        superlative = m.group(1)
        if superlative == 'oldest':
            return max(target, key=lambda r: r['age'])['name']
        elif superlative == 'youngest':
            return min(target, key=lambda r: r['age'])['name']
        elif superlative == 'tallest':
            return max(target, key=lambda r: r['height'])['name']
        elif superlative == 'shortest':
            return min(target, key=lambda r: r['height'])['name']
        elif superlative == 'heaviest':
            return max(target, key=lambda r: r['weight'])['name']
        elif superlative == 'lightest':
            return min(target, key=lambda r: r['weight'])['name']
    
    # "What is the name of the last penguin/giraffe?"
    m = re.search(r'name of the last (penguin|giraffe|animal)\b', q)
    if m:
        animal_type = m.group(1)
        # Check if "sorted by alphabetic order" is in the question
        if 'sorted by alphabetic order' in q or 'alphabetic order' in q:
            if animal_type == 'animal':
                all_animals = penguin_table + giraffe_table
                sorted_animals = sorted(all_animals, key=lambda r: r['name'])
            elif animal_type == 'giraffe':
                sorted_animals = sorted(giraffe_table, key=lambda r: r['name'])
            else:
                sorted_animals = sorted(target, key=lambda r: r['name'])
            if sorted_animals:
                return sorted_animals[-1]['name']
        else:
            if animal_type == 'giraffe':
                if giraffe_table:
                    return giraffe_table[-1]['name']
            elif animal_type == 'animal':
                all_animals = penguin_table + giraffe_table
                if all_animals:
                    return all_animals[-1]['name']
            else:
                if target:
                    return target[-1]['name']
    
    # "What is the name of the first penguin/giraffe?"
    m = re.search(r'name of the first (penguin|giraffe|animal)\b', q)
    if m:
        animal_type = m.group(1)
        if 'sorted by alphabetic order' in q or 'alphabetic order' in q:
            if animal_type == 'animal':
                all_animals = penguin_table + giraffe_table
                sorted_animals = sorted(all_animals, key=lambda r: r['name'])
            elif animal_type == 'giraffe':
                sorted_animals = sorted(giraffe_table, key=lambda r: r['name'])
            else:
                sorted_animals = sorted(target, key=lambda r: r['name'])
            if sorted_animals:
                return sorted_animals[0]['name']
        else:
            if animal_type == 'giraffe':
                if giraffe_table:
                    return giraffe_table[0]['name']
            elif animal_type == 'animal':
                all_animals = penguin_table + giraffe_table
                if all_animals:
                    return all_animals[0]['name']
            else:
                if target:
                    return target[0]['name']
    
    # "What is the name of the last animal sorted by alphabetic order?"
    if 'last' in q and 'alphabetic' in q:
        if 'animal' in q:
            all_animals = penguin_table + giraffe_table
        elif 'giraffe' in q:
            all_animals = giraffe_table
        else:
            all_animals = target
        sorted_animals = sorted(all_animals, key=lambda r: r['name'])
        if sorted_animals:
            return sorted_animals[-1]['name']
    
    # "What is the cumulated/total age of the penguins?"
    m = re.search(r'(?:cumulated|total|sum of) (age|height|weight)', q)
    if m:
        key = m.group(1)
        return str(sum(r[key] for r in target))
    
    # "What is the average age/height/weight?"
    m = re.search(r'average (age|height|weight)', q)
    if m:
        key = m.group(1)
        if target:
            avg = sum(r[key] for r in target) / len(target)
            # Return as int if it's a whole number
            if avg == int(avg):
                return str(int(avg))
            return str(avg)
    
    # "What is the shortest/tallest height?"
    m = re.search(r'(?:what is the )(shortest|tallest|lowest|highest|smallest|largest|minimum|maximum) (height|weight|age)', q)
    if m:
        direction = m.group(1)
        key = m.group(2)
        if direction in ('shortest', 'lowest', 'smallest', 'minimum'):
            val = min(r[key] for r in target)
        else:
            val = max(r[key] for r in target)
        return str(val)
    
    # "What is the second shortest/tallest height?"
    m = re.search(r'second (shortest|tallest|lowest|highest|smallest|largest) (height|weight|age)', q)
    if m:
        direction = m.group(1)
        key = m.group(2)
        vals = sorted(set(r[key] for r in target))
        if len(vals) >= 2:
            if direction in ('shortest', 'lowest', 'smallest'):
                return str(vals[1])
            else:
                return str(vals[-2])
    
    # "What is the age of X?" or "What is the height of X?"
    m = re.search(r'what is the (age|height|weight) of (\w+)', q)
    if m:
        key = m.group(1)
        name = m.group(2).capitalize()
        all_animals = penguin_table + giraffe_table
        for r in all_animals:
            if r['name'] == name:
                return str(r[key])
    
    # "How many penguins are there?"
    if 'how many' in q and ('penguin' in q or 'animal' in q or 'giraffe' in q):
        if 'animal' in q:
            return str(len(penguin_table) + len(giraffe_table))
        elif 'giraffe' in q:
            return str(len(giraffe_table))
        else:
            return str(len(penguin_table))
    
    # "How many penguins weigh more/less than X kg?"
    m = re.search(r'how many (?:penguins|giraffes|animals) weigh (?:more|less) than (\d+)', q)
    if m:
        threshold = int(m.group(1))
        if 'more' in q:
            count = sum(1 for r in target if r['weight'] > threshold)
        else:
            count = sum(1 for r in target if r['weight'] < threshold)
        return str(count)
    
    # Fall through - try LLM-based approach
    return None


def _match_option(answer: str, options: List[Tuple[str, str]]) -> Optional[str]:
    """Match an answer string to one of the options."""
    answer_lower = answer.strip().lower()
    
    # Exact match
    for letter, value in options:
        if answer_lower == value.strip().lower():
            return letter
    
    # Try numeric match
    try:
        answer_num = float(answer)
        for letter, value in options:
            try:
                if float(value) == answer_num:
                    return letter
            except (ValueError, TypeError):
                pass
    except (ValueError, TypeError):
        pass
    
    # Try substring match (for name answers)
    for letter, value in options:
        if answer_lower == value.strip().lower():
            return letter
        if answer_lower in value.strip().lower() or value.strip().lower() in answer_lower:
            # Be more careful - only match if it's a clear match
            if len(answer_lower) > 1 and len(value.strip()) > 1:
                return letter
    
    return None
