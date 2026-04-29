"""Auto-generated code-distilled implementation for verify_alibis."""

def verify_alibis(narrative, extracted_info):
    import urllib.request
    import json
    import os

    prompt = f"""You are a detective analyst. Given a murder mystery narrative and extracted suspect information, verify each suspect's alibi by analyzing the narrative carefully.

For each suspect, provide:
- alibi_holds: Whether the alibi holds (True, False, Partially, or descriptive)
- alibi_gaps: Time periods or activities not covered by the alibi
- contradictions: Any contradictions between claimed alibi and narrative facts
- corroborating_evidence: Evidence that supports or undermines the alibi
- additional_notes: (only if relevant) Any extra observations

Format your response as plain text with each suspect separated by a blank line. Use the exact field names above. Do NOT use markdown, bullet points with *, or JSON. Use the format shown in examples below.

Example output format:
suspect: Name
alibi_holds: False
alibi_gaps: Description of gaps
contradictions: Description of contradictions
corroborating_evidence: Description of evidence

NARRATIVE:
{narrative}

EXTRACTED INFORMATION:
{extracted_info}

Now verify each suspect's alibi based on the narrative and extracted information. Be specific and reference details from the narrative."""

    api_key = os.environ.get("OPENAI_API_KEY", "")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = json.dumps({
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are a precise detective analyst who verifies alibis against narrative evidence. Provide structured, concise analysis."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 2000
    }).encode("utf-8")
    
    try:
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=data,
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"].strip()
            return content
    except Exception:
        return None
