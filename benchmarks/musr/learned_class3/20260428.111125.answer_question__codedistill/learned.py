"""Auto-generated code-distilled implementation for answer_question."""

def answer_question(story, question, choices):
    import re
    
    if question != 'Who is the most likely murderer?':
        return None
    
    if len(choices) != 2:
        return None
    
    story_lower = story.lower()
    
    # Split the story into sections for each suspect
    # Each suspect typically has their own narrative section
    
    def count_evidence(text, suspect_name):
        text_lower = text.lower()
        name_lower = suspect_name.lower()
        score = 0
        
        # Strong motive indicators
        motive_phrases = [
            'threaten', 'blackmail', 'expose', 'reveal', 'secret',
            'fear', 'afraid', 'desperate', 'losing', 'lose',
            'affair', 'jealous', 'revenge', 'anger', 'angry',
            'criminal', 'illegal', 'stolen', 'theft', 'steal',
            'reputation', 'ruin', 'destroy', 'incriminate',
            'evidence against', 'discovered', 'found out',
            'financial', 'debt', 'loan', 'money', 'inherit',
            'insurance', 'payout', 'will', 'estate',
            'plagiariz', 'humiliat', 'embarrass',
            'prison', 'jail', 'arrest', 'police',
            'conflict', 'argument', 'quarrel', 'dispute',
            'leaked', 'betray', 'disclose',
            'serial killer', 'past victims', 'similar incidents',
            'criminal record', 'report to the authorities',
        ]
        
        # Opportunity indicators  
        opportunity_phrases = [
            'alone', 'only one', 'no one else', 'nobody else',
            'present during', 'was there', 'at the scene',
            'same time', 'at the time', 'during the murder',
            'private', 'soundproof', 'no security camera',
            'no witnesses', 'solitary', 'exclusive access',
            'only staff', 'only.*on duty', 'keys to',
            'scheduled', 'appointment',
        ]
        
        # Means indicators
        means_phrases = [
            'murder weapon', 'weapon of choice', 'identified as the murder',
            'collection', 'owned', 'carried', 'brought',
            'skill', 'trained', 'practice', 'experienced',
            'familiar', 'knowledge', 'expertise',
            'permit', 'license',
            'extract poison', 'poison', 'acid', 'bleach',
            'shotgun', 'machete', 'hatchet', 'sickle', 'crossbow',
            'hunting knife', 'nunchaku',
        ]
        
        # Behavioral guilt indicators
        guilt_phrases = [
            'nervous', 'stuttered', 'stammer', 'pale', 'paler',
            'agitated', 'uncomfortable', 'anxious', 'evasive',
            'darting', 'avoided', 'avoiding', 'fidget',
            'sweat', 'shaky', 'crumbling',
            'confessed', 'admitted', 'conceded',
            'worst nightmare', 'can\'t go to jail',
            'desperate', 'distress',
        ]
        
        for phrase in motive_phrases:
            score += len(re.findall(phrase, text_lower)) * 3
            
        for phrase in opportunity_phrases:
            score += len(re.findall(phrase, text_lower)) * 2
            
        for phrase in means_phrases:
            score += len(re.findall(phrase, text_lower)) * 2
            
        for phrase in guilt_phrases:
            score += len(re.findall(phrase, text_lower)) * 2
        
        # Check for specific strong patterns
        # "was the murder weapon" near suspect's belongings
        if re.search(r'murder weapon', text_lower):
            score += 5
        
        # Being at the crime scene alone
        if re.search(r'(only|alone|no one else|nobody else)', text_lower):
            score += 3
            
        # Direct threat from victim
        if re.search(r'(threaten|blackmail|expos|reveal).{0,100}(secret|illegal|criminal|reputation|career|affair)', text_lower):
            score += 8
            
        # Victim discovered something about suspect
        if re.search(r'(discover|found out|learn|noticed).{0,100}(illegal|criminal|theft|steal|plagiari|affair|secret)', text_lower):
            score += 8
            
        # Serial killer indicators
        if re.search(r'serial killer', text_lower):
            score += 10
        if re.search(r'similar (incidents|circumstances|cases)', text_lower):
            score += 8
        if re.search(r'past victims', text_lower):
            score += 8
        if re.search(r'previous investigations', text_lower):
            score += 5
            
        # Exclusive access / keys
        if re.search(r'(only|exclusive).{0,30}(key|access)', text_lower):
            score += 5
            
        # Found at crime scene with weapon
        if re.search(r'(equipment|gear).{0,50}(found at|crime scene|murder site)', text_lower):
            score += 5
        if re.search(r'(crime scene|murder site).{0,50}(equipment|gear|found)', text_lower):
            score += 5
            
        return score
    
    # Try to split the story by suspect narratives
    # Stories typically have two main sections, one per suspect
    
    def find_suspect_sections(story, choices):
        """Split story into sections most relevant to each suspect"""
        sections = {}
        
        # Try splitting by paragraph breaks that signal new investigation
        paragraphs = story.split('\n\n')
        
        for i, choice in enumerate(choices):
            sections[i] = ""
        
        # Assign paragraphs to suspects based on which name appears more
        for para in paragraphs:
            para_lower = para.lower()
            counts = []
            for choice in choices:
                counts.append(para_lower.count(choice.lower()))
            
            if counts[0] > counts[1]:
                sections[0] += " " + para
            elif counts[1] > counts[0]:
                sections[1] += " " + para
            else:
                # Both equal - assign to both
                sections[0] += " " + para
                sections[1] += " " + para
        
        return sections
    
    sections = find_suspect_sections(story, choices)
    
    scores = []
    for i, choice in enumerate(choices):
        section = sections[i]
        if not section.strip():
            section = story  # fallback to full story
        score = count_evidence(section, choice)
        scores.append(score)
    
    # If scores are too close, try alternative approach
    if abs(scores[0] - scores[1]) < 3:
        # Use full story approach with name-proximity scoring
        scores2 = [0, 0]
        for i, choice in enumerate(choices):
            name = choice.lower()
            # Find all occurrences of the name and check nearby context
            for m in re.finditer(re.escape(name), story_lower):
                start = max(0, m.start() - 200)
                end = min(len(story_lower), m.end() + 200)
                context = story_lower[start:end]
                scores2[i] += count_evidence(context, choice)
        
        if scores2[0] != scores2[1]:
            return 0 if scores2[0] > scores2[1] else 1
    
    if scores[0] == scores[1]:
        return 0
    
    return 0 if scores[0] > scores[1] else 1
