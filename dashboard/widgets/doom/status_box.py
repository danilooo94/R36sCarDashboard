import pygame
import config
from dashboard.widgets.base import Widget


class DoomStatusBoxWidget(Widget):
    """Caixas de status rebaixadas para temperatura do motor e bateria, com slot para ícones."""

    def __init__(self, surface, rect):
        super().__init__(surface, rect)
        self.temp = 0
        self.volt = 0.0
        self._font_small = pygame.font.SysFont("monospace", 15, bold=True)
        
        self.c_red    = (220, 20, 20)
        self.c_yellow = (240, 200, 20)
        self.c_green  = (40, 220, 80)

    def update(self, data: dict):
        self.temp = int(data.get("water_temp", 0))
        self.volt = float(data.get("voltage", 0.0))

    def _color_for_temp(self) -> tuple:
        """Determina a cor do valor de temperatura baseado nos thresholds."""
        t_warn   = getattr(config, "TEMP_COLOR_WARN", 95.0)
        t_danger = getattr(config, "TEMP_COLOR_DANGER", 105.0)
        if self.temp >= t_danger:
            return self.c_red
        if self.temp >= t_warn:
            return self.c_yellow
        return self.c_green

    def _color_for_volt(self) -> tuple:
        """Determina a cor do valor de voltagem baseado nos thresholds."""
        v_low_dang  = getattr(config, "VOLT_COLOR_LOW_DANGER", 11.8)
        v_low_warn  = getattr(config, "VOLT_COLOR_LOW_WARN", 13.0)
        v_high_warn = getattr(config, "VOLT_COLOR_HIGH_WARN", 14.8)

        if self.volt < v_low_dang or self.volt > v_high_warn:
            return self.c_red
        if self.volt < v_low_warn:
            return self.c_yellow
        return self.c_green

    def _draw_recessed_box(self, r):
        """Moldura rebaixada metálica estilo Doom."""
        pygame.draw.rect(self.surface, (18, 18, 22), r)
        pygame.draw.rect(self.surface, (75, 75, 80), r, 2)
        pygame.draw.line(self.surface, (30, 30, 35), (r.left, r.top), (r.right, r.top), 1)
        pygame.draw.line(self.surface, (30, 30, 35), (r.left, r.top), (r.left, r.bottom), 1)
        pygame.draw.line(self.surface, (115, 115, 120), (r.left, r.bottom - 1), (r.right, r.bottom - 1), 1)
        pygame.draw.line(self.surface, (115, 115, 120), (r.right - 1, r.top), (r.right - 1, r.bottom), 1)

    def draw(self):
        x, y, w = self.rect.x, self.rect.y, self.rect.width
        box_h = 34
        gap   = 10

        temp_box = pygame.Rect(x, y, w, box_h)
        volt_box = pygame.Rect(x, y + box_h + gap, w, box_h)

        # 1. Caixas rebaixadas
        self._draw_recessed_box(temp_box)
        self._draw_recessed_box(volt_box)

        # 2. Slots reservados para ícones (26x26 à esquerda)
        for box in (temp_box, volt_box):
            slot = pygame.Rect(box.x + 4, box.y + 4, 26, 26)
            pygame.draw.rect(self.surface, (26, 26, 30), slot)
            pygame.draw.rect(self.surface, (40, 40, 48), slot, 1)

        # 3. Textos após os ícones (rótulo neutro + apenas o valor mutável com cor)
        c_label = (220, 225, 230)

        # Temperatura (cor dinâmica baseada nos thresholds)
        lbl_temp = self._font_small.render("motor temp: ", True, c_label)
        val_temp = self._font_small.render(f"{self.temp:02d}C", True, self._color_for_temp())
        start_x = temp_box.x + 36
        self.surface.blit(lbl_temp, (start_x, temp_box.y + 8))
        self.surface.blit(val_temp, (start_x + lbl_temp.get_width(), temp_box.y + 8))

        # Bateria (cor dinâmica baseada nos thresholds)
        lbl_volt = self._font_small.render("bateria: ", True, c_label)
        val_volt = self._font_small.render(f"{self.volt:.1f}V", True, self._color_for_volt())
        start_x = volt_box.x + 36
        self.surface.blit(lbl_volt, (start_x, volt_box.y + 8))
        self.surface.blit(val_volt, (start_x + lbl_volt.get_width(), volt_box.y + 8))

