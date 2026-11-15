"""Live per-parameter telemetry charts page with inner parameter tabs (640x480).

Supports R36S gamepad & keyboard navigation:
  - Up / Down (or W / S, Tab, Mouse Click): switch active parameter tab
  - A / B / X (or Enter / Space): cycle time scale (30s / 60s / 180s)
  - Left / Right: switch dashboard page (handled by MultiPageApp)
"""
from dataclasses import dataclass
from typing import Optional
import math
import time

import pygame
from pygame import gfxdraw

import config
import settings
from dashboard.console_battery import draw_phone_battery
from dashboard.page_base import Page
from dashboard.page_daily import (
    BG,
    CARD,
    CARD_DARK,
    BORDER,
    BADGE_BG,
    BADGE_BD,
    TXT_MAIN,
    TXT_SUB,
    TXT_MUTED,
    SKY,
    TEAL,
    EMERALD,
    GREEN_DOT,
    AMBER,
    AMBER_TXT,
    RED,
    _build_radial_glow,
)
from dashboard.telemetry import TelemetryHistory
from i18n import get_lang, t

W, H = 640, 480

_TAB_ACTIVE_BG = (22, 38, 58)
_GRID_LINE     = (20, 30, 44)
_GRID_SUB      = (16, 24, 36)
_WINDOWS       = (30, 60, 180)


@dataclass(frozen=True)
class ParamSpec:
    key: str
    unit: str
    fmt: str
    y_min: float
    y_max: float
    y_fmt: str
    color: tuple
    feature: Optional[str] = None
    warn_high: Optional[float] = None
    danger_high: Optional[float] = None
    warn_low: Optional[float] = None
    danger_low: Optional[float] = None


def _build_specs() -> list[ParamSpec]:
    return [
        ParamSpec(
            key="rpm",
            unit="rpm",
            fmt="{:.0f}",
            y_min=0.0,
            y_max=float(getattr(config, "RPM_MAX", 7000)),
            y_fmt="{:.0f}",
            color=SKY,
            feature=None,
            warn_high=float(getattr(config, "SHIFT_RPM", 5300)),
            danger_high=float(getattr(config, "RPM_REDLINE", 5500)),
        ),
        ParamSpec(
            key="speed",
            unit="km/h",
            fmt="{:.0f}",
            y_min=0.0,
            y_max=float(getattr(config, "SPEED_MAX", 200)),
            y_fmt="{:.0f}",
            color=TEAL,
            feature=None,
        ),
        ParamSpec(
            key="water_temp",
            unit="°C",
            fmt="{:.1f}",
            y_min=float(getattr(config, "TEMP_MIN", 40)),
            y_max=float(getattr(config, "TEMP_MAX", 120)),
            y_fmt="{:.0f}",
            color=SKY,
            feature="water_temp",
            warn_high=float(getattr(config, "TEMP_COLOR_WARN", 95.0)),
            danger_high=float(getattr(config, "TEMP_COLOR_DANGER", 105.0)),
        ),
        ParamSpec(
            key="oil_temp",
            unit="°C",
            fmt="{:.1f}",
            y_min=40.0,
            y_max=130.0,
            y_fmt="{:.0f}",
            color=AMBER_TXT,
            feature="oil_temp",
            warn_high=float(getattr(config, "TEMP_COLOR_WARN", 95.0)),
            danger_high=float(getattr(config, "TEMP_COLOR_DANGER", 105.0)),
        ),
        ParamSpec(
            key="voltage",
            unit="V",
            fmt="{:.2f}",
            y_min=10.5,
            y_max=15.5,
            y_fmt="{:.1f}",
            color=EMERALD,
            feature="battery_voltage",
            warn_low=float(getattr(config, "VOLT_COLOR_LOW_WARN", 13.0)),
            danger_low=float(getattr(config, "VOLT_COLOR_LOW_DANGER", 11.8)),
            danger_high=float(getattr(config, "VOLT_COLOR_HIGH_WARN", 14.8)),
        ),
        ParamSpec(
            key="throttle",
            unit="%",
            fmt="{:.1f}",
            y_min=0.0,
            y_max=100.0,
            y_fmt="{:.0f}",
            color=SKY,
            feature="tps_load",
        ),
        ParamSpec(
            key="load",
            unit="%",
            fmt="{:.1f}",
            y_min=0.0,
            y_max=100.0,
            y_fmt="{:.0f}",
            color=TEAL,
            feature="tps_load",
        ),
        ParamSpec(
            key="intake_temp",
            unit="°C",
            fmt="{:.1f}",
            y_min=0.0,
            y_max=80.0,
            y_fmt="{:.0f}",
            color=TEAL,
            feature="intake_temp",
        ),
        ParamSpec(
            key="consumption_kml",
            unit="km/l",
            fmt="{:.1f}",
            y_min=0.0,
            y_max=25.0,
            y_fmt="{:.0f}",
            color=EMERALD,
            feature="consumption",
        ),
        ParamSpec(
            key="maf",
            unit="g/s",
            fmt="{:.1f}",
            y_min=0.0,
            y_max=100.0,
            y_fmt="{:.0f}",
            color=SKY,
            feature="consumption",
        ),
        ParamSpec(
            key="fuel",
            unit="%",
            fmt="{:.1f}",
            y_min=0.0,
            y_max=100.0,
            y_fmt="{:.0f}",
            color=AMBER_TXT,
            feature="fuel_level",
            warn_low=20.0,
            danger_low=10.0,
        ),
        ParamSpec(
            key="boost_bar",
            unit="bar",
            fmt="{:.2f}",
            y_min=0.0,
            y_max=float(getattr(config, "BOOST_MAX_BAR", 2.0)),
            y_fmt="{:.1f}",
            color=AMBER_TXT,
            feature="turbo",
            warn_high=float(getattr(config, "BOOST_MAX_BAR", 2.0)) * 0.85,
        ),
        ParamSpec(
            key="map_kpa",
            unit="kPa",
            fmt="{:.0f}",
            y_min=0.0,
            y_max=250.0,
            y_fmt="{:.0f}",
            color=SKY,
            feature="turbo",
        ),
    ]


class ChartsPage(Page):
    """Real-time line & area chart viewer with dedicated inner tabs per OBD parameter."""

    @property
    def name(self) -> str:
        return t("charts.page_name")

    def __init__(self, screen, history: TelemetryHistory):
        super().__init__(screen)
        self.history = history
        sw, sh = screen.get_size()
        self._direct = (sw, sh) == (W, H)
        self.cv = screen if self._direct else pygame.Surface((W, H))

        self._all_specs = _build_specs()
        self._selected_key = "rpm"
        self._window_idx = 1  # default 60s
        self._tab_scroll_x = 0.0
        self._tab_hitboxes = []  # list of (pygame.Rect, param_key)
        self._win_pill_rect = None
        self._axis_y_active = False
        self._data = {}

        self._fonts = {}
        self._text_cache = {}
        self._lang = get_lang()
        self._bg_glow = _build_radial_glow((W, H), (W // 2, 50), 340, SKY, max_alpha=28)

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
        if get_lang() != self._lang:
            self._lang = get_lang()
            self._text_cache.clear()
        key = (text_str, size, color, mono, bold)
        surf = self._text_cache.get(key)
        if surf is None:
            if len(self._text_cache) > 600:
                self._text_cache.clear()
            surf = self._font(size, mono=mono, bold=bold).render(text_str, True, color)
            self._text_cache[key] = surf
        return surf

    @staticmethod
    def _blit_center(dst, surf, cx: int, cy: int):
        dst.blit(surf, (cx - surf.get_width() // 2, cy - surf.get_height() // 2))

    # ── Active Tabs & Input ──────────────────────────────────────────────────

    def _active_specs(self) -> list[ParamSpec]:
        active = [
            s for s in self._all_specs
            if s.feature is None or settings.enabled(s.feature)
        ]
        return active or [self._all_specs[0]]

    def _current_index_and_specs(self) -> tuple[int, list[ParamSpec]]:
        specs = self._active_specs()
        for i, s in enumerate(specs):
            if s.key == self._selected_key:
                return i, specs
        self._selected_key = specs[0].key
        return 0, specs

    def _step_tab(self, delta: int):
        idx, specs = self._current_index_and_specs()
        new_idx = (idx + delta) % len(specs)
        self._selected_key = specs[new_idx].key

    def _cycle_window(self):
        self._window_idx = (self._window_idx + 1) % len(_WINDOWS)

    def handle_event(self, event) -> bool:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w, pygame.K_PAGEUP):
                self._step_tab(-1)
                return True
            if event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_PAGEDOWN):
                self._step_tab(1)
                return True
            if event.key == pygame.K_TAB:
                mods = pygame.key.get_mods()
                self._step_tab(-1 if (mods & pygame.KMOD_SHIFT) else 1)
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._cycle_window()
                return True

        elif event.type == pygame.JOYHATMOTION:
            _hx, hy = event.value
            if hy == 1:
                self._step_tab(-1)
                return True
            if hy == -1:
                self._step_tab(1)
                return True

        elif event.type == pygame.JOYAXISMOTION and event.axis == 1:
            if event.value < -0.55 and not self._axis_y_active:
                self._axis_y_active = True
                self._step_tab(-1)
                return True
            if event.value > 0.55 and not self._axis_y_active:
                self._axis_y_active = True
                self._step_tab(1)
                return True
            if -0.30 <= event.value <= 0.30:
                self._axis_y_active = False

        elif event.type == pygame.JOYBUTTONDOWN:
            if event.button in (0, 1, 2):
                self._cycle_window()
                return True
            if event.button in (11, 13):
                self._step_tab(-1)
                return True
            if event.button in (12, 14):
                self._step_tab(1)
                return True

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mx, my = event.pos
                if not self._direct:
                    sw, sh = self.screen.get_size()
                    if sw > 0 and sh > 0:
                        mx = int(mx * W / sw)
                        my = int(my * H / sh)
                for rect, key in self._tab_hitboxes:
                    if rect.collidepoint(mx, my):
                        self._selected_key = key
                        return True
                if self._win_pill_rect and self._win_pill_rect.collidepoint(mx, my):
                    self._cycle_window()
                    return True
            elif event.button == 4:  # scroll up
                self._step_tab(-1)
                return True
            elif event.button == 5:  # scroll down
                self._step_tab(1)
                return True

        return False

    # ── Status Evaluation ────────────────────────────────────────────────────

    @staticmethod
    def _eval_state(spec: ParamSpec, val: float, connected: bool) -> int:
        if not connected or val <= 0:
            return 0
        if spec.danger_high is not None and val >= spec.danger_high:
            return 2
        if spec.danger_low is not None and val <= spec.danger_low:
            return 2
        if spec.warn_high is not None and val >= spec.warn_high:
            return 1
        if spec.warn_low is not None and val <= spec.warn_low:
            return 1
        return 0

    @staticmethod
    def _draw_dashed_hline(cv, x1: int, x2: int, y: int, color: tuple, dash: int = 6, gap: int = 4):
        x = x1
        while x < x2:
            end_x = min(x2, x + dash)
            pygame.draw.line(cv, color, (x, y), (end_x, y), 1)
            x += dash + gap

    # ── Lifecycle & Rendering ────────────────────────────────────────────────

    def update(self, data: dict):
        self._data = data

    def _draw_tab_strip(self, cv, sel_idx: int, specs: list[ParamSpec]):
        strip_rect = pygame.Rect(28, 42, W - 56, 30)
        gap = 6
        pills = []
        cursor_x = 0
        for i, spec in enumerate(specs):
            lbl = t(f"charts.tab.{spec.key}")
            is_sel = i == sel_idx
            surf = self._txt(lbl, 11, TXT_MAIN if is_sel else TXT_SUB, bold=True)
            pw = max(54, surf.get_width() + 22)
            pills.append((i, spec, surf, cursor_x, pw))
            cursor_x += pw + gap

        total_content_w = max(0, cursor_x - gap)
        max_scroll = max(0.0, float(total_content_w - strip_rect.w))

        # Keep active pill comfortably centered inside strip_rect
        _, _, _, sel_x, sel_w = pills[sel_idx]
        target_scroll = (sel_x + sel_w * 0.5) - (strip_rect.w * 0.5)
        target_scroll = max(0.0, min(max_scroll, target_scroll))
        self._tab_scroll_x += (target_scroll - self._tab_scroll_x) * 0.32
        if abs(target_scroll - self._tab_scroll_x) < 0.5:
            self._tab_scroll_x = target_scroll

        old_clip = cv.get_clip()
        cv.set_clip(strip_rect)
        self._tab_hitboxes = []

        for i, spec, surf, rel_x, pw in pills:
            px = int(round(strip_rect.x + rel_x - self._tab_scroll_x))
            r = pygame.Rect(px, strip_rect.y + 1, pw, 28)
            if r.right < strip_rect.left or r.left > strip_rect.right:
                continue

            is_sel = i == sel_idx
            if is_sel:
                pygame.draw.rect(cv, _TAB_ACTIVE_BG, r, border_radius=7)
                pygame.draw.rect(cv, spec.color, r, 1, border_radius=7)
                pygame.draw.rect(cv, spec.color, (r.x + 10, r.bottom - 3, r.w - 20, 2), border_radius=1)
            else:
                pygame.draw.rect(cv, CARD, r, border_radius=7)
                pygame.draw.rect(cv, BORDER, r, 1, border_radius=7)

            self._blit_center(cv, surf, r.centerx, r.centery - (1 if is_sel else 0))
            clipped_hit = r.clip(strip_rect)
            if clipped_hit.w > 0:
                self._tab_hitboxes.append((clipped_hit, spec.key))

        cv.set_clip(old_clip)

        # Subtle overflow chevrons with clean margin
        if self._tab_scroll_x > 2.0:
            self._blit_center(cv, self._txt("‹", 16, SKY, bold=True), 15, strip_rect.centery - 1)
        if (max_scroll - self._tab_scroll_x) > 2.0:
            self._blit_center(cv, self._txt("›", 16, SKY, bold=True), W - 15, strip_rect.centery - 1)

    def draw(self):
        cv = self.cv
        cv.fill(BG)
        cv.blit(self._bg_glow, (0, 0))

        d = self._data
        now = time.monotonic()
        sel_idx, specs = self._current_index_and_specs()
        spec = specs[sel_idx]
        win_secs = _WINDOWS[self._window_idx]

        connected = bool(d.get("connected", False))
        is_mock = settings.enabled("mock_mode")
        obd_port = str(d.get("obd_port", "") or "").replace("/dev/", "")

        # 1. Top Header Bar
        sub_txt = t("charts.tab_counter", idx=sel_idx + 1, total=len(specs))
        cv.blit(self._txt(sub_txt, 12, TXT_SUB, mono=True), (24, 17))

        hdr_surf = self._txt(t("charts.page_name"), 13, SKY, bold=True)
        self._blit_center(cv, hdr_surf, W // 2, 24)
        hdr_half_w = hdr_surf.get_width() // 2

        dot_col = GREEN_DOT if connected else RED
        dot_x = W // 2 - hdr_half_w - 12
        gfxdraw.filled_circle(cv, dot_x, 24, 4, dot_col)
        gfxdraw.aacircle(cv, dot_x, 24, 4, dot_col)

        if is_mock:
            cv.blit(self._txt(t("mode.badge_mock"), 11, AMBER_TXT, mono=True), (W // 2 + hdr_half_w + 10, 18))
        elif connected and obd_port:
            cv.blit(self._txt(obd_port, 11, TXT_MUTED, mono=True), (W // 2 + hdr_half_w + 10, 18))

        if settings.enabled("console_battery"):
            draw_phone_battery(
                cv,
                W - 24,
                24,
                d.get("console_battery_pct"),
                bool(d.get("console_battery_charging", False)),
                self._font(13, mono=True, bold=True),
            )

        # 2. Inner Parameter Tab Strip
        self._draw_tab_strip(cv, sel_idx, specs)

        # 3. Main Telemetry Chart Card
        card_r = pygame.Rect(24, 80, W - 48, 338)
        pygame.draw.rect(cv, CARD, card_r, border_radius=10)
        pygame.draw.rect(cv, BORDER, card_r, 1, border_radius=10)

        raw_val = d.get(spec.key)
        live_val = float(raw_val) if raw_val is not None else 0.0
        state = self._eval_state(spec, live_val, connected)

        st_dot_col = RED if state == 2 else (AMBER if state == 1 else (GREEN_DOT if connected else BADGE_BD))
        gfxdraw.filled_circle(cv, card_r.x + 18, card_r.y + 20, 4, st_dot_col)
        gfxdraw.aacircle(cv, card_r.x + 18, card_r.y + 20, 4, st_dot_col)

        title_surf = self._txt(t(f"charts.title.{spec.key}"), 13, TXT_SUB, bold=True)
        cv.blit(title_surf, (card_r.x + 28, card_r.y + 12))

        if connected and (raw_val is not None):
            val_str = spec.fmt.format(live_val)
            val_col = RED if state == 2 else (AMBER_TXT if state == 1 else TXT_MAIN)
        else:
            val_str = "--"
            val_col = TXT_MUTED

        val_surf = self._txt(val_str, 28, val_col, mono=True, bold=True)
        cv.blit(val_surf, (card_r.x + 16, card_r.y + 32))
        unit_surf = self._txt(spec.unit, 12, spec.color, bold=True)
        cv.blit(unit_surf, (card_r.x + 22 + val_surf.get_width(), card_r.y + 44))

        # Fetch window samples
        samples = self.history.get_window(spec.key, float(win_secs), now=now)
        if connected and raw_val is not None:
            if not samples or (now - samples[-1][0]) > 0.02:
                samples = samples + [(now, live_val)]

        # Compute window KPIs (Min / Avg / Max)
        if samples:
            vals = [v for _, v in samples]
            s_min = spec.fmt.format(min(vals))
            s_avg = spec.fmt.format(sum(vals) / len(vals))
            s_max = spec.fmt.format(max(vals))
        else:
            s_min = s_avg = s_max = "--"

        kpis = (
            (t("charts.stat_min"), s_min, TXT_MAIN),
            (t("charts.stat_avg"), s_avg, TXT_MAIN),
            (t("charts.stat_max"), s_max, TXT_MAIN),
            (t("charts.stat_win"), f"{win_secs}s", SKY),
        )
        pill_w = 68
        pill_gap = 6
        kpi_start_x = card_r.right - 14 - (pill_w * 4 + pill_gap * 3)
        self._win_pill_rect = None
        for ki, (k_lbl, k_val, k_col) in enumerate(kpis):
            kr = pygame.Rect(kpi_start_x + ki * (pill_w + pill_gap), card_r.y + 14, pill_w, 48)
            is_win_pill = ki == 3
            pygame.draw.rect(cv, BADGE_BG if is_win_pill else CARD_DARK, kr, border_radius=7)
            pygame.draw.rect(cv, SKY if is_win_pill else BORDER, kr, 1, border_radius=7)
            cv.blit(self._txt(k_lbl, 9, TXT_MUTED, bold=True), (kr.x + 8, kr.y + 6))
            cv.blit(self._txt(k_val, 13, k_col, mono=True, bold=True), (kr.x + 8, kr.y + 23))
            if is_win_pill:
                self._win_pill_rect = kr

        # 4. Inset Plot Canvas
        plot_box = pygame.Rect(38, 152, W - 76, 254)
        pygame.draw.rect(cv, CARD_DARK, plot_box, border_radius=8)
        pygame.draw.rect(cv, BORDER, plot_box, 1, border_radius=8)

        p_left   = plot_box.x + 48
        p_right  = plot_box.right - 14
        p_top    = plot_box.y + 14
        p_bottom = plot_box.bottom - 24
        p_w      = p_right - p_left
        p_h      = p_bottom - p_top

        # Dynamic Y-scale expansion if signal exceeds nominal range
        y_min = spec.y_min
        y_max = spec.y_max
        if samples:
            actual_min = min(v for _, v in samples)
            actual_max = max(v for _, v in samples)
            if actual_min < y_min:
                y_min = math.floor(actual_min / 5.0) * 5.0 if y_min > 0 else actual_min
            if actual_max > y_max:
                y_max = actual_max * 1.08
        y_span = max(1e-3, y_max - y_min)

        def val_to_y(v: float) -> float:
            clamped = max(y_min, min(y_max, v))
            return p_bottom - ((clamped - y_min) / y_span) * p_h

        # Y-axis horizontal gridlines & labels
        for step_i in range(5):
            frac = step_i / 4.0
            gy = int(round(p_bottom - frac * p_h))
            g_val = y_min + frac * y_span
            pygame.draw.line(cv, _GRID_LINE, (p_left, gy), (p_right, gy), 1)
            ylbl = self._txt(spec.y_fmt.format(g_val), 10, TXT_MUTED, mono=True, bold=False)
            cv.blit(ylbl, (p_left - 6 - ylbl.get_width(), gy - ylbl.get_height() // 2))

        # X-axis vertical time gridlines & labels
        for step_i in range(5):
            frac = step_i / 4.0
            gx = int(round(p_left + frac * p_w))
            pygame.draw.line(cv, _GRID_SUB, (gx, p_top), (gx, p_bottom), 1)
            secs_ago = int(round((1.0 - frac) * win_secs))
            tlbl_str = t("charts.now") if secs_ago == 0 else f"-{secs_ago}s"
            tlbl = self._txt(tlbl_str, 10, TXT_MUTED, mono=True, bold=False)
            if step_i == 4:
                cv.blit(tlbl, (p_right - tlbl.get_width(), p_bottom + 6))
            else:
                self._blit_center(cv, tlbl, gx, p_bottom + 12)

        # Threshold dashed guide lines
        thresholds = (
            (spec.warn_high, AMBER),
            (spec.warn_low, AMBER),
            (spec.danger_high, RED),
            (spec.danger_low, RED),
        )
        for th_val, th_col in thresholds:
            if th_val is not None and y_min < th_val < y_max:
                ty = int(round(val_to_y(th_val)))
                self._draw_dashed_hline(cv, p_left, p_right, ty, th_col)

        # Plot Area + Smooth Curve
        if len(samples) >= 2:
            # Downsample if needed so x coordinates advance cleanly
            pts = []
            last_px = None
            for t_pt, v_pt in samples:
                age = max(0.0, min(float(win_secs), now - t_pt))
                px = p_right - (age / float(win_secs)) * p_w
                py = val_to_y(v_pt)
                ipx = int(round(px))
                if last_px is None or ipx != last_px or t_pt == samples[-1][0]:
                    pts.append((px, py))
                    last_px = ipx

            if len(pts) >= 2:
                old_clip = cv.get_clip()
                cv.set_clip(pygame.Rect(p_left, p_top - 2, p_w + 2, p_h + 4))

                fill_surf = pygame.Surface((p_w + 2, p_h + 2), pygame.SRCALPHA)
                local_pts = [(int(round(px - p_left)), int(round(py - p_top))) for px, py in pts]
                poly = [(local_pts[0][0], p_h)] + local_pts + [(local_pts[-1][0], p_h)]
                if len(poly) >= 3:
                    pygame.draw.polygon(fill_surf, (*spec.color, 44), poly)
                cv.blit(fill_surf, (p_left, p_top))

                int_pts = [(int(round(px)), int(round(py))) for px, py in pts]
                pygame.draw.lines(cv, spec.color, False, int_pts, 2)
                pygame.draw.aalines(cv, spec.color, False, pts)
                cv.set_clip(old_clip)

                # Live glowing dot at current tip
                tip_x, tip_y = int(round(pts[-1][0])), int(round(pts[-1][1]))
                tip_col = RED if state == 2 else (AMBER_TXT if state == 1 else spec.color)
                glow = pygame.Surface((20, 20), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*tip_col, 70), (10, 10), 8)
                cv.blit(glow, (tip_x - 10, tip_y - 10))
                gfxdraw.filled_circle(cv, tip_x, tip_y, 4, tip_col)
                gfxdraw.aacircle(cv, tip_x, tip_y, 4, TXT_MAIN)
        elif not connected:
            wait_surf = self._txt(t("charts.waiting"), 12, TXT_MUTED, bold=False)
            self._blit_center(cv, wait_surf, (p_left + p_right) // 2, (p_top + p_bottom) // 2)

        # 5. Footer Controls Legend
        hint_str = t("charts.hint", idx=sel_idx + 1, total=len(specs), win=win_secs)
        self._blit_center(cv, self._txt(hint_str, 11, TXT_MUTED, bold=False), W // 2, 434)

        if not self._direct:
            pygame.transform.smoothscale(cv, self.screen.get_size(), self.screen)

    def draw_alarms(self, alarm):
        if not alarm.blink_on:
            return
        lvl = alarm.overall()
        if lvl >= 1:
            col = RED if lvl == 2 else AMBER
            pygame.draw.rect(self.screen, col, self.screen.get_rect(), 3)
