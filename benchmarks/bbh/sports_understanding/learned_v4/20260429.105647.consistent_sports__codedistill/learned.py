"""Auto-generated code-distilled implementation for consistent_sports."""

def consistent_sports(sport1, sport2):
    # Split each sport string into individual sports using "and" and "or" as delimiters
    import re
    
    def parse_sports(s):
        # Split by " and " or " or "
        parts = re.split(r'\s+and\s+|\s+or\s+', s.strip())
        return [p.strip() for p in parts if p.strip()]
    
    def sports_match(a, b):
        """Check if two individual sport names are compatible."""
        a_lower = a.lower()
        b_lower = b.lower()
        # Exact match
        if a_lower == b_lower:
            return True
        # One is a substring of the other (e.g., "hockey" in "ice hockey")
        if a_lower in b_lower or b_lower in a_lower:
            return True
        return False
    
    sports1 = parse_sports(sport1)
    sports2 = parse_sports(sport2)
    
    # Check if any sport from sports1 matches any sport from sports2
    for s1 in sports1:
        for s2 in sports2:
            if sports_match(s1, s2):
                return True
    
    return False
