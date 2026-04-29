"""Auto-generated code-distilled implementation for score_team_assignments."""

import re

def score_team_assignments(story, requirements, question, choices):
    """Score team assignments based on story, requirements, and choices."""
    
    req_lower = requirements.lower()
    
    # Extract hard constraints
    hard_constraints = []
    # Find hard_constraints section
    hc_match = re.search(r'hard_constraints[:\s]*\[?(.*?)(?:\]?\s*(?:soft_constraints|scoring_rules|synerg|conflict|$))', requirements, re.DOTALL | re.IGNORECASE)
    if hc_match:
        hc_text = hc_match.group(1)
        # Extract individual constraints
        constraints_raw = re.findall(r'["\-]\s*([^"\n\[\]]+)', hc_text)
        for c in constraints_raw:
            c = c.strip().rstrip(',').strip('"').strip("'").strip()
            if c:
                hard_constraints.append(c)
    
    # Extract soft constraints
    soft_constraints = []
    sc_match = re.search(r'soft_constraints[:\s]*\[?(.*?)(?:\]?\s*(?:hard_constraints|scoring_rules|synerg|conflict|$))', requirements, re.DOTALL | re.IGNORECASE)
    if sc_match:
        sc_text = sc_match.group(1)
        scs_raw = re.findall(r'["\-]\s*([^"\n\[\]]+)', sc_text)
        for c in scs_raw:
            c = c.strip().rstrip(',').strip('"').strip("'").strip()
            if c:
                soft_constraints.append(c)
    
    # Extract synergies
    synergies = []
    syn_match = re.search(r'synerg[a-z]*[:\s]*\[?(.*?)(?:\]?\s*(?:hard_constraints|soft_constraints|scoring_rules|conflict|$))', requirements, re.DOTALL | re.IGNORECASE)
    if syn_match:
        syn_text = syn_match.group(1)
        syn_pairs = re.findall(r'\(\s*["\']?(\w+)["\']?\s*,\s*["\']?(\w+)["\']?\s*\)', syn_text)
        synergies = list(syn_pairs)
    
    # Extract conflicts
    conflicts = []
    con_match = re.search(r'conflicts[:\s]*\[?(.*?)(?:\]?\s*(?:hard_constraints|soft_constraints|scoring_rules|synerg|$))', requirements, re.DOTALL | re.IGNORECASE)
    if con_match:
        con_text = con_match.group(1)
        con_pairs = re.findall(r'\(\s*["\']?(\w+)["\']?\s*,\s*["\']?(\w+)["\']?\s*\)', con_text)
        conflicts = list(con_pairs)
    
    # Parse each choice into task assignments
    def parse_choice(choice_str):
        """Parse a choice string into dict of {task: [persons]}"""
        assignments = {}
        # Split by comma but be careful about commas within person lists
        # Format: "Task1: Person1, Task2: Person2 and Person3"
        # or "Task1: Person1 and Person2, Task2: Person3"
        parts = re.split(r',\s*(?=[A-Z])', choice_str)
        for part in parts:
            part = part.strip()
            m = re.match(r'(.+?):\s*(.+)', part)
            if m:
                task = m.group(1).strip()
                persons_str = m.group(2).strip()
                persons = re.split(r'\s+and\s+|,\s*', persons_str)
                persons = [p.strip() for p in persons if p.strip()]
                assignments[task] = persons
        return assignments
    
    def get_all_persons(assignments):
        """Get all persons from assignments"""
        persons = []
        for task, ps in assignments.items():
            for p in ps:
                persons.append(p)
        return persons
    
    def get_person_task_map(assignments):
        """Get mapping of person -> task"""
        mapping = {}
        for task, ps in assignments.items():
            for p in ps:
                mapping[p] = task
        return mapping
    
    def get_task_groups(assignments):
        """Get groups of people working together on same task"""
        groups = []
        for task, ps in assignments.items():
            if len(ps) > 1:
                groups.append((task, ps))
        return groups
    
    def names_in_text(name, text):
        """Check if name appears in text (case insensitive)"""
        return name.lower() in text.lower()
    
    def check_cannot_pair(constraint, assignments):
        """Check 'cannot pair X with Y' constraint"""
        # Extract names from constraint
        m = re.search(r'cannot\s+pair\s+(\w+)\s+with\s+(\w+)', constraint, re.IGNORECASE)
        if m:
            p1, p2 = m.group(1), m.group(2)
            # Check if they're in the same task group
            for task, persons in assignments.items():
                persons_lower = [p.lower() for p in persons]
                if p1.lower() in persons_lower and p2.lower() in persons_lower:
                    return True
        return False
    
    def check_cannot_assign_to_task(constraint, assignments, all_tasks):
        """Check 'X cannot be assigned to Y' type constraint"""
        # Various patterns
        patterns = [
            r'(\w+)\s+cannot\s+be\s+(?:assigned\s+to|a)\s+(.+)',
            r'cannot\s+assign\s+(\w+)\s+to\s+(.+)',
        ]
        for pattern in patterns:
            m = re.search(pattern, constraint, re.IGNORECASE)
            if m:
                person = m.group(1).strip()
                task_desc = m.group(2).strip().lower()
                
                # Find which task this person is assigned to
                for task, persons in assignments.items():
                    persons_lower = [p.lower() for p in persons]
                    if person.lower() in persons_lower:
                        # Check if the task matches the forbidden task
                        task_lower = task.lower()
                        # Direct match or substring match
                        if task_matches_description(task_lower, task_desc):
                            return True
        return False
    
    def task_matches_description(task_name, desc):
        """Check if a task name matches a constraint description"""
        task_name = task_name.lower().strip()
        desc = desc.lower().strip()
        
        # Remove trailing explanations in parentheses
        desc = re.sub(r'\s*\(.*\)', '', desc).strip()
        
        # Direct containment checks
        if task_name in desc or desc in task_name:
            return True
        
        # Check individual significant words
        task_words = set(re.findall(r'\w+', task_name))
        desc_words = set(re.findall(r'\w+', desc))
        
        # Remove common words
        stop_words = {'the', 'a', 'an', 'to', 'of', 'for', 'in', 'on', 'at', 'by', 
                      'with', 'from', 'due', 'his', 'her', 'its', 'as', 'he', 'she',
                      'cannot', 'be', 'assigned', 'work', 'tasks', 'role', 'that',
                      'and', 'or', 'not', 'is', 'are', 'was', 'were', 'has', 'have',
                      'requiring', 'related', 'based'}
        
        task_sig = task_words - stop_words
        desc_sig = desc_words - stop_words
        
        if task_sig and desc_sig and task_sig & desc_sig:
            return True
        
        # Special keyword mappings
        keyword_map = {
            'surgery': ['surgeon', 'surgical', 'surgery', 'performing'],
            'surgeon': ['surgery', 'surgical', 'surgeon', 'performing'],
            'therapist': ['therapy', 'therapist', 'providing'],
            'therapy': ['therapist', 'therapy', 'providing'],
            'cooking': ['chef', 'cook', 'meal', 'meals', 'culinary', 'kitchen'],
            'chef': ['cooking', 'cook', 'meal', 'meals', 'culinary'],
            'serving': ['server', 'serve', 'waiter', 'waitstaff'],
            'server': ['serving', 'serve', 'waiter', 'waitstaff'],
            'manufacturing': ['assembly', 'production', 'manufacture'],
            'quality': ['control', 'inspection', 'quality'],
            'roller': ['roller', 'operating', 'machinery'],
            'groundwork': ['groundwork', 'foundation', 'ground'],
            'driving': ['drive', 'driver', 'getaway', 'car'],
            'programming': ['programming', 'code', 'coding', 'software'],
            'project': ['management', 'managing', 'project'],
            'medical': ['medical', 'aid', 'medicine', 'nurse'],
            'food': ['food', 'distribution', 'feeding'],
            'plant': ['plant', 'care', 'garden'],
            'bouquet': ['bouquet', 'flower', 'arrangement'],
            'data': ['data', 'collection', 'analysis'],
            'community': ['community', 'engagement', 'outreach'],
            'safe': ['safe', 'cracking', 'crack'],
            'getaway': ['driving', 'drive', 'getaway', 'car'],
            'layout': ['design', 'layout', 'designing'],
            'structure': ['build', 'building', 'construction', 'structure'],
            'itinerary': ['itinerary', 'event', 'schedule', 'planning'],
            'public': ['public', 'relations', 'pr'],
            'content': ['content', 'creation', 'writing'],
            'magazine': ['magazine', 'layout', 'design'],
            'workout': ['workout', 'exercise', 'fitness', 'managing'],
            'hygiene': ['hygiene', 'cleaning', 'clean', 'maintaining'],
            'budget': ['budget', 'financial', 'planning'],
            'event': ['event', 'planning', 'itinerary'],
            'livestock': ['livestock', 'animal', 'animals', 'care'],
            'crop': ['crop', 'cultivation', 'farming', 'crops'],
            'army': ['army', 'armies', 'military', 'lead', 'leading'],
            'court': ['court', 'manage', 'managing'],
            'explaining': ['explaining', 'concept', 'articulating', 'education'],
            'handling': ['handling', 'recording', 'technical', 'video'],
            'recording': ['recording', 'video', 'technical', 'handling'],
            'concept': ['concept', 'explaining', 'articulating'],
            'astronautical': ['astronautical', 'space', 'astronaut'],
            'mission': ['mission', 'control', 'operating'],
            'cartographer': ['cartography', 'cartographer', 'map', 'maps'],
            'digger': ['dig', 'digging', 'excavation', 'physical'],
            'zookeeper': ['zookeeper', 'animal', 'care', 'zoo'],
            'show': ['show', 'presenter', 'presentation', 'presenting'],
            'presenter': ['show', 'presenter', 'presentation', 'stage'],
            'climate': ['climate', 'modelling', 'model'],
            'field': ['field', 'research', 'outdoor'],
            'preparing': ['preparing', 'meals', 'cooking', 'cook'],
            'cleaning': ['cleaning', 'clean', 'hygiene', 'tidy'],
            'software': ['software', 'application', 'develop', 'development'],
            'server': ['server', 'infrastructure', 'manage'],
            'sponsors': ['sponsors', 'donations', 'seeking', 'fundraising'],
            'organizing': ['organizing', 'event', 'details'],
            'architectural': ['architectural', 'design', 'architecture'],
            'foundation': ['foundation', 'building', 'groundwork'],
            'electrical': ['electrical', 'wiring', 'wire'],
            'repetitive': ['repetitive', 'monotony', 'monotonous'],
            'assembly': ['assembly', 'line', 'manufacturing'],
        }
        
        for tw in task_sig:
            if tw in keyword_map:
                for kw in keyword_map[tw]:
                    if kw in desc_sig:
                        return True
        
        for dw in desc_sig:
            if dw in keyword_map:
                for kw in keyword_map[dw]:
                    if kw in task_sig:
                        return True
        
        return False
    
    def check_hard_constraint(constraint, assignments):
        """Check if a hard constraint is violated. Returns True if violated."""
        c_lower = constraint.lower().strip()
        
        # Skip generic constraints that can't be verified from narrative
        generic_patterns = [
            'must have safety certification',
            'needs at least one senior member',
        ]
        for gp in generic_patterns:
            if gp in c_lower:
                return False  # Skip - can't verify, assume ok
        
        # "cannot pair X with Y"
        if 'cannot pair' in c_lower or 'cannot be paired' in c_lower:
            return check_cannot_pair(constraint, assignments)
        
        # "X cannot be assigned to Y" / "X cannot be a Y" / "cannot assign X to Y"
        # "X cannot do Y" / "X cannot work with Y"
        if 'cannot work with' in c_lower or 'cannot work together' in c_lower:
            # This is like "cannot pair"
            m = re.search(r'(\w+)\s+cannot\s+work\s+(?:with|together)', constraint, re.IGNORECASE)
            if m:
                person = m.group(1)
                # Find the other person mentioned
                m2 = re.search(r'cannot\s+work\s+(?:with|together)\s+(?:with\s+)?(\w+)', constraint, re.IGNORECASE)
                if m2:
                    other = m2.group(1)
                    for task, persons in assignments.items():
                        persons_lower = [p.lower() for p in persons]
                        if person.lower() in persons_lower and other.lower() in persons_lower:
                            return True
            return False
        
        # "X and Y cannot work together" / "X and Y cannot be assigned together"
        m = re.search(r'(\w+)\s+and\s+(\w+)\s+cannot\s+(?:work|be\s+assigned)\s+together', constraint, re.IGNORECASE)
        if m:
            p1, p2 = m.group(1), m.group(2)
            for task, persons in assignments.items():
                persons_lower = [p.lower() for p in persons]
                if p1.lower() in persons_lower and p2.lower() in persons_lower:
                    return True
            return False
        
        # "X cannot tolerate Y" - treat as soft unless it prevents pairing
        if 'cannot tolerate' in c_lower:
            # Extract the two people involved
            m = re.search(r'(\w+)\s+cannot\s+tolerate\s+.*?(\w+)', constraint, re.IGNORECASE)
            if m:
                # This is more of a soft constraint
                pass
            return False
        
        # "X cannot be assigned to/as [role]" / "X cannot do [task]" / "X cannot be a [role]"
        # Also "X should not be a [role]"
        assign_patterns = [
            (r'(\w+)\s+cannot\s+be\s+(?:assigned\s+to|a)\s+(.+?)(?:\s*\(|$)', None),
            (r'cannot\s+assign\s+(\w+)\s+to\s+(.+?)(?:\s*\(|$)', None),
            (r'(\w+)\s+cannot\s+do\s+(.+?)(?:\s*\(|$)', None),
            (r'(\w+)\s+cannot\s+be\s+(?:assigned\s+to)\s+(.+?)(?:\s*\(|$)', None),
            (r'(\w+)\s+(?:should|must)\s+not\s+be\s+(?:a|assigned\s+to)\s+(.+?)(?:\s*\(|$)', None),
            (r'(\w+)\s+cannot\s+(?:stand|lead|manage)\s+(.+?)(?:\s*\(|$)', None),
        ]
        
        for pattern, _ in assign_patterns:
            m = re.search(pattern, constraint, re.IGNORECASE)
            if m:
                person = m.group(1).strip()
                forbidden = m.group(2).strip().rstrip(',').strip('"').strip("'").strip()
                
                # Check if person is assigned to a task matching the forbidden description
                for task, persons in assignments.items():
                    persons_lower = [p.lower() for p in persons]
                    if person.lower() in persons_lower:
                        if task_matches_description(task, forbidden):
                            return True
        
        # Additional patterns for specific constraint types
        # "X cannot stand for extended periods" - relates to physical tasks
        if 'cannot stand for extended' in c_lower:
            m = re.search(r'(\w+)\s+cannot\s+stand', constraint, re.IGNORECASE)
            if m:
                person = m.group(1)
                # This person should not be in tasks requiring standing
                # Check if they're in a physical task
                for task, persons in assignments.items():
                    persons_lower = [p.lower() for p in persons]
                    if person.lower() in persons_lower:
                        # Check if task is physical (food distribution etc might require standing)
                        # This is context-dependent, treat as soft
                        pass
            return False
        
        # "X cannot lead armies" type  
        m = re.search(r'(\w+)\s+cannot\s+lead\s+(.+?)(?:\s*\(|$)', constraint, re.IGNORECASE)
        if m:
            person = m.group(1).strip()
            forbidden_task = m.group(2).strip()
            for task, persons in assignments.items():
                persons_lower = [p.lower() for p in persons]
                if person.lower() in persons_lower:
                    if task_matches_description(task, forbidden_task):
                        return True
            return False
        
        return False
    
    def count_hard_violations(assignments, hard_constraints_list):
        """Count number of hard constraint violations"""
        count = 0
        for hc in hard_constraints_list:
            if check_hard_constraint(hc, assignments):
                count += 1
        return count
    
    def check_pairing_constraint(constraint, assignments):
        """Check if a pairing constraint (cannot pair X with Y) is about same-task pairing"""
        m = re.search(r'cannot\s+pair\s+(\w+)\s+with\s+(\w+)', constraint, re.IGNORECASE)
        if not m:
            m = re.search(r'(\w+)\s+cannot\s+be\s+paired\s+with\s+(\w+)', constraint, re.IGNORECASE)
        if m:
            p1, p2 = m.group(1), m.group(2)
            for task, persons in assignments.items():
                persons_lower = [p.lower() for p in persons]
                if p1.lower() in persons_lower and p2.lower() in persons_lower:
                    return True
        return False
    
    def score_soft_constraints(assignments, soft_constraints_list):
        """Score based on soft constraints. Return number of satisfied soft constraints."""
        score = 0
        person_task = get_person_task_map(assignments)
        
        for sc in soft_constraints_list:
            sc_lower = sc.lower()
            
            # "prefer to assign X to Y" / "prefer assigning X to Y"
            m = re.search(r'prefer\s+(?:to\s+)?assign(?:ing)?\s+(\w+)\s+to\s+(.+?)(?:\s+due|\s+role|\s+where|$)', sc, re.IGNORECASE)
            if m:
                person = m.group(1).strip()
                pref_task = m.group(2).strip()
                if person.lower() in [p.lower() for p in person_task]:
                    actual_task = None
                    for p, t in person_task.items():
                        if p.lower() == person.lower():
                            actual_task = t
                            break
                    if actual_task and task_matches_description(actual_task, pref_task):
                        score += 1
                    else:
                        score -= 0  # Don't penalize for not meeting soft
                continue
            
            # "prefer pairing X and Y" / "prefer X and Y together" / "prefer to pair X and Y"
            m = re.search(r'prefer\s+(?:to\s+)?pair(?:ing)?\s+(\w+)\s+(?:and|with)\s+(\w+)', sc, re.IGNORECASE)
            if m:
                p1, p2 = m.group(1), m.group(2)
                for task, persons in assignments.items():
                    persons_lower = [p.lower() for p in persons]
                    if p1.lower() in persons_lower and p2.lower() in persons_lower:
                        score += 1
                        break
                continue
            
            # "avoid pairing X and Y" / "avoid assigning X and Y together"
            m = re.search(r'avoid\s+(?:pairing|assigning)\s+(\w+)\s+(?:and|with)\s+(\w+)', sc, re.IGNORECASE)
            if m:
                p1, p2 = m.group(1), m.group(2)
                paired = False
                for task, persons in assignments.items():
                    persons_lower = [p.lower() for p in persons]
                    if p1.lower() in persons_lower and p2.lower() in persons_lower:
                        paired = True
                        break
                if not paired:
                    score += 1
                else:
                    score -= 1
                continue
            
            # "prefer X to Y role" or generic preferences
            # "prefer same-shift workers" - ignore (not verifiable)
            
        return score
    
    def score_synergies(assignments, synergy_list):
        """Score based on synergies (people paired together)"""
        score = 0
        for s1, s2 in synergy_list:
            for task, persons in assignments.items():
                persons_lower = [p.lower() for p in persons]
                if s1.lower() in persons_lower and s2.lower() in persons_lower:
                    score += 1
                    break
        return score
    
    def score_conflicts(assignments, conflict_list):
        """Penalize for conflicts (people paired together who shouldn't be)"""
        score = 0
        for c1, c2 in conflict_list:
            for task, persons in assignments.items():
                persons_lower = [p.lower() for p in persons]
                if c1.lower() in persons_lower and c2.lower() in persons_lower:
                    score -= 1
                    break
        return score
    
    # Parse all choices
    parsed_choices = []
    for choice in choices:
        assignments = parse_choice(choice)
        parsed_choices.append(assignments)
    
    # Evaluate each choice
    results = []
    for i, (choice_str, assignments) in enumerate(zip(choices, parsed_choices)):
        violations = count_hard_violations(assignments, hard_constraints)
        soft_score = score_soft_constraints(assignments, soft_constraints)
        syn_score = score_synergies(assignments, synergies)
        con_score = score_conflicts(assignments, conflicts)
        total_score = soft_score + syn_score + con_score
        is_valid = (violations == 0)
        results.append({
            'index': i,
            'choice': choice_str,
            'assignments': assignments,
            'violations': violations,
            'is_valid': is_valid,
            'soft_score': soft_score,
            'syn_score': syn_score,
            'con_score': con_score,
            'total_score': total_score,
        })
    
    # Find valid candidates
    valid_results = [r for r in results if r['is_valid']]
    
    if valid_results:
        # Among valid, pick highest total score
        valid_results.sort(key=lambda r: r['total_score'], reverse=True)
        best = valid_results[0]
        # If tie, use narrative-based heuristic
        if len(valid_results) > 1 and valid_results[0]['total_score'] == valid_results[1]['total_score']:
            # Use narrative matching as tiebreaker
            best = narrative_tiebreaker(valid_results, story, assignments_list=parsed_choices)
        return best['choice']
    else:
        # All invalid - pick the one with fewest violations
        results.sort(key=lambda r: (r['violations'], -r['total_score']))
        if len(results) > 1 and results[0]['violations'] == results[1]['violations']:
            # Tiebreak by total_score
            tied = [r for r in results if r['violations'] == results[0]['violations']]
            tied.sort(key=lambda r: r['total_score'], reverse=True)
            if len(tied) > 1 and tied[0]['total_score'] == tied[1]['total_score']:
                best = narrative_tiebreaker(tied, story, parsed_choices)
                return best['choice']
            return tied[0]['choice']
        return results[0]['choice']


def narrative_tiebreaker(candidates, story, assignments_list):
    """Use narrative context to break ties between candidates."""
    story_lower = story.lower()
    
    best = candidates[0]
    best_narrative_score = -999
    
    for r in candidates:
        ns = 0
        assignments = r['assignments']
        for task, persons in assignments.items():
            task_lower = task.lower()
            task_words = set(re.findall(r'\w+', task_lower))
            
            for person in persons:
                person_lower = person.lower()
                # Look for narrative evidence that this person is suited for this task
                # Search for sentences mentioning both the person and task-related keywords
                
                # Simple heuristic: count co-occurrences of person name and task keywords
                # in nearby text
                sentences = re.split(r'[.!?]', story)
                for sent in sentences:
                    sent_lower = sent.lower()
                    if person_lower in sent_lower:
                        for tw in task_words:
                            if len(tw) > 3 and tw in sent_lower:
                                ns += 1
                
                # Check for negative indicators (person struggles with task)
                negative_patterns = [
                    f'{person_lower}.*(?:struggle|fail|lack|poor|weak|cannot|fear|phobia|panic|forgot|botch|difficult)',
                ]
                for sent in sentences:
                    sent_lower = sent.lower()
                    if person_lower in sent_lower:
                        for tw in task_words:
                            if len(tw) > 3 and tw in sent_lower:
                                for neg in ['struggle', 'fail', 'lack', 'poor', 'weak', 'cannot', 'fear', 
                                           'phobia', 'panic', 'forgot', 'botch', 'difficult', 'faint',
                                           'limited', 'hesitant', 'uncomfortable', 'dislike', 'aversion',
                                           'never', 'no experience', 'missing']:
                                    if neg in sent_lower:
                                        ns -= 2
        
        if ns > best_narrative_score:
            best_narrative_score = ns
            best = r
    
    return best
