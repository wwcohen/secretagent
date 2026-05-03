"""Auto-generated code-distilled implementation for infer_belief."""

def infer_belief(story, movements_text, question, choices):
    import re
    
    # Parse the question to find the person and object
    q_match = re.search(r'Which location is the most likely place (\w+) would look to find the (.+?) given', question)
    if not q_match:
        return None
    
    person = q_match.group(1)
    target_object = q_match.group(2).strip().lower()
    
    # Parse movements
    moves = []
    move_pattern = re.compile(
        r'\d+\.\s*object=(.+?),\s*from=(.+?),\s*to=(.+?),\s*actor=(.+?),\s*present=\[([^\]]*)\],\s*absent=\[([^\]]*)\]'
    )
    
    lines = movements_text.split('\n')
    for line in lines:
        m = move_pattern.search(line)
        if m:
            obj = m.group(1).strip()
            frm = m.group(2).strip()
            to = m.group(3).strip()
            actor = m.group(4).strip()
            present_str = m.group(5).strip()
            absent_str = m.group(6).strip()
            present = [p.strip() for p in present_str.split(',') if p.strip()]
            absent = [p.strip() for p in absent_str.split(',') if p.strip()]
            moves.append((obj, frm, to, actor, present, absent))
    
    # Parse discoveries
    discoveries = []
    disc_pattern = re.compile(
        r'\d+\.\s*observer=(.+?),\s*object=(.+?),\s*location=(.+?),\s*mode=(.+?)$'
    )
    for line in lines:
        dm = disc_pattern.search(line.strip())
        if dm:
            discoveries.append((dm.group(1).strip(), dm.group(2).strip(), dm.group(3).strip(), dm.group(4).strip()))
    
    # Collect all people mentioned
    all_people = set()
    for obj, frm, to, actor, present, absent in moves:
        if actor and actor != 'None':
            all_people.add(actor)
        all_people.update(present)
        all_people.update(absent)
    for d in discoveries:
        all_people.add(d[0])
    
    # Collect all objects and their initial locations
    # Initial location is the 'from' of the first movement of each object
    obj_initial = {}
    for obj, frm, to, actor, present, absent in moves:
        obj_lower = obj.lower()
        if obj_lower not in obj_initial and frm and frm != 'None':
            obj_initial[obj_lower] = frm
    
    # Track beliefs: for each person, what they believe the location of each object is
    # Initialize: everyone knows initial locations
    beliefs = {}
    for p in all_people:
        beliefs[p] = {}
        for obj_lower, loc in obj_initial.items():
            beliefs[p][obj_lower] = loc
    
    # Track actual object locations (for incidental discovery via visiting)
    actual_locations = dict(obj_initial)
    
    # Process movements in order
    for obj, frm, to, actor, present, absent in moves:
        obj_lower = obj.lower()
        
        if to and to != 'None':
            # Update actual location
            actual_locations[obj_lower] = to
            
            # Actor and present people learn the new location
            witnesses = list(present)
            if actor and actor != 'None':
                witnesses.append(actor)
            
            for w in witnesses:
                if w in beliefs:
                    beliefs[w][obj_lower] = to
            
            # Check if actor goes to the 'to' location - they might see other objects there
            if actor and actor != 'None' and actor in beliefs:
                for other_obj, other_loc in actual_locations.items():
                    if other_obj != obj_lower and other_loc == to:
                        # Actor sees other objects at destination
                        beliefs[actor][other_obj] = to
                # Also present people see what's at the destination
                for w in present:
                    if w in beliefs:
                        for other_obj, other_loc in actual_locations.items():
                            if other_obj != obj_lower and other_loc == to:
                                beliefs[w][other_obj] = to
    
    # Process discoveries
    for observer, obj, location, mode in discoveries:
        obj_lower = obj.lower()
        if observer in beliefs:
            beliefs[observer][obj_lower] = location
    
    # Now find the answer
    if person not in beliefs:
        return None
    
    person_beliefs = beliefs[person]
    
    # Try to match target object with known objects
    best_match = None
    best_score = -1
    
    for obj_key, loc in person_beliefs.items():
        # Check similarity between target_object and obj_key
        if target_object == obj_key:
            best_match = loc
            best_score = 1000
            break
        # Check if one contains the other
        t_words = set(target_object.split())
        o_words = set(obj_key.split())
        common = len(t_words & o_words)
        if common > best_score:
            best_score = common
            best_match = loc
    
    if best_match is None or best_score == 0:
        # Try partial matching
        for obj_key, loc in person_beliefs.items():
            if target_object in obj_key or obj_key in target_object:
                best_match = loc
                break
    
    if best_match is None:
        return None
    
    # Match to closest choice
    best_choice = None
    best_choice_score = -1
    
    for choice in choices:
        choice_lower = choice.lower().strip()
        match_lower = best_match.lower().strip()
        
        if choice_lower == match_lower:
            return choice
        
        # Fuzzy matching
        c_words = set(choice_lower.split())
        m_words = set(match_lower.split())
        common = len(c_words & m_words)
        
        if common > best_choice_score:
            best_choice_score = common
            best_choice = choice
        
        if match_lower in choice_lower or choice_lower in match_lower:
            if best_choice_score < 100:
                best_choice_score = 100
                best_choice = choice
    
    if best_choice_score > 0:
        return best_choice
    
    # Last resort: substring matching
    for choice in choices:
        if best_match.lower() in choice.lower() or choice.lower() in best_match.lower():
            return choice
    
    return best_choice if best_choice else None
