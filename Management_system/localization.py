import json, os

def get_translations(lang='en'):
    path = os.path.join(os.path.dirname(__file__),'locales', 'translations.json')
    with open(path, encoding='utf-8') as f:
        full_dict = json.load(f)

    return {key: value.get(lang, key) for key, value in full_dict.items()}
