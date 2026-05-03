"""Auto-generated code-distilled implementation for extract_index."""

def extract_index(name, options):
    try:
        return options.index(name)
    except ValueError:
        return None
