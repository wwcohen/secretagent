"""Auto-generated code-distilled implementation for extract_answer."""

import re

def extract_answer(text, choices=None):
    if not text:
        return None
    
    # If choices are provided, try to find the best matching choice
    if choices:
        # First, look for choices in quotes in the text
        for choice in choices:
            # Check for exact quoted match
            if f'"{choice}"' in text or f"'{choice}'" in text:
                return choice
        
        # Check for choice appearing near key phrases like "return", "answer", "output"
        key_patterns = [
            r'(?:return|answer|output)[^"\']*["\']([^"\']+)["\']',
            r'["\']([^"\']+)["\'][^"\']*(?:is the|as the)',
        ]
        for pat in key_patterns:
            matches = re.findall(pat, text, re.IGNORECASE)
            for m in matches:
                if m in choices:
                    return m
        
        # Look for any choice mentioned in the text
        # Prefer choices that appear more prominently
        for choice in choices:
            if choice in text:
                return choice
        
        return None
    
    # No choices provided - extract a free-form answer
    
    # Look for quoted answers with key context phrases
    # Pattern: "return" or "output" or "answer" followed by quoted value
    patterns = [
        r'(?:return|output|answer)[^"\']*["\'](\d+(?:\.\d+)?)["\']',
        r'["\'](\d+(?:\.\d+)?)["\']',
        r'
