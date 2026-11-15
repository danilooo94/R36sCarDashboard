import logging
import os
import sys
from datetime import datetime

import config
import settings

_ENABLED = settings.enabled("data_logging")

_LOG_FILE = (
    os.path.join(
        config.LOG_DIR,
        datetime.now().strftime("errors_%Y-%m-%d_%H-%M-%S.txt"),
    )
    if _ENABLED
    else None
)


def _setup() -> logging.Logger:
    log = logging.getLogger("cardatareader")
    log.handlers.clear()
    log.propagate = False

    if not _ENABLED:
        log.addHandler(logging.NullHandler())
        log.disabled = True
        return log

    os.makedirs(config.LOG_DIR, exist_ok=True)
    log.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    log.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    log.addHandler(ch)

    return log


_log = _setup()

debug     = _log.debug
info      = _log.info
warning   = _log.warning
error     = _log.error
critical  = _log.critical
exception = _log.exception   # logs ERROR + full traceback


def install_excepthook():
    """Capture unhandled exceptions into the log file when logging is enabled."""
    if not _ENABLED:
        return

    def _hook(exc_type, exc_value, exc_tb):
        _log.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook


path = _LOG_FILE
