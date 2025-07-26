import json
import os

def load_json(filepath, default=None):
    if not os.path.exists(filepath):
        return default if default is not None else []
    try:
        with open(filepath, 'r') as f:
            content = f.read().strip()
            if not content:  # Handle empty files
                return default if default is not None else []
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return default if default is not None else []

def save_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)
