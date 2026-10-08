import pygame
import config
from dashboard.page_base            import Page
from dashboard.widgets.speed        import SpeedDisplay
from dashboard.widgets.temp_graph   import TempGraph
from dashboard.widgets.battery      import BatteryWidget

_SEP_Y = 340  # y position of the horizontal divider


class HudPage(Page):
    """Main HUD: speedometer arc, temperature history graph, battery bar."""

    name = "HUD"

    def __init__(self, screen):
        super().__init__(screen)
        W = config.SCREEN_WIDTH
        self.widgets = [
            SpeedDisplay(screen,  pygame.Rect(0,   0,   W,       _SEP_Y)),
            TempGraph(screen,     pygame.Rect(20,  370, 275,     100)),
            BatteryWidget(screen, pygame.Rect(345, 365, W - 365, 110)),
        ]

    # ── Chrome ───────────────────────────────────────────────────────────────

    def draw_chrome(self, data: dict):
        W = config.SCREEN_WIDTH
        # Separator line
        pygame.draw.line(self.screen, config.COLORS["divider"],
                         (20, _SEP_Y), (W - 20, _SEP_Y), 1)
        # OBD status dot
        connected = data.get("connected", False)
        self._draw_obd_dot(connected)

