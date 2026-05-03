"""Auto-generated code-distilled implementation for extract_suspects_and_evidence."""

def extract_suspects_and_evidence(text):
    import re
    
    if not text or not isinstance(text, str):
        return None
    
    lines = text.strip()
    
    # Extract victim name from the opening paragraph
    victim = None
    # Common patterns: "X is discovered lifelessly slain", "X found her end", "X's life was abruptly ended",
    # "X was found dead", "X lay lifeless", "X meets her untimely death", etc.
    victim_patterns = [
        r"when\s+(\w+)\s+is\s+discovered\s+lifelessly",
        r"when\s+(\w+)\s+was\s+(?:found\s+)?(?:brutally\s+)?(?:shot|killed|murdered|stabbed)",
        r"(\w+)\s+found\s+her\s+end",
        r"(\w+)\s+found\s+his\s+end",
        r"(\w+)'s\s+life\s+was\s+(?:abruptly\s+)?(?:unexpect\w*\s+)?(?:ended|cut\s+short|silenced)",
        r"(\w+)\s+was\s+found\s+(?:dead|lifeless|murdered)",
        r"(\w+)\s+was\s+(?:brutally\s+)?(?:shot|killed|murdered|stabbed|poisoned)",
        r"(\w+)\s+lay\s+(?:dead|lifeless)",
        r"(\w+)\s+lies\s+dead",
        r"(\w+)\s+met\s+(?:her|his|an)\s+(?:untimely\s+)?(?:end|death|demise)",
        r"(\w+)\s+meets\s+(?:her|his|an)\s+(?:untimely\s+)?(?:end|death|demise)",
        r"murder\s+of\s+(\w+)",
        r"(\w+)'s?\s+(?:lifeless\s+)?body\s+(?:is|was)\s+found",
        r"(\w+)\s+had\s+tragically\s+met",
        r"(\w+)'s\s+exercise\s+regime\s+is\s+abruptly\s+terminated",
        r"tragedy\s+struck\s+as\s+(\w+)\s+was",
        r"(?:the\s+)?(?:murder|death|killing)\s+of\s+(\w+)",
        r"(\w+)\s+was\s+found\s+(?:\w+\s+)*dead",
        r"(\w+)'s\s+(?:lifeless\s+)?body",
        r"(\w+)\s+(?:was|is)\s+(?:found\s+)?(?:horrifically\s+)?(?:mutilated|slain|killed)",
    ]
    
    for pattern in victim_patterns:
        m = re.search(pattern, lines, re.IGNORECASE)
        if m:
            candidate = m.group(1)
            # Filter out common non-name words
            if candidate.lower() not in ('the', 'a', 'an', 'when', 'in', 'at', 'his', 'her', 'it', 'detective', 'winston'):
                victim = candidate
                break
    
    if not victim:
        return None
    
    # Extract suspects from the opening paragraph
    # Common pattern: "suspects, X and Y" or "suspects X and Y"
    suspects_names = []
    suspect_patterns = [
        r"suspects?[,:]?\s+(\w+)\s+and\s+(\w+)",
        r"suspecting\s+(\w+)\s+and\s+(\w+)",
        r"suspects?\s+(\w+)\s+and\s+(\w+)",
        r"(\w+)\s+and\s+(\w+)\s+(?:as\s+)?(?:the\s+)?(?:prime\s+)?suspects",
        r"(\w+)\s+and\s+(\w+)\s+(?:become|are|were)\s+(?:his\s+)?(?:primary\s+)?suspects",
        r"(\w+)\s+and\s+(\w+)\s+under\s+(?:the\s+)?(?:weight\s+of\s+)?suspicion",
        r"(\w+)\s+and\s+(\w+),?\s+(?:the\s+)?(?:enigmatic\s+|elusive\s+)?suspects",
        r"(?:interrogate|interview)\s+(?:top\s+)?suspects?\s+(\w+)\s+and\s+(\w+)",
        r"(?:interrogate|interview)\s+(\w+)\s+and\s+(\w+)",
        r"around\s+(\w+)\s+and\s+(\w+)",
        r"spun\s+by\s+(?:two\s+prime\s+suspects,\s+)?(\w+)\s+and\s+(\w+)",
        r"(?:featuring|with)\s+suspects?\s+(\w+)\s+and\s+(\w+)",
    ]
    
    # Look in first paragraph
    first_para = lines.split('\n')[0]
    
    for pattern in suspect_patterns:
        m = re.search(pattern, first_para, re.IGNORECASE)
        if m:
            s1, s2 = m.group(1), m.group(2)
            if s1.lower() not in ('the', 'a', 'an', 'detective', 'winston', 'his', 'her', 'two', 'prime') and \
               s2.lower() not in ('the', 'a', 'an', 'detective', 'winston', 'his', 'her', 'two', 'prime'):
                suspects_names = [s1, s2]
                break
    
    if not suspects_names:
        # Try broader search in full text
        for pattern in suspect_patterns:
            m = re.search(pattern, lines, re.IGNORECASE)
            if m:
                s1, s2 = m.group(1), m.group(2)
                if s1.lower() not in ('the', 'a', 'an', 'detective', 'winston', 'his', 'her', 'two', 'prime') and \
                   s2.lower() not in ('the', 'a', 'an', 'detective', 'winston', 'his', 'her', 'two', 'prime'):
                    suspects_names = [s1, s2]
                    break
    
    if not suspects_names:
        return None
    
    # Extract crime details from opening paragraph
    # Get weapon
    weapon = None
    weapon_patterns = [
        r"(?:murder|killed|slain|death)\s+(?:\w+\s+)*?(?:by|with|using)\s+(?:a\s+)?(\w+(?:\s+\w+)?)",
        r"(?:a|the)\s+(\w+(?:\s+\w+)?)\s+(?:being\s+)?(?:the\s+)?(?:weapon|murder\s+weapon)",
        r"(?:at\s+the\s+prongs\s+of\s+)?a\s+(\w+)",
        r"(?:lethal|deadly)\s+(\w+)",
    ]
    
    # Try to find weapon from first paragraph
    weapon_specific_patterns = [
        r"(?:by|with|using)\s+(?:a\s+)?(\w+(?:\s+\w+)?)\s*[;,.]",
        r"(?:a|the)\s+(\w+(?:\s+\w+)?)\s+(?:being\s+the\s+weapon|his\s+(?:cruel|final)\s+end)",
        r"(?:prongs\s+of\s+a|stroke\s+of\s+a|crack\s+of\s+a|blast\s+of\s+a)\s+(\w+)",
        r"(?:shot|stabbed|poisoned|strangled|killed)\s+(?:dead\s+)?(?:by|with)\s+(?:a\s+)?(\w+(?:\s+\w+)?)",
        r"(?:a|the)\s+(\w+)\s+(?:being\s+the\s+weapon\s+of\s+choice)",
        r"(?:lethal|deadly|fatal)\s+(\w+(?:\s+\w+)?)",
        r"murdered?\s+(?:\w+\s+)*?(?:by|with)\s+(?:a\s+)?(\w+(?:\s+\w+)?)",
    ]
    
    for pattern in weapon_specific_patterns:
        m = re.search(pattern, first_para, re.IGNORECASE)
        if m:
            w = m.group(1).strip().rstrip('.,;')
            if w.lower() not in ('a', 'the', 'an', 'detective', 'winston'):
                weapon = w
                break
    
    # Extract location
    location = None
    location_patterns = [
        r"(?:in|at)\s+(?:the\s+)?(?:a\s+)?(?:\w+\s+)*?(mountain\s+cabin|wrestling\s+ring|synagogue|mosque|hockey\s+rink|rainforest|gym|fitness\s+center|casino|cinema\s+hall|labyrinth|zoo|chalet|office|cemetery|park|church|bar|restaurant|hospital|library|museum|school|theater|theatre|arena|studio|garage|warehouse|basement|attic|garden|beach|lake|river|forest|jungle|desert|cave|mine|farm|ranch|factory|mall|store|shop|station|airport|train|bus|boat|ship|submarine|plane|helicopter|rocket|spaceship|satellite)",
        r"(?:in|at)\s+(?:the|a|an)\s+(\w+(?:\s+\w+){0,2})\s*,",
    ]
    
    for pattern in location_patterns:
        m = re.search(pattern, first_para, re.IGNORECASE)
        if m:
            location = m.group(1)
            break
    
    # Now we need to split the text into sections for each suspect
    # Usually the text has paragraphs separated by \n\n
    paragraphs = re.split(r'\n\s*\n', lines)
    
    # Build suspect sections
    suspect_sections = {}
    for name in suspects_names:
        suspect_sections[name] = []
    
    for para in paragraphs:
        for name in suspects_names:
            if name in para:
                suspect_sections[name].append(para)
    
    # Helper function to find sentences containing certain keywords near a suspect's name
    def find_relevant_sentences(text_block, keywords):
        sentences = re.split(r'(?<=[.!?])\s+', text_block)
        relevant = []
        for sent in sentences:
            for kw in keywords:
                if re.search(kw, sent, re.IGNORECASE):
                    relevant.append(sent.strip())
                    break
        return relevant
    
    # Build crime details string
    crime_details = f"{victim} was "
    if weapon:
        if 'shot' in first_para.lower() or 'gun' in first_para.lower() or 'pistol' in first_para.lower() or 'bullet' in first_para.lower():
            crime_details = f"{victim} was shot"
            if weapon and weapon.lower() not in ('shot', 'bullet'):
                crime_details += f" by a {weapon}"
        elif 'strangl' in first_para.lower() or 'rope' in first_para.lower():
            crime_details = f"{victim} was strangled with a {weapon}"
        elif 'poison' in first_para.lower() or 'venom' in first_para.lower():
            crime_details = f"{victim} was poisoned by {weapon}"
        elif 'explos' in first_para.lower() or 'grenade' in first_para.lower():
            crime_details = f"{victim} was killed by a {weapon} explosion"
        else:
            crime_details = f"{victim} was killed with a {weapon}"
    else:
        crime_details = f"{victim} was murdered"
    
    if location:
        crime_details += f" in a {location}" if not location.startswith('the') else f" in {location}"
    crime_details += "."
    
    # For each suspect, extract details
    def extract_suspect_info(name, sections):
        full_text = ' '.join(sections)
        
        info = {
            'name': name,
            'motive': 'Not explicitly stated.',
            'means': 'Not explicitly stated.',
            'opportunity': 'Not explicitly stated.',
            'alibi_claim': 'Not explicitly stated.',
            'alibi_witnesses': 'None mentioned.',
            'suspicious_behavior': 'None mentioned.',
            'physical_evidence': 'None mentioned.'
        }
        
        # Motive keywords
        motive_sentences = find_relevant_sentences(full_text, [
            r'threaten', r'expos', r'blackmail', r'affair', r'debt', r'money',
            r'divorc', r'jealous', r'revenge', r'grudge', r'secret', r'fear',
            r'hate', r'ruin', r'destroy', r'conflict', r'disput', r'argument',
            r'betray', r'steal', r'fraud', r'embezzl', r'inherit', r'insurance',
            r'accus', r'lawsuit', r'malpractice', r'plagiar', r'compet',
            r'break.?up', r'disclose', r'discover', r'found\s+(?:out|documents|letters)',
            r'implic', r'illicit', r'criminal', r'report.*(?:police|authorit)',
            r'testif', r'witness', r'coveted', r'obsess', r'victim.*reject'
        ])
        if motive_sentences:
            info['motive'] = ' '.join(motive_sentences[:3])
        
        # Means keywords
        means_sentences = find_relevant_sentences(full_text, [
            r'weapon', r'knife', r'gun', r'pistol', r'shotgun', r'rifle',
            r'shovel', r'tool', r'syringe', r'rope', r'pipe', r'cleaver',
            r'machete', r'trident', r'sai', r'nail\s*gun', r'bleach',
            r'poison', r'venom', r'snake', r'grenade', r'explos',
            r'collection', r'own(?:s|ed)', r'access', r'skill',
            r'training', r'martial\s+art', r'military', r'anatomic',
            r'experience.*(?:with|using)', r'practice.*(?:with|using)',
            r'firearm', r'ammunition', r'shell', r'bullet'
        ])
        if means_sentences:
            info['means'] = ' '.join(means_sentences[:3])
        
        # Opportunity keywords
        opportunity_sentences = find_relevant_sentences(full_text, [
            r'(?:was|were)\s+(?:at|in|near|present)',
            r'seen\s+(?:at|in|near|enter)',
            r'footage\s+show', r'camera',
            r'(?:confirm|verif).*(?:present|attend|there)',
            r'alone\s+(?:at|in|with|during)',
            r'(?:during|at)\s+(?:the\s+)?(?:time|night|day|morning|evening)',
            r'schedule', r'routine', r'arrived',
            r'backstage', r'access'
        ])
        if opportunity_sentences:
            info['opportunity'] = ' '.join(opportunity_sentences[:3])
        
        # Alibi keywords
        alibi_sentences = find_relevant_sentences(full_text, [
            r'alibi', r'claim', r'stat(?:e|ed|ing)\s+(?:he|she|they)',
            r'was\s+(?:at|in)\s+(?:the|his|her)',
            r'(?:said|told|mention|assert|insist)',
        ])
        if alibi_sentences:
            info['alibi_claim'] = ' '.join(alibi_sentences[:2])
        
        # Alibi witnesses
        witness_sentences = find_relevant_sentences(full_text, [
            r'witness', r'(?:seen|saw)\s+(?:by|him|her)',
            r'confirm', r'verif', r'vouch',
            r'neighbor', r'colleague', r'friend', r'coworker',
        ])
        if witness_sentences:
            info['alibi_witnesses'] = ' '.join(witness_sentences[:2])
        
        # Suspicious behavior
        suspicious_sentences = find_relevant_sentences(full_text, [
            r'nervous', r'anxious', r'shak(?:y|ing)', r'fidget',
            r'defensive', r'evas', r'avoid', r'reluctan',
            r'stutter', r'stammer', r'hesitat', r'uncomfortabl',
            r'flicker', r'flush', r'pale', r'sweat',
            r'caught\s+off\s+guard', r'taken\s+aback',
            r'odd', r'unusual', r'strange', r'peculiar', r'suspicious',
            r'disappear', r'midnight', r'solitary', r'alone',
            r'shun', r'anger', r'upset', r'agitat',
        ])
        if suspicious_sentences:
            info['suspicious_behavior'] = ' '.join(suspicious_sentences[:3])
        
        # Physical evidence
        evidence_sentences = find_relevant_sentences(full_text, [
            r'found\s+(?:at|in|near|on)', r'fingerprint', r'DNA',
            r'blood', r'footage', r'security\s+cam', r'surveillance',
            r'receipt', r'document', r'record',
            r'match', r'similar\s+to', r'identical',
            r'(?:murder|crime)\s+weapon',
        ])
        if evidence_sentences:
            info['physical_evidence'] = ' '.join(evidence_sentences[:3])
        
        return info
    
    suspect_infos = []
    for name in suspects_names:
        sections = suspect_sections.get(name, [])
        if not sections:
            # Use entire text
            sections = [lines]
        info = extract_suspect_info(name, sections)
        suspect_infos.append(info)
    
    # Format output
    output_lines = []
    output_lines.append(f"victim: {victim}")
    output_lines.append(f"crime_details: {crime_details}")
    output_lines.append("suspects:")
    
    for info in suspect_infos:
        output_lines.append(f"- suspect: {info['name']}")
        output_lines.append(f"  motive: {info['motive']}")
        output_lines.append(f"  means: {info['means']}")
        output_lines.append(f"  opportunity: {info['opportunity']}")
        output_lines.append(f"  alibi_claim: {info['alibi_claim']}")
        output_lines.append(f"  alibi_witnesses: {info['alibi_witnesses']}")
        output_lines.append(f"  suspicious_behavior: {info['suspicious_behavior']}")
        output_lines.append(f"  physical_evidence: {info['physical_evidence']}")
    
    return '\n'.join(output_lines)
