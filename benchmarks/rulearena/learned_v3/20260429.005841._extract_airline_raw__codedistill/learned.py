"""Auto-generated code-distilled implementation for _extract_airline_raw."""

def _extract_airline_raw(text):
    import re
    import json
    
    # Try to find JSON already embedded in the text
    # Look for the data section after the rules
    # The input likely has a section with the query parameters
    
    # Search for key fields in the text
    try:
        # Look for base_price
        bp_match = re.search(r'base[_ ]price["\s:]*(\d+)', text)
        cc_match = re.search(r'customer[_ ]class["\s:]*["\']([^"\']+)["\']', text)
        rt_match = re.search(r'routine["\s:]*["\']([^"\']+)["\']', text)
        dir_match = re.search(r'direction["\s:]*(\d+)', text)
        
        if not all([bp_match, cc_match, rt_match, dir_match]):
            return None
        
        base_price = int(bp_match.group(1))
        customer_class = cc_match.group(1)
        routine = rt_match.group(1)
        direction = int(dir_match.group(1))
        
        # Extract bag list - find all bag entries
        bag_list = []
        # Look for bag patterns: id, name, size, weight
        bag_pattern = re.compile(
            r'["\']?id["\']?\s*:\s*(\d+)\s*,\s*["\']?name["\']?\s*:\s*["\']([^"\']+)["\']\s*,\s*["\']?size["\']?\s*:\s*\[(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\]\s*,\s*["\']?weight["\']?\s*:\s*(\d+)'
        )
        
        for m in bag_pattern.finditer(text):
            bag_list.append({
                "id": int(m.group(1)),
                "name": m.group(2),
                "size": [int(m.group(3)), int(m.group(4)), int(m.group(5))],
                "weight": int(m.group(6))
            })
        
        result = {
            "result": {
                "base_price": base_price,
                "customer_class": customer_class,
                "routine": routine,
                "direction": direction,
                "bag_list": bag_list
            }
        }
        
        # Format as JSON string
        result_str = json.dumps(result, indent=2)
        
        # Check if the original text suggests
