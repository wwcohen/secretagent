"""Auto-generated code-distilled implementation for extract_index."""

def extract_index(item: str, options: list) -> int:
    """Return the index of the item in the options list."""
    try:
        return options.index(item)
    except ValueError:
        # Try case-insensitive match or stripped match
        item_lower = item.strip().lower()
        for i, option in enumerate(options):
            if option.strip().lower() == item_lower:
                return i
        # Try substring matching as fallback
        for i, option in enumerate(options):
            if item_lower in option.strip().lower() or option.strip().lower() in item_lower:
                return i
        return None
