"""Auto-generated code-distilled implementation for deduce_murderer."""

def deduce_murderer(story, alibi_analysis, question, suspects):
    import re
    
    if not suspects:
        return None
    
    if len(suspects) == 1:
        return suspects[0]
    
    text = alibi_analysis.lower()
    
    scores = {}
    
    for suspect in suspects:
        scores[suspect] = 0
    
    # Split the alibi analysis by suspect sections
    suspect_sections = {}
    for i, suspect in enumerate(suspects):
        pattern = re.compile(r'suspect[:\s]+' + re.escape(suspect.lower()), re.IGNORECASE)
        matches = list(pattern.finditer(alibi_analysis))
        if matches:
            start = matches[0].start()
            # Find the end - next suspect section or end of text
            end = len(alibi_analysis)
            for other in suspects:
                if other == suspect:
                    continue
                other_pattern = re.compile(r'suspect[:\s]+' + re.escape(other.lower()), re.IGNORECASE)
                other_matches = list(other_pattern.finditer(alibi_analysis))
                for m in other_matches:
                    if m.start() > start:
                        end = min(end, m.start())
            suspect_sections[suspect] = alibi_analysis[start:end].lower()
        else:
            suspect_sections[suspect] = ""
    
    for suspect in suspects:
        section = suspect_sections.get(suspect, "")
        if not section:
            continue
        
        # alibi_holds: False is very suspicious
        if re.search(r'alibi_holds[:\s]*(false|no\b)', section):
            scores[suspect] += 10
        elif re.search(r'alibi_holds[:\s]*(partially|partial)', section):
            scores[suspect] += 5
        elif re.search(r'alibi_holds[:\s]*(true|yes)', section):
            scores[suspect] -= 5
        
        # Count contradictions
        contradictions_match = re.search(r'contradictions[:\s]*(.*?)(?=\n[a-z_]+[\s:]*|$)', section, re.DOTALL)
        if contradictions_match:
            contra_text = contradictions_match.group(1).strip()
            if contra_text and not re.match(r'^(none|no\b|n/a)', contra_text):
                scores[suspect] += 8
                # More detailed contradictions
                scores[suspect] += contra_text.count(';')
        
        # Alibi gaps
        gaps_match = re.search(r'alibi_gaps[:\s]*(.*?)(?=\n[a-z_]+[\s:]*|$)', section, re.DOTALL)
        if gaps_match:
            gaps_text = gaps_match.group(1).strip()
            if gaps_text and not re.match(r'^(none|no\b|n/a)', gaps_text):
                scores[suspect] += 5
                if 'entire' in gaps_text or 'unaccounted' in gaps_text or 'significant' in gaps_text:
                    scores[suspect] += 3
        
        # Corroborating evidence against them
        corr_match = re.search(r'corroborating_evidence[:\s]*(.*?)(?=\n[a-z_]+[\s:]*|$)', section, re.DOTALL)
        if corr_match:
            corr_text = corr_match.group(1).strip()
            if corr_text and not re.match(r'^(none|no\b|n/a)', corr_text):
                scores[suspect] += 5
                # Keywords indicating strong evidence
                for kw in ['weapon', 'scene', 'motive', 'forensic', 'cctv', 'witness', 'seen', 'match', 'ballistic']:
                    if kw in corr_text:
                        scores[suspect] += 2
        
        # Additional suspicious keywords in section
        for kw in ['decepti', 'falsif', 'lied', 'lying', 'suspicious', 'nervous', 'incriminat']:
            scores[suspect] += section.count(kw) * 2
    
    if not scores:
        return None
    
    most_likely = max(suspects, key=lambda s: scores.get(s, 0))
    return most_likely
