import json


def safe_parse_json_block(text: str):
    """Try to find and parse the first JSON-like block in text."""
    # Very simple heuristic parser — the model should return clean JSON, but
    # fallback to scanning for a JSON substring.
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end+1])
        except Exception:
            return None
    return None