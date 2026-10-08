import math
import time
import pygame
import config
from dashboard.widgets.base import Widget


class DoomFaceWidget(Widget):
    """Nicho central com o rosto do Doomguy que reage à velocidade e temperatura."""

    def __init__(self, surface, rect):
        super().__init__(surface, rect)
        self.speed = 0
        self.temp  = 0
        self.c_red = (220, 20, 20)

        # Carrega as expressões do Doomguy
        self.faces = {}
        face_files = {
            "happy":   "happy_no_bg.png",
            "scary":   "scary.png",
            "neutral": "neutral.png",
            "burning": "burning.png"
        }
        
        # Tamanho do sprite dentro do retângulo
        sprite_w = max(10, rect.width - 20)
        sprite_h = max(10, rect.height - 24)

        for key, filename in face_files.items():
            for path in [f"assets/faces/{filename}", f"assets/face/{filename}"]:
                try:
                    face = pygame.image.load(path).convert_alpha()
                    self.faces[key] = pygame.transform.scale(face, (sprite_w, sprite_h))
                    break
                except Exception:
                    pass

        self.face_happy   = self.faces.get("happy")
        self.face_scary   = self.faces.get("scary")
        self.face_neutral = self.faces.get("neutral")
        self.face_burning = self.faces.get("burning")

        # Fallback de fonte caso as imagens não existam
        font_path = "fonts/DooM.ttf"
        try:
            self._font_fallback = pygame.font.Font(font_path, 48)
        except Exception:
            self._font_fallback = pygame.font.SysFont("impact", 72)

        # Superfície de alerta vermelho transparente pré-alocada
        inner_w = max(10, rect.width - 4)
        inner_h = max(10, rect.height - 4)
        self._alert_overlay = pygame.Surface((inner_w, inner_h), pygame.SRCALPHA)
        self._alert_overlay.fill((230, 20, 20, 255))

    def update(self, data: dict):
        self.speed = int(data.get("speed", 0))
        self.temp  = int(data.get("water_temp", 0))

    def _draw_recessed_box(self):
        """Moldura rebaixada 3D metálica estilo Doom."""
        r = self.rect
        # Fundo carvão rebaixado
        pygame.draw.rect(self.surface, (18, 18, 22), r)
        # Borda externa
        pygame.draw.rect(self.surface, (75, 75, 80), r, 2)
        # Chanfro com sombra superior/esquerda e brilho inferior/direita
        pygame.draw.line(self.surface, (30, 30, 35), (r.left, r.top), (r.right, r.top), 1)
        pygame.draw.line(self.surface, (30, 30, 35), (r.left, r.top), (r.left, r.bottom), 1)
        pygame.draw.line(self.surface, (115, 115, 120), (r.left, r.bottom - 1), (r.right, r.bottom - 1), 1)
        pygame.draw.line(self.surface, (115, 115, 120), (r.right - 1, r.top), (r.right - 1, r.bottom), 1)

    def draw(self):
        # 1. Moldura do nicho
        self._draw_recessed_box()

        # 2. Limiares configurados
        temp_threshold = getattr(config, "RETRO_TEMP_THRESHOLD", 100)
        speed_scary    = getattr(config, "RETRO_SPEED_SCARY", 100)
        speed_happy    = getattr(config, "RETRO_SPEED_HAPPY", 80)

        # 3. Lógica de seleção do rosto
        if self.temp >= temp_threshold and self.face_burning:
            active_face = self.face_burning
        elif self.speed > speed_scary:
            active_face = self.face_scary or self.face_happy
        elif self.speed > speed_happy:
            active_face = self.face_happy
        else:
            active_face = self.face_neutral or self.face_happy

        if active_face:
            f_rect = active_face.get_rect(center=self.rect.center)
            self.surface.blit(active_face, f_rect)
        else:
            # Fallback em texto
            if self.temp >= temp_threshold:
                txt, col = "X_X", self.c_red
            elif self.speed > speed_scary:
                txt, col = "o_O", (240, 200, 20)
            elif self.speed > speed_happy:
                txt, col = "^_^", (200, 150, 100)
            else:
                txt, col = "-_-", (200, 150, 100)

            surf = self._font_fallback.render(txt, True, col)
            self.surface.blit(surf, (self.rect.centerx - surf.get_width() // 2,
                                     self.rect.centery - surf.get_height() // 2))

        # 4. Alerta visual: pisca vermelho transparente se a temperatura ultrapassar o limite
        temp_alert = getattr(config, "RETRO_TEMP_ALERT", 95)
        if self.temp >= temp_alert:
            pulse = max(0.0, math.sin(time.time() * 9))
            if pulse > 0:
                alpha = int(pulse * 130)  # Tom vermelho translúcido
                self._alert_overlay.set_alpha(alpha)
                self.surface.blit(self._alert_overlay, (self.rect.x + 2, self.rect.y + 2))

