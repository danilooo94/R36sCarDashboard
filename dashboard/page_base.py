import pygame
import config


class Page:
    """Base class for dashboard pages.

    Each page owns a list of widgets and knows how to draw
    chrome (dividers, status indicators) and alarm overlays.
    """

    name = "Page"  # human-readable, shown in page indicator

    def __init__(self, screen):
        self.screen = screen
        self.widgets = []
        self._font_status = pygame.font.SysFont("monospace", 11)

    # ── Widget lifecycle ─────────────────────────────────────────────────────

    def update(self, data: dict):
        """Pull new sensor values into every widget."""
        for w in self.widgets:
            w.update(data)

    def draw(self):
        """Render every widget onto the screen."""
        for w in self.widgets:
            w.draw()

    # ── Page-specific overlays (override in subclasses) ──────────────────────

    def draw_chrome(self, data: dict):
        """Draw dividers, connection indicators, etc."""
        pass

    def draw_alarms(self, alarm):
        """Draw blinking alarm borders when sensors exceed thresholds."""
        pass

    # ── Shared helper: OBD status dot ────────────────────────────────────────

    def _draw_obd_dot(self, connected: bool, port: str = ""):
        """Small coloured dot + label at the top-right corner."""
        W = config.SCREEN_WIDTH
        dot_color = config.COLORS["primary"] if connected else config.COLORS["danger"]
        dot_label = "OBD" if connected else "—"
        lbl = self._font_status.render(dot_label, True, dot_color)
        pygame.draw.circle(self.screen, dot_color, (W - 8, 8), 4)
        self.screen.blit(lbl, (W - lbl.get_width() - 16, 2))
        if port:
            port_short = port.replace("/dev/", "")
            port_lbl = self._font_status.render(port_short, True, config.COLORS["muted"])
            self.screen.blit(port_lbl, (W - port_lbl.get_width() - 4, 14))

