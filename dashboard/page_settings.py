"""Interactive R36S / desktop Settings page for enabling/disabling features and language."""
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
    GREEN_DOT,
    AMBER,
    AMBER_TXT,
    _build_radial_glow,
)
from i18n import get_lang, t

W, H = 640, 480

_ROW_SELECT_BG = (24, 36, 54)
_VISIBLE_ROWS  = 7

# Ordered list of configurable entries: (kind, key, label_i18n_key)
_ITEMS = [
    ("lang",   "language",        "settings.item.language"),
    ("toggle", "data_logging",    "settings.item.data_logging"),
    ("toggle", "turbo",           "settings.item.turbo"),
    ("toggle", "water_temp",      "settings.item.water_temp"),
    ("toggle", "oil_temp",        "settings.item.oil_temp"),
    ("toggle", "battery_voltage", "settings.item.battery_voltage"),
    ("toggle", "tps_load",        "settings.item.tps_load"),
    ("toggle", "fuel_level",      "settings.item.fuel_level"),
    ("toggle", "consumption",     "settings.item.consumption"),
    ("toggle", "zero_to_hundred", "settings.item.zero_to_hundred"),
    ("toggle", "gear_indicator",  "settings.item.gear_indicator"),
    ("toggle", "intake_temp",     "settings.item.intake_temp"),
    ("toggle", "console_battery", "settings.item.console_battery"),
    ("toggle", "alarm_sound",     "settings.item.alarm_sound"),
    ("reset",  "reset",           "settings.item.reset"),
]


class SettingsPage(Page):
    """Gamepad & keyboard navigable settings menu matching the OEM Daily theme."""

    @property
    def name(self) -> str:
        return t("settings.page_name")

    def __init__(self, screen):
        super().__init__(screen)
        sw, sh = screen.get_size()
        self._direct = (sw, sh) == (W, H)
        self.cv = screen if self._direct else pygame.Surface((W, H))

        self.selected = 0
        self.scroll_top = 0
        self._axis_y_active = False
        self._data = {}

        sans = "segoeui,dejavusans,liberationsans,arial,sans-serif"
        mono = "consolas,dejavusansmono,liberationmono,monospace"
        self._font_hdr   = pygame.font.SysFont(sans, 13, bold=True)
        self._font_sub   = pygame.font.SysFont(mono, 12, bold=True)
        self._font_row   = pygame.font.SysFont(sans, 14, bold=True)
        self._font_badge = pygame.font.SysFont(mono, 12, bold=True)
        self._font_hint  = pygame.font.SysFont(sans, 12, bold=False)

        self._bg_glow = _build_radial_glow((W, H), (W // 2, 50), 340, SKY, max_alpha=28)

    # ── Navigation & Activation ──────────────────────────────────────────────

    def _move(self, delta: int):
        n = len(_ITEMS)
        self.selected = (self.selected + delta) % n
        if self.selected < self.scroll_top:
            self.scroll_top = self.selected
        elif self.selected >= self.scroll_top + _VISIBLE_ROWS:
            self.scroll_top = self.selected - _VISIBLE_ROWS + 1

    def _activate(self):
        kind, key, _ = _ITEMS[self.selected]
        if kind == "lang":
            settings.cycle_language()
            pygame.display.set_caption(t("app.window_title"))
        elif kind == "toggle":
            settings.toggle(key)
        elif kind == "reset":
            settings.reset_defaults()
            pygame.display.set_caption(t("app.window_title"))

    def handle_event(self, event) -> bool:
        # Keyboard navigation
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self._move(-1)
                return True
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self._move(1)
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._activate()
                return True

        # Gamepad D-pad Hat (Up/Down only; Left/Right passes through to switch pages)
        elif event.type == pygame.JOYHATMOTION:
            _hx, hy = event.value
            if hy == 1:
                self._move(-1)
                return True
            if hy == -1:
                self._move(1)
                return True

        # Gamepad Analog Stick Y-axis (with hysteresis)
        elif event.type == pygame.JOYAXISMOTION and event.axis == 1:
            if event.value < -0.55 and not self._axis_y_active:
                self._axis_y_active = True
                self._move(-1)
                return True
            if event.value > 0.55 and not self._axis_y_active:
                self._axis_y_active = True
                self._move(1)
                return True
            if -0.30 <= event.value <= 0.30:
                self._axis_y_active = False

        # Gamepad Buttons (Face buttons A/B/X toggle; D-pad button mappings 11/12 or 8/9 move)
        elif event.type == pygame.JOYBUTTONDOWN:
            # Face buttons A (0), B (1), X (2) toggle the highlighted option instead of exiting
            if event.button in (0, 1, 2):
                self._activate()
                return True
            # Common SDL2 Linux D-pad Up / Down button indices on R36S
            if event.button in (11, 13):
                self._move(-1)
                return True
            if event.button in (12, 14):
                self._move(1)
                return True

        return False

    # ── Rendering ────────────────────────────────────────────────────────────

    @staticmethod
    def _blit_center(dst, surf, cx: int, cy: int):
        dst.blit(surf, (cx - surf.get_width() // 2, cy - surf.get_height() // 2))

    def update(self, data: dict):
        self._data = data

    def _draw_switch(self, cv, right_x: int, center_y: int, is_on: bool):
        """Draw an OEM pill switch + status text aligned to `right_x`."""
        sw_w, sw_h = 42, 22
        sw_rect = pygame.Rect(right_x - sw_w, center_y - sw_h // 2, sw_w, sw_h)
        bg_col = GREEN_DOT if is_on else BADGE_BG
        bd_col = GREEN_DOT if is_on else BADGE_BD

        pygame.draw.rect(cv, bg_col, sw_rect, border_radius=11)
        pygame.draw.rect(cv, bd_col, sw_rect, 1, border_radius=11)

        knob_x = sw_rect.right - 11 if is_on else sw_rect.left + 11
        knob_col = TXT_MAIN if is_on else TXT_MUTED
        gfxdraw.filled_circle(cv, knob_x, center_y, 7, knob_col)
        gfxdraw.aacircle(cv, knob_x, center_y, 7, knob_col)

        st_str = t("settings.on") if is_on else t("settings.off")
        st_col = TEAL if is_on else TXT_MUTED
        lbl = self._font_badge.render(st_str, True, st_col)
        cv.blit(lbl, (sw_rect.left - 10 - lbl.get_width(), center_y - lbl.get_height() // 2))

    def draw(self):
        cv = self.cv
        cv.fill(BG)
        cv.blit(self._bg_glow, (0, 0))

        # 1. Top Header Bar
        cv.blit(self._font_sub.render(t("settings.header_sub"), True, TXT_SUB), (28, 17))
        self._blit_center(cv, self._font_hdr.render(t("settings.page_name"), True, SKY), W // 2, 24)

        if settings.enabled("console_battery"):
            draw_phone_battery(
                cv,
                W - 28,
                24,
                self._data.get("console_battery_pct"),
                bool(self._data.get("console_battery_charging", False)),
                self._font_sub,
            )

        # 2. Main List Card Container
        panel_rect = pygame.Rect(28, 46, W - 56, 368)
        pygame.draw.rect(cv, CARD, panel_rect, border_radius=10)
        pygame.draw.rect(cv, BORDER, panel_rect, 1, border_radius=10)

        total = len(_ITEMS)
        row_x = panel_rect.x + 10
        row_w = panel_rect.w - 28  # reserve space on right for scrollbar track
        row_h = 46
        gap   = 4
        start_y = panel_rect.y + 11

        visible_slice = _ITEMS[self.scroll_top : self.scroll_top + _VISIBLE_ROWS]
        for vis_i, (kind, key, lbl_key) in enumerate(visible_slice):
            idx = self.scroll_top + vis_i
            ry = start_y + vis_i * (row_h + gap)
            r = pygame.Rect(row_x, ry, row_w, row_h)
            is_sel = idx == self.selected

            if is_sel:
                pygame.draw.rect(cv, _ROW_SELECT_BG, r, border_radius=7)
                pygame.draw.rect(cv, SKY, r, 1, border_radius=7)
                pygame.draw.rect(cv, SKY, (r.x + 4, r.y + 9, 4, r.h - 18), border_radius=2)
            else:
                pygame.draw.rect(cv, CARD_DARK, r, border_radius=7)

            txt_col = TXT_MAIN if is_sel else TXT_SUB
            lbl_surf = self._font_row.render(t(lbl_key), True, txt_col)
            cv.blit(lbl_surf, (r.x + 16, r.centery - lbl_surf.get_height() // 2))

            right_edge = r.right - 14
            if kind == "lang":
                val_txt = f"< {t('lang.name')} >"
                badge = self._font_badge.render(val_txt, True, SKY if is_sel else TEAL)
                cv.blit(badge, (right_edge - badge.get_width(), r.centery - badge.get_height() // 2))
            elif kind == "toggle":
                self._draw_switch(cv, right_edge, r.centery, settings.enabled(key))
            elif kind == "reset":
                btn_lbl = self._font_badge.render(t("settings.action_reset"), True, AMBER_TXT)
                bw = btn_lbl.get_width() + 20
                btn_r = pygame.Rect(right_edge - bw, r.centery - 12, bw, 24)
                pygame.draw.rect(cv, BADGE_BG, btn_r, border_radius=5)
                pygame.draw.rect(cv, AMBER if is_sel else BADGE_BD, btn_r, 1, border_radius=5)
                self._blit_center(cv, btn_lbl, btn_r.centerx, btn_r.centery)

        # 3. Slim Scrollbar Track on right edge of card
        sb_x = panel_rect.right - 10
        sb_y = panel_rect.y + 12
        sb_h = panel_rect.h - 24
        pygame.draw.rect(cv, CARD_DARK, (sb_x, sb_y, 4, sb_h), border_radius=2)
        thumb_h = max(24, int(sb_h * (_VISIBLE_ROWS / total)))
        max_scroll = max(1, total - _VISIBLE_ROWS)
        thumb_y = sb_y + int((sb_h - thumb_h) * (self.scroll_top / max_scroll))
        pygame.draw.rect(cv, SKY, (sb_x, thumb_y, 4, thumb_h), border_radius=2)

        # 4. Controls Legend above page indicator dots
        hint_surf = self._font_hint.render(t("settings.hint"), True, TXT_MUTED)
        self._blit_center(cv, hint_surf, W // 2, 428)

        if not self._direct:
            pygame.transform.smoothscale(cv, self.screen.get_size(), self.screen)
