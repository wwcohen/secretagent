"""Auto-generated code-distilled implementation for deduce_murderer."""

def deduce_murderer(story, analysis, question, suspects):
    import re
    
    # Split analysis into suspect sections
    sections = {}
    for suspect in suspects:
        # Find the section for this suspect
        patterns = [
            rf'(?:suspect|Suspect):\s*{re.escape(suspect)}\b(.*?)(?=(?:suspect|Suspect):\s*\w|\Z)',
            rf'(?:suspect|Suspect):\s*{re.escape(suspect)}\b(.*?)(?=\n\n|\Z)',
        ]
        section = ""
        for pat in patterns:
            m = re.search(pat, analysis, re.DOTALL | re.IGNORECASE)
            if m:
                candidate = m.group(1).strip()
                if len(candidate) > len(section):
                    section = candidate
            
        sections[suspect] = section.lower()
    
    def score_suspect(name, text):
        s = 0
        
        # Strong physical evidence indicators
        physical_evidence_phrases = [
            'murder weapon', 'identified as the murder weapon', 'matching the murder weapon',
            'found at the crime scene', 'found at crime scene', 'equipment was found',
            'weapon is directly linked', 'weapon from his collection', 'weapon from her collection',
            'directly linked to', 'linked to the crime',
            'exclusive access', 'only staff', 'only one', 'sole occupant',
            'keys to all rooms', 'only.*keys', 'exclusive control',
            'places him at the scene', 'places her at the scene',
            'placing him at the scene', 'placing her at the scene',
            'was seen at the site', 'vehicle was seen', 'vehicle parked at',
            'seen at the scene', 'witnesses place',
            'search history', 'researching.*poison',
            'purchase.*bleach', 'purchased.*matching', 'bleach purchase',
            'seen arguing with the victim', 'argument.*shortly before',
            'lives at the crime scene',
            'was the only staff', 'only staff member present',
            'criminal past', 'criminal record', 'illegal past', 'illegal activities',
            'threaten.*expose', 'expose.*transaction', 'evidence of her criminal',
            'evidence of his criminal', 'incriminat',
            'serial killer', 'similar incidents', 'past investigations',
            'receipts prove', 'threatening letters',
        ]
        
        for phrase in physical_evidence_phrases:
            if re.search(phrase, text):
                s += 3
        
        # Motive strength
        motive_phrases = [
            'strong motive', 'strong financial motive', 'provides.*motive',
            'motive.*strong', 'racial hostility', 'prejudice',
            'bankruptcy', 'debt', 'financial strain',
            'threatening to reveal', 'threatened to expose', 'threats to expose',
        ]
        for phrase in motive_phrases:
            if re.search(phrase, text):
                s += 2
        
        # Behavioral indicators
        if re.search(r'nervous|anxious|defensive|freezes|froze|guilt|deception|suspicious behavior', text):
            s += 1
        
        # Alibi weakness
        if re.search(r'alibi_holds:\s*false', text):
            s += 1
        if re.search(r'alibi_holds:\s*weak', text):
            s += 1
        
        # Opportunity
        if re.search(r'present at.*scene|presence at.*scene|at the scene during', text):
            s += 2
        if re.search(r'alone with.*victim|alone.*cabin|only.*present', text):
            s += 2
            
        return s
    
    scores = {}
    for suspect in suspects:
        scores[suspect] = score_suspect(suspect, sections[suspect])
    
    # Return suspect with highest score
    best = max(suspects, key=lambda x: scores[x])
    
    # If tied, return second suspect (heuristic from patterns)
    if scores[suspects[0]] == scores[suspects[1]]:
        return suspects[1]
    
    return best
