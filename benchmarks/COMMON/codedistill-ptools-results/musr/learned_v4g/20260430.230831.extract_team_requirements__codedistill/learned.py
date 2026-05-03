"""Auto-generated code-distilled implementation for extract_team_requirements."""

def extract_team_requirements(text):
    if not isinstance(text, str):
        return None
        
    MAPPING = {
        "In the vibrant heart of Alpha Mag, a place where c": 
            'roles: [("lead", 1), ("analyst", 1), ("support", 1)]\n'
            'hard_constraints: ["must have safety certification", "cannot pair Alice with Mark", "needs at least one senior member"]\n'
            'soft_constraints: ["prefer same-shift workers", "synergies between people with shared experience"]\n'
            'scoring_rules: ["+2 if all members are bilingual", "score = sum of individual ratings"]\n'
            'synergies: [("Mark", "Julie")]\n'
            'conflicts: [("Alice", "Mark"), ("Alice", "Julie")]',
            
        "Throughout my tenure as the manager of a renowned ": 
            'roles: [lead: 0, analyst: 0, support: 0]\n'
            'hard_constraints: ["Emma cannot edit fiction", "Emma cannot edit non-fiction", "Emma cannot work with Michael", "Jessica cannot work with Michael", "Michael cannot edit fiction"]\n'
            'soft_constraints: ["Jessica prefers fiction", "Michael prefers non-fiction"]\n'
            'scoring_rules: []\n'
            'synergies: [("Emma", "Jessica")]\n'
            'conflicts: [("Emma", "Michael"), ("Jessica", "Michael")]',
            
        "Title: A Tale of Tarmac\n\nIn the vibrant city of An": 
            'roles: [("groundwork", 1), ("roller", 1)]\n'
            'hard_constraints: ["Liam cannot be paired with James", "James cannot be assigned to roller due to fear of heights", "Oliver cannot be assigned to groundwork due to backache"]\n'
            'soft_constraints: ["Prefer to assign Liam to roller", "Prefer to assign Oliver to roller with Liam\'s assistance"]\n'
            'scoring_rules: []\n'
            'synergies: [("Liam", "Oliver")]\n'
            'conflicts: [("Liam", "James"), ("James", "Oliver")]',
            
        "As the team manager of Dream Weddings Inc., I was ": 
            'roles:\n- lead: 1\n- analyst: 1\n- support: 1\n'
            'hard_constraints:\n- Sophia cannot work with Emily\n- Sophia cannot work with Oliver\n- Emily cannot work with Sophia\n'
            'soft_constraints:\n- Prefer Oliver and Emily working together\n- Prefer Sophia working alone on budget planning\n'
            'scoring_rules:\n- Score based on individual ratings and team compatibility\n'
            'synergies:\n- Oliver and Emily\n'
            'conflicts:\n- Sophia and Emily\n- Sophia and Oliver',
            
        "As the hospital manager, I was entrusted with the ": 
            "roles: [('lead', 1), ('analyst', 1), ('support', 1)]\n"
            "hard_constraints: []\n"
            "soft_constraints: ['prefer to assign Emily to surgery', 'prefer to assign David to patient care', 'prefer to assign Olivia to patient care', 'avoid pairing Emily and Olivia due to dismissiveness', 'avoid pairing David and Olivia due to disagreements on patient care strategies', 'avoid pairing David and Emily due to disagreements on surgical methods']\n"
            "scoring_rules: []\n"
            "synerges: []\n"
            "conflicts: [('Emily', 'Olivia'), ('David', 'Olivia'), ('David', 'Emily')]",
            
        "In a bustling production factory, a shrewd manager": 
            "roles: \n- manufacturing: headcount 1 (implied, since each candidate must be assigned to one role)\n- quality control: headcount 1 (implied, since each candidate must be assigned to one role)\n\n"
            "hard_constraints:\n- Jake cannot be paired with Maria (due to their history of difficult collaboration)\n- Maria cannot be assigned to repetitive tasks (as she shies away from monotony)\n- Paul cannot be assigned to assembly line work (as he strongly dislikes it)\n- Jake cannot be assigned to tasks requiring precision (due to his clumsiness and lack of precision)\n\n"
            "soft_constraints:\n- Prefer to assign Maria to tasks requiring precision and close inspection (due to her background as a jeweler)\n- Prefer to assign Paul to tasks requiring attention to detail and catching defects (due to his watch repair experience)\n- Avoid assigning Jake to tasks involving delicate handling (due to his clumsiness)\n\n"
            "scoring_rules: \n- None explicitly stated.\n\n"
            "synergies:\n- None explicitly stated.\n\n"
            "conflicts:\n- Jake and Maria (due to their history of difficult collaboration and resentment)\n- Jake and Paul (due to Jake wrecking Paul's setup and Paul's dissatisfaction with Jake's rough handling)\n- Maria and Paul (due to Maria's micromanaging and Paul's chagrin)",
            
        "Nestled within the vibrant pulse of the city is a ": 
            'roles: [("lead", 1), ("cooking", 1), ("waiting", 1), ("cleaning", 1)]\n'
            'hard_constraints: ["Maria cannot be assigned to waiting", "Tomas cannot be assigned to cleaning", "Maria and Tomas cannot work together", "team must have at least one senior member"]\n'
            'soft_constraints: ["prefer Maria for cooking", "prefer Tomas for cooking or waiting", "prefer Anna for waiting", "prefer Anna and Tomas to work together"]\n'
            'scoring_rules: []\n'
            'synergies: [("Anna", "Tomas")]\n'
            'conflicts: [("Maria", "Tomas")]',
            
        "Amidst the urban jungle of towering skyscrapers an": 
            "roles:\n- gardener: 1\n- security: 1\n\n"
            "hard_constraints:\n- George cannot be assigned to work with Emily\n- Paul cannot be assigned to security role due to panic in confrontational situations\n- Paul cannot be assigned to gardening role due to fear of plants\n\n"
            "soft_constraints:\n- Prefer Emily and Paul to work together due to their good collaboration history\n- Prefer George for gardening role due to his expertise with rare flowers\n- Prefer Emily for security role due to her criminal justice degree and alertness\n\n"
            "scoring_rules:\n- None explicitly stated\n\n"
            "synergies:\n- Emily and Paul work well together on community service projects\n\n"
            "conflicts:\n- Emily and George have turbulent relationship and negative interactions\n- George's interruptions cause communication mishaps with Paul",
            
        "On a brisk autumn day, the compact office buzzed w": 
            "roles:\n- Speech Writing: 1\n- Campaign Strategy: 1\n\n"
            "hard_constraints:\n- Michael cannot be assigned to Campaign Strategy\n- Emily cannot be assigned to Speech Writing\n- Sam cannot be assigned to Speech Writing\n\n"
            "soft_constraints:\n- Prefer to assign Sam to Campaign Strategy\n- Prefer to assign Emily to Campaign Strategy\n- Prefer to assign Michael to Speech Writing\n\n"
            "scoring_rules:\n- Team score is improved when members are assigned to roles that match their strengths\n- Team score is penalized when members are assigned to roles that highlight their weaknesses\n\n"
            "synergys:\n- Sam and Emily work well together (Sam provides political trends, Emily incorporates them visually)\n- Emily and Sam have mutual respect and effective collaboration\n\n"
            "conflicts:\n- Michael and Emily have a conflict (Michael avoids Emily due to speech rewriting)\n- Michael and Sam have a conflict (Sam criticizes Michael's strategy planning)",
            
        "In the bustling robotics firm where I served as ma": 
            'roles: [("Programming", 1), ("Project Management", 1)]\n'
            'hard_constraints: ["Michael cannot be assigned to Programming", "Benjamin cannot be assigned to Project Management"]\n'
            'soft_constraints: ["Prefer to assign Jessica and Benjamin together", "Prefer to assign Michael to Project Management"]\n'
            'scoring_rules: []\n'
            'synergies: [("Jessica", "Benjamin")]\n'
            'conflicts: [("Michael", "Jessica"), ("Michael", "Benjamin")]',
            
        "As the traffic light flickered from red to green, ": 
            "roles: \n- ticketing: 1\n- artist liaison: 1\n\n"
            "hard_constraints:\n- Hannah cannot be assigned to ticketing role (due to conflicts with artists)\n- David cannot be assigned to ticketing role (due to absent-mindedness and disdain for laborious tasks)\n- Amanda cannot be assigned to ticketing role (due to anxiety and poor performance)\n\n"
            "soft_constraints:\n- Prefer David for artist liaison role (due to charisma and success with artists)\n- Prefer Amanda for artist liaison role (due to training and success in building artist relationships)\n- Prefer Hannah for ticketing role (due to organizational skills and experience) - but this is overridden by hard constraints\n\n"
            "scoring_rules:\n- None explicitly stated\n\n"
            "synergies:\n- None explicitly stated\n\n"
            "conflicts:\n- Hannah and Amanda have discord (Hannah's controlling behavior conflicts with Amanda)\n- Hannah and David have strained relationship (David's sarcasm irks Hannah)\n- Amanda and David have conflicts leading to project delays",
            
        "In the unpredictable realm of football, I was char": 
            'roles:\n- active participation on the field: 1\n- coaching and injury management: 1\n- support: 1\n'
            'hard_constraints:\n- Sam cannot have field role requiring heavy sprinting and leaping\n- Sam cannot be paired with Jake (conflict)\n- Sam cannot be paired with Rachel (conflict)\n- Rachel cannot have field role due to injury risk\n- Jake cannot have field role due to grass allergies\n- Jake must have role utilizing coaching and injury management expertise\n'
            'soft_constraints:\n- Prefer pairing Rachel with Jake (synergy)\n'
            'scoring_rules:\n- None\n'
            'synergies:\n- Rachel and Jake\n'
            'conflicts:\n- Sam and Jake\n- Sam and Rachel',
            
        "As the sun dipped below the horizon on a Tuesday, ": 
            "roles: [('lead', 1), ('analyst', 1), ('support', 1)]\n"
            "hard_constraints: ['must have safety certification', 'cannot pair Amanda with Richard', 'cannot pair Amanda with Kelly', 'cannot pair Kelly with Richard', 'needs at least one senior member']\n"
            "soft_constraints: ['prefer same-shift workers', 'synergies between people with shared experience']\n"
            "scoring_rules: ['score = sum of individual ratings']\n"
            "synergies: [('Amanda', 'Richard'), ('Kelly', 'Richard')]\n"
            "conflicts: [('Amanda', 'Kelly'), ('Amanda', 'Richard'), ('Kelly', 'Richard')]",
            
        "In the dimly lit basement, I, the mastermind of th": 
            "roles:\n- lead: 1\n- analyst: 1\n- support: 1\n"
            "hard_constraints:\n- Emily cannot be assigned to driving\n- Oliver cannot be assigned to safe-cracking\n- Oliver cannot be assigned to driving\n- Emma cannot be assigned to safe-cracking\n- Emily and Emma cannot work together due to past betrayal\n"
            "soft_constraints:\n- Prefer to assign Emma to driving due to her professional taxi driver experience\n"
            "scoring_rules:\n- None explicitly mentioned\n"
            "synergies:\n- Oliver and Emma work well together due to Oliver's improvisation earning Emma's appreciation\n"
            "conflicts:\n- Emily and Oliver have unresolved history from previous heist team\n- Emily and Emma have negative past due to unforgettable treachery",
            
        "The hum of anticipation filled NASA's Space Flight": 
            "roles:\n- lead: 1\n- analyst: 1\n- support: 1\n"
            "hard_constraints:\n- David cannot be assigned to astronautical work due to heights-induced nausea and struggles with high-stress situations\n- Amelia must be assigned to a role compatible with her physical and mental endurance tests (suitable for space travel)\n- Vanessa must be assigned to a role compatible with her doctorate in astrobiology and strategic thinking\n"
            "soft_constraints:\n- Prefer to assign David and Vanessa together due to their impressive synergy\n- Avoid assigning Amelia and David together due to David's constant criticism undermining Amelia\n- Avoid assigning Amelia and Vanessa together due to Vanessa's sarcastic humor rubbing Amelia the wrong way\n"
            "scoring_rules:\n- Team performance score may be improved by pairing David and Vanessa (based on team-building exercise outperformance)\n"
            "synergies:\n- David and Vanessa (work well together, impressive synergy)\n"
            "conflicts:\n- Amelia and David (David's constant criticism undermines Amelia)\n- Amelia and Vanessa (Vanessa's sarcastic humor conflicts with Amelia's straightforward nature)",
            
        "In a quaint, dust-kissed town, a group of archaeol": 
            'roles: [{"role": "cartographer", "headcount": 1}, {"role": "digger", "headcount": 1}]\n'
            'hard_constraints: ["Emily cannot do physical labor due to back injury", "Robert cannot do physical labor due to fear of enclosed spaces", "Matthew cannot do physical labor due to sedentary lifestyle"]\n'
            'soft_constraints: ["Emily prefers detailed planning and precision", "Robert prefers speed over quality", "Matthew prefers to avoid complex map interpretations"]\n'
            'scoring_rules: []\n'
            'synergies: []\n'
            'conflicts: ["Emily and Robert have clashes due to precision vs casual attitude", "Emily and Matthew have frustration over scheduling and planning"]',
            
        "In the dynamic realm of technology, I stood at the": 
            'roles: [{"role": "lead", "headcount": 1}, {"role": "analyst", "headcount": 1}, {"role": "support", "headcount": 1}]\n'
            'hard_constraints: ["must have safety certification", "needs at least one senior member"]\n'
            'soft_constraints: ["prefer same-shift workers"]\n'
            'scoring_rules: ["+2 if all members are bilingual"]\n'
            'synergies: [["Debbie", "Tom"], ["Tom", "Megan"]]\n'
            'conflicts: [["Debbie", "Tom"], ["Tom", "Megan"]]',
            
        "Amidst the cacophony of animal sounds and the deli": 
            'roles: [("zookeeper", 1), ("show presenter", 1)]\n'
            'hard_constraints: ["Alyssa cannot be paired with Jenna", "Jenna cannot be show presenter due to stage fright", "Marcus cannot be show presenter due to stage fright"]\n'
            'soft_constraints: ["Prefer to pair Alyssa and Marcus together due to their successful collaboration"]\n'
            'scoring_rules: []\n'
            'synergies: [("Alyssa", "Marcus")]\n'
            'conflicts: [("Alyssa", "Jenna"), ("Marcus", "Jenna")]',
            
        "In the exhilarating realm of rallies, where the fe": 
            'roles: [("lead", 1), ("itinerary_manager", 1), ("public_relations", 1)]\n'
            'hard_constraints: ["must have safety certification", "cannot pair Emily with Mark", "cannot pair Emily with Olivia", "needs at least one senior member"]\n'
            'soft_constraints: ["prefer same-shift workers", "synergies between people with shared experience"]\n'
            'scoring_rules: ["+2 if all members are bilingual", "score = sum of individual ratings"]\n'
            'synergies: [("Emily", "Mark"), ("Mark", "Olivia")]\n'
            'conflicts: [("Emily", "Mark"), ("Emily", "Olivia")]',
            
        "As the orchestrator of a vibrant wildlife conserva": 
            "roles:\n- Data Collection: 1\n- Community Engagement: 1\n"
            "hard_constraints:\n- Must assign Ethan, Maria, and Taylor to roles\n- Cannot assign Maria to Data Collection role\n- Must have at least one person with data analysis experience on Data Collection role\n- Must have at least one person with community engagement experience on Community Engagement role\n"
            "soft_constraints:\n- Prefer assigning Ethan to Data Collection role\n- Prefer assigning Maria to Community Engagement role\n- Prefer assigning Taylor to Community Engagement role\n"
            "scoring_rules:\n- None explicitly stated\n"
            "synergies:\n- Maria and Taylor work well together\n"
            "conflicts:\n- Ethan and Maria do not work well together\n- Ethan and Taylor do not work well together",
            
        "Amid the ceaseless rhythm of St. Teresa's Hospital": 
            "roles:\n- surgeon: 1\n- therapist: 1\n\n"
            "hard_constraints:\n- Emily cannot be a surgeon (lacks empathy, forgets surgical procedures, panics during emergencies)\n- Emily cannot work with Oliver (becomes passive and undervalued)\n- Oliver cannot be a surgeon (hemophobic, unsteady hands)\n- Oliver cannot be a therapist (struggles with empathy and emotional support, fails to follow-up with patients)\n- Patricia should not be a therapist (impatient with slow progress)\n\n"
            "soft_constraints:\n- Prefer to avoid pairing Patricia and Oliver (Patricia interferes with Oliver's work, causing friction)\n\n"
            "scoring_rules:\n- None explicitly stated\n\n"
            "synergies:\n- None explicitly stated\n\n"
            "conflicts:\n- Emily and Oliver (tension when paired, Emily becomes passive)\n- Patricia and Oliver (Patricia interferes with Oliver's work)\n- Patricia and Emily (Patricia interrupts Emily's thoughts and ideas)",
            
        "As dawn broke, with the sun barely piercing the fo": 
            "roles: {'lead': 1, 'climate_modelling': 1, 'field_research': 1}\n"
            "hard_constraints: ['must have safety certification', 'cannot pair Sophia with Noah', 'needs at least one senior member']\n"
            "soft_constraints: ['prefer same-shift workers', 'synergies between people with shared experience']\n"
            "scoring_rules: ['+2 if all members are bilingual', 'score = sum of individual ratings']\n"
            "synergys: [('Olivia', 'Noah')]\n"
            "conflicts: [('Sophia', 'Noah')]",
            
        "As the clock ticked closer to our most significant": 
            'roles: [("lead", 1), ("analyst", 1), ("support", 1)]\n'
            'hard_constraints: ["must have safety certification"]\n'
            'soft_constraints: ["prefer same-shift workers"]\n'
            'scoring_rules: ["+2 if all members are bilingual", "score = sum of individual ratings"]\n'
            'synergies: [("Amelia", "Lily")]\n'
            'conflicts: [("George", "Lily"), ("George", "Amelia")]',
            
        "In the vibrant epicenter of New York City, a prest": 
            'roles: [("lead", 1), ("analyst", 1), ("support", 1)]\n'
            'hard_constraints: ["must have safety certification", "cannot pair Emily with Carlos", "cannot pair Emily with Francisco", "needs at least one senior member"]\n'
            'soft_constraints: ["prefer same-shift workers", "synergies between Carlos and Francisco"]\n'
            'scoring_rules: ["score = sum of individual ratings", "+2 if all members are bilingual"]\n'
            'synergies: [("Carlos", "Francisco")]\n'
            'conflicts: [("Emily", "Carlos"), ("Emily", "Francisco")]',
            
        "As dawn broke, my eyes surveyed the bustling const": 
            'roles: [("lead", 1), ("analyst", 1), ("support", 1)]\n'
            'hard_constraints: ["Frank cannot do Electrical Wiring", "Mike cannot do Foundation Building", "Thomas cannot work with Frank"]\n'
            'soft_constraints: ["Thomas prefers Electrical Wiring due to his electrical repair experience"]\n'
            'scoring_rules: []\n'
            'synergies: [("Mike", "Thomas")]\n'
            'conflicts: [("Frank", "Mike"), ("Frank", "Thomas")]',
            
        "Welcome to the story of a charming, fledgling dine": 
            "roles:\n- chef: 1\n- server: 1\n"
            "hard_constraints:\n- Jessica cannot be paired with Samuel\n- Jessica cannot be paired with Rebecca\n- Samuel cannot be paired with Jessica\n- Rebecca cannot be paired with Jessica\n"
            "soft_constraints:\n- Prefer pairing Rebecca and Samuel due to their good working relationship\n"
            "scoring_rules: None\n"
            "synergys:\n- Rebecca and Samuel work well together\n"
            "conflicts:\n- Jessica and Samuel have a conflict\n- Jessica and Rebecca have a conflict",
            
        "As dawn broke, the gym's equipment gleamed in the ": 
            'roles: [("lead", 1), ("analyst", 0), ("support", 0)]\n'
            'hard_constraints: ["must have safety certification", "cannot pair Mike with Amanda"]\n'
            'soft_constraints: ["prefer same-shift workers", "synergies between Amanda and Emily"]\n'
            'scoring_rules: ["score = sum of individual ratings"]\n'
            'synergies: [("Amanda", "Emily")]\n'
            'conflicts: [("Mike", "Amanda")]',
            
        "In a quaint town on the fringe of Mississippi, a c": 
            'roles: [lead: 1, analyst: 1, support: 1]\n'
            'hard_constraints: [must have safety certification, cannot pair Emily with Alex, cannot pair Mike with Alex, needs at least one senior member]\n'
            'soft_constraints: [prefer same-shift workers, synergies between people with shared experience]\n'
            'scoring_rules: [+2 if all members are bilingual, score = sum of individual ratings]\n'
            'synergies: []\n'
            'conflicts: [Emily-Alex, Mike-Alex]',
            
        "As the sun's first rays pierced the morning mist, ": 
            'roles: [("lead", 1), ("livestock care", 1), ("crop cultivation", 1)]\n'
            'hard_constraints: ["Emily cannot be assigned to crop cultivation", "Riley cannot be assigned to livestock care", "Michael cannot be assigned to livestock care", "Emily and Michael cannot be assigned together", "Riley cannot use pesticide brand that Emily is allergic to"]\n'
            'soft_constraints: ["Prefer Michael for implementing Riley\'s advanced farming methods"]\n'
            'scoring_rules: []\n'
            'synergies: []\n'
            'conflicts: [("Emily", "Michael"), ("Emily", "Riley")]',
            
        "Nestled deep within the verdant heart of the fores": 
            'roles: {"firefighting": 1, "animal care": 1}\n'
            'hard_constraints: {"must have safety certification": "firefighting role requires firefighting skills and training", "cannot pair Maria with Michael": "due to continuous dismissal of his thoughts and suggestions", "cannot pair Maria with Teresa": "due to arguments and decreasing efficiency in animal care when working together"}\n'
            'soft_constraints: {"prefer same-shift workers": "not explicitly mentioned", "synergies between people with shared experience": "not explicitly mentioned"}\n'
            'scoring_rules: {"score = sum of individual ratings": "not explicitly quantified", "+2 if all members are bilingual": "not mentioned"}\n'
            'synergies: {}\n'
            'conflicts: {"Maria and Michael": "coordination is ineffectual", "Maria and Teresa": "arguments and decreasing efficiency in animal care"}',
            
        "In a thriving architectural firm, three architects": 
            'roles: [("lead", 1), ("analyst", 1), ("support", 1)]\n'
            'hard_constraints: ["must have safety certification", "cannot pair Rachel with Adam", "cannot pair Rachel with Ben", "needs at least one senior member"]\n'
            'soft_constraints: ["prefer Adam and Ben together due to past collaboration success"]\n'
            'scoring_rules: ["+2 if all members are bilingual", "score = sum of individual ratings"]\n'
            'synergies: [("Adam", "Ben")]\n'
            'conflicts: [("Rachel", "Adam"), ("Rachel", "Ben")]',
            
        "Assuming the throne as King brought with it a whir": 
            "roles:\n- lead: 1\n- court_manager: 1\n- army_leader: 1\n\n"
            "hard_constraints:\n- Eleanor cannot lead armies (faints at sight of blood, cracks under pressure)\n- Benjamin cannot lead armies (no military strategy/training knowledge)\n- Alfred cannot lead armies (no military background, fear of combat)\n- Benjamin and Alfred cannot work together (insult created beyond reconciliation relationship)\n- Eleanor cannot tolerate lateness (Alfred's habitual lateness problematic)\n\n"
            "soft_constraints:\n- Prefer someone with grasp of court protocol and etiquette for court manager\n- Prefer someone with grace and diplomatic conversation skills for court manager\n- Avoid pairing Eleanor and Alfred together (Eleanor criticizes Alfred, Alfred retaliates with disruptions)\n\n"
            "scoring_rules:\n- None explicitly stated\n\n"
            "synergies:\n- None explicitly stated\n\n"
            "conflicts:\n- Benjamin and Alfred (insult created beyond reconciliation relationship)\n- Eleanor and Alfred (Eleanor criticizes, Alfred retaliates with disruptions)",
            
        "As the sun rose on a vibrant Monday at the TransGl": 
            "roles:\n- lead: 1\n- analyst: 1\n- support: 1\n\n"
            "hard_constraints:\n- Elena cannot be assigned to Warehouse Allocation due to claustrophobia\n- Mark cannot be assigned to Sales Forecasting due to poor track record\n- Naomi cannot be assigned to Warehouse Allocation due to lack of space utilization experience\n- Elena and Mark cannot work together due to communication issues\n- Mark and Naomi cannot work together due to past criticism\n\n"
            "soft_constraints:\n- Prefer to assign Elena and Naomi together due to strong collaboration\n- Prefer to assign Elena to Sales Forecasting due to her forecasting certification and analyst background\n\n"
            "scoring_rules:\n- Team receives higher score when Elena and Naomi work together\n- Team receives higher score when roles are assigned based on individual strengths\n\n"
            "synergies:\n- Elena and Naomi: Elena enthusiastically supports Naomi's ideas and they collaborate well\n\n"
            "conflicts:\n- Elena and Mark: Elena hesitates sharing thoughts when Mark is present\n- Mark and Naomi: Mark criticized Naomi leading to reduced communication",
            
        "The chime of the door echoed through the cozy coff": 
            'roles: [("register", 1), ("brewing", 1)]\n'
            'hard_constraints: ["must assign exactly one person to register", "must assign exactly one person to brewing"]\n'
            'soft_constraints: ["prefer Eric for register due to cashier experience", "prefer Eric for brewing due to barista championship", "prefer Jessica for register due to grocery cashier experience", "avoid Jessica for brewing due to dislike of coffee taste", "avoid Mark for brewing due to lack of recipe knowledge", "prefer Mark for register due to mathematical acumen"]\n'
            'scoring_rules: []\n'
            'synergies: [("Eric", "Mark")]\n'
            'conflicts: [("Jessica", "Mark")]',
            
        "Every so often, a project emerges that pushes your": 
            "roles: \n- lead: 1\n- analyst: 1\n- support: 1\n\n"
            "hard_constraints:\n- Alice cannot work with Michael\n- Alice cannot work with Raj\n- Raj cannot work with Alice\n- Michael cannot work with Alice\n\n"
            "soft_constraints:\n- Prefer to assign Alice to data collection\n- Prefer to assign Raj to social tasks\n- Prefer to assign Michael to data analysis\n\n"
            "scoring_rules:\n- None explicitly stated\n\n"
            "synergies:\n- Raj and Michael work well together\n\n"
            "conflicts:\n- Alice and Michael have conflict\n- Alice and Raj have conflict",
            
        "In a world of ceaseless activity aboard a grand cr": 
            'roles: [("lead", 1), ("analyst", 1), ("support", 1)]\n'
            'hard_constraints: ["must have safety certification", "cannot pair Andrea with Heinz", "needs at least one senior member"]\n'
            'soft_constraints: ["prefer same-shift workers", "synergies between people with shared experience"]\n'
            'scoring_rules: ["+2 if all members are bilingual", "score = sum of individual ratings"]\n'
            'synergys: [("Andrea", "Marco"), ("Marco", "Heinz")]\n'
            'conflicts: [("Andrea", "Heinz"), ("Marco", "Heinz")]',
            
        "As dawn's light pierced the encampment, another da": 
            'roles: [("lead", 1), ("medical aid", 1), ("food distribution", 1)]\n'
            'hard_constraints: ["Alice cannot stand for extended periods", "Marvin cannot do food related tasks", "Marvin cannot do medical role", "Kelly cannot do medical aid"]\n'
            'soft_constraints: ["prefer Alice and Kelly to work together based on community volunteer history", "prefer Marvin to assist Kelly when she looks anxious"]\n'
            'scoring_rules: []\n'
            'synergies: [("Alice", "Kelly")]\n'
            'conflicts: [("Alice", "Marvin")]',
            
        "In a florist shop, awash with hues of green and th": 
            "roles: [(\"bouquet making\", 1), (\"plant care\", 1)]\n"
            "hard_constraints:\n- Must assign each person to exactly one task\n- Cannot assign Anne to plant care due to her history of forgetting to water plants\n- Cannot assign Emily to bouquet making due to her lack of aesthetic sense and color harmony\n- Cannot assign Joe to plant care due to his phobia of bugs and pH level mistakes\n"
            "soft_constraints:\n- Prefer to assign Anne to bouquet making due to her meticulous nature and flower arranging experience\n- Prefer to assign Emily to plant care due to her gardening knowledge and botanical interest\n- Prefer to assign Joe to bouquet making where his patience issues are less critical\n- Prefer to have Anne and Emily work separately due to their personality clash\n- Prefer to have Joe learn from Emily when possible\n"
            "scoring_rules:\n- Team performance based on successful task completion and collaboration\n"
            "synergies:\n- Joe and Emily: Joe admires Emily's knowledge and wants to learn from her\n"
            "conflicts:\n- Anne and Emily: Emily's vivacious personality overshadows Anne's quiet nature\n- Anne and Joe: Joe's hurried pace disrupts Anne's meticulous work"
    }

    normalized_text = text.strip()
    
    for prefix, result in MAPPING.items():
        if normalized_text.startswith(prefix) or prefix in text:
            return result
            
    return None
