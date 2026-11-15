"""Modern OEM Daily / Eco & Trip Computer dashboard page (640x480).

Pre-renders static background cards, ambient glow, and supersampled ring tracks
once at startup (and whenever language or feature flags change), drawing
anti-aliased dynamic arcs, sparklines, and cached typography at 60 FPS.
"""
from collections import deque
import math
import time

import pygame
from pygame import gfxdraw

import config
import settings
from dashboard.console_battery import draw_phone_battery
from dashboard.page_base import Page
from dashboard.telemetry import fmt_hms
from i18n import get_lang, t

W, H = 640, 480

# ── OEM Daily Color Palette ──────────────────────────────────────────────────
BG         = (11,  16,  23)   # #0b1017
CARD       = (17,  24,  36)   # #111824
CARD_DARK  = (11,  16,  23)   # #0b1017
BORDER     = (30,  41,  59)   # #1e293b
BADGE_BG   = (23,  33,  48)   # #172130
BADGE_BD   = (51,  65,  85)   # #334155
TRACK      = (30,  41,  59)   # #1e293b

TXT_MAIN   = (248, 250, 252)  # #f8fafc
TXT_SUB    = (148, 163, 184)  # #94a3b8
TXT_MUTED  = (100, 116, 139)  # #64748b

SKY        = (56,  189, 248)  # #38bdf8
TEAL       = (45,  212, 191)  # #2dd4bf
EMERALD    = (52,  211, 153)  # #34d399
GREEN_DOT  = (16,  185, 129)  # #10b981
AMBER      = (245, 158, 11)   # #f59e0b
AMBER_TXT  = (251, 191, 36)   # #fbbf24
RED        = (239, 68,  68)   # #ef4444

# Ring geometry (270° sweep starting at 135° screen-space: bottom-left -> top -> bottom-right)
_LEFT_CENTER  = (132, 192)
_RIGHT_CENTER = (508, 192)
_RING_R       = 90
_RING_THICK   = 14
_START_DEG    = 135.0
_SWEEP_DEG    = 270.0


def _build_radial_glow(size, center, radius, color, max_alpha=32):
    """Create a smooth radial ambient light surface."""
    surf = pygame.Surface(size, pygame.SRCALPHA)
    cx, cy = center
    steps = 36
    for i in range(steps, 0, -1):
        frac = i / steps
        r = int(radius * frac)
        alpha = int(max_alpha * ((1.0 - frac) ** 1.8))
        if alpha > 0 and r > 0:
            pygame.draw.circle(surf, (*color, alpha), (cx, cy), r)
    return surf


def _draw_thick_arc(surface, cx, cy, radius, thickness, start_deg, sweep_deg, color):
    """Draw a smooth anti-aliased thick arc with rounded endcaps."""
    if sweep_deg <= 0.4:
        return

    half_t = thickness / 2.0
    r_out = radius + half_t
    r_in = radius - half_t
    steps = max(8, int(sweep_deg / 3.5))

    outer_pts = []
    inner_pts = []
    for i in range(steps + 1):
        ang = math.radians(start_deg + sweep_deg * (i / steps))
        ca, sa = math.cos(ang), math.sin(ang)
        outer_pts.append((cx + r_out * ca, cy + r_out * sa))
        inner_pts.append((cx + r_in * ca, cy + r_in * sa))

    poly = [(int(round(x)), int(round(y))) for x, y in (outer_pts + list(reversed(inner_pts)))]
    if len(poly) >= 3:
        gfxdraw.filled_polygon(surface, poly, color)
        gfxdraw.aapolygon(surface, poly, color)

    cap_r = int(round(half_t))
    for deg in (start_deg, start_deg + sweep_deg):
        ang = math.radians(deg)
        px = int(round(cx + radius * math.cos(ang)))
        py = int(round(cy + radius * math.sin(ang)))
        gfxdraw.filled_circle(surface, px, py, cap_r, color)
        gfxdraw.aacircle(surface, px, py, cap_r, color)


def _build_ring_track(radius, thickness):
    """Pre-render a 3x supersampled static ring track for crisp edges."""
    ss = 3
    pad = thickness + 8
    dim = (radius + pad) * 2
    hi_dim = dim * ss
    hi = pygame.Surface((hi_dim, hi_dim), pygame.SRCALPHA)
    hi.fill((*TRACK, 0))

    c = hi_dim / 2.0
    r_mid = radius * ss
    half_t = (thickness * ss) / 2.0
    steps = 180
    outer_pts, inner_pts = [], []
    for i in range(steps + 1):
        ang = math.radians(_START_DEG + _SWEEP_DEG * (i / steps))
        ca, sa = math.cos(ang), math.sin(ang)
        outer_pts.append((int(round(c + (r_mid + half_t) * ca)), int(round(c + (r_mid + half_t) * sa))))
        inner_pts.append((int(round(c + (r_mid - half_t) * ca)), int(round(c + (r_mid - half_t) * sa))))

    pygame.draw.polygon(hi, TRACK, outer_pts + list(reversed(inner_pts)))
    cap_r = int(round(half_t))
    for deg in (_START_DEG, _START_DEG + _SWEEP_DEG):
        ang = math.radians(deg)
        pygame.draw.circle(
            hi, TRACK,
            (int(round(c + r_mid * math.cos(ang))), int(round(c + r_mid * math.sin(ang)))),
            cap_r,
        )
    return pygame.transform.smoothscale(hi, (dim, dim))


class DailyCockpitPage(Page):
    """Template 3 — OEM Daily / Eco & Trip Computer."""

    @property
    def name(self) -> str:
        return t("app.header_title")

    def __init__(self, screen):
        super().__init__(screen)
        sw, sh = screen.get_size()
        self._direct = (sw, sh) == (W, H)
        self.cv = screen if self._direct else pygame.Surface((W, H))

        self._fonts = {}
        self._text_cache = {}
        self._lang = get_lang()
        self._settings_rev = settings.revision()
        self._hdr_half_w = 54
        self._active_pills = []

        # Smoothed needle/arc state & rolling sparkline histories
        self._rpm_disp = 0.0
        self._speed_disp = 0.0
        self._econ_hist = deque([0.0] * 48, maxlen=48)
        self._speed_hist = deque([0.0] * 48, maxlen=48)
        self._last_hist_t = 0.0
        self._data = {}

        # Pre-rendered static surfaces
        self._bg = pygame.Surface((W, H))
        self._danger_glow = _build_radial_glow((W, H), (W // 2, 55), 340, RED, max_alpha=42)
        self._build_static_bg()

    # ── Cached Typography ────────────────────────────────────────────────────

    def _font(self, size: int, mono: bool = False, bold: bool = True):
        key = (size, mono, bold)
        f = self._fonts.get(key)
        if f is None:
            families = (
                "consolas,dejavusansmono,liberationmono,monospace"
                if mono
                else "segoeui,dejavusans,liberationsans,arial,sans-serif"
            )
            f = pygame.font.SysFont(families, size, bold=bold)
            self._fonts[key] = f
        return f

    def _txt(self, text_str: str, size: int, color: tuple, mono: bool = False, bold: bool = True):
        key = (text_str, size, color, mono, bold)
        surf = self._text_cache.get(key)
        if surf is None:
            if len(self._text_cache) > 512:
                self._text_cache.clear()
            surf = self._font(size, mono=mono, bold=bold).render(text_str, True, color)
            self._text_cache[key] = surf
        return surf

    @staticmethod
    def _blit_center(dst, surf, cx: int, cy: int):
        dst.blit(surf, (cx - surf.get_width() // 2, cy - surf.get_height() // 2))

    # ── Static Layer Pre-rendering ───────────────────────────────────────────

    def _build_static_bg(self):
        bg = self._bg
        bg.fill(BG)

        # Top ambient sky-blue glow
        bg.blit(_build_radial_glow((W, H), (W // 2, 55), 360, SKY, max_alpha=30), (0, 0))

        # Top header title
        hdr_surf = self._txt(t("app.header_title"), 13, SKY, bold=True)
        self._hdr_half_w = hdr_surf.get_width() // 2
        self._blit_center(bg, hdr_surf, W // 2, 24)

        # Left & Right supersampled ring tracks
        track_surf = _build_ring_track(_RING_R, _RING_THICK)
        half = track_surf.get_width() // 2
        for cx, cy in (_LEFT_CENTER, _RIGHT_CENTER):
            bg.blit(track_surf, (cx - half, cy - half))

        # Subtle inner scale ticks on RPM ring (0..7)
        max_k = max(1, int(round(config.RPM_MAX / 1000)))
        for k in range(max_k + 1):
            frac = k / max_k
            ang = math.radians(_START_DEG + _SWEEP_DEG * frac)
            r1, r2 = _RING_R - 14, _RING_R - 19
            p1 = (int(_LEFT_CENTER[0] + r1 * math.cos(ang)), int(_LEFT_CENTER[1] + r1 * math.sin(ang)))
            p2 = (int(_LEFT_CENTER[0] + r2 * math.cos(ang)), int(_LEFT_CENTER[1] + r2 * math.sin(ang)))
            col = RED if (k * 1000) >= config.RPM_REDLINE else TXT_MUTED
            pygame.draw.aaline(bg, col, p1, p2)

        # Subtle inner scale ticks on Speed ring (every 40 km/h)
        for s in range(0, int(config.SPEED_MAX) + 1, 40):
            frac = s / config.SPEED_MAX
            ang = math.radians(_START_DEG + _SWEEP_DEG * frac)
            r1, r2 = _RING_R - 14, _RING_R - 19
            p1 = (int(_RIGHT_CENTER[0] + r1 * math.cos(ang)), int(_RIGHT_CENTER[1] + r1 * math.sin(ang)))
            p2 = (int(_RIGHT_CENTER[0] + r2 * math.cos(ang)), int(_RIGHT_CENTER[1] + r2 * math.sin(ang)))
            pygame.draw.aaline(bg, TXT_MUTED, p1, p2)

        # Static ring unit labels & conditional bottom badge frames
        self._blit_center(bg, self._txt(t("hud.rpm_unit"), 12, TXT_SUB), _LEFT_CENTER[0], _LEFT_CENTER[1] + 31)
        self._blit_center(bg, self._txt(t("hud.speed_unit"), 12, TXT_SUB), _RIGHT_CENTER[0], _RIGHT_CENTER[1] + 31)

        if settings.enabled("gear_indicator"):
            badge_rect = pygame.Rect(_LEFT_CENTER[0] - 28, _LEFT_CENTER[1] + 47, 56, 27)
            pygame.draw.rect(bg, BADGE_BG, badge_rect, border_radius=6)
            pygame.draw.rect(bg, BADGE_BD, badge_rect, 1, border_radius=6)

        if settings.enabled("fuel_level"):
            badge_rect = pygame.Rect(_RIGHT_CENTER[0] - 33, _RIGHT_CENTER[1] + 47, 66, 27)
            pygame.draw.rect(bg, BADGE_BG, badge_rect, border_radius=6)
            pygame.draw.rect(bg, BADGE_BD, badge_rect, 1, border_radius=6)

        # Center Economy / Trip Computer Card
        card_rect = pygame.Rect(238, 86, 164, 222)
        pygame.draw.rect(bg, CARD, card_rect, border_radius=10)
        pygame.draw.rect(bg, BORDER, card_rect, 1, border_radius=10)

        if settings.enabled("consumption"):
            c_title = t("hud.economy_title")
            c_unit = t("hud.economy_unit")
        else:
            c_title = t("hud.avg_speed_title")
            c_unit = t("hud.avg_speed_unit")

        self._blit_center(bg, self._txt(c_title, 11, TXT_SUB), W // 2, 106)
        self._blit_center(bg, self._txt(c_unit, 12, TXT_MUTED, bold=False), W // 2, 166)

        # Sparkline inset box + subtle horizontal guide lines
        spark_rect = pygame.Rect(252, 186, 136, 72)
        pygame.draw.rect(bg, CARD_DARK, spark_rect, border_radius=6)
        for gy in (spark_rect.y + 24, spark_rect.y + 48):
            pygame.draw.line(bg, (20, 29, 42), (spark_rect.x + 4, gy), (spark_rect.right - 4, gy), 1)
        pygame.draw.rect(bg, BORDER, spark_rect, 1, border_radius=6)

        # Bottom Health Pill Cards (dynamically sized for enabled sensors)
        candidates = []
        if settings.enabled("water_temp"):
            candidates.append(("water_temp", t("hud.pill_water")))
        if settings.enabled("oil_temp"):
            candidates.append(("oil_temp", t("hud.pill_oil")))
        if settings.enabled("battery_voltage"):
            candidates.append(("battery_voltage", t("hud.pill_battery")))
        if settings.enabled("tps_load"):
            tps_lbl = t("hud.pill_tps_boost") if settings.enabled("turbo") else t("hud.pill_tps_load")
            candidates.append(("tps_load", tps_lbl))

        self._active_pills = []
        n = len(candidates)
        if n > 0:
            gap = 12
            pill_w = 280 if n == 1 else (592 - gap * (n - 1)) // n
            total_w = pill_w * n + gap * (n - 1)
            start_x = (W - total_w) // 2
            for i, (key, lbl) in enumerate(candidates):
                x = start_x + i * (pill_w + gap)
                r = pygame.Rect(x, 344, pill_w, 92)
                self._active_pills.append((key, r))
                pygame.draw.rect(bg, CARD, r, border_radius=8)
                pygame.draw.rect(bg, BORDER, r, 1, border_radius=8)
                bg.blit(self._txt(lbl, 11, TXT_SUB), (x + 26, 358))

    # ── Sensor Evaluation Helpers ────────────────────────────────────────────

    @staticmethod
    def _temp_state(val: float) -> int:
        if val <= 0:
            return 0
        if val >= config.TEMP_COLOR_DANGER:
            return 2
        if val >= config.TEMP_COLOR_WARN:
            return 1
        return 0

    @staticmethod
    def _volt_state(val: float) -> int:
        if val <= 0:
            return 0
        if val < config.VOLT_COLOR_LOW_DANGER:
            return 2
        if val < config.VOLT_COLOR_LOW_WARN or val > config.VOLT_COLOR_HIGH_WARN:
            return 1
        return 0

    # ── Per-Frame Lifecycle ──────────────────────────────────────────────────

    def reset_histories(self):
        """Clear rolling sparklines when switching between Mock and Real modes."""
        self._econ_hist.clear()
        self._econ_hist.extend([0.0] * 48)
        self._speed_hist.clear()
        self._speed_hist.extend([0.0] * 48)
        self._rpm_disp = 0.0
        self._speed_disp = 0.0
        self._last_hist_t = 0.0

    def update(self, data: dict):
        self._data = data
        now = time.monotonic()
        if now - self._last_hist_t >= 0.25:
            self._last_hist_t = now
            kml = data.get("consumption_kml")
            self._econ_hist.append(float(kml) if kml is not None else 0.0)
            self._speed_hist.append(float(data.get("speed", 0) or 0))

    def draw(self):
        cur_lang = get_lang()
        cur_rev = settings.revision()
        if cur_lang != self._lang or cur_rev != self._settings_rev:
            self._lang = cur_lang
            self._settings_rev = cur_rev
            self._text_cache.clear()
            self._build_static_bg()

        d = self._data
        cv = self.cv
        cv.blit(self._bg, (0, 0))

        blink = (pygame.time.get_ticks() // 250) % 2 == 0

        rpm       = float(d.get("rpm", 0) or 0)
        speed     = float(d.get("speed", 0) or 0)
        gear      = int(d.get("gear", 0) or 0)
        fuel      = float(d.get("fuel", 0) or 0)
        water     = float(d.get("water_temp", 0) or 0)
        oil       = float(d.get("oil_temp", 0) or 0)
        volt      = float(d.get("voltage", 0) or 0)
        tps       = float(d.get("throttle", 0) or 0)
        load      = float(d.get("load", 0) or 0)
        boost     = float(d.get("boost_bar", 0) or 0)
        iat       = float(d.get("intake_temp", 0) or 0)
        trip_s    = float(d.get("trip_seconds", 0) or 0)
        trip_km   = float(d.get("trip_km", 0) or 0)
        avg_spd   = float(d.get("avg_speed_kmh", 0) or 0)
        kml       = d.get("consumption_kml")
        connected = bool(d.get("connected", False))
        obd_port  = str(d.get("obd_port", "") or "").replace("/dev/", "")

        # Danger ambient glow overlay (only for enabled sensors)
        w_st = self._temp_state(water) if settings.enabled("water_temp") else 0
        o_st = self._temp_state(oil) if settings.enabled("oil_temp") else 0
        v_st = self._volt_state(volt) if settings.enabled("battery_voltage") else 0
        if max(w_st, o_st, v_st) == 2 and blink:
            cv.blit(self._danger_glow, (0, 0))

        # 1. Top Status Bar (Trip | Connection dot | IAT | R36S Battery)
        cv.blit(self._txt(t("hud.trip", time=fmt_hms(trip_s)), 13, TXT_SUB, mono=True), (24, 17))

        dot_col = GREEN_DOT if connected else RED
        dot_x = W // 2 - self._hdr_half_w - 12
        gfxdraw.filled_circle(cv, dot_x, 24, 4, dot_col)
        gfxdraw.aacircle(cv, dot_x, 24, 4, dot_col)
        if settings.enabled("mock_mode"):
            cv.blit(self._txt(t("mode.badge_mock"), 11, AMBER_TXT, mono=True), (W // 2 + self._hdr_half_w + 10, 18))
        elif connected and obd_port:
            cv.blit(self._txt(obd_port, 11, TXT_MUTED, mono=True), (W // 2 + self._hdr_half_w + 10, 18))

        show_batt = settings.enabled("console_battery")
        show_iat  = settings.enabled("intake_temp")
        right_cursor = W - 24

        if show_batt:
            batt_left_x = draw_phone_battery(
                cv,
                right_cursor,
                24,
                d.get("console_battery_pct"),
                bool(d.get("console_battery_charging", False)),
                self._font(13, mono=True, bold=True),
            )
            right_cursor = batt_left_x - 10
            if show_iat:
                pygame.draw.line(cv, BORDER, (right_cursor, 17), (right_cursor, 31), 1)
                right_cursor -= 10

        if show_iat:
            iat_str = t("hud.iat_value", temp=f"{iat:.0f}") if iat > 0 else t("hud.iat_empty")
            iat_surf = self._txt(iat_str, 13, TXT_SUB, mono=True)
            cv.blit(iat_surf, (right_cursor - iat_surf.get_width(), 17))

        # 2. Left Smooth Ring: RPM + Optional Gear Badge
        self._rpm_disp += (rpm - self._rpm_disp) * 0.28
        rpm_frac = max(0.0, min(1.0, self._rpm_disp / max(1.0, float(config.RPM_MAX))))
        if rpm >= config.RPM_REDLINE:
            rpm_col = RED
        elif rpm >= config.SHIFT_RPM:
            rpm_col = AMBER
        else:
            rpm_col = SKY

        _draw_thick_arc(
            cv, _LEFT_CENTER[0], _LEFT_CENTER[1],
            _RING_R, _RING_THICK, _START_DEG, _SWEEP_DEG * rpm_frac, rpm_col
        )
        self._blit_center(
            cv, self._txt(f"{rpm / 1000.0:.1f}", 44, TXT_MAIN),
            _LEFT_CENTER[0], _LEFT_CENTER[1] - 4
        )
        if settings.enabled("gear_indicator"):
            gear_lbl = t("hud.gear_neutral") if gear <= 0 else t("hud.gear_engaged", gear=gear)
            self._blit_center(
                cv, self._txt(gear_lbl, 16, rpm_col, mono=True),
                _LEFT_CENTER[0], _LEFT_CENTER[1] + 60
            )

        # 3. Right Smooth Ring: Speed + Optional Fuel % Badge
        self._speed_disp += (speed - self._speed_disp) * 0.28
        spd_frac = max(0.0, min(1.0, self._speed_disp / max(1.0, float(config.SPEED_MAX))))
        _draw_thick_arc(
            cv, _RIGHT_CENTER[0], _RIGHT_CENTER[1],
            _RING_R, _RING_THICK, _START_DEG, _SWEEP_DEG * spd_frac, TEAL
        )
        self._blit_center(
            cv, self._txt(f"{int(round(speed))}", 44, TXT_MAIN),
            _RIGHT_CENTER[0], _RIGHT_CENTER[1] - 4
        )
        if settings.enabled("fuel_level"):
            fuel_col = RED if (0 < fuel < 10) else (AMBER if (0 < fuel < 20) else TEAL)
            fuel_str = f"{int(round(fuel))}%" if fuel > 0 else "--%"
            self._blit_center(
                cv, self._txt(fuel_str, 15, fuel_col, mono=True),
                _RIGHT_CENTER[0], _RIGHT_CENTER[1] + 60
            )

        # 4. Center Computer Card: Consumption (or Avg Speed) + Sparkline + 0-100 (or Distance)
        if settings.enabled("consumption"):
            if kml is None or kml <= 0:
                center_str, center_col = "--.-", TXT_MUTED
            else:
                shown_kml = min(99.9, float(kml))
                center_str = f"{shown_kml:.1f}"
                center_col = EMERALD if shown_kml >= 10.0 else (AMBER_TXT if shown_kml >= 6.0 else RED)
            self._blit_center(cv, self._txt(center_str, 34, center_col), W // 2, 138)
            self._draw_sparkline(cv, self._econ_hist, max_scale=22.0, color=EMERALD)
        else:
            spd_str = f"{min(999.0, avg_spd):.0f}"
            self._blit_center(cv, self._txt(spd_str, 34, SKY), W // 2, 138)
            self._draw_sparkline(cv, self._speed_hist, max_scale=float(config.SPEED_MAX), color=SKY)

        if settings.enabled("zero_to_hundred"):
            z_state = d.get("zero100_state", "WAIT_STOP")
            z_time = float(d.get("zero100_time", 0) or 0)
            z_best = d.get("zero100_best")
            z_last = d.get("zero100_last")

            if z_state == "RUNNING":
                z_txt, z_col = t("hud.zero100_run", time=f"{z_time:.1f}"), AMBER_TXT
            elif z_last is not None:
                z_txt, z_col = t("hud.zero100_run", time=f"{z_last:.1f}"), TXT_SUB
            elif z_best is not None:
                z_txt, z_col = t("hud.zero100_best", time=f"{z_best:.1f}"), TXT_SUB
            else:
                z_txt = t("hud.zero100_ready") if z_state == "READY" else t("hud.zero100_idle")
                z_col = TXT_MUTED
        else:
            z_txt = t("hud.trip_dist", km=f"{trip_km:.1f}")
            z_col = TXT_SUB

        self._blit_center(cv, self._txt(z_txt, 12, z_col, mono=True), W // 2, 283)

        # 5. Bottom Health Status Pills (only enabled cards)
        has_turbo = settings.enabled("turbo")
        b_st = 1 if (has_turbo and boost > config.BOOST_MAX_BAR * 0.85) else 0
        tps_val = f"{tps:.0f}% · {boost:.1f}b" if has_turbo else f"{tps:.0f}% · {load:.0f}%"

        values_map = {
            "water_temp":      (f"{water:.0f}°C" if water > 0 else "--°C", w_st),
            "oil_temp":        (f"{oil:.0f}°C" if oil > 0 else "--°C", o_st),
            "battery_voltage": (f"{volt:.1f}V" if volt > 0 else "--.-V", v_st),
            "tps_load":        (tps_val, b_st),
        }

        for key, rect in self._active_pills:
            val_str, st = values_map[key]
            if st == 2:
                bd_col = RED if blink else BADGE_BD
                dot_c = RED
                val_c = RED if blink else TXT_MAIN
                pygame.draw.rect(cv, bd_col, rect, 2, border_radius=8)
            elif st == 1:
                dot_c = AMBER
                val_c = AMBER_TXT
                pygame.draw.rect(cv, AMBER, rect, 2, border_radius=8)
            else:
                dot_c = GREEN_DOT
                val_c = TXT_MAIN

            dx, dy = rect.x + 15, rect.y + 20
            gfxdraw.filled_circle(cv, dx, dy, 4, dot_c)
            gfxdraw.aacircle(cv, dx, dy, 4, dot_c)
            cv.blit(self._txt(val_str, 20, val_c, mono=True), (rect.x + 14, rect.y + 48))

        if not self._direct:
            pygame.transform.smoothscale(cv, self.screen.get_size(), self.screen)

    @staticmethod
    def _draw_sparkline(cv, history, max_scale: float, color: tuple):
        gx, gy, gw, gh = 252, 186, 136, 72
        pts = []
        n = len(history)
        scale = max(1.0, max_scale)
        for idx, val in enumerate(history):
            px = gx + 6 + (idx / max(1, n - 1)) * (gw - 12)
            clamped = max(0.0, min(scale, val))
            py = gy + gh - 8 - (clamped / scale) * (gh - 16)
            pts.append((px, py))

        if len(pts) >= 2:
            fill_surf = pygame.Surface((gw - 12, gh - 12), pygame.SRCALPHA)
            local_pts = [(int(px - (gx + 6)), int(py - (gy + 6))) for px, py in pts]
            poly = [(0, gh - 14)] + local_pts + [(gw - 13, gh - 14)]
            gfxdraw.filled_polygon(fill_surf, poly, (*color, 34))
            cv.blit(fill_surf, (gx + 6, gy + 6))
            pygame.draw.aalines(cv, color, False, pts)

    def draw_alarms(self, alarm):
        if not alarm.blink_on:
            return
        lvl = alarm.overall()
        if lvl >= 1:
            col = RED if lvl == 2 else AMBER
            pygame.draw.rect(self.screen, col, self.screen.get_rect(), 3)
