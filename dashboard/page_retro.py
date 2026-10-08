import pygame
import config
from dashboard.page_base import Page
from dashboard.widgets.doom import (
    DoomSpeedWidget,
    DoomFaceWidget,
    DoomTachometerWidget,
    DoomStatusBoxWidget,
    DoomFuelWidget,
)


class RetroPage(Page):
    """HUD baseada na imagem de referência do Doom/Retro com componentes modulares."""

    name = "RETRO HUD"

    def __init__(self, screen):
        super().__init__(screen)

        # 1. Fonte do título
        font_path = "fonts/DooM.ttf"
        try:
            self._font_title = pygame.font.Font(font_path, 28)
        except Exception:
            self._font_title = pygame.font.SysFont("impact", 32)

        self.c_red = (220, 20, 20)

        # 2. Imagem de fundo completa
        self.bg_img = None
        try:
            img = pygame.image.load("assets/doom_bg.jpg").convert_alpha()
            self.bg_img = pygame.transform.scale(img, (config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        except FileNotFoundError:
            import app_log
            app_log.warning("[HUD] Imagem assets/doom_bg.jpg não encontrada.")

        # 3. Componentes como widgets separados (redimensionados conforme solicitado)
        self.widgets = [
            # Painel esquerdo: Velocidade e Combustível (reduzido)
            DoomSpeedWidget(screen, pygame.Rect(40, 50, 160, 150)),
            DoomFuelWidget(screen, pygame.Rect(100, 320, 105, 155)),

            # Painel central: Rosto do Doomguy com moldura
            DoomFaceWidget(screen, pygame.Rect(226, 128, 170, 204)),

            # Painel direito: Tacômetro (reduzido para 235x235) e Caixas de Status
            DoomTachometerWidget(screen, pygame.Rect(405, 45, 235, 235)),
            DoomStatusBoxWidget(screen, pygame.Rect(420, 310, 205, 80)),
        ]

    def draw_chrome(self, data: dict):
        pass  # Sem chrome padrão

    def draw(self):
        # 1. Fundo
        if self.bg_img:
            self.screen.blit(self.bg_img, (0, 0))
        else:
            self.screen.fill((40, 40, 45))
            pygame.draw.rect(self.screen, (130, 130, 135),
                             (10, 40, config.SCREEN_WIDTH - 20, config.SCREEN_HEIGHT - 50))

        # 3. Renderiza todos os widgets filhos
        for w in self.widgets:
            w.draw()
