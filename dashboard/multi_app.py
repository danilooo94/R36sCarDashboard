import math
import time

import pygame
from pygame import gfxdraw

import config
import settings
from dashboard.alarm           import AlarmManager
from dashboard.console_battery import ConsoleBatteryReader, draw_phone_battery
from dashboard.page_daily      import (
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
    DailyCockpitPage,
    _build_radial_glow,
    _draw_thick_arc,
)
from dashboard.page_charts     import ChartsPage
from dashboard.page_settings   import SettingsPage
from dashboard.page_webserver  import WebServerPage
from dashboard.telemetry       import DerivedTelemetry, TelemetryHistory
from i18n                      import get_lang, t
from web.server                import WebAnalyticsServer


class MultiPageApp:
    """Unified application loop managing Cockpit, Live Charts, Web Analytics, and Settings pages."""

    _CONN_RING_CENTER = (320, 172)
    _CONN_RING_R      = 66
    _CONN_RING_THICK  = 12
    _MIN_SPLASH_SECS  = 1.4

    def __init__(self, store, start_page=0, web_server=None, reader_manager=None):
        pygame.init()
        flags = pygame.FULLSCREEN if config.FULLSCREEN else 0
        self.screen = pygame.display.set_mode(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT), flags)
        pygame.display.set_caption(t("app.window_title"))
        self.clock   = pygame.time.Clock()
        self.store   = store
        self.reader_manager = reader_manager
        self.running = True

        # ── Telemetria derivada, histórico de gráficos, bateria & Webserver ──
        self.derived = DerivedTelemetry()
        self.history = TelemetryHistory()
        self.console_battery = ConsoleBatteryReader()
        self.web_server = web_server or WebAnalyticsServer()

        # ── Alarm (global, always active) ────────────────────────────────────
        self.alarm = AlarmManager()

        # ── Pages (0 = Cockpit, 1 = Live Charts, 2 = Web Server, 3 = Settings)
        self.daily_page = DailyCockpitPage(self.screen)
        self.charts_page = ChartsPage(self.screen, self.history)
        self.pages = [
            self.daily_page,
            self.charts_page,
            WebServerPage(self.screen, self.web_server),
            SettingsPage(self.screen),
        ]
        self.current = max(0, min(start_page, len(self.pages) - 1))
        self._axis_x_active = False

        # ── Connection state for Page 0 ──────────────────────────────────────
        self._ever_connected = False
        self._boot_at = time.monotonic()

        # ── Fonts (matched to DailyCockpitPage) ──────────────────────────────
        sans = "segoeui,dejavusans,liberationsans,arial,sans-serif"
        mono = "consolas,dejavusansmono,liberationmono,monospace"
        self._font_ind      = pygame.font.SysFont(mono, 10, bold=True)
        self._font_batt     = pygame.font.SysFont(mono, 13, bold=True)
        self._font_hdr      = pygame.font.SysFont(sans, 13, bold=True)
        self._font_title    = pygame.font.SysFont(sans, 19, bold=True)
        self._font_sub      = pygame.font.SysFont(sans, 13, bold=False)
        self._font_hint     = pygame.font.SysFont(sans, 11, bold=False)
        self._font_pill_lbl = pygame.font.SysFont(sans, 10, bold=True)
        self._font_pill_val = pygame.font.SysFont(mono, 14, bold=True)
        self._font_badge    = pygame.font.SysFont(mono, 12, bold=True)

        # Pre-render static startup background & runtime mode state
        self._last_mock_mode = settings.enabled("mock_mode")
        self._mode_toast_until = 0.0
        self._mode_toast_mock = self._last_mock_mode
        self._conn_state = (get_lang(), self._last_mock_mode)
        self._conn_hdr_half_w = 54
        self._conn_bg = self._build_connecting_bg()

        # ── Joystick / gamepad init ──────────────────────────────────────────
        pygame.joystick.init()
        for i in range(pygame.joystick.get_count()):
            pygame.joystick.Joystick(i).init()

    # ── Navigation ───────────────────────────────────────────────────────────

    def _next_page(self):
        self.current = (self.current + 1) % len(self.pages)

    def _prev_page(self):
        self.current = (self.current - 1) % len(self.pages)

    def _showing_connecting(self) -> bool:
        return self.current == 0 and not self._ever_connected

    # ── Event handling ───────────────────────────────────────────────────────

    def _handle_events(self):
        page_next_key = getattr(config, "PAGE_NEXT_KEY", pygame.K_RIGHT)
        page_prev_key = getattr(config, "PAGE_PREV_KEY", pygame.K_LEFT)
        lang_key      = getattr(config, "LANG_KEY", pygame.K_l)
        mock_key      = getattr(config, "MOCK_KEY", pygame.K_m)
        lang_btn      = getattr(config, "LANG_BUTTON", 3)
        exit_key      = getattr(config, "EXIT_KEY", 97)  # pygame.K_a

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue

            # Give active page first chance to handle navigation/toggles (except splash on page 0)
            if not self._showing_connecting() and self.pages[self.current].handle_event(event):
                continue

            # ── Keyboard ─────────────────────────────────────────────────────
            if event.type == pygame.KEYDOWN:
                if event.key in (exit_key, pygame.K_ESCAPE):
                    self.running = False
                elif event.key == page_next_key:
                    self._next_page()
                elif event.key == page_prev_key:
                    self._prev_page()
                elif event.key == mock_key:
                    settings.toggle("mock_mode")
                elif event.key == lang_key:
                    settings.cycle_language()
                    pygame.display.set_caption(t("app.window_title"))

            # ── Joystick buttons ─────────────────────────────────────────────
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button == 0:
                    self.running = False
                elif event.button in (5, 16):   # R1 or D-pad Right button
                    self._next_page()
                elif event.button in (4, 15):   # L1 or D-pad Left button
                    self._prev_page()
                elif event.button == lang_btn:
                    settings.cycle_language()
                    pygame.display.set_caption(t("app.window_title"))

            # ── Joystick hat (D-pad) ─────────────────────────────────────────
            elif event.type == pygame.JOYHATMOTION:
                hat_x, _hat_y = event.value
                if hat_x == 1:
                    self._next_page()
                elif hat_x == -1:
                    self._prev_page()

            # ── Joystick left stick X-axis (page switch with hysteresis) ─────
            elif event.type == pygame.JOYAXISMOTION and event.axis == 0:
                if event.value > 0.65 and not self._axis_x_active:
                    self._axis_x_active = True
                    self._next_page()
                elif event.value < -0.65 and not self._axis_x_active:
                    self._axis_x_active = True
                    self._prev_page()
                elif -0.30 <= event.value <= 0.30:
                    self._axis_x_active = False

    # ── Page indicator (dots) ────────────────────────────────────────────────

    def _draw_page_indicator(self):
        """Draw sleek pill/dot indicators at the bottom-centre showing current page."""
        n = len(self.pages)
        if n <= 1:
            return

        y = config.SCREEN_HEIGHT - 13
        items_w = [18 if i == self.current else 6 for i in range(n)]
        gap = 8
        total_w = sum(items_w) + gap * (n - 1)
        x = (config.SCREEN_WIDTH - total_w) // 2

        for i, w in enumerate(items_w):
            col = SKY if i == self.current else BADGE_BD
            pygame.draw.rect(self.screen, col, (x, y - 3, w, 6), border_radius=3)
            x += w + gap

    # ── OEM Daily Startup / Connecting Screen ────────────────────────────────

    @staticmethod
    def _blit_center(dst, surf, cx: int, cy: int):
        dst.blit(surf, (cx - surf.get_width() // 2, cy - surf.get_height() // 2))

    def _build_connecting_bg(self):
        """Pre-render static elements of the startup screen matching DailyCockpitPage."""
        W, H = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
        bg = pygame.Surface((W, H))
        bg.fill(BG)

        # Ambient top sky-blue glow + soft center halo behind spinner ring
        bg.blit(_build_radial_glow((W, H), (W // 2, 55), 360, SKY, max_alpha=30), (0, 0))
        bg.blit(_build_radial_glow((W, H), self._CONN_RING_CENTER, 150, TEAL, max_alpha=20), (0, 0))

        # Top header bar (matches DailyCockpitPage layout)
        mode_str = t("conn.mode_mock") if settings.enabled("mock_mode") else t("conn.mode_usb")
        mode_col = AMBER_TXT if settings.enabled("mock_mode") else TXT_SUB
        bg.blit(self._font_batt.render(mode_str, True, mode_col), (24, 17))
        hdr_surf = self._font_hdr.render(t("app.header_title"), True, SKY)
        self._conn_hdr_half_w = hdr_surf.get_width() // 2
        self._blit_center(bg, hdr_surf, W // 2, 24)

        # Supersampled 360° circular ring track in center
        ss = 3
        r_mid = self._CONN_RING_R
        thick = self._CONN_RING_THICK
        dim = (r_mid + thick + 8) * 2
        hi = pygame.Surface((dim * ss, dim * ss), pygame.SRCALPHA)
        hi.fill((*BORDER, 0))
        c = (dim * ss) // 2
        pygame.draw.circle(
            hi,
            BORDER,
            (c, c),
            int((r_mid + thick / 2) * ss),
            width=int(thick * ss),
        )
        track = pygame.transform.smoothscale(hi, (dim, dim))
        cx, cy = self._CONN_RING_CENTER
        bg.blit(track, (cx - dim // 2, cy - dim // 2))

        # Inner subtle badge circle + crisp OBD-II / USB connector icon
        gfxdraw.filled_circle(bg, cx, cy, 45, CARD)
        gfxdraw.aacircle(bg, cx, cy, 45, BORDER)

        # Stylized trapezoidal OBD-II 16-pin connector silhouette
        trap = [
            (cx - 24, cy - 16),
            (cx + 24, cy - 16),
            (cx + 19, cy + 4),
            (cx - 19, cy + 4),
        ]
        gfxdraw.filled_polygon(bg, trap, BADGE_BG)
        gfxdraw.aapolygon(bg, trap, SKY)
        for row_y in (cy - 10, cy - 3):
            for col_i in range(4):
                px = cx - 12 + col_i * 8
                gfxdraw.filled_circle(bg, px, row_y, 1, TEAL)

        self._blit_center(bg, self._font_badge.render(t("conn.obd_badge"), True, TXT_SUB), cx, cy + 19)

        # Center Status Card
        card_rect = pygame.Rect((W - 432) // 2, 264, 432, 98)
        pygame.draw.rect(bg, CARD, card_rect, border_radius=10)
        pygame.draw.rect(bg, BORDER, card_rect, 1, border_radius=10)

        self._blit_center(
            bg,
            self._font_title.render(t("conn.title"), True, TXT_MAIN),
            W // 2,
            290,
        )
        self._blit_center(
            bg,
            self._font_sub.render(t("conn.subtitle"), True, TXT_SUB),
            W // 2,
            316,
        )

        # Progress bar inset well inside status card
        bar_well = pygame.Rect((W - 340) // 2, 338, 340, 8)
        pygame.draw.rect(bg, CARD_DARK, bar_well, border_radius=4)
        pygame.draw.rect(bg, BORDER, bar_well, 1, border_radius=4)

        # Bottom 3 Configuration / Status Pills
        raw_port = str(getattr(config, "OBD_PORT", "auto"))
        port_cfg = t("conn.port_auto") if raw_port.lower() == "auto" else raw_port.upper()
        baud_cfg = f"{getattr(config, 'OBD_BAUD', 38400)} bps"
        pills = (
            (t("conn.pill_port"), port_cfg),
            (t("conn.pill_baud"), baud_cfg),
            (t("conn.pill_status"), None),  # dynamic
        )
        pill_w = 136
        gap = 12
        total_w = pill_w * 3 + gap * 2
        start_x = (W - total_w) // 2
        self._conn_status_pill = None

        for i, (lbl, val) in enumerate(pills):
            r = pygame.Rect(start_x + i * (pill_w + gap), 374, pill_w, 56)
            pygame.draw.rect(bg, CARD, r, border_radius=8)
            pygame.draw.rect(bg, BORDER, r, 1, border_radius=8)
            bg.blit(self._font_pill_lbl.render(lbl, True, TXT_MUTED), (r.x + 14, r.y + 8))
            if val is not None:
                bg.blit(self._font_pill_val.render(val, True, TXT_MAIN), (r.x + 14, r.y + 28))
            else:
                self._conn_status_pill = r

        # Navigation hint so user knows they can reach Web Server & Settings offline
        self._blit_center(
            bg,
            self._font_hint.render(t("conn.hint_pages"), True, TXT_MUTED),
            W // 2,
            444,
        )

        return bg

    def _draw_connecting_screen(self, data: dict = None):
        """Draws the OEM Daily startup screen while waiting for OBD-II connection."""
        cur_state = (get_lang(), settings.enabled("mock_mode"))
        if cur_state != self._conn_state:
            self._conn_state = cur_state
            self._conn_bg = self._build_connecting_bg()

        W = config.SCREEN_WIDTH
        t_sec = pygame.time.get_ticks() / 1000.0
        cx, cy = self._CONN_RING_CENTER

        self.screen.blit(self._conn_bg, (0, 0))

        # 1. Top Bar: status dot next to header + R36S Battery on right
        is_connected = bool(data and data.get("connected", False))
        pulse_on = (int(t_sec * 2.5) % 2) == 0
        dot_col = GREEN_DOT if is_connected else (AMBER if pulse_on else BADGE_BD)
        dot_x = W // 2 - self._conn_hdr_half_w - 12
        gfxdraw.filled_circle(self.screen, dot_x, 24, 4, dot_col)
        gfxdraw.aacircle(self.screen, dot_x, 24, 4, dot_col)

        if data and settings.enabled("console_battery"):
            draw_phone_battery(
                self.screen,
                W - 24,
                24,
                data.get("console_battery_pct"),
                bool(data.get("console_battery_charging", False)),
                self._font_batt,
            )

        # 2. Dual smooth orbiting arcs around the central OBD-II ring
        base_deg = (t_sec * 150.0) % 360.0
        sweep = 88.0 + 28.0 * math.sin(t_sec * 2.6)
        _draw_thick_arc(
            self.screen, cx, cy,
            self._CONN_RING_R, self._CONN_RING_THICK,
            base_deg, sweep, SKY,
        )
        _draw_thick_arc(
            self.screen, cx, cy,
            self._CONN_RING_R, self._CONN_RING_THICK,
            (base_deg + 180.0) % 360.0, sweep * 0.65, TEAL,
        )

        # 3. Smooth sliding scanner pill inside the center card's progress bar
        track_x = (W - 336) // 2
        track_w = 336
        seg_w = 96
        pos = (math.sin(t_sec * 2.4) + 1.0) * 0.5
        seg_x = int(track_x + pos * (track_w - seg_w))
        pygame.draw.rect(self.screen, SKY, (seg_x, 339, seg_w, 6), border_radius=3)

        # 4. Dynamic "STATUS" bottom pill
        if self._conn_status_pill is not None:
            r = self._conn_status_pill
            dx, dy = r.x + 18, r.y + 36
            if is_connected:
                gfxdraw.filled_circle(self.screen, dx, dy, 4, GREEN_DOT)
                gfxdraw.aacircle(self.screen, dx, dy, 4, GREEN_DOT)
                st_surf = self._font_pill_val.render(t("conn.status_connected"), True, TEAL)
            else:
                gfxdraw.filled_circle(self.screen, dx, dy, 4, AMBER if pulse_on else BADGE_BD)
                gfxdraw.aacircle(self.screen, dx, dy, 4, AMBER if pulse_on else BADGE_BD)
                dots = "." * ((int(t_sec * 2.0) % 3) + 1)
                st_surf = self._font_pill_val.render(f"{t('conn.status_searching')}{dots}", True, AMBER_TXT)
            self.screen.blit(st_surf, (r.x + 28, r.y + 28))

    def _draw_mode_toast(self):
        """Draw temporary floating pill notification when switching Mock <-> Real mode."""
        is_mock = self._mode_toast_mock
        msg = t("mode.toast_mock") if is_mock else t("mode.toast_real")
        bd_col = AMBER if is_mock else SKY
        txt_col = AMBER_TXT if is_mock else SKY
        dot_col = AMBER if is_mock else GREEN_DOT

        lbl = self._font_badge.render(msg, True, txt_col)
        pw = lbl.get_width() + 40
        ph = 28
        pr = pygame.Rect((config.SCREEN_WIDTH - pw) // 2, 42, pw, ph)

        shadow = pygame.Surface((pw + 8, ph + 8), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 130), (0, 0, pw + 8, ph + 8), border_radius=16)
        self.screen.blit(shadow, (pr.x - 4, pr.y - 2))

        pygame.draw.rect(self.screen, (14, 21, 32), pr, border_radius=14)
        pygame.draw.rect(self.screen, bd_col, pr, 1, border_radius=14)
        gfxdraw.filled_circle(self.screen, pr.x + 15, pr.centery, 4, dot_col)
        gfxdraw.aacircle(self.screen, pr.x + 15, pr.centery, 4, dot_col)
        self.screen.blit(lbl, (pr.x + 26, pr.centery - lbl.get_height() // 2))

    # ── Main loop ────────────────────────────────────────────────────────────

    def run(self):
        try:
            while self.running:
                self._handle_events()

                now = time.monotonic()

                # Live mode switch synchronization (Mock <-> Real OBD-II)
                cur_mock = settings.enabled("mock_mode")
                switched = self.reader_manager.sync() if self.reader_manager is not None else False
                if switched or cur_mock != self._last_mock_mode:
                    self._last_mock_mode = cur_mock
                    self.history.clear()
                    self.derived.reset()
                    self.daily_page.reset_histories()
                    self._mode_toast_mock = cur_mock
                    self._mode_toast_until = now + 2.2
                    if cur_mock:
                        self._ever_connected = True
                    else:
                        self._ever_connected = False
                        self._boot_at = now - self._MIN_SPLASH_SECS

                data = self.store.snapshot()
                data.update(self.derived.update(data, now))
                self.history.record(data, now)
                if settings.enabled("console_battery"):
                    batt_pct, batt_chg = self.console_battery.read(now)
                    data["console_battery_pct"] = batt_pct
                    data["console_battery_charging"] = batt_chg
                self.alarm.update(data)

                if not self._ever_connected:
                    splash_done = (now - self._boot_at) >= self._MIN_SPLASH_SECS
                    if data.get("connected", False) and splash_done:
                        self._ever_connected = True

                self.screen.fill(config.COLORS["bg"])

                if self._showing_connecting():
                    self._draw_connecting_screen(data)
                else:
                    page = self.pages[self.current]
                    page.update(data)
                    page.draw()
                    page.draw_chrome(data)
                    page.draw_alarms(self.alarm)

                if now < self._mode_toast_until:
                    self._draw_mode_toast()

                self._draw_page_indicator()

                pygame.display.flip()
                self.clock.tick(config.FPS)
        finally:
            self.web_server.stop()
            pygame.quit()
