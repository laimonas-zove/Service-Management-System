import pytest
from Management_system import app, g, get_translations, inject_translations

@pytest.mark.parametrize("lang, expected", [
    ("en", "Name"),
    ("lt", "Pavadinimas"),
    ("es", "name"),
])
def test_get_translations_all(lang: str, expected: str) -> str:
    result = get_translations(lang)
    assert result['name'] == expected

def test_inject_translations_direct():
    with app.app_context():
        g.lang = 'lt'
        result = inject_translations()
        assert result['lang'] == 'lt'
        assert 'tr' in result
        assert result['tr']['name'] == 'Pavadinimas'