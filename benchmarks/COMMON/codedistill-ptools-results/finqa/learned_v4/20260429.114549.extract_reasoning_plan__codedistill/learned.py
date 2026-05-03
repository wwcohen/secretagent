"""Auto-generated code-distilled implementation for extract_reasoning_plan."""

def extract_reasoning_plan(prompt: str) -> str:
    import re
    
    if not prompt or not isinstance(prompt, str):
        return None
    
    # Parse the prompt to extract components
    # Extract question
    question_match = re.search(r'## Question\s*\n(.+?)(?:\n##|\n\n|$)', prompt, re.DOTALL)
    if not question_match:
        question_match = re.search(r'\?\s*$', prompt, re.MULTILINE)
    
    question = question_match.group(1).strip() if question_match else ""
    
    # Extract table
    table_match = re.search(r'## Table\s*\n(.+?)(?:\n## |\Z)', prompt, re.DOTALL)
    table_text = table_match.group(1).strip() if table_match else ""
    
    # Extract context before table
    pre_context_match = re.search(r'## Context \(text before table\)\s*\n(.+?)(?:\n## Table)', prompt, re.DOTALL)
    pre_context = pre_context_match.group(1).strip() if pre_context_match else ""
    
    # Extract context after table
    post_context_match = re.search(r'## Context \(text after table\)\s*\n(.+?)(?:\n## Question|\n## |\Z)', prompt, re.DOTALL)
    post_context = post_context_match.group(1).strip() if post_context_match else ""
    
    # Extract answer/plan section if present
    plan_match = re.search(r'## (?:Answer|Plan|Reasoning)\s*\n(.+?)(?:\n##|\Z)', prompt, re.DOTALL)
    if plan_match:
        return plan_match.group(1).strip()
    
    # Look for explicit answer pattern
    answer_match = re.search(r'(?:the answer is|answer:|result:)\s*(.+?)(?:\n|$)', prompt, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).strip()
    
    # Extract the generated reasoning/plan from the prompt
    # Look for patterns after the question that contain the reasoning
    after_question = ""
    if question_match:
        start = question_match.end()
        after_question = prompt[start:].strip()
    
    # Check if there's a reasoning plan after the question
    if after_question:
        # Remove markdown headers
        plan = re.sub(r'^##.*$', '', after_question, flags=re.MULTILINE).strip()
        if plan:
            return plan
    
    # Try to find the plan/answer embedded in the prompt after all sections
    sections = re.split(r'\n## ', prompt)
    if sections:
        last_section = sections[-1].strip()
        # Check if last section contains an answer/plan
        lines = last_section.split('\n')
        if len(lines) > 1:
            content = '\n'.join(lines[1:]).strip()
            if content:
                return content
    
    return None
