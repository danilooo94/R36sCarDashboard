"""Locale catalogs registry."""
from i18n.locales import en, pt_br

CATALOGS = {
    "pt-BR": pt_br.STRINGS,
    "en":    en.STRINGS,
}
