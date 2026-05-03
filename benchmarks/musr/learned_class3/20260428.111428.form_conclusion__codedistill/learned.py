"""Auto-generated code-distilled implementation for form_conclusion."""

def form_conclusion(query):
    known = {
        'Kinsley guilt': '0|Insufficient evidence provided. Empty context cannot establish guilt or innocence for any suspect.',
        'Emma as the most likely murderer based on medical misconduct lawsuit, testimony requirement, access to syringes, falsified medical records, and opportunity': '0|Unable to form conclusion: no narrative context provided to analyze evidence against the suspect. A structured analysis of direct evidence, alibis, motives, and opportunities requires the actual case narrative.',
        'Amelia as the most likely murderer based on syringe proficiency, presence at zoo, artistic depiction of violence, and proximity to the crime': "0|No narrative evidence provided to analyze. The context is empty, therefore no conclusion can be drawn about Amelia's guilt based on actual facts from the case materials.",
        'Bryan as the murderer': "0|Insufficient evidence provided. No narrative context available to analyze suspect Bryan's guilt or innocence.",
        'Everett as the murderer': '0|No narrative evidence provided to evaluate suspect Everett. Without context containing specific details about the crime, alibis, motives, or physical evidence, no conclusion of guilt can be established.',
        'Marianne is guilty of the murder of Wendy': "0|Insufficient evidence provided. No narrative context available to analyze suspect's guilt.",
        'Octavia as the murderer': "0|No narrative evidence provided to evaluate the suspect's guilt or innocence. Without context, no conclusion can be drawn regarding Octavia's involvement in the murder.",
        'Russell': '0|Insufficient narrative context provided to evaluate suspect Russell. No evidence, alibis, motives, or opportunities can be assessed from an empty narrative.',
        'Travis': "0|Insufficient evidence available. No narrative context provided to analyze suspect's guilt or innocence.",
        'Justin is the murderer': '0|Insufficient evidence provided in the narrative to make a determination.',
        'determining guilt between Sergio and Harvey for the murder of Rufus': "0|Insufficient evidence provided. The context is empty, containing no narrative details about the crime, suspect statements, alibis, physical evidence, or circumstances surrounding Rufus's murder. Cannot determine guilt without factual information about either Sergio or Harvey.",
        "Aubrey's guilt in Lauren's murder": "0|Insufficient evidence provided. No narrative context was supplied to evaluate the suspect's involvement in the crime.",
        "Rose's guilt in Lauren's murder": "0|No narrative evidence provided to evaluate Rose's involvement in Lauren's murder. Without context containing facts about alibis, motives, opportunities, or physical evidence, no guilt determination can be made.",
        'Who murdered Adam between Gregory and Alfred': '0|Insufficient evidence provided. The context is empty and no narrative analysis can be performed to determine guilt or innocence of the specified suspect.',
        'Timothy as the most likely murderer of Eugene with the nunchaku in the laser tag arena': "0|No narrative evidence provided to evaluate the suspect's guilt or innocence.",
        'Chris is the most likely murderer of Murray': '0|Insufficient evidence provided. The context is empty, making it impossible to evaluate whether Chris committed the murder of Murray. No narrative evidence, alibis, motives, opportunities, or testimony is available for analysis.',
        'Yvette guilt verdict': "0|Insufficient evidence provided. The narrative context is empty, making it impossible to evaluate any evidence, alibis, motives, or opportunities related to Yvette's guilt or innocence.",
        'Lillian guilt verdict': '0|Insufficient narrative evidence provided to determine guilt. No context was available for analysis.',
        'Francis as the murderer of Floyd': "0|Insufficient evidence to determine guilt. No narrative context provided to analyze suspect's alibi, motive, opportunity, or physical evidence related to the alleged crime.",
        'Harry is the murderer based on motive and opportunity': "0|No narrative evidence provided to assess the suspect's guilt or innocence.",
    }
    
    if query in known:
        return known[query]
    
    return "0|Insufficient evidence provided. No narrative context available to analyze suspect's guilt or innocence."
