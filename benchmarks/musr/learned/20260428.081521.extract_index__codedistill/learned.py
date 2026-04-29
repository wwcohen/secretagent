"""Auto-generated code-distilled implementation for extract_index."""

def extract_index(name, names_list):
    try:
        return names_list.index(name)
    except ValueError:
        return None
