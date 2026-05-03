"""Auto-generated code-distilled implementation for analyze_sentence."""

import re

def analyze_sentence(sentence):
    # Fix typo
    sentence = sentence.replace('comitted', 'committed')
    
    # Extract player name - names end where a lowercase verb starts
    # Handle Jr. and initials like A.J.
    name_pattern = r'^((?:[A-Z][a-zA-Z]*(?:\.[A-Z]\.?)*[-\s])*(?:[A-Z][a-zA-Z]*\.?(?:\s+Jr\.)?))\s+'
    
    # Try to find where name ends and action begins
    # Name: sequence of capitalized words (possibly with Jr., initials, hyphens)
    # Action starts with a lowercase word (verb)
    
    m = re.match(r'^((?:[A-Z]\.?[a-zA-Z.-]*\s+)*?[A-Z][a-zA-Z.-]*(?:\s+Jr\.)?)\s+((?:was|earned|scored|hit|launched|airballed|set|beat|caught|performed|called|comitted|committed|skated|grounded|drew|had|made|completed|threw|blocked|kicked|ran|fumbled|struck|saved|grabbed|pulled|fired|drove|posted|recorded|delivered|attempted|missed|sank|nailed|drained|dropped|flipped|pitched|batted|bunted|fouled|tagged|stole|walked|singled|doubled|tripled|homered)\b.*)$', sentence)
    
    if not m:
        return None
    
    name = m.group(1)
    rest = m.group(2)
    
    # Now split rest into action and context
    # Context patterns: "in the <Event/Tournament/Period>." or "to the <place>."
    # These are typically proper-noun-heavy phrases about events, tournaments, rounds, cups, series
    
    context_patterns = [
        r'\s+(in the (?:Stanley Cup|European Cup|NFC (?:divisional round|championship)|AFC (?:divisional round|championship)|Superbowl|Super Bowl|Western Conference Finals?|Eastern Conference Finals?|National League Championship Series|American League Championship Series|World Series|UEFA Champions League|NBA Finals?|NHL Finals?|MLS Cup|playoffs?|postseason)\.)$',
        r'\s+(in the \w[\w\s]*(?:Cup|Series|Finals|Bowl|League|Round|championship|round)\.)$',
        r'\s+(to the [\w\s]+\.)$',
        r'\s+(in the third period\.)$',
        r'\s+(in the (?:first|second|third|fourth) (?:period|quarter|half|inning|set)\.)$',
    ]
    
    context = ''
    action = rest
    
    for pat in context_patterns:
        cm = re.search(pat, rest, re.IGNORECASE)
        if cm:
            context = cm.group(1)
            action = rest[:cm.start(1)].rstrip()
            break
    
    # Strip trailing period from action if no context
    if not context:
        action = action.rstrip('.')
    
    return [name, action, context]
