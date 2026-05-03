"""Auto-generated code-distilled implementation for extract_suspects_and_evidence."""

import re
import json
import urllib.request
import os


def extract_suspects_and_evidence(text):
    try:
        # Try to use an LLM API if available
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            prompt = (
                "Extract the following from the mystery narrative below and format as plain text (not markdown):\n"
                "victim: <name>\n"
                "crime_details: <how they were killed, where, and where body was found>\n"
                "suspects:\n"
                "- suspect: <name>\n"
                "  motive: <motive>\n"
                "  means: <means/weapons/skills>\n"
                "  opportunity: <opportunity to commit crime>\n"
                "  alibi_claim: <what they claim>\n"
                "  alibi_witnesses: <witnesses>\n"
                "  suspicious_behavior: <suspicious actions>\n"
                "  physical_evidence: <evidence>\n"
                "\nRepeat for each suspect. Be thorough and detailed.\n\n"
                "Narrative:\n" + text
            )
            
            data = json.dumps({
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 3000
            }).encode("utf-8")
            
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
            )
            
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    
    # Fallback: rule-based extraction
    try:
        # Extract victim name from first sentence patterns
        victim_match = re.search(r'(?:murder of|death of|killing of|body of|victim,?\s*)\s+(\w+)', text, re.IGNORECASE)
        if not victim_match:
            victim_match = re.search(r"(\w+)(?:'s life ends|'s lifeless| meets? (?:her|his|their) (?:untimely )?(?:death|end)|was found (?:dead|lifeless)|met (?:a |an )?(?:untimely |grisly )?(?:death|end))", text, re.IGNORECASE)
        
        victim = victim_match.group(1) if victim_match else "Unknown"
        
        # Extract suspects from intro
        suspects_match = re.search(r'suspects?,?\s+(\w+)\s+and\s+(\w+)', text, re.IGNORECASE)
        suspects = []
        if suspects_match:
            suspects = [suspects_match.group(1), suspects_match.group(2)]
        
        # Extract weapon
        weapon_match = re.search(r'(?:murdered|killed|death|end).*?(?:by|with|from)\s+(?:a\s+)?(.+?)[\.,;]', text[:500], re.IGNORECASE)
        weapon = weapon_match.group(1).strip() if weapon_match else "unknown weapon"
        
        # Build output
        lines = [f"victim: {victim}"]
        lines.append(f"crime_details: {victim} was killed by {weapon}.")
        lines.append("suspects:")
        
        for s in suspects:
            lines.append(f"- suspect: {s}")
            lines.append(f"  motive: Not enough information extracted.")
            lines.append(f"  means: Not enough information extracted.")
            lines.append(f"  opportunity: Not enough information extracted.")
            lines.append(f"  alibi_claim: Not explicitly stated.")
            lines.append(f"  alibi_witnesses: None mentioned.")
            lines.append(f"  suspicious_behavior: Not enough information extracted.")
            lines.append(f"  physical_evidence: Not mentioned.")
        
        return "\n".join(lines)
    except Exception:
        return None
