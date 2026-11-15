import math
import time

import pygame
from pygame import gfxdraw

import config
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
from dashboard.telemetry       import DerivedTelemetry


class MultiPageApp:
    """Unified application loop that manages dashboard pages and the OEM startup screen.

    Pages can be cycled at runtime using the left/right arrow keys
    (or D-pad on the R36S).  The AlarmManager runs globally so beeps
    and blink state are maintained regardless of which page is visible.
    """

    _CONN_RING_CENTER = (320, 182)
    _CONN_RING_R      = 68
    _CONN_RING_THICK  = 12
    _MIN_SPLASH_SECS  = 1.4

    def __init__(self, store, start_page=0):
        pygame.init()
        flags = pygame.FULLSCREEN if config.FULLSCREEN else 0
        self.screen = pygame.display.set_mode(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT), flags)
        pygame.display.set_caption("Daily Cockpit — OBD2")
        self.clock   = pygame.time.Clock()
        self.store   = store
        self.running = True

        # ── Telemetria derivada & bateria do console ─────────────────────────
        self.derived = DerivedTelemetry()
        self.console_battery = ConsoleBatteryReader()

        # ── Alarm (global, always active) ────────────────────────────────────
        self.alarm = AlarmManager()

        # ── Pages ────────────────────────────────────────────────────────────
        self.pages = [
            DailyCockpitPage(self.screen),
        ]
        self.current = max(0, min(start_page, len(self.pages) - 1))

        # ── State Machine ────────────────────────────────────────────────────
        # "CONNECTING" shows the initial loading screen until OBD connects.
        self.state = "CONNECTING"
        self._boot_at = time.monotonic()

        # ── Fonts (matched to DailyCockpitPage) ──────────────────────────────
        sans = "segoeui,dejavusans,liberationsans,arial,sans-serif"
        mono = "consolas,dejavusansmono,liberationmono,monospace"
        self._font_ind      = pygame.font.SysFont(mono, 10, bold=True)
        self._font_batt     = pygame.font.SysFont(mono, 13, bold=True)
        self._font_hdr      = pygame.font.SysFont(sans, 13, bold=True)
        self._font_title    = pygame.font.SysFont(sans, 19, bold=True)
        self._font_sub      = pygame.font.SysFont(sans, 13, bold=False)
        self._font_pill_lbl = pygame.font.SysFont(sans, 10, bold=True)
        self._font_pill_val = pygame.font.SysFont(mono, 14, bold=True)
        self._font_badge    = pygame.font.SysFont(mono, 12, bold=True)

        # Pre-render static startup background
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

    # ── Event handling ───────────────────────────────────────────────────────

    def _handle_events(self):
        page_next_key = getattr(config, "PAGE_NEXT_KEY", pygame.K_RIGHT)
        page_prev_key = getattr(config, "PAGE_PREV_KEY", pygame.K_LEFT)
        exit_key      = getattr(config, "EXIT_KEY", 97)  # pygame.K_a

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            # ── Keyboard ─────────────────────────────────────────────────────
            elif event.type == pygame.KEYDOWN:
                if event.key == exit_key:
                    self.running = False
                elif event.key == page_next_key:
                    self._next_page()
                elif event.key == page_prev_key:
                    self._prev_page()

            # ── Joystick buttons ─────────────────────────────────────────────
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button == 0:
                    self.running = False
                elif event.button == 5:
                    self._next_page()
                elif event.button == 4:
                    self._prev_page()

            # ── Joystick hat (D-pad) ─────────────────────────────────────────
            elif event.type == pygame.JOYHATMOTION:
                hat_x, _hat_y = event.value
                if hat_x == 1:
                    self._next_page()
                elif hat_x == -1:
                    self._prev_page()

    # ── Page indicator (dots) ────────────────────────────────────────────────

    def _draw_page_indicator(self):
        """Draw small dots at the bottom-centre showing current page."""
        n = len(self.pages)
        if n <= 1:
            return

        dot_r   = 4
        gap     = 14
        total   = n * dot_r * 2 + (n - 1) * (gap - dot_r * 2)
        start_x = (config.SCREEN_WIDTH - total) // 2 + dot_r
        y       = config.SCREEN_HEIGHT - 12

        for i in range(n):
            cx = start_x + i * gap
            if i == self.current:
                pygame.draw.circle(self.screen, config.COLORS["primary"], (cx, y), dot_r)
            else:
                pygame.draw.circle(self.screen, config.COLORS["muted"], (cx, y), dot_r, 1)

        page = self.pages[self.current]
        lbl = self._font_ind.render(page.name, True, config.COLORS["muted"])
        self.screen.blit(lbl, ((config.SCREEN_WIDTH - lbl.get_width()) // 2,
                               y - dot_r - lbl.get_height() - 2))

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
        bg.blit(self._font_batt.render("USB SERIAL", True, TXT_SUB), (24, 17))
        self._blit_center(bg, self._font_hdr.render("DAILY COCKPIT", True, SKY), W // 2, 24)

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
        gfxdraw.filled_circle(bg, cx, cy, 46, CARD)
        gfxdraw.aacircle(bg, cx, cy, 46, BORDER)

        # Stylized trapezoidal OBD-II 16-pin connector silhouette
        trap = [
            (cx - 24, cy - 16),
            (cx + 24, cy - 16),
            (cx + 19, cy + 4),
            (cx - 19, cy + 4),
        ]
        gfxdraw.filled_polygon(bg, trap, BADGE_BG)
        gfxdraw.aapolygon(bg, trap, SKY)
        # Two rows of 4 pin dots inside the OBD connector
        for row_y in (cy - 10, cy - 3):
            for col_i in range(4):
                px = cx - 12 + col_i * 8
                gfxdraw.filled_circle(bg, px, row_y, 1, TEAL)

        self._blit_center(bg, self._font_badge.render("OBD-II", True, TXT_SUB), cx, cy + 20)

        # Center Status Card
        card_rect = pygame.Rect((W - 432) // 2, 276, 432, 102)
        pygame.draw.rect(bg, CARD, card_rect, border_radius=10)
        pygame.draw.rect(bg, BORDER, card_rect, 1, border_radius=10)

        self._blit_center(
            bg,
            self._font_title.render("Conectando à interface OBD-II", True, TXT_MAIN),
            W // 2,
            304,
        )
        self._blit_center(
            bg,
            self._font_sub.render("Conecte o adaptador USB ELM327 e ligue a ignição", True, TXT_SUB),
            W // 2,
            330,
        )

        # Progress bar inset well inside status card
        bar_well = pygame.Rect((W - 340) // 2, 352, 340, 8)
        pygame.draw.rect(bg, CARD_DARK, bar_well, border_radius=4)
        pygame.draw.rect(bg, BORDER, bar_well, 1, border_radius=4)

        # Bottom 3 Configuration / Status Pills
        port_cfg = str(getattr(config, "OBD_PORT", "auto")).upper()
        baud_cfg = f"{getattr(config, 'OBD_BAUD', 38400)} bps"
        pills = (
            ("PORTA USB", port_cfg),
            ("VELOCIDADE", baud_cfg),
            ("STATUS", None),  # dynamic
        )
        pill_w = 136
        gap = 12
        total_w = pill_w * 3 + gap * 2
        start_x = (W - total_w) // 2
        self._conn_status_pill = None

        for i, (lbl, val) in enumerate(pills):
            r = pygame.Rect(start_x + i * (pill_w + gap), 396, pill_w, 62)
            pygame.draw.rect(bg, CARD, r, border_radius=8)
            pygame.draw.rect(bg, BORDER, r, 1, border_radius=8)
            bg.blit(self._font_pill_lbl.render(lbl, True, TXT_MUTED), (r.x + 14, r.y + 10))
            if val is not None:
                bg.blit(self._font_pill_val.render(val, True, TXT_MAIN), (r.x + 14, r.y + 32))
            else:
                self._conn_status_pill = r

        return bg

    def _draw_connecting_screen(self, data: dict = None):
        """Draws the OEM Daily startup screen while waiting for OBD-II connection."""
        W = config.SCREEN_WIDTH
        t = pygame.time.get_ticks() / 1000.0
        cx, cy = self._CONN_RING_CENTER

        self.screen.blit(self._conn_bg, (0, 0))

        # 1. Top Bar: status dot next to DAILY COCKPIT + R36S Battery on right
        is_connected = bool(data and data.get("connected", False))
        pulse_on = (int(t * 2.5) % 2) == 0
        dot_col = GREEN_DOT if is_connected else (AMBER if pulse_on else BADGE_BD)
        gfxdraw.filled_circle(self.screen, W // 2 - 66, 24, 4, dot_col)
        gfxdraw.aacircle(self.screen, W // 2 - 66, 24, 4, dot_col)

        if data and getattr(config, "SHOW_CONSOLE_BATTERY", True):
            draw_phone_battery(
                self.screen,
                W - 24,
                24,
                data.get("console_battery_pct"),
                bool(data.get("console_battery_charging", False)),
                self._font_batt,
            )

        # 2. Dual smooth orbiting arcs around the central OBD-II ring
        base_deg = (t * 150.0) % 360.0
        sweep = 88.0 + 28.0 * math.sin(t * 2.6)
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
        pos = (math.sin(t * 2.4) + 1.0) * 0.5  # smooth ease-in-out 0..1
        seg_x = int(track_x + pos * (track_w - seg_w))
        pygame.draw.rect(self.screen, SKY, (seg_x, 353, seg_w, 6), border_radius=3)

        # 4. Dynamic "STATUS" bottom pill
        if self._conn_status_pill is not None:
            r = self._conn_status_pill
            dx, dy = r.x + 18, r.y + 40
            if is_connected:
                gfxdraw.filled_circle(self.screen, dx, dy, 4, GREEN_DOT)
                gfxdraw.aacircle(self.screen, dx, dy, 4, GREEN_DOT)
                st_surf = self._font_pill_val.render("CONECTADO", True, TEAL)
            else:
                gfxdraw.filled_circle(self.screen, dx, dy, 4, AMBER if pulse_on else BADGE_BD)
                gfxdraw.aacircle(self.screen, dx, dy, 4, AMBER if pulse_on else BADGE_BD)
                dots = "." * ((int(t * 2.0) % 3) + 1)
                st_surf = self._font_pill_val.render(f"BUSCANDO{dots}", True, AMBER_TXT)
            self.screen.blit(st_surf, (r.x + 28, r.y + 32))

    # ── Main loop ────────────────────────────────────────────────────────────

    def run(self):
        try:
            while self.running:
                self._handle_events()

                now = time.monotonic()
                data = self.store.snapshot()
                data.update(self.derived.update(data, now))
                if getattr(config, "SHOW_CONSOLE_BATTERY", True):
                    batt_pct, batt_chg = self.console_battery.read(now)
                    data["console_battery_pct"] = batt_pct
                    data["console_battery_charging"] = batt_chg
                self.alarm.update(data)

                self.screen.fill(config.COLORS["bg"])

                if self.state == "CONNECTING":
                    splash_done = (now - self._boot_at) >= self._MIN_SPLASH_SECS
                    if data.get("connected", False) and splash_done:
                        self.state = "DASHBOARD"
                    else:
                        self._draw_connecting_screen(data)

                if self.state == "DASHBOARD":
                    page = self.pages[self.current]
                    page.update(data)
                    page.draw()
                    page.draw_chrome(data)
                    page.draw_alarms(self.alarm)

                    self._draw_page_indicator()

                pygame.display.flip()
                self.clock.tick(config.FPS)
        finally:
            pygame.quit()
