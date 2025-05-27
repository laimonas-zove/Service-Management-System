import json, os
from typing import Dict

def get_translations(lang: str = 'en') -> Dict[str, str]:
    """
    Load translations for the specified language from a JSON file.

    Args:
        lang (str): Language code to load (e.g., 'en', 'lt'). Defaults to 'en'.

    Returns:
        Dict[str, str]: A dictionary mapping translation keys to localized strings.
                        Falls back to the key itself if no translation is found.
    """
    path = os.path.join(os.path.dirname(__file__),'locales', 'translations.json')
    with open(path, encoding='utf-8') as f:
        full_dict: Dict[str, Dict[str, str]] = json.load(f)

    return {key: value.get(lang, key) for key, value in full_dict.items()}
