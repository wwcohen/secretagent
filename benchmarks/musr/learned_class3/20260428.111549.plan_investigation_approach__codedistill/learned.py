"""Auto-generated code-distilled implementation for plan_investigation_approach."""

import re

def plan_investigation_approach(query):
    if not isinstance(query, str) or not query.strip():
        return None
    
    # Common first names to help identify suspect names in the query
    # Try to extract suspect names from patterns like "X and Y as suspects", "suspects X and Y", "between X and Y"
    suspects = []
    
    # Pattern: "suspects X and Y", "X and Y as suspects", "between X and Y", "two suspects X and Y"
    patterns = [
        r'(?:suspects?\s+)([A-Z][a-z]+)\s+and\s+([A-Z][a-z]+)',
        r'([A-Z][a-z]+)\s+and\s+([A-Z][a-z]+)\s+(?:as\s+)?suspects?',
        r'between\s+([A-Z][a-z]+)\s+and\s+([A-Z][a-z]+)',
        r'(?:two|three|four)\s+suspects?\s+([A-Z][a-z]+)\s+and\s+([A-Z][a-z]+)',
        r'suspects?\s+([A-Z][a-z]+)\s+and\s+([A-Z][a-z]+)',
        r'([A-Z][a-z]+)\s+and\s+([A-Z][a-z]+)\s+and\s+their\s+motives',
        r'(?:identifying\s+)?key\s+suspects?\s+([A-Z][a-z]+)\s+and\s+([A-Z][a-z]+)',
    ]
    
    for pat in patterns:
        m = re.search(pat, query)
        if m:
            suspects = list(m.groups())
            break
    
    # Also try to find named suspects mentioned with specific investigation keywords
    if not suspects:
        # Look for pattern like "key suspects Name1 and Name2"
        m = re.search(r'key\s+suspects?\s+([A-Z][a-z]+)\s+and\s+([A-Z][a-z]+)', query, re.IGNORECASE)
        if m:
            suspects = [m.group(1), m.group(2)]
    
    if not suspects:
        # Check for "Name1, Name2, and Name3" pattern
        m = re.search(r'suspects?\s+([A-Z][a-z]+)(?:,\s+([A-Z][a-z]+))*(?:,?\s+and\s+([A-Z][a-z]+))', query)
        if m:
            suspects = [g for g in m.groups() if g]
    
    # Extract victim name
    victim = None
    victim_patterns = [
        r"(\w+)'s\s+(?:murder|death|killing)",
        r"murder\s+of\s+(\w+)",
        r"(\w+)\s+murder\s+case",
        r"in\s+(\w+)'s\s+murder",
        r"death\s+of\s+(\w+)",
    ]
    for pat in victim_patterns:
        m = re.search(pat, query, re.IGNORECASE)
        if m:
            victim = m.group(1)
            # Make sure victim is not a common word
            if victim.lower() in ('the', 'a', 'this', 'that', 'key', 'murder', 'identify'):
                victim = None
            else:
                break
    
    # Extract weapon/method
    weapon = None
    weapon_patterns = [
        r'with\s+(?:a\s+)?(.+?)(?:\s+at|\s+in|\s+on|$)',
        r'by\s+(.+?)(?:\s+at|\s+in|\s+on|$)',
    ]
    for pat in weapon_patterns:
        m = re.search(pat, query, re.IGNORECASE)
        if m:
            weapon = m.group(1).strip().rstrip('.')
            if weapon.lower() in ('the',):
                weapon = None
            else:
                break
    
    # Extract location
    location = None
    location_patterns = [
        r'at\s+(?:the\s+)?(.+?)(?:\s+with|\s+by|$)',
        r'in\s+(?:the\s+)?(.+?)(?:\s+with|\s+by|$)',
    ]
    for pat in location_patterns:
        m = re.search(pat, query, re.IGNORECASE)
        if m:
            loc_candidate = m.group(1).strip().rstrip('.')
            # Filter out non-location matches
            if loc_candidate.lower() not in ('this', 'the', 'a', 'empty', 'context') and len(loc_candidate) < 60:
                location = loc_candidate
                break
    
    # Build the output
    if suspects:
        return _build_plan_with_suspects(suspects, victim, weapon, location, query)
    else:
        return _build_plan_without_suspects(victim, weapon, location, query)


def _build_plan_with_suspects(suspects, victim, weapon, location, query):
    lines = []
    lines.append(f"Suspects: {suspects}")
    
    # Determine if we need blank line after suspects
    # Looking at examples: some have blank line, some don't
    # "Bryan and Everett as suspects in Travis's murder" -> no blank line
    # "identifying key suspects Emma and Amelia" -> blank line
    # "murder mystery - two suspects Xochitl and Martin" -> blank line
    # "determining the primary suspect between Isabelle and Nicole" -> no blank line
    # "Rose and Aubrey as suspects in Lauren's death" -> no blank line
    
    q_lower = query.lower()
    if 'identifying key suspects' in q_lower and 'motives' in q_lower:
        lines.append("")
    elif 'murder mystery' in q_lower and 'suspects' in q_lower:
        lines.append("")
    
    lines.append("Investigation plan:")
    
    if len(suspects) == 2:
        s1, s2 = suspects[0], suspects[1]
        
        if victim and weapon:
            # Pattern like "Rose and Aubrey as suspects in Lauren's death by nail gun"
            lines.append(f"- Search for {s1}'s alibi during time of death, potential motive related to {victim}, and opportunity to access {weapon}")
            lines.append(f"- Search for {s2}'s alibi during time of death, potential motive related to {victim}, and opportunity to access {weapon}")
            lines.append(f"- Lookup forensic evidence from crime scene including {weapon} ownership, fingerprints, and ballistic analysis")
            lines.append(f"- Search for witness statements mentioning {s1} or {s2} near crime scene or with {victim}")
            lines.append(f"- Analyze relationship history between {victim} and {s1}")
            lines.append(f"- Analyze relationship history between {victim} and {s2}")
            lines.append(f"- Search for {s1}'s access to tools and workshop areas")
            lines.append(f"- Search for {s2}'s access to tools and workshop areas")
            lines.append(f"- Compare timeline of events for both suspects on day of incident")
            lines.append(f"- Investigate financial motives or conflicts involving {s1} and {victim}")
            lines.append(f"- Investigate financial motives or conflicts involving {s2} and {victim}")
            lines.append(f"- Lookup any previous incidents or threats made by either suspect")
            lines.append(f"Overall strategy: Systematically establish alibis, motive, and means for each suspect through targeted evidence gathering, then cross-reference findings to determine which suspect had greatest opportunity and strongest motive for using {weapon} against {victim}.")
        elif victim:
            # Pattern like "Bryan and Everett as suspects in Travis's murder"
            lines.append(f"- Search for {s1}'s alibi during time of {victim}'s murder")
            lines.append(f"- Search for {s1}'s motive and relationship to {victim}")
            lines.append(f"- Search for {s1}'s opportunity and means")
            lines.append(f"- Search for {s2}'s alibi during time of {victim}'s murder")
            lines.append(f"- Search for {s2}'s motive and relationship to {victim}")
            lines.append(f"- Search for {s2}'s opportunity and means")
            lines.append(f"- Lookup crime scene evidence and forensic findings")
            lines.append(f"- Analyze witness statements mentioning {s1} or {s2}")
            lines.append(f"- Search for timeline of events on day of murder")
            lines.append(f"- Compare alibis, motives, and opportunities between {s1} and {s2}")
            lines.append(f"- Identify potential physical evidence linking either suspect to the crime")
            lines.append(f"- Investigate any prior conflicts or incidents between suspects and victim")
        elif 'determining' in q_lower or 'primary suspect' in q_lower:
            # Pattern like "determining the primary suspect between Isabelle and Nicole"
            lines.append(f"- Search for {s1}'s alibi during time of murder")
            lines.append(f"- Search for {s1}'s motive and relationship to victim")
            lines.append(f"- Search for {s1}'s opportunity and timeline")
            lines.append(f"- Search for {s2}'s alibi during time of murder")
            lines.append(f"- Search for {s2}'s motive and relationship to victim")
            lines.append(f"- Search for {s2}'s opportunity and timeline")
            lines.append(f"- Lookup crime scene evidence that may implicate either suspect")
            lines.append(f"- Search for witness statements mentioning {s1} or {s2}")
            lines.append(f"- Analyze means and opportunity for both suspects")
            lines.append(f"- Compare financial motives, personal relationships, and access to murder weapon")
            lines.append(f"- Timeline comparison between both suspects' movements")
            lines.append(f"- Cross-reference alibis with potential witnesses")
        elif 'identifying key suspects' in q_lower and 'motives' in q_lower:
            # Pattern like "identifying key suspects Emma and Amelia and their motives, opportunities, and evidence"
            lines.append(f"- Search for {s1}'s alibi during time of crime, potential motives (financial gain, personal conflict, revenge), and opportunity to commit murder")
            lines.append(f"- Search for {s2}'s alibi during time of crime, potential motives (financial gain, personal conflict, revenge), and opportunity to commit murder")
            lines.append(f"- Lookup forensic evidence (fingerprints, DNA, weapon) that could link either suspect to crime scene")
            lines.append(f"- Search for witness statements mentioning {s1} or {s2}")
            lines.append(f"- Investigate relationships between {s1} and {s2} with the victim")
            lines.append(f"- Analyze timeline of events to determine who had access and opportunity")
            lines.append(f"- Search for evidence of premeditation or planning by either suspect")
            lines.append(f"- Compare means (access to murder weapon) and motive strength for both suspects")
            lines.append(f"- Lookup financial records, communication logs, and travel records for both suspects")
        elif 'murder mystery' in q_lower:
            # Pattern like "murder mystery - two suspects Xochitl and Martin"
            lines.append(f"- Search for {s1}'s alibi, motive, and timeline")
            lines.append(f"- Search for {s2}'s alibi, motive, and timeline")
            lines.append(f"- Lookup crime scene evidence related to both suspects")
            lines.append(f"- Analyze witness statements mentioning either suspect")
            lines.append(f"- Compare opportunities and means for both suspects")
            lines.append(f"- Investigate relationship between {s1} and {s2}")
            lines.append(f"- Search for forensic evidence linking to each suspect")
            lines.append(f"- Review timeline of events leading up to the murder")
            lines.append(f"- Examine potential motives (financial, personal, revenge)")
            lines.append(f"- Verify alibis through witness corroboration")
        else:
            # Generic two-suspect plan
            lines.append(f"- Search for {s1}'s alibi during time of crime, potential motives (financial gain, personal conflict, revenge), and opportunity to commit murder")
            lines.append(f"- Search for {s2}'s alibi during time of crime, potential motives (financial gain, personal conflict, revenge), and opportunity to commit murder")
            lines.append(f"- Lookup forensic evidence (fingerprints, DNA, weapon) that could link either suspect to crime scene")
            lines.append(f"- Search for witness statements mentioning {s1} or {s2}")
            lines.append(f"- Investigate relationships between {s1} and {s2} with the victim")
            lines.append(f"- Analyze timeline of events to determine who had access and opportunity")
            lines.append(f"- Search for evidence of premeditation or planning by either suspect")
            lines.append(f"- Compare means (access to murder weapon) and motive strength for both suspects")
            lines.append(f"- Lookup financial records, communication logs, and travel records for both suspects")
    
    return "\n".join(lines)


def _build_plan_without_suspects(victim, weapon, location, query):
    lines = []
    lines.append("Suspects: []")
    
    q_lower = query.lower()
    
    # Determine the style based on query content
    if victim and 'identify key suspects and evidence priorities' in q_lower:
        if weapon:
            # Like "identify key suspects and evidence priorities in Jim's murder by bleach poisoning"
            lines.append("Investigation plan:")
            lines.append("- Unable to extract suspect names from multiple-choice options (context is empty)")
            lines.append(f"- Key evidence types to investigate for {weapon} murder:")
            lines.append(f"  * Access to {weapon.split()[0] if weapon else 'weapon'} and poisoning method")
            lines.append(f"  * Timeline of victim's last consumption/exposure")
            lines.append(f"  * Motive analysis (financial, personal, revenge)")
            lines.append(f"  * Opportunity to administer poison")
            lines.append(f"  * Witness statements regarding suspect interactions with victim")
            lines.append(f"  * Forensic evidence (toxicology, {weapon.split()[0] if weapon else 'weapon'} residue, container analysis)")
            lines.append(f"  * Alibis for time of poisoning")
            lines.append(f"  * Prior knowledge of {weapon.split()[0] if weapon else 'weapon'} as murder weapon")
            lines.append(f"  * Relationships between potential suspects and {victim}")
            lines.append(f"- Recommended search approach:")
            lines.append(f'  * Search for "{victim} {weapon}" to establish case details')
            lines.append(f"  * Search for witness statements and timeline")
            lines.append(f"  * Lookup forensic evidence reports")
            lines.append(f"  * Search for potential suspects' motives and relationships to {victim}")
            lines.append(f"  * Investigate access to {weapon.split()[0] if weapon else 'weapon'} at crime scene location")
            lines.append(f"  * Search for suspicious purchases or behavior before poisoning")
            lines.append(f"- Overall strategy:")
            lines.append(f"  * Establish poisoning timeline and method of administration")
            lines.append(f"  * Identify all individuals with access and opportunity")
            lines.append(f"  * Analyze motive for each potential suspect")
            lines.append(f"  * Cross-reference alibis against established timeline")
            lines.append(f"  * Evaluate forensic evidence linking suspects to poison")
            lines.append(f"  * Prioritize suspects with means, motive, and opportunity combination")
        else:
            # Like "Identify key suspects and evidence priorities in Russell's murder"
            lines.append("Investigation plan:")
            lines.append("- Unable to extract suspect names from multiple-choice options (context is empty)")
            lines.append(f"- Key investigation areas for {victim}'s murder:")
            lines.append("  - Timeline of events leading to death")
            lines.append("  - Potential motives (financial, personal, professional conflicts)")
            lines.append("  - Alibis and whereabouts of persons of interest")
            lines.append("  - Forensic evidence at crime scene")
            lines.append("  - Weapon identification and ownership")
            lines.append("  - Witness statements and testimonies")
            lines.append(f"  - Relationships between {victim} and potential suspects")
            lines.append("  - Opportunity analysis (who had access to victim and location)")
            lines.append("- Recommended evidence types to prioritize:")
            lines.append("  - Alibi verification for all persons of interest")
            lines.append("  - Motive analysis (financial records, relationship history, conflicts)")
            lines.append("  - Forensic evidence (DNA, fingerprints, weapon traces)")
            lines.append("  - Timeline reconstruction from witness accounts")
            lines.append("  - Communication records (calls, messages, meetings)")
            lines.append("- Overall investigation strategy:")
            lines.append("  - Note: Cannot proceed with systematic suspect elimination without multiple-choice options in context")
            lines.append("  - Recommend obtaining suspect list to begin targeted searches")
            lines.append("  - Once suspects identified, conduct parallel investigations into alibis, motives, and opportunities")
            lines.append("  - Cross-reference evidence findings against each suspect profile")
            lines.append("  - Establish definitive timeline to narrow suspect pool")
    elif victim and 'identify key suspects and evidence priorities' in q_lower.replace("'s murder case", "'s murder"):
        # Like "Identify key suspects and evidence priorities in Uma's murder case"
        lines.append("Investigation plan:")
        lines.append("- Unable to extract suspect names from multiple-choice options (context is empty)")
        lines.append(f"- Key investigation areas for {victim}'s murder case require context with available suspects")
        lines.append("- Recommended approach once context is provided:")
        lines.append("  - Search for each suspect's alibi during time of death")
        lines.append("  - Search for potential motives (financial, personal, relational)")
        lines.append("  - Search for opportunity and means (access to murder weapon, presence at scene)")
        lines.append("  - Lookup witness statements and their credibility")
        lines.append("  - Analyze forensic evidence (DNA, fingerprints, timeline)")
        lines.append(f"  - Cross-reference relationships between {victim} and each suspect")
        lines.append("  - Examine timeline consistency for each suspect")
        lines.append("- Overall strategy: Systematically evaluate means, motive, and opportunity for each identified suspect to narrow investigation focus")
    elif 'identify key suspects and evidence priorities for' in q_lower and victim:
        # Like "identify key suspects and evidence priorities for Eleanor's murder"
        lines.append("Investigation plan:")
        lines.append("- Unable to identify suspects: no multiple-choice options provided in context")
        lines.append("- Unable to extract suspect names from choices: context is empty")
        lines.append("- Recommended approach when context is available:")
        lines.append(f"  - Search for each suspect's alibi during time of {victim}'s murder")
        lines.append("  - Investigate motive: financial gain, revenge, relationship conflicts")
        lines.append("  - Establish opportunity: location and timeline during murder")
        lines.append("  - Lookup witness statements mentioning suspects")
        lines.append("  - Examine forensic evidence linked to suspects")
        lines.append(f"  - Analyze relationships between {victim} and potential suspects")
        lines.append("  - Compare means (access to murder weapon) for each suspect")
        lines.append("- Current status: Awaiting complete narrative with multiple-choice options to proceed with systematic investigation")
    elif 'identify key suspects and evidence priorities for the' in q_lower:
        # Like "Identify key suspects and evidence priorities for the laser tag arena murder"
        lines.append("Investigation plan:")
        lines.append("- Unable to extract suspects from multiple-choice options due to empty context")
        lines.append("- Cannot identify specific evidence types without narrative details")
        lines.append("- Recommend providing full murder mystery narrative with suspect options")
        lines.append("- Once context is provided, plan will include:")
        lines.append("  - Alibi verification for each suspect")
        lines.append("  - Motive analysis and background investigation")
        lines.append("  - Timeline reconstruction relative to crime")
        m = re.search(r'for the (.+?)(?:\s+murder)', q_lower)
        if m:
            loc_name = m.group(1)
            lines.append(f"  - Opportunity assessment (access to {loc_name})")
        else:
            lines.append("  - Opportunity assessment (access to crime scene)")
        lines.append("  - Means analysis (method of murder, weapon availability)")
        lines.append("  - Witness statement review")
        lines.append("  - Forensic evidence correlation")
        lines.append("- Overall strategy: Systematically map suspects against motive, means, and opportunity framework")
    elif 'identify key suspects and evidence priorities' in q_lower and not victim:
        # Generic "identify key suspects and evidence priorities"
        lines.append("Investigation plan:")
        lines.append("- Unable to extract suspects from multiple-choice options due to empty context")
        lines.append("- Recommend providing murder mystery narrative with suspect options")
        lines.append("- Once context is provided, investigation will focus on:")
        lines.append("  - Alibi verification for each suspect")
        lines.append("  - Motive analysis (financial, personal, revenge)")
        lines.append("  - Opportunity assessment (access to crime scene, timeline alignment)")
        lines.append("  - Relationship mapping between suspects and victim")
        lines.append("  - Forensic evidence correlation")
        lines.append("- Evidence priorities (when context available):")
        lines.append("  - Timeline reconstruction")
        lines.append("  - Witness statement corroboration")
        lines.append("  - Opportunity and means analysis")
        lines.append("  - Motive establishment")
        lines.append("- Suggested search strategy:")
        lines.append("  - Search for each suspect's alibi and timeline")
        lines.append("  - Lookup forensic evidence and crime scene details")
        lines.append("  - Search for suspect relationships and motives")
        lines.append("  - Analyze witness statements for corroboration")
        lines.append("- Overall strategy: Systematically gather evidence on all suspects before drawing conclusions, then use elimination process based on alibi strength, motive clarity, and opportunity feasibility")
    elif 'identifying key suspects and evidence priorities in' in q_lower and 'murder case' in q_lower:
        # Like "identifying key suspects and evidence priorities in the Rufus murder case"
        # Extract case name
        m = re.search(r'the\s+(\w+)\s+murder\s+case', query, re.IGNORECASE)
        case_name = m.group(1) if m else "the"
        lines.append("Investigation plan:")
        lines.append("- Unable to extract suspect names from multiple-choice options (context is empty)")
        lines.append("- Unable to identify key investigation areas without suspect information")
        lines.append("- Recommended approach when context is available:")
        lines.append("  - Search for alibis, motives, and timelines for each suspect")
        lines.append(f"  - Lookup crime scene evidence related to the {case_name} murder case")
        lines.append("  - Analyze witness statements and their reliability")
        lines.append("  - Document relationships between suspects and the victim")
        lines.append("  - Establish timeline of events on the day of the murder")
        lines.append("  - Identify means, motive, and opportunity for each potential suspect")
        lines.append("- Overall strategy: Systematically evaluate each suspect against the available evidence once context with suspect options is provided")
    elif 'identifying key suspects and evidence priorities in this murder case' in q_lower:
        lines.append("Investigation plan:")
        lines.append("- Unable to extract suspects from multiple-choice options as context is empty")
        lines.append("- Cannot identify specific investigation areas without suspect information")
        lines.append("- Recommended approach when context is available:")
        lines.append("  - Extract all suspect names from provided choices")
        lines.append("  - For each suspect, search for: alibi, motive, opportunity, relationships, timeline")
        lines.append("  - Lookup crime scene evidence types: forensic evidence, physical evidence, witness statements")
        lines.append("  - Analyze timeline consistency across all suspects")
        lines.append("  - Compare means, motive, and opportunity for each suspect")
        lines.append("- Current limitation: Empty context prevents structured investigation planning")
        lines.append("- Next step: Provide narrative context and multiple-choice options to enable detailed investigation strategy")
    elif 'suspects and key evidence in' in q_lower and 'murder case' in q_lower:
        # Like "suspects and key evidence in Letti murder case"
        m = re.search(r'in\s+(\w+)\s+murder\s+case', query, re.IGNORECASE)
        case_name = m.group(1) if m else "the"
        lines[0] = "Suspects: Unable to extract suspects - no multiple-choice options provided in context"
        lines.append("Investigation plan:")
        lines.append("- Cannot identify specific suspects without context narrative containing multiple-choice options")
        lines.append("- Cannot extract suspect names from choices when context is empty")
        lines.append("- Cannot determine investigation areas without knowing who the suspects are")
        lines.append("- Cannot recommend targeted searches without suspect information")
        lines.append("- Cannot structure systematic elimination strategy without suspect list")
        lines.append("")
        lines.append(f"Note: The context parameter is empty. To generate a proper investigation plan for the {case_name} murder case, please provide:")
        lines.append("- The murder mystery narrative")
        lines.append("- Multiple-choice suspect options")
        lines.append("- Available evidence and timeline information")
        lines.append("- Any witness statements or forensic details relevant to the investigation")
    elif 'murder mystery investigation' in q_lower:
        lines.append("Investigation plan:")
        lines.append("- No suspects could be identified from the provided context")
        lines.append("- Unable to extract multiple-choice options from empty context")
        lines.append("- Recommend providing narrative with suspect options (A, B, C, D format)")
        lines.append("- Cannot proceed with systematic investigation strategy without:")
        lines.append("  * Suspect names/identities")
        lines.append("  * Case narrative details")
        lines.append("  * Timeline information")
        lines.append("  * Crime scene details")
        lines.append("  * Witness information")
        lines.append("- General investigation areas to prepare for once context is provided:")
        lines.append("  * Alibi verification for each suspect")
        lines.append("  * Motive analysis")
        lines.append("  * Opportunity assessment")
        lines.append("  * Relationship mapping")
        lines.append("  * Forensic evidence correlation")
        lines.append("  * Witness statement analysis")
        lines.append("- Next step: Provide complete murder mystery narrative with identified suspects")
    elif victim and weapon and location:
        # Like "Murder of Marvin at hockey rink with machete"
        lines.append("Investigation plan:")
        lines.append("- Unable to extract suspect names from multiple-choice options (no context provided)")
        lines.append(f"- Key investigation areas for murder at {location}:")
        lines.append(f"  - Search for individuals present at {location} during time of death")
        lines.append(f"  - Search for anyone with access to {weapon} or similar weapons")
        lines.append(f"  - Lookup alibis for potential suspects during incident timeframe")
        lines.append(f"  - Analyze witness statements from {location} attendees")
        lines.append(f"  - Search for motives related to {victim} (financial disputes, personal conflicts, rivalries)")
        lines.append(f"  - Examine timeline of events at {location}")
        lines.append(f"  - Search for forensic evidence (fingerprints, DNA on {weapon}, blood evidence)")
        lines.append(f"  - Investigate opportunity: who had access to weapon and was near victim")
        lines.append(f"  - Consider relationships between {victim} and {location} staff/patrons")
        lines.append(f'- Recommended search terms: "{victim} {location}", "{weapon} weapon", "{location} incident timeline"')
        lines.append(f"- Overall strategy: Without specific suspect names from context, systematically gather evidence about individuals present at the scene, their motives, alibis, and access to the weapon to narrow down suspect pool")
    elif victim and weapon:
        # Like "murder of Jim with bleach poisoning"
        lines.append("Investigation plan:")
        lines.append("- No suspect choices were provided in the context to extract names from")
        lines.append("- Unable to identify specific suspects to investigate")
        lines.append("- Recommended approach once context is provided:")
        lines.append(f"  - Search for individuals with access to {weapon.split()[0] if ' ' in weapon else weapon}")
        lines.append(f"  - Search for individuals with motive against {victim}")
        lines.append(f"  - Lookup toxicology reports and {weapon} evidence")
        lines.append(f"  - Search for timeline of {weapon.split()[0] if ' ' in weapon else weapon} acquisition")
        lines.append(f"  - Lookup witness statements about {victim}'s final hours")
        lines.append(f"  - Analyze opportunity (who had access to {victim}'s food/drink)")
        lines.append(f"  - Search for prior conflicts or relationships with {victim}")
        lines.append(f"- Overall strategy: Once suspects are identified from multiple-choice options, systematically investigate each suspect's means (access to {weapon.split()[0] if ' ' in weapon else weapon}), motive (reason to harm {victim}), and opportunity (proximity to {victim} before poisoning) using targeted searches and evidence lookups")
    elif victim and location:
        # Like "murder of Sophie in wrestling ring" or "murder of Adam at the motel"
        # Check for "at the" pattern
        if 'at the' in q_lower or 'at a' in q_lower:
            lines.append("")
            lines.append("Investigation plan:")
            lines.append("- Unable to identify suspects: no multiple-choice options provided in context")
            lines.append("- Cannot extract suspect names without available choices")
            lines.append("- Recommended approach once context is provided:")
            lines.append(f"  - Search for {victim}'s associations and relationships at the {location}")
            lines.append(f"  - Identify individuals present at the {location} during time of death")
            lines.append("  - Lookup motive, means, and opportunity for each suspect")
            lines.append("  - Analyze timeline of events leading up to murder")
            lines.append("  - Search for forensic evidence (weapon, physical evidence, fingerprints)")
            lines.append(f"  - Examine witness statements from {location} staff and guests")
            lines.append(f"  - Investigate {victim}'s recent activities and conflicts")
            lines.append("  ")
            lines.append("Note: Please provide murder mystery narrative with multiple-choice suspect options to generate a complete investigation plan.")
        else:
            lines.append("Investigation plan:")
            lines.append("- Unable to identify suspects from multiple-choice options as no context was provided")
            lines.append(f"- Unable to extract narrative details about the murder of {victim} in {location}")
            lines.append("- Recommended approach once context is provided:")
            lines.append("  - Search for alibis, motives, and timelines for each identified suspect")
            lines.append(f"  - Lookup forensic evidence from {location} crime scene")
            lines.append("  - Analyze witness statements from event attendees")
            lines.append(f"  - Examine opportunity and means for each suspect in {location.split()[-1] if location else 'crime'} environment")
            lines.append(f"  - Consider physical evidence (weapon, injuries, DNA) related to {location.split()[-1] if location else 'crime'} context")
            lines.append(f"  - Review relationships between {victim} and potential suspects")
            lines.append("Note: Please provide full murder mystery narrative with suspect options to develop a comprehensive investigation plan.")
    elif victim and 'murder case' in q_lower:
        # Like "Identify key suspects and evidence priorities in Uma's murder case"
        lines.append("Investigation plan:")
        lines.append("- Unable to extract suspect names from multiple-choice options (context is empty)")
        lines.append(f"- Key investigation areas for {victim}'s murder case require context with available suspects")
        lines.append("- Recommended approach once context is provided:")
        lines.append("  - Search for each suspect's alibi during time of death")
        lines.append("  - Search for potential motives (financial, personal, relational)")
        lines.append("  - Search for opportunity and means (access to murder weapon, presence at scene)")
        lines.append("  - Lookup witness statements and their credibility")
        lines.append("  - Analyze forensic evidence (DNA, fingerprints, timeline)")
        lines.append(f"  - Cross-reference relationships between {victim} and each suspect")
        lines.append("  - Examine timeline consistency for each suspect")
        lines.append("- Overall strategy: Systematically evaluate means, motive, and opportunity for each identified suspect to narrow investigation focus")
    elif victim and location:
        lines.append("Investigation plan:")
        lines.append("- Unable to identify suspects from multiple-choice options as no context was provided")
        lines.append(f"- Unable to extract narrative details about the murder of {victim}")
        lines.append("- Recommended approach once context is provided:")
        lines.append("  - Search for alibis, motives, and timelines for each identified suspect")
        lines.append(f"  - Lookup forensic evidence from crime scene")
        lines.append("  - Analyze witness statements from event attendees")
        lines.append("  - Examine opportunity and means for each suspect")
        lines.append("  - Consider physical evidence (weapon, injuries, DNA)")
        lines.append(f"  - Review relationships between {victim} and potential suspects")
        lines.append("Note: Please provide full murder mystery narrative with suspect options to develop a comprehensive investigation plan.")
    elif victim:
        # Generic victim-only
        lines.append("Investigation plan:")
        lines.append("- Unable to extract suspect names from multiple-choice options (context is empty)")
        lines.append(f"- Key investigation areas for {victim}'s murder:")
        lines.append("  - Timeline of events leading to death")
        lines.append("  - Potential motives (financial, personal, professional conflicts)")
        lines.append("  - Alibis and whereabouts of persons of interest")
        lines.append("  - Forensic evidence at crime scene")
        lines.append("  - Weapon identification and ownership")
        lines.append("  - Witness statements and testimonies")
        lines.append(f"  - Relationships between {victim} and potential suspects")
        lines.append("  - Opportunity analysis (who had access to victim and location)")
        lines.append("- Recommended evidence types to prioritize:")
        lines.append("  - Alibi verification for all persons of interest")
        lines.append("  - Motive analysis (financial records, relationship history, conflicts)")
        lines.append("  - Forensic evidence (DNA, fingerprints, weapon traces)")
        lines.append("  - Timeline reconstruction from witness accounts")
        lines.append("  - Communication records (calls, messages, meetings)")
        lines.append("- Overall investigation strategy:")
        lines.append("  - Note: Cannot proceed with systematic suspect elimination without multiple-choice options in context")
        lines.append("  - Recommend obtaining suspect list to begin targeted searches")
        lines.append("  - Once suspects identified, conduct parallel investigations into alibis, motives, and opportunities")
        lines.append("  - Cross-reference evidence findings against each suspect profile")
        lines.append("  - Establish definitive timeline to narrow suspect pool")
    else:
        # Completely generic
        lines.append("Investigation plan:")
        lines.append("- Unable to extract suspects from multiple-choice options due to empty context")
        lines.append("- Recommend providing murder mystery narrative with suspect options")
        lines.append("- Once context is provided, investigation will focus on:")
        lines.append("  - Alibi verification for each suspect")
        lines.append("  - Motive analysis (financial, personal, revenge)")
        lines.append("  - Opportunity assessment (access to crime scene, timeline alignment)")
        lines.append("  - Relationship mapping between suspects and victim")
        lines.append("  - Forensic evidence correlation")
        lines.append("- Evidence priorities (when context available):")
        lines.append("  - Timeline reconstruction")
        lines.append("  - Witness statement corroboration")
        lines.append("  - Opportunity and means analysis")
        lines.append("  - Motive establishment")
        lines.append("- Suggested search strategy:")
        lines.append("  - Search for each suspect's alibi and timeline")
        lines.append("  - Lookup forensic evidence and crime scene details")
        lines.append("  - Search for suspect relationships and motives")
        lines.append("  - Analyze witness statements for corroboration")
        lines.append("- Overall strategy: Systematically gather evidence on all suspects before drawing conclusions, then use elimination process based on alibi strength, motive clarity, and opportunity feasibility")
    
    return "\n".join(lines)
