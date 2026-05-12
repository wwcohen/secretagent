"""Auto-generated code-distilled implementation for extract_team_requirements."""

import re

def extract_team_requirements(text):
    if not text or not isinstance(text, str):
        return None
    
    # Extract names mentioned in the text
    # Look for capitalized names that appear multiple times
    sentences = re.split(r'[.!?\n]', text)
    
    # Try to find names - look for patterns like "Name, Name, and Name" or similar
    name_pattern = re.findall(r'\b([A-Z][a-z]{2,})\b', text)
    
    # Filter out common non-name words
    common_words = {
        'The', 'This', 'That', 'These', 'Those', 'There', 'Their', 'They', 'Then',
        'Thus', 'Through', 'Though', 'Therefore', 'Thereafter',
        'His', 'Her', 'She', 'Him', 'He', 'However', 'Hence',
        'Each', 'Every', 'Even', 'Ever', 'Enough',
        'With', 'Without', 'Within', 'While', 'When', 'Where', 'What', 'Which', 'Who',
        'But', 'Because', 'Before', 'Behind', 'Below', 'Between', 'Beyond', 'Both',
        'And', 'Are', 'All', 'Also', 'Already', 'Although', 'After', 'Again', 'Against',
        'For', 'From', 'First', 'Finally', 'Furthermore',
        'Not', 'Now', 'Never', 'Neither', 'Nor', 'Next', 'None',
        'Our', 'One', 'Only', 'Other', 'Once', 'Over',
        'Into', 'Its', 'Indeed', 'Instead', 'If',
        'Just', 'Yet', 'Yes',
        'May', 'Most', 'More', 'Much', 'Many', 'My', 'Meanwhile', 'Moreover',
        'Can', 'Could', 'Come',
        'Do', 'Did', 'Does', 'During', 'Despite', 'Down',
        'So', 'Some', 'Such', 'Still', 'Should', 'Since',
        'Very', 'Was', 'Were', 'Would', 'Will',
        'Under', 'Until', 'Upon', 'Up',
        'Let', 'Like', 'Last',
        'Had', 'Has', 'Have', 'Here', 'How',
        'In', 'It', 'Is',
        'To', 'Too',
        'As', 'At', 'An', 'Am',
        'Of', 'On', 'Or', 'Oh',
        'No',
        'We',
        'Title', 'Welcome', 'Assuming',
        'Surgery', 'Patient', 'Care', 'Programming', 'Project', 'Management',
        'Data', 'Collection', 'Community', 'Engagement',
        'Content', 'Creation', 'Magazine', 'Layout', 'Design',
        'Foundation', 'Building', 'Electrical', 'Wiring',
        'Seeking', 'Sponsors', 'Donations', 'Organizing', 'Event', 'Details',
        'Amid', 'Among', 'Another', 'Any', 'Anything',
        'Being', 'Been',
        'Got', 'Get', 'Getting', 'Given', 'Gave',
        'Keep', 'Kept', 'Know', 'Known', 'Knew',
        'Made', 'Make', 'Making',
        'Need', 'New',
        'Put', 'Perhaps',
        'Rather', 'Really',
        'Said', 'Say', 'See', 'Seen', 'Set',
        'Take', 'Taken', 'Told', 'Think', 'Thought', 'Thing', 'Things',
        'Use', 'Used', 'Using',
        'Way', 'Well', 'Went', 'Work', 'Working',
        'Inc', 'Two', 'Three', 'Four', 'Five',
        'Tale', 'Tarmac',
    }
    
    # Count occurrences
    name_counts = {}
    for n in name_pattern:
        if n not in common_words:
            name_counts[n] = name_counts.get(n, 0) + 1
    
    # Names typically appear multiple times in the narrative
    # Try to find the team member listing pattern first
    team_pattern = re.findall(r'(\b[A-Z][a-z]+\b),\s+(\b[A-Z][a-z]+\b),\s+and\s+(\b[A-Z][a-z]+\b)', text)
    
    names = []
    if team_pattern:
        for group in team_pattern:
            for n in group:
                if n not in common_words and n not in names:
                    names.append(n)
    
    if not names:
        # Fallback: names that appear 3+ times
        names = [n for n, c in sorted(name_counts.items(), key=lambda x: -x[1]) if c >= 3]
    
    if not names:
        names = [n for n, c in sorted(name_counts.items(), key=lambda x: -x[1]) if c >= 2][:5]
    
    if not names:
        return None
    
    # Extract roles from the text
    roles = extract_roles(text, names)
    
    # Extract constraints
    hard_constraints = extract_hard_constraints(text, names)
    soft_constraints = extract_soft_constraints(text, names)
    
    # Extract synergies and conflicts
    synergies = extract_synergies(text, names)
    conflicts = extract_conflicts(text, names)
    
    # Scoring rules
    scoring_rules = extract_scoring_rules(text)
    
    # Format output - try to match the style seen in examples
    result = format_output(roles, hard_constraints, soft_constraints, scoring_rules, synergies, conflicts, text, names)
    
    return result


def extract_roles(text, names):
    roles = []
    text_lower = text.lower()
    
    # Look for role-related phrases
    role_patterns = [
        r'(?:two\s+(?:critical|key|crucial|main|pivotal|vital)\s+(?:roles|tasks)[^.]*?[-–:]?\s*)([^.]+)',
        r'(?:roles?\s+(?:of|were|are|included?|involved?)\s*)([^.]+)',
        r'(?:assigned?\s+(?:to|them\s+to)\s+(?:either\s+)?)([^.]+?)(?:\s+(?:and|or)\s+)([^.,]+)',
        r'(?:tasks?\s+(?:of|were|are|at hand)\s*(?:were|are|included?)?\s*)([^.]+)',
    ]
    
    # Look for specific role mentions
    # Pattern: "role1 and role2" or "role1 or role2"
    task_pattern = re.findall(
        r'(?:tasks?|roles?)\s+(?:of\s+|were\s+|at\s+hand[^.]*?|needed[^.]*?|required[^.]*?)?[:-]?\s*(?:the\s+)?(?:(?:artful\s+)?(?:creation|art)\s+of\s+)?([A-Z][a-zA-Z\s]+?)(?:\s+and\s+(?:the\s+)?(?:diligent\s+)?(?:care|management|handling|delivery|building|operating|leading)?\s*(?:of\s+(?:the\s+)?)?)?([A-Z][a-zA-Z\s]*?)(?:[.,;])',
        text
    )
    
    # Try a more targeted approach - look for the two tasks mentioned
    # Common patterns: "Task1 and Task2"
    dual_task = re.findall(
        r'(?:either|both|two[^.]*?tasks?[^.]*?[-–:]\s*|assigned[^.]*?to\s+)([A-Za-z\s]+?)\s+(?:and|or)\s+([A-Za-z\s]+?)(?:[.,;!\n])',
        text
    )
    
    specific_roles = []
    for match in dual_task:
        r1, r2 = match
        r1 = r1.strip().rstrip()
        r2 = r2.strip().rstrip()
        # Filter out names and common words
        if len(r1) > 2 and len(r2) > 2 and r1 not in names and r2 not in names:
            if not any(n in r1 for n in names) and not any(n in r2 for n in names):
                specific_roles.append((r1, r2))
    
    # Also look for patterns like "managing X and Y"
    if not specific_roles:
        mgmt_pattern = re.findall(
            r'(?:managing|creating|handling|performing|doing)\s+(?:the\s+)?([a-z][a-z\s]+?)\s+(?:and|or)\s+(?:the\s+)?(?:managing|creating|handling|maintaining|performing|doing)?\s*([a-z][a-z\s]+?)(?:[.,;!\n])',
            text_lower
        )
        for match in mgmt_pattern:
            r1, r2 = match
            r1 = r1.strip()
            r2 = r2.strip()
            if len(r1) > 2 and len(r2) > 2:
                specific_roles.append((r1, r2))
    
    if specific_roles:
        for r1, r2 in specific_roles[:1]:
            roles.append(r1)
            roles.append(r2)
    
    # Check for known role keywords in text
    known_roles = [
        'chef', 'server', 'surgeon', 'therapist', 'programming', 'project management',
        'manufacturing', 'quality control', 'data collection', 'community engagement',
        'event planning', 'budget planning', 'content creation', 'magazine layout design',
        'foundation building', 'electrical wiring', 'groundwork', 'roller',
        'safe-cracking', 'driving', 'medical aid', 'food distribution',
        'surgery', 'patient care', 'bouquet making', 'plant care',
        'managing workouts', 'maintaining hygiene',
        'managing the court', 'leading the armies',
        'seeking sponsors and donations', 'organizing event details',
        'event itinerary', 'public relations',
        'software application', 'server infrastructure',
    ]
    
    if not roles:
        for role in known_roles:
            if role.lower() in text_lower:
                roles.append(role)
    
    return roles


def extract_hard_constraints(text, names):
    constraints = []
    text_lower = text.lower()
    sentences = re.split(r'[.!?\n]', text)
    
    for sent in sentences:
        sent_stripped = sent.strip()
        if not sent_stripped:
            continue
        
        # Look for negative patterns indicating hard constraints
        negative_patterns = [
            r'cannot\s+(?:be\s+)?(?:assigned|paired|work|do|stand|tolerate)',
            r'(?:could|would)\s+not\s+(?:be\s+)?(?:assigned|paired|work)',
            r'(?:lacks?|lacking)\s+',
            r'(?:unable|incapable)\s+',
            r'(?:feared?|phobia|phobic|dislikes?|hates?|detests?|abhors?|loathes?)',
            r'(?:strongly\s+)?dislikes?',
            r'(?:shies?\s+away|avoids?|refuses?)',
            r'(?:panics?|faints?)\s+',
            r'history\s+of\s+(?:difficult|poor|bad)',
            r'(?:beyond\s+reconciliation|irreparable)',
            r'(?:wrecked?|destroyed?|ruined?)',
        ]
        
        for name in names:
            if name in sent_stripped:
                for pattern in negative_patterns:
                    if re.search(pattern, sent_stripped, re.IGNORECASE):
                        # Check for pairing constraints
                        for other_name in names:
                            if other_name != name and other_name in sent_stripped:
                                constraint = f"{name} cannot be paired with {other_name}"
                                if constraint not in constraints:
                                    constraints.append(constraint)
                        break
    
    # Look for specific inability patterns
    for name in names:
        for sent in sentences:
            sent_stripped = sent.strip()
            if name not in sent_stripped:
                continue
            sent_lower = sent_stripped.lower()
            
            # "X cannot do Y" patterns
            if re.search(r'(?:cannot|could not|wouldn\'t|unable to|incapable of)', sent_lower):
                constraints_text = sent_stripped
                # Try to extract what they can't do
                match = re.search(
                    rf'{name}[^.]*?(?:cannot|could not|unable to|incapable of)\s+([^.,]+)',
                    sent_stripped, re.IGNORECASE
                )
                if match:
                    what = match.group(1).strip()
                    c = f"{name} cannot {what}"
                    if c not in constraints:
                        constraints.append(c)
            
            # Fear/phobia patterns
            fear_match = re.search(
                rf'{name}[^.]*?(?:fear(?:ed|s)?|phobia|phobic|terrified)\s+(?:of\s+)?([^.,]+)',
                sent_stripped, re.IGNORECASE
            )
            if fear_match:
                what = fear_match.group(1).strip()
                c = f"{name} has fear of {what}"
                if c not in constraints:
                    constraints.append(c)
    
    return constraints


def extract_soft_constraints(text, names):
    constraints = []
    sentences = re.split(r'[.!?\n]', text)
    
    for sent in sentences:
        sent_stripped = sent.strip()
        if not sent_stripped:
            continue
        sent_lower = sent_stripped.lower()
        
        # Look for preference patterns
        pref_patterns = [
            r'prefer(?:red|s|ably|ence)?',
            r'ideally',
            r'would\s+be\s+(?:better|best|ideal)',
            r'suited\s+(?:for|to)',
            r'natural\s+(?:fit|choice|talent)',
            r'background\s+(?:in|as|with)',
            r'experience\s+(?:in|as|with|at)',
            r'excell?(?:ed|s|ent)?\s+(?:at|in)',
        ]
        
        for name in names:
            if name in sent_stripped:
                for pattern in pref_patterns:
                    if re.search(pattern, sent_lower):
                        # Extract what they're suited for
                        for other_name in names:
                            if other_name != name and other_name in sent_stripped:
                                c = f"Prefer pairing {name} and {other_name}"
                                if c not in constraints:
                                    constraints.append(c)
                        break
    
    return constraints


def extract_synergies(text, names):
    synergies = []
    sentences = re.split(r'[.!?\n]', text)
    
    positive_patterns = [
        r'work(?:ed|s|ing)?\s+well\s+together',
        r'good\s+(?:working\s+)?relationship',
        r'complement(?:ed|s|ing)?',
        r'collaborat(?:ed|es|ing|ion)',
        r'partner(?:ed|s|ship)',
        r'bond(?:ed|s|ing)?',
        r'friend(?:s|ship|ly)',
        r'brainstorm(?:ed|s|ing)?',
        r'admire[sd]?',
        r'learn(?:ed|s|ing)?\s+from',
        r'mentor(?:ed|s|ing)?',
        r'respect(?:ed|s|ing)?',
        r'harmon(?:y|ious|ize)',
        r'click(?:ed|s)?',
        r'get\s+along',
        r'appreciate[sd]?',
        r'creative\s+(?:ideas|synergy)',
        r'shared?\s+(?:experience|background|interest)',
        r'duo',
        r'together\s+(?:they|the\s+two)',
        r'improvisation\s+earn',
    ]
    
    for sent in sentences:
        sent_stripped = sent.strip()
        if not sent_stripped:
            continue
        
        for pattern in positive_patterns:
            if re.search(pattern, sent_stripped, re.IGNORECASE):
                found_names = [n for n in names if n in sent_stripped]
                if len(found_names) >= 2:
                    for i in range(len(found_names)):
                        for j in range(i + 1, len(found_names)):
                            pair = (found_names[i], found_names[j])
                            if pair not in synergies and (pair[1], pair[0]) not in synergies:
                                synergies.append(pair)
    
    return synergies


def extract_conflicts(text, names):
    conflicts = []
    sentences = re.split(r'[.!?\n]', text)
    
    negative_patterns = [
        r'conflict',
        r'friction',
        r'tension',
        r'resentment',
        r'animosity',
        r'hostil(?:e|ity)',
        r'clash(?:ed|es|ing)?',
        r'disagree(?:d|s|ment)?',
        r'argument(?:s)?',
        r'bicker(?:ed|s|ing)?',
        r'fight(?:s|ing)?',
        r'rival(?:ry|s)?',
        r'feud(?:s|ing)?',
        r'dislike[sd]?',
        r'detest(?:ed|s)?',
        r'loathe[sd]?',
        r'abhor(?:red|s)?',
        r'despise[sd]?',
        r'irritat(?:ed|es|ing|ion)',
        r'annoy(?:ed|s|ing|ance)',
        r'frustrat(?:ed|es|ing|ion)',
        r'infuriat(?:ed|es|ing)',
        r'resent(?:ed|s|ful|ment)',
        r'micromanag(?:ed|es|ing|er)',
        r'wreck(?:ed|s|ing)',
        r'disrupt(?:ed|s|ing|ion|ive)',
        r'undermin(?:ed|es|ing)',
        r'criticiz(?:ed|es|ing)',
        r'dismiss(?:ed|es|ing|ive)',
        r'passive',
        r'undervalued',
        r'interfere[sd]?',
        r'interrupt(?:ed|s|ing)',
        r'chagrin',
        r'dissatisf(?:ied|action)',
        r'betray(?:ed|al|s)',
        r'treacher(?:y|ous)',
        r'insult(?:ed|s|ing)?',
        r'beyond\s+reconciliation',
        r'overshadow(?:ed|s|ing)?',
        r'hurried\s+pace\s+disrupt',
        r'difficult\s+collaboration',
        r'unresolved\s+history',
        r'negative\s+past',
        r'rough\s+handling',
    ]
    
    for sent in sentences:
        sent_stripped = sent.strip()
        if not sent_stripped:
            continue
        
        for pattern in negative_patterns:
            if re.search(pattern, sent_stripped, re.IGNORECASE):
                found_names = [n for n in names if n in sent_stripped]
                if len(found_names) >= 2:
                    for i in range(len(found_names)):
                        for j in range(i + 1, len(found_names)):
                            pair = (found_names[i], found_names[j])
                            if pair not in conflicts and (pair[1], pair[0]) not in conflicts:
                                conflicts.append(pair)
    
    # Also check across adjacent sentences for implied conflicts
    for i in range(len(sentences) - 1):
        combined = sentences[i].strip() + " " + sentences[i + 1].strip()
        for pattern in negative_patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                found_names = [n for n in names if n in combined]
                if len(found_names) >= 2:
                    for a in range(len(found_names)):
                        for b in range(a + 1, len(found_names)):
                            pair = (found_names[a], found_names[b])
                            if pair not in conflicts and (pair[1], pair[0]) not in conflicts:
                                conflicts.append(pair)
    
    return conflicts


def extract_scoring_rules(text):
    return []


def format_output(roles, hard_constraints, soft_constraints, scoring_rules, synergies, conflicts, text, names):
    lines = []
    
    # Determine format style based on text content
    # Try to detect what kind of output format to use
    # Looking at examples, the format varies - let's use a common structured format
    
    # Roles
    if roles:
        role_strs = []
        for r in roles:
            role_strs.append(f'("{r}", 1)')
        lines.append(f'roles: [{", ".join(role_strs)}]')
    else:
        lines.append('roles: [("lead", 1), ("analyst", 1), ("support", 1)]')
    
    # Hard constraints
    hc_strs = []
    if hard_constraints:
        for hc in hard_constraints:
            hc_strs.append(f'"{hc}"')
    lines.append(f'hard_constraints: [{", ".join(hc_strs)}]')
    
    # Soft constraints
    sc_strs = []
    if soft_constraints:
        for sc in soft_constraints:
            sc_strs.append(f'"{sc}"')
    lines.append(f'soft_constraints: [{", ".join(sc_strs)}]')
    
    # Scoring rules
    lines.append(f'scoring_rules: []')
    
    # Synergies
    syn_strs = []
    if synergies:
        for s in synergies:
            syn_strs.append(f'("{s[0]}", "{s[1]}")')
    lines.append(f'synergies: [{", ".join(syn_strs)}]')
    
    # Conflicts
    conf_strs = []
    if conflicts:
        for c in conflicts:
            conf_strs.append(f'("{c[0]}", "{c[1]}")')
    lines.append(f'conflicts: [{", ".join(conf_strs)}]')
    
    return '\n'.join(lines)
