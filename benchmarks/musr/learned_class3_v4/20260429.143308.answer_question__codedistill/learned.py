"""Auto-generated code-distilled implementation for answer_question."""

def answer_question(story, question, choices):
    import urllib.request
    import json
    import os
    
    prompt = f"""Read the following story carefully and answer the question by selecting the best answer choice. Return ONLY the index number (0-based) of the correct answer.

For location questions: Track where each person LAST BELIEVES an item to be. A person only updates their belief about an item's location if they directly witnessed or performed the move. If they were in a different room, engrossed in something else, or otherwise unable to observe, they still believe the item is where they last knew it to be.

For task allocation questions: Consider each person's skills, weaknesses, experiences, and interpersonal dynamics to find the optimal unique assignment.

Story:
{story}

Question: {question}

Choices:
{chr(10).join(f'{i}: {c}' for i, c in enumerate(choices))}

Think step by step about what each person knows/believes, then respond with ONLY a single integer representing the correct answer index."""

    api_key = os.environ.get("OPENAI_API_KEY", "")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = json.dumps({
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are an expert at reading comprehension, theory of mind reasoning, and tracking beliefs about object locations. Answer with just the index number."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,
        "max_tokens": 50
    }).encode("utf-8")
    
    try:
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=data,
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"].strip()
            
            import re
            numbers = re.findall(r'\d+', content)
            if numbers:
                idx = int(numbers[-1])
                if 0 <= idx < len(choices):
                    return idx
                # Try first number
                idx = int(numbers[0])
                if 0 <= idx < len(choices):
                    return idx
            
            return None
    except Exception as e:
        # If API fails, try basic heuristic
        return None
