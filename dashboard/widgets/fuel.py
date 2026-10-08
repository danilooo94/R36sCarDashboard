import pygame
import config
from dashboard.widgets.base import Widget


class FuelWidget(Widget):
    """Widget de combustível dividido em dois blocos rebaixados estilo Doom."""

    def __init__(self, surface, rect):
        super().__init__(surface, rect)
        self.fuel_pct = 75.0  # 0 a 100%
        self._font_label = pygame.font.SysFont("monospace", 13, bold=True)
        self._font_indicator = pygame.font.SysFont("monospace", 13, bold=True)

        # Cores
        self.c_bg_bar = (10, 10, 12)
        self.c_green  = (40, 220, 80)
        self.c_yellow = (240, 200, 20)
        self.c_red    = (220, 20, 20)
        self.c_white  = (225, 230, 235)
        self.c_pump   = (230, 150, 30)

    def update(self, data: dict):
        """Atualiza a porcentagem de combustível (0 a 100%)."""
        val = data.get("fuel_level", data.get("fuel", None))
        if val is not None:
            try:
                self.fuel_pct = max(0.0, min(100.0, float(val)))
            except (ValueError, TypeError):
                pass

    def _draw_recessed_box(self, r):
        """Moldura rebaixada metálica estilo Doom idêntica às caixas de status."""
        pygame.draw.rect(self.surface, (18, 18, 22), r)
        pygame.draw.rect(self.surface, (75, 75, 80), r, 2)
        pygame.draw.line(self.surface, (30, 30, 35), (r.left, r.top), (r.right, r.top), 1)
        pygame.draw.line(self.surface, (30, 30, 35), (r.left, r.top), (r.left, r.bottom), 1)
        pygame.draw.line(self.surface, (115, 115, 120), (r.left, r.bottom - 1), (r.right, r.bottom - 1), 1)
        pygame.draw.line(self.surface, (115, 115, 120), (r.right - 1, r.top), (r.right - 1, r.bottom), 1)

    def _draw_pump_icon(self, x, y):
        """Desenha um ícone pixel art de bomba de combustível."""
        pygame.draw.rect(self.surface, self.c_pump, (x, y + 4, 14, 18), 2)
        pygame.draw.rect(self.surface, self.c_pump, (x + 3, y + 7, 8, 6))
        pygame.draw.line(self.surface, self.c_pump, (x + 14, y + 8), (x + 18, y + 12), 2)
        pygame.draw.line(self.surface, self.c_pump, (x + 18, y + 12), (x + 18, y + 20), 2)

    def draw(self):
        x, y, w, h = self.rect.x, self.rect.y, self.rect.width, self.rect.height

        # Divide o widget em dois blocos:
        # Bloco 1: Mostrador com barras e ícone
        # Bloco 2: Caixa com o nome 'combustível'
        label_box_h = 30
        gap = 8
        gauge_box_h = h - label_box_h - gap

        gauge_box = pygame.Rect(x, y, w, gauge_box_h)
        label_box = pygame.Rect(x, y + gauge_box_h + gap, w, label_box_h)

        # ── BLOCO 1: Medidor de combustível ──────────────────────────────────
        self._draw_recessed_box(gauge_box)

        # Ícone da bomba
        self._draw_pump_icon(x + 12, y + gauge_box_h // 2 - 12)

        # Dimensões da coluna de barras
        bar_w = max(24, int(w * 0.36))
        bar_h = gauge_box_h - 20
        bar_x = x + w - bar_w - 12
        bar_y = y + 10

        # Indicadores H (High) e E (Empty)
        lbl_h = self._font_indicator.render("H", True, (240, 180, 50))
        lbl_e = self._font_indicator.render("E", True, (240, 180, 50))
        self.surface.blit(lbl_h, (bar_x - 16, bar_y))
        self.surface.blit(lbl_e, (bar_x - 16, bar_y + bar_h - 16))

        # Fundo escuro da coluna
        pygame.draw.rect(self.surface, self.c_bg_bar, (bar_x, bar_y, bar_w, bar_h))
        pygame.draw.rect(self.surface, (40, 40, 48), (bar_x, bar_y, bar_w, bar_h), 1)

        # 10 Segmentos coloridos
        total_segments = 10
        active_segments = int(round((self.fuel_pct / 100.0) * total_segments))
        seg_gap = 2
        seg_h = max(4, (bar_h - 6 - (total_segments - 1) * seg_gap) // total_segments)

        for i in range(total_segments):
            seg_y = bar_y + bar_h - 4 - ((i + 1) * (seg_h + seg_gap))
            is_active = i < active_segments

            if is_active:
                if i < 2:
                    color = self.c_red
                elif i < 4:
                    color = self.c_yellow
                else:
                    color = self.c_green
            else:
                color = (25, 25, 30)

            pygame.draw.rect(self.surface, color, (bar_x + 3, seg_y, bar_w - 6, seg_h))

        # ── BLOCO 2: Caixa do rótulo 'combustível' ───────────────────────────
        self._draw_recessed_box(label_box)

        lbl_fuel = self._font_label.render("combustível", True, self.c_white)
        lbl_x = label_box.centerx - lbl_fuel.get_width() // 2
        lbl_y = label_box.centery - lbl_fuel.get_height() // 2
        self.surface.blit(lbl_fuel, (lbl_x, lbl_y))
