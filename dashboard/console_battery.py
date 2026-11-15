"""Host / R36S console battery reader and smartphone-style status bar renderer."""
import ctypes
import glob
import os
import sys
import time

import pygame
from pygame import gfxdraw

import config

# Colors matching DailyCockpitPage
_OUTLINE   = (148, 163, 184)  # #94a3b8
_TXT_MAIN  = (248, 250, 252)  # #f8fafc
_TXT_SUB   = (148, 163, 184)  # #94a3b8
_TXT_MUTED = (100, 116, 139)  # #64748b
_GREEN     = (52,  211, 153)  # #34d399 (charging)
_AMBER     = (245, 158, 11)   # #f59e0b (< 30%)
_RED       = (239, 68,  68)   # #ef4444 (< 15%)
_BOLT_BG   = (11,  16,  23)


class _SystemPowerStatus(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus",        ctypes.c_byte),
        ("BatteryFlag",         ctypes.c_byte),
        ("BatteryLifePercent",  ctypes.c_byte),
        ("SystemStatusFlag",    ctypes.c_byte),
        ("BatteryLifeTime",     ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


def _read_linux_sysfs():
    """Read battery capacity & charging status from Linux / Armbian sysfs (R36S RK817, etc.)."""
    preferred = [
        "/sys/class/power_supply/battery",
        "/sys/class/power_supply/rk817-battery",
    ]
    candidates = preferred + sorted(glob.glob("/sys/class/power_supply/*"))
    seen = set()

    for supply_dir in candidates:
        if supply_dir in seen or not os.path.isdir(supply_dir):
            continue
        seen.add(supply_dir)

        cap_path = os.path.join(supply_dir, "capacity")
        if not os.path.isfile(cap_path):
            continue

        # Ensure this power_supply entry is actually a Battery (not a USB/AC charger node)
        type_path = os.path.join(supply_dir, "type")
        if os.path.isfile(type_path):
            try:
                with open(type_path, "r", encoding="utf-8") as tf:
                    if tf.read().strip().lower() != "battery":
                        continue
            except OSError:
                pass

        try:
            with open(cap_path, "r", encoding="utf-8") as cf:
                pct = max(0, min(100, int(cf.read().strip())))
        except (OSError, ValueError):
            continue

        charging = False
        status_path = os.path.join(supply_dir, "status")
        if os.path.isfile(status_path):
            try:
                with open(status_path, "r", encoding="utf-8") as sf:
                    st = sf.read().strip().lower()
                charging = st in ("charging", "full")
            except OSError:
                pass

        return pct, charging

    return None, False


def _read_windows_battery():
    """Read laptop battery status on Windows via kernel32 GetSystemPowerStatus."""
    try:
        status = _SystemPowerStatus()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
            return None, False
        # BatteryFlag 128 = No system battery; 255 = Unknown
        if status.BatteryFlag in (128, -128) or status.BatteryLifePercent > 100 or status.BatteryLifePercent < 0:
            return None, False
        charging = (status.ACLineStatus == 1) or bool(status.BatteryFlag & 8)
        return int(status.BatteryLifePercent), charging
    except Exception:
        return None, False


class ConsoleBatteryReader:
    """Throttled reader for the R36S / host device battery."""

    def __init__(self, poll_interval: float = 5.0):
        self.poll_interval = poll_interval
        self._last_poll = 0.0
        self._pct = None
        self._charging = False

    def read(self, now: float = None):
        """Return cached (pct: int | None, charging: bool), refreshing every poll_interval."""
        now = time.monotonic() if now is None else now
        if self._last_poll == 0.0 or (now - self._last_poll) >= self.poll_interval:
            self._last_poll = now
            if sys.platform.startswith("linux"):
                pct, charging = _read_linux_sysfs()
            elif sys.platform == "win32":
                pct, charging = _read_windows_battery()
            else:
                pct, charging = None, False

            if pct is None and getattr(config, "MOCK_MODE", False):
                pct, charging = 84, False

            self._pct = pct
            self._charging = charging

        return self._pct, self._charging


def draw_phone_battery(surface, right_x: int, center_y: int, pct, charging: bool, font) -> int:
    """Draw a smartphone-style battery icon + percentage anchored at `right_x`.

    Layout:  `84% [████ ]`
    Returns the leftmost x coordinate occupied by the widget.
    """
    blink = (pygame.time.get_ticks() // 350) % 2 == 0
    cap_w, cap_h = 2, 6
    body_w, body_h = 25, 13

    # 1. Terminal nub (right side)
    cap_rect = pygame.Rect(right_x - cap_w, center_y - cap_h // 2, cap_w, cap_h)
    body_rect = pygame.Rect(cap_rect.left - 1 - body_w, center_y - body_h // 2, body_w, body_h)

    # Determine status colors
    if pct is None:
        border_col = _TXT_MUTED
        fill_col = _TXT_MUTED
        txt_col = _TXT_MUTED
        pct_str = "--%"
    else:
        pct_clamped = max(0, min(100, int(round(pct))))
        pct_str = f"{pct_clamped}%"
        if charging:
            border_col = _GREEN
            fill_col = _GREEN
            txt_col = _GREEN
        elif pct_clamped < 15:
            border_col = _RED
            fill_col = _RED
            txt_col = _RED if blink else _TXT_MAIN
        elif pct_clamped < 30:
            border_col = _AMBER
            fill_col = _AMBER
            txt_col = _AMBER
        else:
            border_col = _OUTLINE
            fill_col = _TXT_MAIN
            txt_col = _TXT_SUB

    # Draw nub + outer battery body
    pygame.draw.rect(surface, border_col, cap_rect, border_radius=1)
    pygame.draw.rect(surface, border_col, body_rect, 1, border_radius=3)

    # 2. Inner proportional fill
    if pct is not None:
        pct_clamped = max(0, min(100, int(round(pct))))
        if pct_clamped > 0 and not (pct_clamped < 10 and not charging and not blink):
            max_fill_w = body_w - 4
            fill_w = max(2, int(round(max_fill_w * (pct_clamped / 100.0))))
            fill_rect = pygame.Rect(body_rect.x + 2, body_rect.y + 2, fill_w, body_h - 4)
            pygame.draw.rect(surface, fill_col, fill_rect, border_radius=1)

    # 3. Lightning bolt overlay when charging
    if charging:
        bx, by = body_rect.centerx, body_rect.centery
        bolt = [
            (bx + 1, by - 5),
            (bx - 3, by + 0),
            (bx + 0, by + 0),
            (bx - 1, by + 5),
            (bx + 3, by - 1),
            (bx + 0, by - 1),
        ]
        # Subtle dark halo for contrast over bright fill
        for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            gfxdraw.filled_polygon(surface, [(x + ox, y + oy) for x, y in bolt], _BOLT_BG)
        gfxdraw.filled_polygon(surface, bolt, _TXT_MAIN)
        gfxdraw.aapolygon(surface, bolt, _TXT_MAIN)

    # 4. Percentage label to the left of the battery icon
    lbl = font.render(pct_str, True, txt_col)
    lbl_x = body_rect.left - 6 - lbl.get_width()
    lbl_y = center_y - lbl.get_height() // 2
    surface.blit(lbl, (lbl_x, lbl_y))

    return lbl_x
