"""Regionalization / internationalization (i18n) layer.

Supports static configuration via `config.LANGUAGE` ("pt-BR" or "en") as well as
live runtime language switching via `set_lang()` / `next_lang()`.
"""
import config
from i18n.locales import CATALOGS

DEFAULT_LANG = "pt-BR"

_ALIASES = {
    "pt":    "pt-BR",
    "pt-br": "pt-BR",
    "pt_br": "pt-BR",
    "br":    "pt-BR",
    "en":    "en",
    "en-us": "en",
    "en_us": "en",
    "en-gb": "en",
    "en_gb": "en",
}

_ORDER = tuple(CATALOGS.keys())  # ("pt-BR", "en")


def normalize_lang(code: str) -> str:
    """Map common locale codes (e.g. 'pt_BR', 'en-US') to canonical keys ('pt-BR', 'en')."""
    if not code:
        return DEFAULT_LANG
    cleaned = str(code).strip().lower()
    if cleaned in _ALIASES:
        return _ALIASES[cleaned]
    for canonical in _ORDER:
        if canonical.lower() == cleaned:
            return canonical
    return DEFAULT_LANG


_current_lang = normalize_lang(getattr(config, "LANGUAGE", DEFAULT_LANG))


def available_languages() -> tuple:
    """Return tuple of supported canonical language codes."""
    return _ORDER


def get_lang() -> str:
    """Return the active canonical language code (e.g. 'pt-BR' or 'en')."""
    return _current_lang


def set_lang(code: str) -> str:
    """Switch the active language at runtime and return the normalized code."""
    global _current_lang
    _current_lang = normalize_lang(code)
    config.LANGUAGE = _current_lang
    return _current_lang


def next_lang() -> str:
    """Cycle to the next supported language (e.g. 'pt-BR' <-> 'en')."""
    idx = _ORDER.index(_current_lang) if _current_lang in _ORDER else 0
    return set_lang(_ORDER[(idx + 1) % len(_ORDER)])


def t(key: str, **kwargs) -> str:
    """Translate `key` using the active locale, with safe fallback and formatting."""
    catalog = CATALOGS.get(_current_lang) or CATALOGS[DEFAULT_LANG]
    template = catalog.get(key)
    if template is None:
        template = CATALOGS[DEFAULT_LANG].get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError, IndexError):
            return template
    return template
