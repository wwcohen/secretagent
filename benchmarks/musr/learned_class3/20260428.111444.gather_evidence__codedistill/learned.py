"""Auto-generated code-distilled implementation for gather_evidence."""

def gather_evidence(query):
    if not isinstance(query, str):
        return None
    
    # Determine quoting style based on content
    # If query contains both single and double quotes, or other edge cases, return None
    has_apostrophe = "'" in query
    has_double_quote = '"' in query
    
    if has_double_quote:
        return None
    
    # Choose quoting: if the query contains apostrophes, we need to decide
    # Based on examples, the most common approach:
    # - Use single quotes around the query as default
    # - Use double quotes when the query contains apostrophes (sometimes)
    
    # The suffix varies but "in the provided context." is most common
    # Since this appears to be non-deterministic LLM output, pick the most common pattern
    
    if has_apostrophe:
        # Use double quotes around the query, with suffix "in the provided context."
        return f'No evidence found for "{query}" in the provided context.'
    else:
        # Use single quotes around the query, with suffix "in the provided context."
        return f"No evidence found for '{query}' in the provided context."
