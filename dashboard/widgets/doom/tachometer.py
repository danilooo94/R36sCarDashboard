import math
import pygame
import config
from dashboard.widgets.base import Widget


class DoomTachometerWidget(Widget):
    """Tacômetro circular estilo Doom com agulha desenhada manualmente e indicador digital."""

    def __init__(self, surface, rect):
        super().__init__(surface, rect)
        self.rpm = 0
        self.target_rpm = 0.0
        self.current_rpm = 0.0
        self.c_red = (220, 20, 20)

        # Fonte para o valor numérico de RPM
        font_path = "fonts/DooM.ttf"
        try:
            self._font_rpm = pygame.font.Font(font_path, 18)
        except Exception:
            self._font_rpm = pygame.font.SysFont("impact", 18)

        # Carrega o mostrador de fundo
        self.tacho_img = None
        try:
            raw_tacho = pygame.image.load("assets/tachometer_bg.png").convert_alpha()
            cx, cy = 684, 351
            crop_sz = 440
            crop_rect = pygame.Rect(cx - crop_sz // 2, cy - crop_sz // 2, crop_sz, crop_sz)

            tacho_crop = raw_tacho.subsurface(crop_rect).copy()
            target_sz = min(rect.width, rect.height)
            self.tacho_img = pygame.transform.scale(tacho_crop, (target_sz, target_sz))
        except Exception as e:
            import app_log
            app_log.warning(f"[HUD] Erro ao carregar fundo do tacômetro: {e}")

    def update(self, data: dict):
        self.target_rpm = float(data.get("rpm", 0))
        self.rpm = int(self.target_rpm)

    def _draw_needle(self, cx, cy, angle_deg):
        """Desenha uma agulha afilada em pixel/vetor com efeito 3D e contrapeso."""
        rad = math.radians(angle_deg)

        # Proporções da agulha calculadas dinamicamente com base no tamanho atual
        target_sz = min(self.rect.width, self.rect.height)
        scale = target_sz / 280.0

        needle_len = 86 * scale   # Comprimento da ponta
        tail_len   = 16 * scale   # Contrapeso traseiro
        half_w     = max(2.5, 4.5 * scale)  # Meia-largura na base central

        # Ângulos normais para a largura da base
        left_rad  = rad + math.pi / 2
        right_rad = rad - math.pi / 2

        # Vértices da agulha
        tip    = (cx + needle_len * math.cos(rad),       cy - needle_len * math.sin(rad))
        base_l = (cx + half_w     * math.cos(left_rad),  cy - half_w     * math.sin(left_rad))
        base_r = (cx + half_w     * math.cos(right_rad), cy - half_w     * math.sin(right_rad))
        tail   = (cx - tail_len   * math.cos(rad),       cy + tail_len   * math.sin(rad))

        # 1. Sombra projetada da agulha (offset 2px)
        shadow_pts = [(p[0] + 2, p[1] + 2) for p in (tip, base_l, tail, base_r)]
        pygame.draw.polygon(self.surface, (10, 10, 14), shadow_pts)

        # 2. Corpo da agulha com chanfro 3D (lado claro e lado escuro)
        pygame.draw.polygon(self.surface, (245, 245, 250), [tip, base_l, tail])
        pygame.draw.polygon(self.surface, (170, 175, 185), [tip, base_r, tail])
        pygame.draw.polygon(self.surface, (35, 35, 40),    [tip, base_l, tail, base_r], 1)

        # 3. Pino / cubo central metálico
        pygame.draw.circle(self.surface, (25, 25, 30),   (cx, cy), max(6, int(11 * scale)))
        pygame.draw.circle(self.surface, (120, 125, 135), (cx, cy), max(5, int(9 * scale)))
        pygame.draw.circle(self.surface, (215, 220, 230), (cx - 2, cy - 2), max(2, int(3 * scale)))

    def draw(self):
        # Interpolação suave a 60 FPS (Lerp) para a agulha não dar saltos entre ciclos OBD
        self.current_rpm += (self.target_rpm - self.current_rpm) * 0.22

        cx, cy = self.rect.centerx, self.rect.centery

        # 1. Mostrador de fundo
        if self.tacho_img:
            t_rect = self.tacho_img.get_rect(center=(cx, cy))
            self.surface.blit(self.tacho_img, t_rect)
        else:
            # Fallback geométrico se não houver imagem
            r = min(self.rect.width, self.rect.height) // 2
            pygame.draw.circle(self.surface, (20, 20, 20), (cx, cy), r)
            pygame.draw.circle(self.surface, (80, 80, 80), (cx, cy), r, 4)

        # 2. Agulha desenhada manualmente baseada no RPM interpolado
        max_rpm = config.RPM_MAX
        disp_rpm = max(0.0, self.current_rpm)
        # Mapeamento do arco: 0 RPM = 222° (início azul), max_rpm = -18° (fim vermelho)
        angle_deg = 222 + (min(disp_rpm, max_rpm) / max_rpm) * (-240)
        self._draw_needle(cx, cy, angle_deg)

        # 3. Indicador digital de RPM
        val_str = f"{int(round(disp_rpm)):04d}"
        val_rpm = self._font_rpm.render(val_str, True, self.c_red)
        shadow_rpm = self._font_rpm.render(val_str, True, (0, 0, 0))

        text_y = cy + 25
        self.surface.blit(shadow_rpm, (cx - val_rpm.get_width() // 2 + 1, text_y + 1))
        self.surface.blit(val_rpm,    (cx - val_rpm.get_width() // 2,     text_y))
