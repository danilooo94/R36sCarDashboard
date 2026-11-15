import math
import time

import pygame
import config
from dashboard.alarm       import AlarmManager
from dashboard.page_daily  import DailyCockpitPage
from dashboard.telemetry   import DerivedTelemetry


class MultiPageApp:
    """Unified application loop that manages multiple dashboard pages.

    Pages can be cycled at runtime using the left/right arrow keys
    (or D-pad on the R36S).  The AlarmManager runs globally so beeps
    and blink state are maintained regardless of which page is visible.
    """

    def __init__(self, store, start_page=0):
        pygame.init()
        flags = pygame.FULLSCREEN if config.FULLSCREEN else 0
        self.screen = pygame.display.set_mode(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT), flags)
        pygame.display.set_caption("Car HUD")
        self.clock   = pygame.time.Clock()
        self.store   = store
        self.running = True

        # ── Telemetria derivada (marchas, 0-100, consumo, boost) ─────────────
        self.derived = DerivedTelemetry()

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

        # ── Fonts ────────────────────────────────────────────────────────────
        self._font_ind = pygame.font.SysFont("monospace", 10)
        self._font_title = pygame.font.SysFont("monospace", 32, bold=True)
        self._font_subtitle = pygame.font.SysFont("monospace", 16)

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
                # Button 0 = A on most gamepads → exit
                if event.button == 0:
                    self.running = False
                # Button 5 = R1 / right bumper → next page
                elif event.button == 5:
                    self._next_page()
                # Button 4 = L1 / left bumper → prev page
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
        n      = len(self.pages)
        if n <= 1:
            return

        dot_r  = 4
        gap    = 14
        total  = n * dot_r * 2 + (n - 1) * (gap - dot_r * 2)
        start_x = (config.SCREEN_WIDTH - total) // 2 + dot_r
        y       = config.SCREEN_HEIGHT - 12

        for i in range(n):
            cx = start_x + i * gap
            if i == self.current:
                pygame.draw.circle(self.screen, config.COLORS["primary"], (cx, y), dot_r)
            else:
                pygame.draw.circle(self.screen, config.COLORS["muted"],   (cx, y), dot_r, 1)

        # Page name label
        page = self.pages[self.current]
        lbl = self._font_ind.render(page.name, True, config.COLORS["muted"])
        self.screen.blit(lbl, ((config.SCREEN_WIDTH - lbl.get_width()) // 2,
                               y - dot_r - lbl.get_height() - 2))

    # ── Initial Connection Screen ────────────────────────────────────────────

    def _draw_connecting_screen(self):
        """Draws the initial screen while waiting for OBD-II connection."""
        title = self._font_title.render("CAR DATA READER", True, config.COLORS["text"])
        subtitle = self._font_subtitle.render("Conectando à interface OBD-II...", True, config.COLORS["muted"])
        
        W = config.SCREEN_WIDTH
        H = config.SCREEN_HEIGHT

        self._draw_engine_spinner((W // 2, H // 2 - 105))
        self.screen.blit(title, ((W - title.get_width()) // 2, H // 2 - 45))
        self.screen.blit(subtitle, ((W - subtitle.get_width()) // 2, H // 2 + 5))

        ticks = pygame.time.get_ticks()
        dot_count = (ticks // 500) % 4
        dots = "." * dot_count
        loading = self._font_subtitle.render(f"Aguarde{dots}", True, config.COLORS["primary"])

        loading_w = self._font_subtitle.size("Aguarde...")[0]
        self.screen.blit(loading, ((W - loading_w) // 2, H // 2 + 45))

    def _draw_engine_spinner(self, center):
        """Draw a small engine outline with a rotating loading arc inside."""
        cx, cy = center
        primary = config.COLORS["primary"]
        muted = config.COLORS["muted"]
        body = pygame.Rect(cx - 33, cy - 24, 66, 48)

        pygame.draw.rect(self.screen, muted, body, 3, border_radius=5)
        pygame.draw.rect(self.screen, muted, (cx - 43, cy - 12, 10, 24), 3)
        pygame.draw.rect(self.screen, muted, (cx + 33, cy - 16, 10, 12), 3)
        pygame.draw.line(self.screen, muted, (cx - 18, cy - 24), (cx - 18, cy - 34), 3)
        pygame.draw.line(self.screen, muted, (cx + 8, cy - 24), (cx + 8, cy - 34), 3)
        pygame.draw.line(self.screen, muted, (cx - 18, cy - 34), (cx + 8, cy - 34), 3)

        spinner = pygame.Rect(cx - 18, cy - 18, 36, 36)
        # pygame.draw.arc(surface, color, rect, start_angle, stop_angle, width=1)
        pygame.draw.arc(self.screen, config.COLORS["arc_bg"], spinner, 0, math.tau, 4)
        angle = (pygame.time.get_ticks() / 1000) * math.tau
        pygame.draw.arc(self.screen, primary, spinner, angle, angle + math.pi * 1.35, 4)

    # ── Main loop ────────────────────────────────────────────────────────────

    def run(self):
        try:
            while self.running:
                self._handle_events()

                data = self.store.snapshot()
                data.update(self.derived.update(data, time.monotonic()))
                self.alarm.update(data)

                self.screen.fill(config.COLORS["bg"])

                if self.state == "CONNECTING":
                    # Transition to dashboard when first connected
                    if data.get("connected", False):
                        self.state = "DASHBOARD"
                    else:
                        self._draw_connecting_screen()

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

