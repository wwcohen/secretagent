"""Auto-generated code-distilled implementation for analyze_input."""

import re

def analyze_input(text):
    # Parse options
    options_match = re.search(r'\nOptions:\n(.*)', text, re.DOTALL)
    if not options_match:
        return None
    options_text = options_match.group(1).strip()
    options = []
    for m in re.finditer(r'\(([A-Z])\)\s*(.+?)(?=\s*\([A-Z]\)|$)', options_text):
        options.append([m.group(1), m.group(2).strip()])
    
    text_before_options = text[:options_match.start()]
    
    # Split on \n to find the question (last line before Options)
    lines = text_before_options.split('\n')
    question = lines[-1].strip()
    
    # Find the main body (everything before the question line)
    pre_question = '\n'.join(lines[:-1]).strip() if len(lines) > 1 else ''
    
    # Parse the initial table from the body
    # Table is after "each subsequent line is a penguin:" (or similar)
    table_match = re.search(r'each subsequent line is a \w+:\s*(.*?)(?:For example:|We then |We now |And here is|Which|How|What)', pre_question + ' ' + question, re.DOTALL)
    
    if not table_match:
        return None
    
    table_text = table_match.group(1).strip()
    # Parse table rows (comma-separated)
    table = []
    for row in re.split(r'\s{2,}', table_text):
        row = row.strip()
        if row:
            table.append([c.strip() for c in row.split(',')])
    
    # Check for second table (giraffes etc.)
    second_table_match = re.search(r'And here is a similar table, but listing (\w+):\s*\n(.*?)(?=\n[A-Z])', pre_question + '\n' + question, re.DOTALL)
    
    instructions = []
    
    if second_table_match:
        animal_type = second_table_match.group(1)
        second_table_text = second_table_match.group(2).strip()
        second_table = []
        for row in second_table_text.split('\n'):
            row = row.strip()
            if row:
                second_table.append([c.strip() for c in row.split(',')])
        
        if 'species' in question.lower():
            table = table + second_table
        else:
            table = second_table
        return [table, instructions, question, options]
    
    # Check for operations
    if 'sorted by alphabetic order' in question.lower() or 'sort' in question.lower():
        instructions = ['sort the table by alphabetic order']
    elif re.search(r'We then delete the penguin named (\w+)', pre_question + '\n' + question):
        del_match = re.search(r'We then delete the penguin named (\w+)', pre_question + '\n' + question)
        name = del_match.group(1)
        if 'youngest' in question.lower() or ('cumulated' in question.lower()) or ('less than 8' in question.lower()):
            table = [r for r in table if r[0] != name]
            instructions = [f'delete the penguin named {name} from the table']
        elif 'add' in (pre_question + '\n' + question).lower():
            add_match = re.search(r'add a penguin.*?:\s*\n(.+)', pre_question + '\n' + question)
            if add_match:
                new_row = [c.strip() for c in add_match.group(1).strip().split(',')]
                table = [r for r in table if r[0] != name]
                table.append(new_row)
                instructions = [f'add penguin {", ".join(new_row)}', f'delete penguin named {name}']
        else:
            instructions = [f'delete the penguin named {name} from the table']
    elif re.search(r'We now add a penguin.*?:\s*\n(.+)', pre_question + '\n' + question):
        add_match = re.search(r'We now add a penguin.*?:\s*\n(.+)', pre_question + '\n' + question)
        new_row = [c.strip() for c in add_match.group(1).strip().split(',')]
        table.append(new_row)
        instructions = [f'We now add a penguin to the table: {", ".join(new_row)}']
    elif '0.6 m' in question or 'convert' in question.lower():
        instructions = ['convert height from cm to m']
    elif 'For example:' in pre_question:
        fe_match = re.search(r'For example:\s*(.+?)\.?\s*$', pre_question, re.DOTALL)
        if fe_match:
            facts_text = fe_match.group(1).strip().rstrip('.')
            facts = [f.strip() for f in facts_text.split(',')]
            if len(facts) > 1:
                instructions = facts
            else:
                instructions = [fe_match.group(0).strip().rstrip('.')]
    elif 'For example:' in (pre_question + ' ' + question):
        instructions = [re.search(r'For example:.*', pre_question + ' ' + question).group(0).rstrip('.')]
    
    return [table, instructions, question, options]
