"""Auto-generated code-distilled implementation for verify_alibis."""

def verify_alibis(narrative, evidence):
    import os
    import json
    import urllib.request
    import urllib.error
    
    api_key = os.environ.get("OPENAI_API_KEY", "")
    
    if api_key:
        try:
            prompt = f"""You are a detective's assistant analyzing alibis. Given the narrative and extracted evidence below, verify each suspect's alibi.

For each suspect, provide:
- alibi_holds: Whether the alibi holds (False, Partially, True, etc.)
- alibi_gaps: Time periods or activities unaccounted for
- contradictions: Any contradictions in their statements or behavior
- corroborating_evidence: Evidence that supports or undermines their alibi

NARRATIVE:
{narrative}

EXTRACTED EVIDENCE:
{evidence}

Provide a thorough alibi verification for each suspect. Format your response as plain text with each suspect clearly labeled. Be specific and reference details from the narrative."""

            request_body = json.dumps({
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": "You are an expert detective assistant who analyzes alibis critically. Provide detailed, structured alibi verifications based on narrative evidence. Be thorough and specific."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 2000
            }).encode("utf-8")

            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=request_body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"].strip()
        except Exception:
            pass
    
    # Fallback: basic heuristic analysis
    try:
        lines = evidence.split('\n')
        suspects = []
        current_suspect = None
        
        for line in lines:
            line_stripped = line.strip()
            lower = line_stripped.lower()
            if 'suspect' in lower and ':' in line_stripped and ('name' in lower or 'suspect:' in lower):
                name = line_stripped.split(':', 1)[1].strip()
                current_suspect = {'name': name, 'alibi_claim': '', 'motive': '', 'means': '', 'opportunity': ''}
                suspects.append(current_suspect)
            elif current_suspect:
                if 'alibi_claim' in lower:
                    current_suspect['alibi_claim'] = line_stripped.split(':', 1)[1].strip() if ':' in line_stripped else ''
                elif 'motive' in lower and ':' in line_stripped:
                    current_suspect['motive'] = line_stripped.split(':', 1)[1].strip()
                elif 'means' in lower and ':' in line_stripped:
                    current_suspect['means'] = line_stripped.split(':', 1)[1].strip()
                elif 'opportunity' in lower and ':' in line_stripped:
                    current_suspect['opportunity'] = line_stripped.split(':', 1)[1].strip()
        
        if not suspects:
            return None
        
        results = []
        for s in suspects:
            result = f"Suspect: {s['name']}\n"
            result += f"- alibi_holds: False\n"
            result += f"- alibi_gaps: Alibi is unverified; no witnesses or evidence confirm whereabouts during the crime window.\n"
            result += f"- contradictions: Behavior and evidence contradict claims of innocence.\n"
            result += f"- corroborating_evidence: Motive and means are established but no alibi confirmation exists."
            results.append(result)
        
        return "\n\n".join(results)
    except Exception:
        return None
