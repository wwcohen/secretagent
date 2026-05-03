"""Auto-generated code-distilled implementation for extract_nba_params."""

import re
import json

def extract_nba_params(query: str) -> str:
    if not query or not isinstance(query, str):
        return None
    
    try:
        # Try to find verdict, illegal_operation, problematic_team, reasoning in the query
        # These may be embedded in the latter part of the query
        
        # Look for verdict indicators
        verdict = None
        illegal_operation = ''
        problematic_team = ''
        reasoning = ''
        
        # Search for structured data patterns in the query
        # Look for verdict
        verdict_match = re.search(r'["\']?verdict["\']?\s*[:=]\s*(True|False|true|false)', query)
        if verdict_match:
            verdict = verdict_match.group(1) in ('True', 'true')
        
        illegal_op_match = re.search(r'["\']?illegal_operation["\']?\s*[:=]\s*["\']([^"\']*)["\']', query)
        if illegal_op_match:
            illegal_operation = illegal_op_match.group(1)
        
        team_match = re.search(r'["\']?problematic_team["\']?\s*[:=]\s*["\']([^"\']*)["\']', query)
        if team_match:
            problematic_team = team_match.group(1)
        
        reasoning_match = re.search(r'["\']?reasoning["\']?\s*[:=]\s*["\'](.+?)["\']?\s*$', query, re.DOTALL)
        if reasoning_match:
            reasoning = reasoning_match.group(1)
        
        # Try JSON parsing from the end of query
        if verdict is None:
            json_match = re.search(r'\{[^{}]*"verdict"[^{}]*\}', query, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                    verdict = data.get('verdict', False)
                    illegal_operation = data.get('illegal_operation', '')
                    problematic_team = data.get('problematic_team', '')
                    reasoning = data.get('reasoning', '')
                except json.JSONDecodeError:
                    pass
        
        if verdict is None:
            return None
        
        verdict_str = 'True' if verdict else 'False'
        
        # Format output
        result = f"verdict={verdict_str} illegal_operation='{illegal_operation}' problematic_team='{problematic_team}' reasoning=\"{reasoning}\""
        
        return result
    
    except Exception:
        return None
