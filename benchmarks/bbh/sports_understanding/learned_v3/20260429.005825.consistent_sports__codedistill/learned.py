"""Auto-generated code-distilled implementation for consistent_sports."""

def consistent_sports(sport1, sport2):
    def extract_sports(text):
        # Normalize the text
        # Split by commas, "and", newlines
        import re
        # First, clean up the text
        text = text.strip()
        # Split by commas, " and ", newlines
        parts = re.split(r',|\band\b|\n', text)
        sports = set()
        for part in parts:
            part = part.strip().lower()
            if part:
                sports.add(part)
        return sports

    def normalize_sport(sport):
        # Normalize equivalent sport names
        sport = sport.strip().lower()
        equivalences = {
            'ice hockey': 'hockey',
        }
        return equivalences.get(sport, sport)

    sports1 = {normalize_sport(s) for s in extract_sports(sport1)}
    sports2 = {normalize_sport(s) for s in extract_sports(sport2)}

    # Filter out empty strings
    sports1 = {s for s in sports1 if s}
    sports2 = {s for s in sports2 if s}

    if not sports1 or not sports2:
        return None

    # Check if there's any intersection
    return len(sports1 & sports2) > 0
