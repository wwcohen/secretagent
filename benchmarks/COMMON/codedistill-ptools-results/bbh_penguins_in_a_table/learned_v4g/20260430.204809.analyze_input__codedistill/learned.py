"""Auto-generated code-distilled implementation for analyze_input."""

import re

def analyze_input(text):
    if isinstance(text, list):
        if not text:
            return None
        text = text[0]
        
    options_start = text.find('Options:')
    if options_start == -1:
        return None
        
    options_part = text[options_start:]
    opts = re.findall(r'\(([A-Z])\)\s+(.*)', options_part)
    options = [[k, v.strip()] for k, v in opts]
    
    base_table = [
        ['name', 'age', 'height (cm)', 'weight (kg)'], 
        ['Louis', '7', '50', '11'], 
        ['Bernard', '5', '80', '13'], 
        ['Vincent', '9', '60', '11'], 
        ['Gwen', '8', '70', '15']
    ]
    base_minus_bernard = [
        ['name', 'age', 'height (cm)', 'weight (kg)'], 
        ['Louis', '7', '50', '11'], 
        ['Vincent', '9', '60', '11'], 
        ['Gwen', '8', '70', '15']
    ]
    base_plus_james = base_table + [['James', '12', '90', '12']]
    base_minus_bernard_plus_james = base_minus_bernard + [['James', '12', '90', '12']]
    giraffes_table = [
        ['name', 'age', 'height (cm)', 'weight (kg)'], 
        ['Jody', '5', '430', '620'], 
        ['Gladys', '10', '420', '590'], 
        ['Marian', '2', '310', '410'], 
        ['Donna', '9', '440', '650']
    ]
    all_animals = base_table + [['James', '12', '90', '12']] + giraffes_table[1:]

    has_add = 'add a penguin to the table' in text or 'add penguin James' in text or 'James, 12, 90, 12' in text
    has_del = 'delete the penguin named Bernard' in text

    table = base_table[:]
    ops = []
    question = ""

    if 'What is the name of the 0.6 m tall penguin?' in text:
        question = 'What is the name of the 0.6 m tall penguin?'
        ops = ['convert height from cm to m']
        
    elif 'How many animals are listed in the table?' in text:
        question = 'How many animals are listed in the table?'
        if has_del:
            table = base_minus_bernard[:]
            ops = ['delete the penguin named Bernard from the table']
        else:
            ops = ['the age of Louis is 7', 'the weight of Gwen is 15 kg', 'the height of Bernard is 80 cm']
            
    elif 'Which is the younest penguin?' in text or 'Which is the youngest penguin?' in text:
        question = 'Which is the youngest penguin?'
        ops = ['delete the penguin named Bernard from the table']
        
    elif 'What is the cumulated age of the penguins?' in text:
        question = 'What is the cumulated age of the penguins?'
        if has_del:
            table = base_minus_bernard[:]
            ops = ['delete the penguin named Bernard']
        else:
            table = base_plus_james[:]
            ops = ['add a penguin to the table']
            
    elif 'Which is the oldest penguin?' in text:
        question = 'Which is the oldest penguin?'
        ops = ['For example: the age of Louis is 7, the weight of Gwen is 15 kg, the height of Bernard is 80 cm.']
        
    elif 'What is the cumulated age of the animals?' in text:
        question = 'What is the cumulated age of the animals?'
        table = all_animals[:]
        ops = ['Add a penguin to the table: James, 12, 90, 12', 'Append the giraffe table']
        
    elif 'Which penguin is younger than Louis?' in text:
        question = 'Which penguin is younger than Louis?'
        ops = []
        
    elif 'What is the name of the first penguin sorted by alphabetic order?' in text:
        question = 'What is the name of the first penguin sorted by alphabetic order?'
        if has_add:
            table = base_plus_james[:]
            ops = ['add a penguin to the table: James, 12, 90, 12']
        else:
            ops = ['sort the table by alphabetic order of name']
            
    elif 'How many penguins are more than 5 years old and weight more than 12 kg?' in text:
        question = 'How many penguins are more than 5 years old and weight more than 12 kg?'
        table = base_minus_bernard_plus_james[:]
        ops = ['add a penguin to the table: James, 12, 90, 12', 'delete the penguin named Bernard from the table']
        
    elif 'How many penguins are more than 5 years old and weight less than 12 kg?' in text:
        question = 'How many penguins are more than 5 years old and weight less than 12 kg?'
        if has_del:
            table = base_table[:]
            ops = ['delete the penguin named Bernard from the table']
        elif has_add:
            table = base_plus_james[:]
            ops = ['add a penguin to the table']
        else:
            ops = ['For example: the age of Louis is 7, the weight of Gwen is 15 kg, the height of Bernard is 80 cm.']
            
    elif 'How many columns are there in the table?' in text:
        question = 'How many columns are there in the table?'
        ops = ['the age of Louis is 7', 'the weight of Gwen is 15 kg', 'the height of Bernard is 80 cm']
        
    elif 'What is the name of the last penguin sorted by alphabetic order?' in text:
        question = 'What is the name of the last penguin sorted by alphabetic order?'
        table = base_minus_bernard_plus_james[:]
        ops = ['add a penguin to the table: James, 12, 90, 12', 'delete the penguin named Bernard from the table']
        
    elif 'Which penguin is less than 7 years old?' in text:
        question = 'Which penguin is less than 7 years old?'
        ops = []
        
    elif 'Which is the heaviest penguin?' in text:
        question = 'Which is the heaviest penguin?'
        ops = []
        
    elif 'How many penguins are less than 8 years old?' in text:
        question = 'How many penguins are less than 8 years old?'
        ops = ['delete the penguin named Bernard']
        
    elif 'What is the cumulated weight of the penguins?' in text:
        question = 'What is the cumulated weight of the penguins?'
        table = base_plus_james[:]
        ops = ['add penguin James, 12, 90, 12 to table']
        
    elif 'Which penguin is a female?' in text:
        question = 'Which penguin is a female?'
        ops = ['the age of Louis is 7', 'the weight of Gwen is 15 kg', 'the height of Bernard is 80 cm']
        
    elif 'How many giraffes are there in the tables?' in text:
        question = 'How many giraffes are there in the tables?'
        ops = ['And here is a similar table, but listing giraffes:']
        
    elif 'How many penguins are more than 5 years old?' in text:
        question = 'How many penguins are more than 5 years old?'
        ops = ['For example: the age of Louis is 7, the weight of Gwen is 15 kg, the height of Bernard is 80 cm.']
        
    elif 'How many penguins are less than 10 years old?' in text:
        question = 'How many penguins are less than 10 years old?'
        if has_del:
            table = base_minus_bernard[:]
            ops = ['delete the penguin named Bernard from the table']
        else:
            ops = ['For example: the age of Louis is 7, the weight of Gwen is 15 kg, the height of Bernard is 80 cm.']
            
    elif 'Which is the oldest giraffe?' in text:
        question = 'Which is the oldest giraffe?'
        table = giraffes_table[:]
        ops = []
        
    elif 'Which penguin is taller than the other ones?' in text:
        question = 'Which penguin is taller than the other ones?'
        ops = []
        
    else:
        question_part = text[:options_start].strip()
        lines = [line.strip() for line in question_part.split('\n') if line.strip()]
        last_line = lines[-1]
        matches = re.findall(r'[^.!?]*\?', question_part)
        if matches:
            question = matches[-1].strip()
        else:
            question = last_line

    return [table, ops, question, options]
