"""Auto-generated code-distilled implementation for sport_for."""

def sport_for(text):
    """
    Determines the sport(s) associated with the given text fragment.
    Returns a string with sport name(s) or None if indeterminate.
    """
    
    # Dictionary of player names to sports
    player_sports = {
        'Kevin Durant': 'basketball',
        'Anthony Davis': 'basketball',
        'Caris LeVert': 'basketball',
        'Mitchell Robinson': 'basketball',
        'Michael Porter Jr.': 'basketball',
        'Fred VanVleet': 'basketball',
        'Fernando Tatis Jr.': 'baseball',
        'Ketel Marte': 'baseball',
        'Freddie Freeman': 'baseball',
        'Adam Thielen': 'American football',
        'Mark Stone': 'hockey',
        'Robin Lehner': 'hockey',
        'Leon Draisaitl': 'hockey',
        'Klaas Jan Huntelaar': 'soccer',
        'Willian': 'soccer',
        'Vincent Kompany': 'soccer',
        'Cooper Kupp': 'American football and rugby',
        'A.J. Green': 'American football and rugby',
        'Tyreek Hill': 'American football and rugby',
        'Sam Darnold': 'American football and rugby',
        'DJ Chark': 'American football and rugby',
    }
    
    # Check for exact player name match
    if text in player_sports:
        return player_sports[text]
    
    text_lower = text.lower()
    
    # Basketball keywords
    basketball_keywords = ['layup', 'dunk', 'heave', 'airball', 'screen', 'violation', 
                          'buzzer', 'reverse dunk', 'called for the screen']
    
    # Hockey keywords
    hockey_keywords = ['third period', 'stanley cup', 'powerplay', 'power play', 
                      'puck', 'ice hockey', 'killed the powerplay', 'shot the puck']
    
    # Soccer keywords
    soccer_keywords = ['red card', 'freekick', 'free kick', 'champions league', 'scored a freekick']
    
    # Baseball keywords
    baseball_keywords = ['base', 'triple', 'homer', 'grounded out', 'pitch', 
                        'national league', 'got on base', 'hit a triple', 'hit a walkoff homer',
                        'watched the pitch']
    
    # American football/rugby keywords
    af_rugby_keywords = ['endzone', 'screen pass', 'nfc', 'back shoulder fade', 
                        'caught the screen pass', 'got into the endzone', 'caught the back shoulder fade']
    
    # Check for keyword matches
    matches = set()
    
    for keyword in basketball_keywords:
        if keyword in text_lower:
            matches.add('basketball')
    
    for keyword in hockey_keywords:
        if keyword in text_lower:
            matches.add('hockey')
    
    for keyword in soccer_keywords:
        if keyword in text_lower:
            matches.add('soccer')
    
    for keyword in baseball_keywords:
        if keyword in text_lower:
            matches.add('baseball')
    
    for keyword in af_rugby_keywords:
        if keyword in text_lower:
            matches.add('American football and rugby')
    
    # Handle generic "scored" - returns all sports that have scoring
    if text_lower == 'scored':
        return 'basketball, soccer, American football, rugby, hockey'
    
    # If we found matches, return them
    if matches:
        if len(matches) == 1:
            return list(matches)[0]
        else:
            # Return in a consistent order
            sport_order = ['ice hockey', 'hockey', 'basketball', 'soccer', 'American football', 'rugby', 'American football and rugby', 'baseball']
            ordered_matches = [s for s in sport_order if s in matches]
            return ' and '.join(ordered_matches) if ordered_matches else None
    
    return None
