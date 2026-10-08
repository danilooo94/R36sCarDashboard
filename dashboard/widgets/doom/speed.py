import pygame
import config
from dashboard.widgets.base import Widget


class DoomSpeedWidget(Widget):
    """Mostrador de velocidade em estilo Doom com números grandes e sombra."""

    def __init__(self, surface, rect):
        super().__init__(surface, rect)
        self.speed = 0
        self.target_speed = 0.0
        self.current_speed = 0.0
        self.c_red = (220, 20, 20)
        
        font_path = "fonts/DooM.ttf"
        try:
            self._font_kmh = pygame.font.Font(font_path, 26)
            self._font_num = pygame.font.Font(font_path, 75)
        except Exception:
            self._font_kmh = pygame.font.SysFont("impact", 36)
            self._font_num = pygame.font.SysFont("impact", 130)

    def update(self, data: dict):
        self.target_speed = float(data.get("speed", 0))
        self.speed = int(self.target_speed)

    def draw(self):
        # Interpolação suave a 60 FPS
        self.current_speed += (self.target_speed - self.current_speed) * 0.28

        x, y = self.rect.x, self.rect.y
        
        # Rótulo estático KM/H em branco/neutro
        c_label = (230, 230, 235)
        lbl_kmh = self._font_kmh.render("KM/H", True, c_label)
        self.surface.blit(lbl_kmh, (x + 20, y))

        # Valor numérico da velocidade com sombra preta
        val_str = f"{int(round(max(0.0, self.current_speed)))}"
        val_shadow = self._font_num.render(val_str, True, (0, 0, 0))
        val_spd    = self._font_num.render(val_str, True, self.c_red)

        self.surface.blit(val_shadow, (x + 5, y + 45))
        self.surface.blit(val_spd, (x, y + 40))

