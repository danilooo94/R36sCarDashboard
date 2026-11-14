import pygame
import config
from dashboard.page_base                import Page
from dashboard.widgets.temp_gauge       import TempGauge
from dashboard.widgets.volt_gauge       import VoltGauge
from dashboard.widgets.console_battery  import ConsoleBatteryWidget

_DIVIDER_Y = 310  # split between temperature gauges and battery section


def _sensor_rects(W):
    """Bounding rects for each sensor zone — used for alarm border drawing."""
    half   = W // 2
    volt_h = config.SCREEN_HEIGHT - _DIVIDER_Y - 10
    return {
        "oil_temp":   pygame.Rect(0,    0,               half, _DIVIDER_Y),
        "water_temp": pygame.Rect(half, 0,               half, _DIVIDER_Y),
        "voltage":    pygame.Rect(0,    _DIVIDER_Y + 10, half, volt_h),
    }


class ExtrasPage(Page):
    """Extras: oil/coolant temperature gauges, voltage gauge, console battery."""

    name = "EXTRAS"

    def __init__(self, screen):
        super().__init__(screen)
        W      = config.SCREEN_WIDTH
        half   = W // 2
        volt_h = config.SCREEN_HEIGHT - _DIVIDER_Y - 10

        self.widgets = [
            TempGauge(screen, pygame.Rect(0,    0,               half, _DIVIDER_Y),
                      "OLEO",          "oil_temp"),
            TempGauge(screen, pygame.Rect(half, 0,               half, _DIVIDER_Y),
                      "ARREFECIMENTO", "water_temp"),
            VoltGauge(screen, pygame.Rect(0,    _DIVIDER_Y + 10, half, volt_h)),
            ConsoleBatteryWidget(screen, pygame.Rect(half, _DIVIDER_Y + 10, half, volt_h)),
        ]

    # ── Chrome ───────────────────────────────────────────────────────────────

    def draw_chrome(self, data: dict):
        W = config.SCREEN_WIDTH
        # Divider lines
        pygame.draw.line(self.screen, config.COLORS["divider"],
                         (20, _DIVIDER_Y), (W - 20, _DIVIDER_Y), 1)
        pygame.draw.line(self.screen, config.COLORS["divider"],
                         (W // 2, 20), (W // 2, _DIVIDER_Y - 20), 1)
        pygame.draw.line(self.screen, config.COLORS["divider"],
                         (W // 2, _DIVIDER_Y + 20), (W // 2, config.SCREEN_HEIGHT - 10), 1)
        # OBD status dot + port name
        connected = data.get("connected", False)
        port = data.get("obd_port", "")
        self._draw_obd_dot(connected, port)

    # ── Alarm borders ────────────────────────────────────────────────────────

    def draw_alarms(self, alarm):
        """Draw blinking colored borders on widgets in alarm state."""
        if not alarm.blink_on:
            return

        W = config.SCREEN_WIDTH
        rects = _sensor_rects(W)

        for key, rect in rects.items():
            lvl = alarm.level(key)
            if lvl == 0:
                continue
            color = config.COLORS["danger"] if lvl == 2 else config.COLORS["warning"]
            pygame.draw.rect(self.screen, color, rect, 2)

        # Full-screen border when any sensor is in danger
        if alarm.overall() == 2:
            pygame.draw.rect(self.screen, config.COLORS["danger"],
                             pygame.Rect(0, 0, W, config.SCREEN_HEIGHT), 2)

