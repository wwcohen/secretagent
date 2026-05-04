"""Auto-generated end-to-end implementation for answer_question."""

import re
import json

def parse_input(story, question, suspects_str):
    """Parse the input arguments."""
    # Parse suspects list
    suspects = re.findall(r"'([^']*)'", suspects_str)
    return story, question, suspects

def score_suspect(story, suspect_name):
    """Score how likely a suspect is the murderer based on textual clues."""
    score = 0
    story_lower = story.lower()
    name_lower = suspect_name.lower()
    
    # Count mentions of the suspect
    mentions = story_lower.count(name_lower)
    score += mentions * 0.5
    
    # Look for incriminating patterns near suspect's name
    # Split into paragraphs/sentences and analyze context
    sentences = re.split(r'[.!?]+', story)
    
    incriminating_keywords = [
        'murder', 'kill', 'weapon', 'motive', 'threat', 'threaten', 'debt',
        'blackmail', 'jealous', 'jealousy', 'anger', 'angry', 'venom', 'poison',
        'illegal', 'crime', 'criminal', 'evidence', 'expose', 'secret',
        'afraid', 'fear', 'confront', 'argue', 'argument', 'dispute',
        'access', 'key', 'alone', 'opportunity', 'present', 'scene',
        'purchase', 'bought', 'buy', 'training', 'skilled', 'proficient',
        'collection', 'own', 'possess', 'handle', 'practice',
        'embezzl', 'smuggl', 'fraud', 'launder', 'steal', 'stole',
        'revenge', 'grudge', 'resent', 'bitter', 'hatred', 'hate',
        'alibi', 'suspicious', 'nervous', 'uncomfortable', 'evasive',
        'witness', 'spotted', 'seen', 'camera', 'footage',
        'victim', 'dead', 'death', 'found', 'body',
        'confess', 'admit', 'guilty', 'deny',
        'knife', 'gun', 'pistol', 'syringe', 'trident', 'nunchaku',
        'sai', 'chainsaw', 'grenade', 'shiv', 'sickle',
        'reputation', 'ruin', 'destroy', 'humiliat',
        'affair', 'infidel', 'betray', 'deceiv',
        'inherit', 'will', 'beneficiary', 'successor', 'next in line',
        'debt', 'owe', 'money', 'financ',
        'falsif', 'manipulat', 'fabricat', 'forge',
        'termina', 'fire', 'dismiss', 'lost job',
    ]
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        if name_lower in sentence_lower:
            for keyword in incriminating_keywords:
                if keyword in sentence_lower:
                    score += 2
    
    # Check for direct connections to murder weapon, scene, victim
    # Second story block typically focuses more on the guilty suspect
    paragraphs = story.split('\n\n')
    
    # The second narrative block often contains the murderer's story
    # Count how much of the later narrative focuses on each suspect
    half = len(story) // 2
    second_half = story[half:].lower()
    first_half = story[:half].lower()
    
    second_half_mentions = second_half.count(name_lower)
    score += second_half_mentions * 0.3
    
    return score

def solve(story, question, suspects):
    """Determine which suspect is the most likely murderer."""
    scores = []
    for suspect in suspects:
        s = score_suspect(story, suspect)
        scores.append(s)
    
    if scores[0] > scores[1]:
        return 0
    elif scores[1] > scores[0]:
        return 1
    else:
        return 0

def format_output(result):
    """Format the output."""
    return result

def answer_question(story, question, suspects_str):
    """Main function to answer the murder mystery question."""
    try:
        story, question, suspects = parse_input(story, question, suspects_str)
        result = solve(story, question, suspects)
        return format_output(result)
    except Exception:
        return None

# Alias
murder = answer_question
