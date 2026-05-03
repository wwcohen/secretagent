"""Auto-generated code-distilled implementation for consistent_sports."""

def consistent_sports(sports1, sports2):
    def parse_sports(s):
        # Split by ', ' and ' and '
        # First split by ', ' then split each part by ' and '
        parts = []
        for chunk in s.split(', '):
            for sub in chunk.split(' and '):
                stripped = sub.strip()
                if stripped:
                    parts.append(stripped)
        return set(parts)
    
    set1 = parse_sports(sports1)
    set2 = parse_sports(sports2)
    
    if not set1 or not set2:
        return None
    
    return len(set1 & set2) > 0
