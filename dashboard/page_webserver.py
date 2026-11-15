"""Interactive R36S / desktop Web Analytics Server page matching the OEM Daily theme."""
import math
import time

import pygame
from pygame import gfxdraw

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
    RED,
    _build_radial_glow,
    _draw_thick_arc,
)
from i18n import t
from web import analytics

W, H = 640, 480


class WebServerPage(Page):
    """Gamepad & keyboard controllable Web Analytics Server dashboard page."""

    _RING_CENTER = (320, 118)
    _RING_R      = 42
    _RING_THICK  = 8

    @property
    def name(self) -> str:
        return t("web.page_name")

    def __init__(self, screen, web_server):
        super().__init__(screen)
        self.web_server = web_server
        sw, sh = screen.get_size()
        self._direct = (sw, sh) == (W, H)
        self.cv = screen if self._direct else pygame.Surface((W, H))

        self._data = {}
        self._overview = {
            "days_count":     0,
            "sessions_count": 0,
            "total_bytes":    0,
        }
        self._last_overview_ts = 0.0
        self._cached_urls = []
        self._last_url_ts = 0.0

        sans = "segoeui,dejavusans,liberationsans,arial,sans-serif"
        mono = "consolas,dejavusansmono,liberationmono,monospace"
        self._font_hdr      = pygame.font.SysFont(sans, 13, bold=True)
        self._font_sub_hdr  = pygame.font.SysFont(mono, 12, bold=True)
        self._font_status   = pygame.font.SysFont(mono, 11, bold=True)
        self._font_title    = pygame.font.SysFont(sans, 16, bold=True)
        self._font_sub      = pygame.font.SysFont(sans, 12, bold=False)
        self._font_url      = pygame.font.SysFont(mono, 20, bold=True)
        self._font_alt_url  = pygame.font.SysFont(mono, 11, bold=False)
        self._font_btn      = pygame.font.SysFont(sans, 13, bold=True)
        self._font_pill_lbl = pygame.font.SysFont(sans, 10, bold=True)
        self._font_pill_val = pygame.font.SysFont(mono, 13, bold=True)
        self._font_hint     = pygame.font.SysFont(sans, 12, bold=False)

        self._glow_top  = _build_radial_glow((W, H), (W // 2, 50), 340, SKY, max_alpha=28)
        self._glow_teal = _build_radial_glow((W, H), self._RING_CENTER, 130, TEAL, max_alpha=24)

    def handle_event(self, event) -> bool:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._toggle_server()
                return True
        elif event.type == pygame.JOYBUTTONDOWN:
            # Face buttons A (0), B (1), X (2) toggle the Web Server on/off
            if event.button in (0, 1, 2):
                self._toggle_server()
                return True
        return False

    def _toggle_server(self):
        self.web_server.toggle()
        self._last_url_ts = 0.0
        self._last_overview_ts = 0.0

    @staticmethod
    def _blit_center(dst, surf, cx: int, cy: int):
        dst.blit(surf, (cx - surf.get_width() // 2, cy - surf.get_height() // 2))

    def _refresh_Throttled(self):
        now = time.monotonic()
        if now - self._last_overview_ts >= 2.0:
            self._last_overview_ts = now
            try:
                self._overview = analytics.get_storage_overview()
            except Exception:
                pass
        if now - self._last_url_ts >= 3.0:
            self._last_url_ts = now
            self._cached_urls = self.web_server.urls()

    def update(self, data: dict):
        self._data = data
        self._refresh_Throttled()

    def _draw_beacon(self, cv, is_online: bool, t_sec: float):
        cx, cy = self._RING_CENTER
        r_mid = self._RING_R
        thick = self._RING_THICK

        # Track circle
        pygame.draw.circle(cv, BORDER, (cx, cy), int(r_mid + thick / 2), width=thick)

        if is_online:
            cv.blit(self._glow_teal, (0, 0))
            deg = (t_sec * 120.0) % 360.0
            _draw_thick_arc(cv, cx, cy, r_mid, thick, deg, 105.0, TEAL)
            _draw_thick_arc(cv, cx, cy, r_mid, thick, (deg + 180.0) % 360.0, 75.0, SKY)

        gfxdraw.filled_circle(cv, cx, cy, 31, CARD)
        gfxdraw.aacircle(cv, cx, cy, 31, TEAL if is_online else BORDER)

        # Stylized Analytics Bar Chart icon inside center circle
        bar_col = TEAL if is_online else TXT_MUTED
        accent_col = SKY if is_online else BADGE_BD
        pygame.draw.rect(cv, accent_col, (cx - 13, cy + 1, 6, 12), border_radius=2)
        pygame.draw.rect(cv, bar_col,    (cx - 3,  cy - 6, 6, 19), border_radius=2)
        pygame.draw.rect(cv, accent_col, (cx + 7,  cy - 12, 6, 25), border_radius=2)

        # Status badge below ring
        st_txt = t("web.status_online") if is_online else t("web.status_offline")
        st_col = TEAL if is_online else TXT_MUTED
        st_surf = self._font_status.render(st_txt, True, st_col)
        bw = st_surf.get_width() + 26
        br = pygame.Rect(cx - bw // 2, cy + 50, bw, 20)
        pygame.draw.rect(cv, BADGE_BG, br, border_radius=10)
        pygame.draw.rect(cv, TEAL if is_online else BADGE_BD, br, 1, border_radius=10)
        dot_c = GREEN_DOT if is_online else TXT_MUTED
        gfxdraw.filled_circle(cv, br.x + 10, br.centery, 3, dot_c)
        gfxdraw.aacircle(cv, br.x + 10, br.centery, 3, dot_c)
        cv.blit(st_surf, (br.x + 18, br.centery - st_surf.get_height() // 2))

    def draw(self):
        cv = self.cv
        cv.fill(BG)
        cv.blit(self._glow_top, (0, 0))

        t_sec = pygame.time.get_ticks() / 1000.0
        is_online = self.web_server.is_running

        # 1. Top Header Bar
        cv.blit(self._font_sub_hdr.render(t("web.header_sub"), True, TXT_SUB), (28, 17))
        hdr_surf = self._font_hdr.render(t("web.page_name"), True, SKY)
        self._blit_center(cv, hdr_surf, W // 2, 24)
        dot_x = W // 2 - hdr_surf.get_width() // 2 - 12
        dot_col = GREEN_DOT if is_online else BADGE_BD
        gfxdraw.filled_circle(cv, dot_x, 24, 4, dot_col)
        gfxdraw.aacircle(cv, dot_x, 24, 4, dot_col)

        if settings.enabled("console_battery"):
            draw_phone_battery(
                cv,
                W - 28,
                24,
                self._data.get("console_battery_pct"),
                bool(self._data.get("console_battery_charging", False)),
                self._font_sub_hdr,
            )

        # 2. Central Beacon Ring + Status Pill
        self._draw_beacon(cv, is_online, t_sec)

        # 3. Main Card
        card_r = pygame.Rect(48, 198, W - 96, 152)
        pygame.draw.rect(cv, CARD, card_r, border_radius=10)
        pygame.draw.rect(cv, BORDER, card_r, 1, border_radius=10)

        urls = self._cached_urls or self.web_server.urls()
        primary_url = urls[0] if urls else f"http://localhost:{self.web_server.port}"

        if is_online:
            self._blit_center(
                cv,
                self._font_title.render(t("web.title_online"), True, TXT_MAIN),
                W // 2,
                221,
            )

            # Highlighted URL box
            url_box = pygame.Rect(card_r.x + 36, 240, card_r.w - 72, 42)
            pygame.draw.rect(cv, CARD_DARK, url_box, border_radius=8)
            pygame.draw.rect(cv, SKY, url_box, 1, border_radius=8)
            self._blit_center(
                cv,
                self._font_url.render(primary_url, True, SKY),
                url_box.centerx,
                url_box.centery,
            )

            if len(urls) > 1:
                alt = ", ".join(urls[1:3])
                self._blit_center(
                    cv,
                    self._font_alt_url.render(t("web.alt_urls", urls=alt), True, TXT_MUTED),
                    W // 2,
                    294,
                )

            # Stop Server button
            btn_r = pygame.Rect((W - 250) // 2, 310, 250, 28)
            pygame.draw.rect(cv, BADGE_BG, btn_r, border_radius=7)
            pygame.draw.rect(cv, AMBER, btn_r, 1, border_radius=7)
            self._blit_center(
                cv,
                self._font_btn.render(t("web.btn_stop"), True, AMBER_TXT),
                btn_r.centerx,
                btn_r.centery,
            )
        else:
            self._blit_center(
                cv,
                self._font_title.render(t("web.title_offline"), True, TXT_MAIN),
                W // 2,
                225,
            )
            self._blit_center(
                cv,
                self._font_sub.render(t("web.sub_offline"), True, TXT_SUB),
                W // 2,
                250,
            )

            err = self.web_server.last_error
            info_txt = err[:58] if err else f"{primary_url}"
            info_col = RED if err else TXT_MUTED
            self._blit_center(
                cv,
                self._font_alt_url.render(info_txt, True, info_col),
                W // 2,
                276,
            )

            # Start Server button
            btn_r = pygame.Rect((W - 266) // 2, 298, 266, 36)
            pygame.draw.rect(cv, (19, 44, 68), btn_r, border_radius=8)
            pygame.draw.rect(cv, SKY, btn_r, 1, border_radius=8)
            self._blit_center(
                cv,
                self._font_btn.render(t("web.btn_start"), True, SKY),
                btn_r.centerx,
                btn_r.centery,
            )

        # 4. Bottom 3 Storage & Traffic Summary Pills
        mb_str = f"{self._overview['total_bytes'] / 1048576.0:.2f}"
        pills = (
            (t("web.pill_days"),     t("web.pill_days_val", n=self._overview["days_count"])),
            (t("web.pill_sessions"), t("web.pill_sessions_val", n=self._overview["sessions_count"], mb=mb_str)),
            (t("web.pill_traffic"),  t("web.pill_traffic_val", port=self.web_server.port, req=self.web_server.request_count)),
        )
        gap = 12
        total_w = W - 96
        pill_w = (total_w - gap * 2) // 3
        sx = 48
        for i, (lbl, val) in enumerate(pills):
            pr = pygame.Rect(sx + i * (pill_w + gap), 362, pill_w, 54)
            pygame.draw.rect(cv, CARD, pr, border_radius=8)
            pygame.draw.rect(cv, BORDER, pr, 1, border_radius=8)
            cv.blit(self._font_pill_lbl.render(lbl, True, TXT_MUTED), (pr.x + 12, pr.y + 8))
            val_col = TEAL if (i == 2 and is_online) else TXT_MAIN
            cv.blit(self._font_pill_val.render(val, True, val_col), (pr.x + 12, pr.y + 27))

        # 5. Footer Controls Legend
        self._blit_center(
            cv,
            self._font_hint.render(t("web.hint"), True, TXT_MUTED),
            W // 2,
            435,
        )

        if not self._direct:
            pygame.transform.smoothscale(cv, self.screen.get_size(), self.screen)
