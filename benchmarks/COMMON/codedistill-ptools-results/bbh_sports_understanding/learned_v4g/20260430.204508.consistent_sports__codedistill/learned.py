"""Auto-generated code-distilled implementation for consistent_sports."""

import re

def consistent_sports(s1, s2):
    """
    Checks whether two strings describing sports or lists of sports are consistent,
    meaning they share at least one sport in common or one represents a sub-category 
    of the other.
    """
    if not isinstance(s1, str) or not isinstance(s2, str):
        return None
        
    s1, s2 = s1.lower(), s2.lower()
    
    def extract(text):
        # Remove any XML/HTML-like tags (e.g., <answer>) that might bleed into the text
        text = re.sub(r'<[^>]+>', ' ', text)
        # Split by commas, specific conjunctions, newlines, and sentence-ending punctuation
        parts = re.split(r',|\band\b|\bor\b|\n|\.|;', text)
        # Clean and filter out empty strings
        return [p.strip() for p in parts if p.strip()]

    parts1 = extract(s1)
    parts2 = extract(s2)
    
    if not parts1 or not parts2:
        return None
        
    for p1 in parts1:
        for p2 in parts2:
            # Exact match between extracted entities
            if p1 == p2:
                return True
            try:
                # Check if one sport is completely contained as a word within the other 
                # (e.g., "hockey" and "ice hockey")
                if re.search(r'\b' + re.escape(p1) + r'\b', p2) or \
                   re.search(r'\b' + re.escape(p2) + r'\b', p1):
                    return True
            except re.error:
                pass
                
    return False
