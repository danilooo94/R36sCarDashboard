"""Runtime feature flags and persistent user preferences (`user_settings.json`).

Initializes defaults from `config.py` (`FEATURES` and `LANGUAGE`), merges any
saved overrides from disk, and provides thread-safe access for both the OBD-II
polling thread and the 60 FPS Pygame UI.
"""
import json
import os
import threading

import config
from i18n import get_lang, normalize_lang, set_lang

_LOCK = threading.Lock()
_REVISION = 1


def _defaults() -> dict:
    base = {
        "mock_mode":       bool(getattr(config, "MOCK_MODE", False)),
        "data_logging":    bool(getattr(config, "LOG_ENABLED", True)),
        "turbo":           False,
        "water_temp":      True,
        "oil_temp":        True,
        "battery_voltage": True,
        "tps_load":        True,
        "fuel_level":      True,
        "consumption":     True,
        "zero_to_hundred": True,
        "gear_indicator":  True,
        "intake_temp":     True,
        "console_battery": bool(getattr(config, "SHOW_CONSOLE_BATTERY", True)),
        "alarm_sound":     bool(getattr(config, "ALARM_SOUND", False)),
    }
    cfg_features = getattr(config, "FEATURES", None)
    if isinstance(cfg_features, dict):
        for k, v in cfg_features.items():
            if k in base:
                base[k] = bool(v)
    return base


_STATE = _defaults()


def _settings_path() -> str:
    return getattr(config, "USER_SETTINGS_FILE", "user_settings.json")


def _load_from_disk():
    global _REVISION
    path = _settings_path()
    if not path or not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if not isinstance(payload, dict):
            return
        with _LOCK:
            features = payload.get("features")
            if isinstance(features, dict):
                for k, v in features.items():
                    if k in _STATE:
                        _STATE[k] = bool(v)
            lang = payload.get("language")
            if isinstance(lang, str) and lang.strip():
                set_lang(lang)
            _REVISION += 1
    except Exception:
        pass


def _save_to_disk():
    path = _settings_path()
    if not path:
        return
    try:
        with _LOCK:
            payload = {
                "language": get_lang(),
                "features": dict(_STATE),
            }
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
    except Exception:
        pass


def enabled(key: str) -> bool:
    """Return True if feature `key` is currently enabled."""
    with _LOCK:
        return bool(_STATE.get(key, True))


def set_enabled(key: str, value: bool) -> bool:
    """Enable or disable feature `key` and persist to disk."""
    global _REVISION
    val = bool(value)
    with _LOCK:
        _STATE[key] = val
        _REVISION += 1
    _save_to_disk()
    return val


def toggle(key: str) -> bool:
    """Flip feature `key` on/off, persist to disk, and return the new state."""
    global _REVISION
    with _LOCK:
        new_val = not bool(_STATE.get(key, True))
        _STATE[key] = new_val
        _REVISION += 1
    _save_to_disk()
    return new_val


def cycle_language() -> str:
    """Cycle UI language (`pt-BR` <-> `en`) and persist to disk."""
    global _REVISION
    from i18n import next_lang
    new_lang = next_lang()
    with _LOCK:
        _REVISION += 1
    _save_to_disk()
    return new_lang


def set_language(code: str) -> str:
    """Set UI language and persist to disk."""
    global _REVISION
    norm = set_lang(normalize_lang(code))
    with _LOCK:
        _REVISION += 1
    _save_to_disk()
    return norm


def reset_defaults():
    """Restore all features and language to `config.py` defaults and clear saved file."""
    global _REVISION
    path = _settings_path()
    try:
        if path and os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass

    with _LOCK:
        _STATE.clear()
        _STATE.update(_defaults())
        _REVISION += 1
    # Restore initial language from config if needed
    set_lang(getattr(config, "DEFAULT_LANGUAGE", getattr(config, "LANGUAGE", "pt-BR")))


def revision() -> int:
    """Monotonic counter incremented whenever any setting changes."""
    with _LOCK:
        return _REVISION


# Capture config.LANGUAGE before disk override so reset_defaults() can restore it
config.DEFAULT_LANGUAGE = getattr(config, "LANGUAGE", "pt-BR")
_load_from_disk()
