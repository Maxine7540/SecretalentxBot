"""
多語言支援模組
"""

SUPPORTED_LANGUAGES = {
    "zh_tw": "🇹🇼 繁體中文",
    "en":    "🇬🇧 English",
    "zh_cn": "🇨🇳 简体中文",
    "ja":    "🇯🇵 日本語",
    "ko":    "🇰🇷 한국어",
    "km":    "🇰🇭 ភាសាខ្មែរ",
    "vi":    "🇻🇳 Tiếng Việt",
    "th":    "🇹🇭 ภาษาไทย",
}

AVAILABLE_LANGUAGES = ["zh_tw", "en"]
DEFAULT_LANG = "zh_tw"


def get_strings(lang: str) -> dict:
    if lang not in AVAILABLE_LANGUAGES:
        lang = DEFAULT_LANG
    if lang == "en":
        from i18n.en import STRINGS
    else:
        from i18n.zh_tw import STRINGS
    return STRINGS


def t(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    strings = get_strings(lang)
    text = strings.get(key, get_strings(DEFAULT_LANG).get(key, key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass
    return text
