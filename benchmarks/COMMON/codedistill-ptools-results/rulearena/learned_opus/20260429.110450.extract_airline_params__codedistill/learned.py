"""Auto-generated code-distilled implementation for extract_airline_params."""

import re
import json

def extract_airline_params(query):
    try:
        # Look for the structured data section - likely after the rules
        # Try to find base_price, customer_class, routine, direction, and bag_list
        
        # Search for QUERY or similar section marker
        # The data is likely in a JSON-like or structured text block at the end
        
        # Try to find a JSON block
        json_match = re.search(r'\{[^{}]*"base_price"[^{}]*\}', query)
        if json_match:
            data = json.loads(json_match.group())
        
        # Look for key-value patterns
        bp_match = re.search(r'["\']?base_price["\']?\s*[:=]\s*(\d+)', query)
        cc_match = re.search(r'["\']?customer_class["\']?\s*[:=]\s*["\']([^"\']+)["\']', query)
        rt_match = re.search(r'["\']?routine["\']?\s*[:=]\s*["\']([^"\']+)["\']', query)
        dir_match = re.search(r'["\']?direction["\']?\s*[:=]\s*(\d+)', query)
        
        base_price = int(bp_match.group(1)) if bp_match else None
        customer_class = cc_match.group(1) if cc_match else None
        routine = rt_match.group(1) if rt_match else None
        direction = int(dir_match.group(1)) if dir_match else 1
        
        if base_price is None or customer_class is None or routine is None:
            return None
        
        # Parse bag list
        bag_list = []
        # Find all bag entries - pattern: id, name, size [w,h,d], weight
        bag_pattern = re.findall(
            r'["\']?id["\']?\s*[:=]\s*(\d+)\s*[,;]\s*["\']?name["\']?\s*[:=]\s*["\']([^"\']+)["\']'
            r'\s*[,;]\s*["\']?size["\']?\s*[:=]\s*\[(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\]'
            r'\s*[,;]\s*["\']?weight["\']?\s*[:=]\s*(\d+)',
            query
        )
        
        for match in bag_pattern:
            bag_id, name, s1, s2, s3, weight = match
            bag_list.append(f"BagItem(id={int(bag_id)}, name='{name}', size=[{int(s1)}, {int(s2)}, {int(s3)}], weight={int(weight)})")
        
        bag_list_str = '[' + ', '.join(bag_list) + ']'
        
        result = (
            f"base_price={base_price} "
            f"customer_class='{customer_class}' "
            f"routine='{routine}' "
            f"direction={direction} "
            f"bag_list={bag_list_str}"
        )
        
        return result
        
    except Exception:
        return None
