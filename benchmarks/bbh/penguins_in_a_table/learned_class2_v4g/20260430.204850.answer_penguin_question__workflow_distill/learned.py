"""Auto-generated workflow-distilled implementation for answer_penguin_question.

Calls existing tools from ptools.
"""

from ptools import *

import re

def answer_penguin_question(input_str: str) -> str:
    # Handle tuple inputs from some evaluation harnesses
    if isinstance(input_str, tuple):
        input_str = input_str[0]
        
    penguins = []
    giraffes = []
    
    # 1. Extract the initial penguins by finding the split point at "For example: ... ."
    example_match = re.search(r'For example:[^\.]*\.', input_str)
    if example_match:
        init_str = input_str[:example_match.start()]
        rest = input_str[example_match.end():]
    else:
        init_str = input_str
        rest = ""
        
    # Extract initial table entries (Name, Age, Height, Weight)
    for m in re.finditer(r'([A-Z][a-z]+),\s*(\d+),\s*(\d+),\s*(\d+)', init_str):
        penguins.append({
            'name': m.group(1),
            'age': int(m.group(2)),
            'height': int(m.group(3)),
            'weight': int(m.group(4))
        })
        
    if not penguins:
        return None
        
    # 2. Process additions and deletions strictly sequentially as described
    for m in re.finditer(r'add a penguin.*?(?:to the table)?:\s*([A-Z][a-z]+),\s*(\d+),\s*(\d+),\s*(\d+)', rest):
        penguins.append({
            'name': m.group(1),
            'age': int(m.group(2)),
            'height': int(m.group(3)),
            'weight': int(m.group(4))
        })
        
    for m in re.finditer(r'delete the penguin named ([A-Z][a-z]+)', rest):
        name_to_delete = m.group(1)
        penguins = [p for p in penguins if p['name'] != name_to_delete]
        
    # 3. Find and extract giraffes if present
    giraffes_start = rest.find('listing giraffes')
    if giraffes_start != -1:
        options_idx = rest.rfind('Options:')
        if options_idx != -1:
            giraffes_str = rest[giraffes_start:options_idx]
        else:
            giraffes_str = rest[giraffes_start:]
            
        for m in re.finditer(r'([A-Z][a-z]+),\s*(\d+),\s*(\d+),\s*(\d+)', giraffes_str):
            giraffes.append({
                'name': m.group(1),
                'age': int(m.group(2)),
                'height': int(m.group(3)),
                'weight': int(m.group(4))
            })
            
    # 4. Extract Question and Options
    options_idx = rest.rfind('Options:')
    if options_idx == -1:
        return None
        
    question_text = rest[:options_idx].strip()
    lines = [line.strip() for line in question_text.split('\n') if line.strip()]
    if lines:
        actual_question = lines[-1]
    else:
        return None
        
    options_str = rest[options_idx:]
    options = {}
    for line in options_str.split('\n'):
        line = line.strip()
        m = re.match(r'^\(([A-Z])\)\s*(.*)', line)
        if m:
            options[m.group(1)] = m.group(2)
            
    if not options:
        return None
        
    # 5. Evaluate the logical query requested in the question
    q = actual_question.lower()
    ans = None
    animals = penguins + giraffes
    
    def get_count(group, q_text):
        count = 0
        for p in group:
            ok = True
            if "more than" in q_text and "years old" in q_text:
                m = re.search(r'more than (\d+) years old', q_text)
                if m and p['age'] <= int(m.group(1)): ok = False
            if "less than" in q_text and "years old" in q_text:
                m = re.search(r'less than (\d+) years old', q_text)
                if m and p['age'] >= int(m.group(1)): ok = False
                
            if "weight more than" in q_text:
                m = re.search(r'weight more than (\d+)', q_text)
                if m and p['weight'] <= int(m.group(1)): ok = False
            elif "weigh more than" in q_text:
                m = re.search(r'weigh more than (\d+)', q_text)
                if m and p['weight'] <= int(m.group(1)): ok = False
                
            if "weight less than" in q_text:
                m = re.search(r'weight less than (\d+)', q_text)
                if m and p['weight'] >= int(m.group(1)): ok = False
            elif "weigh less than" in q_text:
                m = re.search(r'weigh less than (\d+)', q_text)
                if m and p['weight'] >= int(m.group(1)): ok = False
                
            if "height more than" in q_text:
                m = re.search(r'height more than (\d+)', q_text)
                if m and p['height'] <= int(m.group(1)): ok = False
            if "height less than" in q_text:
                m = re.search(r'height less than (\d+)', q_text)
                if m and p['height'] >= int(m.group(1)): ok = False
                
            if ok:
                count += 1
        return count

    try:
        if "cumulated age" in q or "cumulative age" in q:
            target = penguins if "penguin" in q else giraffes if "giraffe" in q else animals
            ans = sum(p['age'] for p in target)
        elif "average height" in q:
            target = penguins if "penguin" in q else giraffes if "giraffe" in q else animals
            if target:
                ans = sum(p['height'] for p in target) / len(target)
                if float(ans).is_integer():
                    ans = int(ans)
        elif "average age" in q:
            target = penguins if "penguin" in q else giraffes if "giraffe" in q else animals
            if target:
                ans = sum(p['age'] for p in target) / len(target)
                if float(ans).is_integer():
                    ans = int(ans)
        elif "average weight" in q:
            target = penguins if "penguin" in q else giraffes if "giraffe" in q else animals
            if target:
                ans = sum(p['weight'] for p in target) / len(target)
                if float(ans).is_integer():
                    ans = int(ans)
        elif "how many" in q and ("more than" in q or "less than" in q):
            target = penguins if "penguin" in q else giraffes if "giraffe" in q else animals
            ans = get_count(target, q)
        elif "how many" in q:
            target = penguins if "penguin" in q else giraffes if "giraffe" in q else animals
            ans = len(target)
        elif "oldest" in q:
            target = penguins if "penguin" in q else giraffes if "giraffe" in q else animals
            ans = max(target, key=lambda x: x['age'])['name']
        elif "youngest" in q:
            target = penguins if "penguin" in q else giraffes if "giraffe" in q else animals
            ans = min(target, key=lambda x: x['age'])['name']
        elif "tallest" in q or "taller than the other ones" in q:
            target = penguins if "penguin" in q else giraffes if "giraffe" in q else animals
            ans = max(target, key=lambda x: x['height'])['name']
        elif "shortest height" in q:
            target = penguins if "penguin" in q else giraffes if "giraffe" in q else animals
            ans = min(target, key=lambda x: x['height'])['height']
        elif "shortest" in q:
            target = penguins if "penguin" in q else giraffes if "giraffe" in q else animals
            ans = min(target, key=lambda x: x['height'])['name']
        elif "heaviest" in q or "highest weight" in q:
            target = penguins if "penguin" in q else giraffes if "giraffe" in q else animals
            if "what is the highest weight" in q:
                ans = max(target, key=lambda x: x['weight'])['weight']
            else:
                ans = max(target, key=lambda x: x['weight'])['name']
        elif "lightest" in q or "lowest weight" in q:
            target = penguins if "penguin" in q else giraffes if "giraffe" in q else animals
            if "what is the lowest weight" in q:
                ans = min(target, key=lambda x: x['weight'])['weight']
            else:
                ans = min(target, key=lambda x: x['weight'])['name']
        elif "last" in q and "sorted by alphabetic order" in q:
            target = penguins if "penguin" in q else giraffes if "giraffe" in q else animals
            sorted_target = sorted(target, key=lambda x: x['name'])
            ans = sorted_target[-1]['name']
        elif "first" in q and "sorted by alphabetic order" in q:
            target = penguins if "penguin" in q else giraffes if "giraffe" in q else animals
            sorted_target = sorted(target, key=lambda x: x['name'])
            ans = sorted_target[0]['name']
        elif "last" in q:
            target = penguins if "penguin" in q else giraffes if "giraffe" in q else animals
            ans = target[-1]['name']
        elif "first" in q:
            target = penguins if "penguin" in q else giraffes if "giraffe" in q else animals
            ans = target[0]['name']
    except Exception:
        # Graceful fallback logic on malformed structures
        return None
        
    if ans is None:
        return None
        
    # Normalize computed answer for matching
    ans_str = re.sub(r'[^\w\s]', '', str(ans).lower())
    
    # 6. Resolve Output Multiple Choice Letter Pattern Matching
    # Pass 1: exact normalized match
    for letter, text in options.items():
        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        if clean_text == ans_str:
            return f"({letter})"
            
    # Pass 2: embedded match (e.g., "(A) 4 penguins" where ans_str="4")
    for letter, text in options.items():
        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        words = clean_text.split()
        if ans_str in words:
            return f"({letter})"

    return None
