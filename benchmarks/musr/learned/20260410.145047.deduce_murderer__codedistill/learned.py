"""Auto-generated code-distilled implementation for deduce_murderer."""

def deduce_murderer(narrative, alibi_report, question, suspects):
    import re
    
    if not suspects or len(suspects) < 2:
        return None
    
    s1, s2 = suspects[0], suspects[1]
    
    # Extract sections for each suspect from the narrative
    def get_suspect_section_score(narrative, suspect, other):
        score = 0
        text = narrative.lower()
        s_lower = suspect.lower()
        
        # Split narrative roughly by suspect focus
        # Find paragraphs/sections mentioning each suspect
        lines = narrative.split('\n')
        suspect_lines = []
        for line in lines:
            if suspect in line:
                suspect_lines.append(line)
        
        suspect_text = ' '.join(suspect_lines).lower()
        full_text = text
        
        # Strong incriminating indicators in narrative about this suspect
        strong_indicators = [
            r'missing', r'missing.*from', r'found missing',
            r'purchase[d]?\s+(?:a\s+)?(?:the\s+)?(?:same|matching|identical)',
            r'receipt', r'purchased',
            r'arranged.*meeting', r'coax', r'lured', r'trap',
            r'threatened?\s+to\s+expose', r'threatened?\s+to\s+reveal',
            r'expose\s+(?:her|his|their)', r'reveal\s+(?:her|his|their)',
            r'blackmail', r'extort',
            r'seen\s+entering', r'spotted\s+at',
            r'last\s+(?:seen|person)\s+with',
            r'alone\s+with',
            r'no\s+one\s+else',
            r'only\s+(?:person|one|staff|the\s+two)',
            r'exclusive\s+(?:access|keys|control)',
            r'keys\s+to\s+(?:all|the|every)',
            r'proficien(?:t|cy)',
            r'expert(?:ise)?',
            r'training\s+in',
            r'practiced?\s+with',
            r'collection\s+of',
            r'eerily\s+similar',
            r'matching\s+markings',
            r'identical\s+to',
            r'same\s+(?:type|kind|weapon|species)',
            r'illegal\s+activit',
            r'criminal\s+(?:record|past|activit)',
            r'stiff(?:ened|ly)',
            r'nervous(?:ly|ness)?',
            r'froze',
            r'defensive',
            r'refuse[ds]?\s+to\s+(?:serve|answer|cooperate)',
            r'racial\s+(?:slur|bias|hatred)',
            r'derogatory',
            r'prejudice',
            r'discriminat',
            r'hate\s+(?:speech|crime)',
            r'research(?:ed|ing)?\s+(?:on\s+)?(?:how\s+to\s+)?(?:extract|poison|bleach)',
            r'search\s+history',
            r'internet\s+search',
            r'beneficiary',
            r'insurance\s+poli(?:cy|cies)',
            r'debt(?:s)?',
            r'bankrupt(?:cy)?',
            r'financial\s+(?:desperat|trouble|struggle|problem)',
            r'mounting\s+debt',
            r'loan\s+shark',
            r'failing\s+(?:shop|business|store)',
            r'violent\s+(?:outburst|tendenc|behavio)',
            r'abuse|abusi(?:ve|ng)',
            r'hospital\s+records',
            r'injur(?:y|ies)\s+treatment',
            r'venom\s+(?:sample|extract)',
            r'poison(?:ous|ed)?',
            r'venomous',
            r'flamethrower',
            r'weapon\s+(?:in|from|match)',
            r'murder\s+weapon',
            r'ballistic(?:s)?',
            r'forensic',
            r'cctv|surveillance|footage|camera',
            r'witness(?:es)?\s+(?:saw|confirm|place|spotted)',
            r'confronted?\s+(?:him|her)',
            r'argument\s+(?:with|between)',
            r'heated\s+(?:argument|dispute|quarrel)',
            r'publicly\s+(?:humiliat|threaten|mock|insult|criticiz)',
            r'reputation',
            r'secret\s+(?:illegal|criminal|shady)',
            r'draft\s+email',
            r'delet(?:e|ed|ing)\s+(?:social|app|evidence)',
            r'social\s+media',
            r'post(?:s|ed|ing)?\s+(?:on|offensive|derogatory|racial)',
        ]
        
        for indicator in strong_indicators:
            # Count occurrences near suspect's name
            pattern = r'(?:' + re.escape(suspect) + r'.{0,500}' + indicator + r'|' + indicator + r'.{0,500}' + re.escape(suspect) + r')'
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            score += len(matches) * 2
        
        # Count how many times suspect name appears in narrative
        name_count = len(re.findall(re.escape(suspect), narrative, re.IGNORECASE))
        score += name_count * 0.1
        
        return score
    
    score1 = get_suspect_section_score(narrative, s1, s2)
    score2 = get_suspect_section_score(narrative, s2, s1)
    
    # Also check alibi report for explicit conclusion favoring one suspect
    # But weight narrative evidence more heavily
    
    alibi_lower = alibi_report.lower()
    
    # Check if alibi report has a conclusion section
    conclusion_match = re.search(r'(?:conclusion|overall|recommendation|summary|assessment)[:\s]*(.+)', alibi_report, re.IGNORECASE | re.DOTALL)
    
    alibi_score1 = 0
    alibi_score2 = 0
    
    if conclusion_match:
        conclusion = conclusion_match.group(1).lower()
        # Check which suspect is called primary/stronger/more likely
        if re.search(re.escape(s1.lower()) + r'.{0,200}(?:primary|stronger|more likely|more suspicious|higher risk|strongest)', conclusion):
            alibi_score1 += 5
        if re.search(re.escape(s2.lower()) + r'.{0,200}(?:primary|stronger|more likely|more suspicious|higher risk|strongest)', conclusion):
            alibi_score2 += 5
        if re.search(r'(?:primary|stronger|more likely|more suspicious|higher risk|strongest).{0,200}' + re.escape(s1.lower()), conclusion):
            alibi_score1 += 5
        if re.search(r'(?:primary|stronger|more likely|more suspicious|higher risk|strongest).{0,200}' + re.escape(s2.lower()), conclusion):
            alibi_score2 += 5

    total1 = score1 + alibi_score1
    total2 = score2 + alibi_score2
    
    if total1 > total2:
        return s1
    elif total2 > total1:
        return s2
    else:
        return s1
