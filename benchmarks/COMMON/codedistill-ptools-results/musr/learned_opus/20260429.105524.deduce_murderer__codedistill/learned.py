"""Auto-generated code-distilled implementation for deduce_murderer."""

def deduce_murderer(narrative, alibi_analysis, question, suspects):
    import re
    
    if not suspects:
        return None
    
    if len(suspects) == 1:
        return suspects[0]
    
    # Parse alibi analysis for each suspect
    suspect_scores = {}
    
    for suspect in suspects:
        suspect_scores[suspect] = 0
    
    text = alibi_analysis
    
    # Split analysis by suspect sections
    for suspect in suspects:
        # Find the section for this suspect (case-insensitive search for suspect name)
        patterns = [
            rf'(?i)suspect[:\s]*{re.escape(suspect)}(.*?)(?=(?:suspect[:\s]*(?:{"|".join(re.escape(s) for s in suspects if s != suspect)})|$)',
            rf'(?i){re.escape(suspect)}[:\s]*(.*?)(?=(?:{"|".join(re.escape(s) for s in suspects if s != suspect)}|$))',
            rf'(?i)name:\s*{re.escape(suspect)}(.*?)(?=(?:name:\s*(?:{"|".join(re.escape(s) for s in suspects if s != suspect)})|$)',
        ]
        
        section = ""
        for pat in patterns:
            match = re.search(pat, text, re.DOTALL)
            if match:
                section = match.group(1)
                break
        
        if not section:
            # Try broader match
            match = re.search(re.escape(suspect) + r'(.*?)(?=' + '|'.join(re.escape(s) for s in suspects if s != suspect) + r'|$)', text, re.DOTALL)
            if match:
                section = match.group(1)
        
        section_lower = section.lower()
        
        # alibi_holds: False increases suspicion
        if re.search(r'alibi_holds[:\s]*false', section_lower):
            suspect_scores[suspect] += 3
        elif re.search(r'alibi_holds[:\s]*partially', section_lower):
            suspect_scores[suspect] += 1
        elif re.search(r'alibi_holds[:\s]*true', section_lower):
            suspect_scores[suspect] -= 2
        
        # Alibi gaps - more text about gaps = more suspicious
        gaps_match = re.search(r'alibi_gaps[:\s]*(.*?)(?=\n\s*[-•]|\n\s*\w+[:\s]|$)', section, re.DOTALL | re.IGNORECASE)
        if gaps_match:
            gaps_text = gaps_match.group(1).lower()
            if 'entire crime period' in gaps_text or 'unaccounted' in gaps_text:
                suspect_scores[suspect] += 2
            if 'no' not in gaps_text or 'no alibi' in gaps_text or 'no specific' in gaps_text or 'no witnesses' in gaps_text:
                suspect_scores[suspect] += 1
        
        # Contradictions
        contra_match = re.search(r'contradictions[:\s]*(.*?)(?=\n\s*[-•]|\n\s*\w+[:\s]|$)', section, re.DOTALL | re.IGNORECASE)
        if contra_match:
            contra_text = contra_match.group(1).lower().strip()
            if contra_text and 'none' not in contra_text[:10]:
                suspect_scores[suspect] += 2
        
        # Corroborating evidence against them
        corr_match = re.search(r'corroborating_evidence[:\s]*(.*?)(?=\n\s*[-•]|\n\s*suspect|\n\s*\w+[:\s]|$)', section, re.DOTALL | re.IGNORECASE)
        if corr_match:
            corr_text = corr_match.group(1).lower().strip()
            if 'none' not in corr_text[:10] and len(corr_text) > 10:
                suspect_scores[suspect] += 2
            if 'matches' in corr_text or 'murder weapon' in corr_text or 'places' in corr_text:
                suspect_scores[suspect] += 1
        
        # Motive keywords
        if 'motive' in section_lower and ('strong' in section_lower):
            suspect_scores[suspect] += 1
        
        # Evidence at scene
        if 'scene' in section_lower and ('place' in section_lower or 'seen' in section_lower):
            suspect_scores[suspect] += 1
    
    # Return suspect with highest score
    best = max(suspects, key=lambda s: suspect_scores.get(s, 0))
    return best
