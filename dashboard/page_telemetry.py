"""Página "R36S CAR HUD - OBD2 TELEMETRY" (estilo Doom / steampunk).

Tudo é desenhado proceduralmente num canvas lógico de 640x480. As camadas
estáticas (placas, mostradores, ícones, rótulos) são pré-renderizadas uma única
vez em ``self._bg``; por frame só são desenhados ponteiros, barras e textos
dinâmicos (com cache de superfícies de texto) para ser leve no R36S.
"""
import math
import os

import pygame
from pygame import gfxdraw

import config
from dashboard.page_base import Page
from dashboard.telemetry import fmt_time, fmt_hms
from dashboard.widgets.doom.face import DoomFaceWidget

W, H = 640, 480

# ── Paleta ────────────────────────────────────────────────────────────────
BG = (24, 25, 28)
PLATE = (52, 54, 58)
PLATE_HI = (92, 94, 98)
PLATE_LO = (14, 14, 16)
WELL = (10, 10, 12)
RED = (225, 30, 25)
RED_DIM = (70, 14, 12)
AMBER = (255, 176, 20)
AMBER_DIM = (70, 48, 8)
GREEN = (60, 230, 70)
GREEN_DIM = (14, 56, 18)
KHAKI = (196, 182, 120)
TXT = (214, 214, 206)
TXT_DIM = (130, 130, 124)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FONT_DOOM = os.path.join(_ROOT, "fonts", "DooM.ttf")
_fonts = {}
_texts = {}


def font(size, doom=False):
    key = (size, doom)
    f = _fonts.get(key)
    if f is None:
        if doom and os.path.exists(_FONT_DOOM):
            f = pygame.font.Font(_FONT_DOOM, size)
        elif doom:
            f = pygame.font.SysFont("impact", size)
        else:
            f = pygame.font.SysFont("dejavusansmono,consolas,couriernew,monospace", size, bold=True)
        _fonts[key] = f
    return f


def text(s, size, color, doom=False):
    key = (s, size, color, doom)
    surf = _texts.get(key)
    if surf is None:
        if len(_texts) > 500:
            _texts.clear()
        surf = font(size, doom).render(s, True, color)
        _texts[key] = surf
    return surf


def blit_c(dst, surf, cx, cy):
    dst.blit(surf, (cx - surf.get_width() // 2, cy - surf.get_height() // 2))


def lerp_col(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ── Primitivas estáticas ──────────────────────────────────────────────────

def plate(surf, rect, base=PLATE, inset=False):
    r = pygame.Rect(rect)
    pygame.draw.rect(surf, base, r, border_radius=3)
    hi, lo = (PLATE_LO, PLATE_HI) if inset else (PLATE_HI, PLATE_LO)
    pygame.draw.line(surf, hi, r.topleft, (r.right - 1, r.top))
    pygame.draw.line(surf, hi, r.topleft, (r.left, r.bottom - 1))
    pygame.draw.line(surf, lo, (r.left, r.bottom - 1), (r.right - 1, r.bottom - 1))
    pygame.draw.line(surf, lo, (r.right - 1, r.top), (r.right - 1, r.bottom - 1))


def rivet(surf, x, y):
    pygame.draw.circle(surf, (20, 20, 22), (x + 1, y + 1), 2)
    pygame.draw.circle(surf, (120, 122, 126), (x, y), 2)
    surf.set_at((x - 1, y - 1), (200, 200, 205))


def well(surf, rect, color=WELL):
    plate(surf, rect, color, inset=True)


def icon_engine(s, cx, cy, c):
    pygame.draw.rect(s, c, (cx - 10, cy - 5, 20, 13), border_radius=2)
    pygame.draw.rect(s, c, (cx - 5, cy - 9, 10, 4))
    pygame.draw.rect(s, c, (cx - 15, cy - 1, 5, 5))
    pygame.draw.rect(s, c, (cx + 10, cy - 3, 5, 9))
    pygame.draw.line(s, BG, (cx - 6, cy + 1), (cx + 6, cy + 1), 2)


def icon_pump(s, cx, cy, c):
    pygame.draw.rect(s, c, (cx - 6, cy - 9, 12, 18), border_radius=2)
    pygame.draw.rect(s, BG, (cx - 3, cy - 6, 6, 6))
    pygame.draw.rect(s, c, (cx - 8, cy + 8, 16, 3))
    pygame.draw.lines(s, c, False, [(cx + 6, cy - 5), (cx + 10, cy - 3), (cx + 10, cy + 4)], 2)


def icon_thermo(s, cx, cy, c):
    pygame.draw.rect(s, c, (cx - 3, cy - 12, 6, 18), border_radius=3)
    pygame.draw.circle(s, c, (cx, cy + 8), 6)
    pygame.draw.rect(s, BG, (cx - 1, cy - 9, 2, 14))
    pygame.draw.circle(s, RED, (cx, cy + 8), 3)


def icon_stopwatch(s, cx, cy, c):
    pygame.draw.circle(s, c, (cx, cy + 2), 10, 2)
    pygame.draw.rect(s, c, (cx - 3, cy - 11, 6, 3))
    pygame.draw.line(s, c, (cx, cy + 2), (cx + 5, cy - 3), 2)
    pygame.draw.line(s, c, (cx + 7, cy - 6), (cx + 9, cy - 8), 2)


def icon_fist(s, cx, cy, c):
    pygame.draw.rect(s, c, (cx - 14, cy - 6, 28, 20), border_radius=5)
    for i in range(4):
        pygame.draw.circle(s, c, (cx - 10 + i * 7, cy - 7), 4)
    pygame.draw.rect(s, c, (cx - 20, cy + 2, 8, 9), border_radius=3)
    for i in range(3):
        pygame.draw.line(s, (120, 60, 0), (cx - 6 + i * 7, cy - 4), (cx - 6 + i * 7, cy + 2))


def icon_leaf(s, cx, cy, c):
    pts = [(cx - 8, cy + 8), (cx - 6, cy - 2), (cx + 2, cy - 9), (cx + 9, cy - 9),
           (cx + 8, cy), (cx + 1, cy + 7)]
    pygame.draw.polygon(s, c, pts)
    pygame.draw.line(s, BG, (cx - 8, cy + 9), (cx + 4, cy - 5), 1)


def icon_turbo(s, cx, cy, c):
    pygame.draw.circle(s, c, (cx, cy), 10, 2)
    pygame.draw.circle(s, c, (cx, cy), 3)
    for a in (0, 120, 240):
        r = math.radians(a)
        pygame.draw.line(s, c, (cx, cy), (cx + 8 * math.cos(r), cy + 8 * math.sin(r)), 2)
    pygame.draw.rect(s, c, (cx + 8, cy - 2, 7, 5))


def temp_level(v):
    if v >= config.TEMP_COLOR_DANGER:
        return 2
    if v >= config.TEMP_COLOR_WARN:
        return 1
    return 0


def volt_level(v):
    if v <= 0:
        return 0
    if v < config.VOLT_COLOR_LOW_DANGER:
        return 2
    if v < config.VOLT_COLOR_LOW_WARN or v > config.VOLT_COLOR_HIGH_WARN:
        return 1
    return 0


# ── Mostradores circulares ────────────────────────────────────────────────

D = 198
SS = 3  # supersampling do mostrador estático


def _pt(c, r, f):
    """Ponto no ângulo da fração f (0..1) do arco 270° (início 225°, horário)."""
    a = math.radians(225 - 270 * f)
    return (c + r * math.cos(a), c - r * math.sin(a))


def build_dial(vmax, major, minor, label_div, redline, face_col, num_col):
    """Gera o mostrador estático (D x D) com RGBA."""
    s = D * SS
    c = s / 2
    surf = pygame.Surface((s, s), pygame.SRCALPHA)
    pygame.draw.circle(surf, (20, 20, 22), (c, c), c - 1)
    pygame.draw.circle(surf, (120, 122, 126), (c, c), c - 3 * SS, 3 * SS)
    pygame.draw.circle(surf, (60, 62, 66), (c, c), c - 7 * SS, 2 * SS)
    pygame.draw.circle(surf, face_col, (c, c), c - 9 * SS)
    R = c - 12 * SS
    if redline is not None:
        n = 40
        f0 = redline / vmax
        for i in range(n):
            fa = f0 + (1 - f0) * i / n
            fb = f0 + (1 - f0) * (i + 1) / n
            pa, pb = _pt(c, R, fa), _pt(c, R, fb)
            pc, pd = _pt(c, R - 7 * SS, fb), _pt(c, R - 7 * SS, fa)
            pygame.draw.polygon(surf, RED, [pa, pb, pc, pd])
    v = 0
    while v <= vmax + 1e-6:
        f = v / vmax
        is_major = (v % major) < 1e-6
        ln = 12 * SS if is_major else 6 * SS
        col = num_col if not (redline is not None and v >= redline) else RED
        pygame.draw.line(surf, col, _pt(c, R - (8 * SS if redline is not None and v >= redline else 0), f),
                         _pt(c, R - ln - (8 * SS if redline is not None and v >= redline else 0), f),
                         (3 if is_major else 2) * SS // 2 + 1)
        v += minor
    surf = pygame.transform.smoothscale(surf, (D, D))
    # números (já na resolução final para ficar nítido)
    v = 0
    while v <= vmax + 1e-6:
        if (v % major) < 1e-6:
            f = v / vmax
            p = _pt(D / 2, D / 2 - 33, f)
            col = RED if (redline is not None and v >= redline) else num_col
            blit_c(surf, text(str(int(v / label_div)), 13, col), int(p[0]), int(p[1]))
        v += major
    return surf


class Dial:
    def __init__(self, rect, vmax, major, minor, label_div, redline, face_col,
                 num_col, needle_col, unit, val_col, round_to):
        self.rect = pygame.Rect(rect)
        self.vmax = vmax
        self.needle_col = needle_col
        self.unit = unit
        self.val_col = val_col
        self.round_to = round_to
        self.img = build_dial(vmax, major, minor, label_div, redline, face_col, num_col)
        self.disp = 0.0

    def draw_static(self, bg):
        bg.blit(self.img, self.rect)
        cx, cy = self.rect.center
        blit_c(bg, text(self.unit, 11, TXT_DIM), cx, cy + 28)
        well(bg, (cx - 34, cy + 40, 68, 28))

    def draw(self, cv, value):
        value = max(0.0, min(self.vmax, value))
        self.disp += (value - self.disp) * 0.35
        cx, cy = self.rect.center
        f = self.disp / self.vmax
        a = math.radians(225 - 270 * f)
        ux, uy = math.cos(a), -math.sin(a)
        px, py = -uy, ux
        L = D / 2 - 22
        pts = [(cx + ux * L, cy + uy * L),
               (cx + px * 4 - ux * 14, cy + py * 4 - uy * 14),
               (cx - px * 4 - ux * 14, cy - py * 4 - uy * 14)]
        ipts = [(int(x), int(y)) for x, y in pts]
        gfxdraw.filled_polygon(cv, ipts, self.needle_col)
        gfxdraw.aapolygon(cv, ipts, self.needle_col)
        gfxdraw.filled_circle(cv, cx, cy, 8, (30, 30, 32))
        gfxdraw.aacircle(cv, cx, cy, 8, (150, 152, 156))
        gfxdraw.filled_circle(cv, cx, cy, 3, self.needle_col)
        shown = int(round(value / self.round_to) * self.round_to)
        blit_c(cv, text(str(shown), 20, self.val_col), cx, cy + 54)


# ── Barras ────────────────────────────────────────────────────────────────

def seg_color(i, n, kind):
    t = i / max(1, n - 1)
    if kind == "fuel":  # embaixo vermelho -> cima verde
        return RED if t < 0.2 else (AMBER if t < 0.4 else GREEN)
    return GREEN if t < 0.5 else (AMBER if t < 0.8 else RED)  # boost


def draw_segbar(cv, rect, frac, kind, n=10):
    r = pygame.Rect(rect)
    gap = 3
    h = (r.h - gap * (n - 1)) / n
    frac = max(0.0, min(1.0, frac))
    for i in range(n):
        y = r.bottom - (i + 1) * h - i * gap
        lit = (i + 0.5) / n <= frac + 0.02 and frac > 0
        col = seg_color(i, n, kind)
        pygame.draw.rect(cv, col if lit else lerp_col(col, (0, 0, 0), 0.82),
                         (r.x, int(y), r.w, int(h)))


class HBar:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        g = pygame.Surface(self.rect.size)
        for x in range(self.rect.w):
            t = x / max(1, self.rect.w - 1)
            col = lerp_col(RED, AMBER, t / 0.5) if t < 0.5 else lerp_col(AMBER, GREEN, (t - 0.5) / 0.5)
            pygame.draw.line(g, col, (x, 0), (x, self.rect.h))
        self.grad = g

    def draw_static(self, bg):
        well(bg, self.rect.inflate(4, 4))

    def draw(self, cv, pct):
        pct = max(0.0, min(100.0, pct))
        w = int(self.rect.w * pct / 100)
        if w > 0:
            cv.blit(self.grad, self.rect.topleft, (0, 0, w, self.rect.h))
        blit_c(cv, text(f"{int(pct)}%", 12, (255, 255, 255)), self.rect.centerx, self.rect.centery)


# ── Página ────────────────────────────────────────────────────────────────

class TelemetryPage(Page):
    name = "TELEMETRY"

    def __init__(self, screen):
        super().__init__(screen)
        sw, sh = screen.get_size()
        self._direct = (sw, sh) == (W, H)
        self.cv = screen if self._direct else pygame.Surface((W, H))
        self._gear_shown = 0

        rm = config.RPM_MAX
        self.speedo = Dial((52, 56, D, D), config.SPEED_MAX, 20, 10, 1, None,
                           (30, 12, 12), (235, 235, 230), (235, 235, 230),
                           "KM/H", RED, 1)
        self.tach = Dial((390, 56, D, D), rm, 1000, 500, 1000, config.RPM_REDLINE,
                         (34, 30, 10), (240, 220, 120), RED,
                         "RPM x1000", AMBER, 10)
        self.tps = HBar((394, 271, 190, 14))
        self.load = HBar((394, 302, 190, 14))
        self.face = DoomFaceWidget(self.cv, pygame.Rect(266, 58, 108, 134))
        self.widgets = [self.face]

        self._bg = pygame.Surface((W, H))
        self._build_bg()

    # ── Camada estática ───────────────────────────────────────────────────
    def _build_bg(self):
        b = self._bg
        b.fill(BG)
        # moldura do título
        plate(b, (4, 3, 632, 26), PLATE)
        blit_c(b, text("R36S CAR HUD - OBD2 TELEMETRY", 22, KHAKI, doom=True), W // 2, 16)
        for x in (10, 630):
            rivet(b, x, 10)
            rivet(b, x, 22)
        # faixa superior: luzes de aviso, shift, indicadores
        plate(b, (254, 31, 134, 25), PLATE, inset=True)
        plate(b, (394, 31, 122, 25), PLATE, inset=True)
        b.blit(text("SHIFT LIGHT", 11, TXT), (412, 37))
        plate(b, (520, 31, 114, 25), PLATE, inset=True)
        # mostradores
        for d in (self.speedo, self.tach):
            plate(b, d.rect.inflate(6, 6).clip(pygame.Rect(0, 0, W, H)), PLATE, inset=True)
            d.draw_static(b)
        # barra FUEL (esquerda)
        plate(b, (5, 56, 44, 264), PLATE)
        well(b, (10, 92, 34, 172))
        b.blit(text("FUEL", 12, TXT), (12, 59))
        blit_c(b, text("F", 13, TXT), 27, 80)
        blit_c(b, text("E", 13, RED), 27, 274)
        icon_pump(b, 27, 296, AMBER)
        # barra BOOST (direita)
        plate(b, (591, 56, 44, 264), PLATE)
        well(b, (596, 92, 34, 172))
        b.blit(text("BOOST", 11, TXT), (595, 59))
        blit_c(b, text("2.0", 12, TXT), 613, 80)
        blit_c(b, text("bar", 11, TXT_DIM), 613, 274)
        icon_turbo(b, 611, 296, AMBER)
        # caixa da marcha
        plate(b, (284, 196, 72, 64), PLATE, inset=True)
        blit_c(b, text("Marcha", 12, TXT), 320, 268)
        # motor temp / bateria
        b.blit(text("motor temp:", 12, TXT), (52, 260))
        b.blit(text("bateria:", 12, TXT), (156, 260))
        well(b, (52, 276, 96, 34), (22, 4, 4))
        well(b, (154, 276, 96, 34), (22, 4, 4))
        # TPS / Load
        b.blit(text("Acelerador (TPS %):", 11, TXT), (394, 257))
        b.blit(text("Carga (Load %):", 11, TXT), (394, 288))
        self.tps.draw_static(b)
        self.load.draw_static(b)
        # painel Berserk
        plate(b, (6, 326, 244, 120), PLATE)
        well(b, (12, 348, 232, 92), (14, 10, 6))
        blit_c(b, text("BERSERK TIMER 0-100", 12, KHAKI, doom=True), 128, 337)
        icon_fist(b, 206, 380, AMBER)
        # painel temp ar
        plate(b, (254, 326, 130, 120), PLATE)
        b.blit(text("Temp ar:", 13, TXT), (264, 334))
        icon_thermo(b, 272, 392, TXT)
        well(b, (290, 372, 88, 40), (4, 18, 6))
        # consumo + trip
        plate(b, (388, 326, 246, 120), PLATE)
        icon_leaf(b, 400, 346, GREEN)
        icon_pump(b, 418, 346, GREEN)
        b.blit(text("Consumo:", 13, TXT), (434, 338))
        well(b, (480, 356, 148, 30), (4, 18, 6))
        icon_stopwatch(b, 402, 410, GREEN)
        b.blit(text("Tempo de Viagem (Trip):", 11, TXT), (418, 392))
        well(b, (418, 408, 210, 32), (4, 18, 6))
        # rebites nos cantos dos painéis
        for r in ((6, 326, 244, 120), (254, 326, 130, 120), (388, 326, 246, 120),
                  (5, 56, 44, 264), (591, 56, 44, 264)):
            x, y, w, h = r
            for px, py in ((x + 5, y + 5), (x + w - 6, y + 5), (x + 5, y + h - 6), (x + w - 6, y + h - 6)):
                rivet(b, px, py)

    # ── Dinâmico ──────────────────────────────────────────────────────────
    def update(self, data: dict):
        self._d = data
        super().update(data)

    @staticmethod
    def _col(level, normal, blink):
        if level == 2:
            return RED if blink else (255, 255, 255)
        if level == 1:
            return AMBER
        return normal

    def draw(self):
        d = getattr(self, "_d", None) or {}
        cv = self.cv
        cv.blit(self._bg, (0, 0))
        blink = (pygame.time.get_ticks() // 250) % 2 == 0

        speed = d.get("speed", 0) or 0
        rpm = d.get("rpm", 0) or 0
        wt = d.get("water_temp", 0) or 0
        ot = d.get("oil_temp", 0) or 0
        volt = d.get("voltage", 0) or 0
        fuel = d.get("fuel", 0) or 0
        thr = d.get("throttle", 0) or 0
        load = d.get("load", 0) or 0
        iat = d.get("intake_temp", 0) or 0
        boost = d.get("boost_bar", 0) or 0
        gear = d.get("gear", 0) or 0

        # luzes de aviso do motor
        wl = max(temp_level(wt), temp_level(ot))
        icon_engine(cv, 276, 43, AMBER if wl >= 1 else AMBER_DIM)
        icon_engine(cv, 364, 43, RED if (wl == 2 and blink) else RED_DIM)

        # shift light
        shift = rpm >= config.SHIFT_RPM
        over = rpm >= config.RPM_REDLINE
        led = (RED if (not over or blink) else RED_DIM) if shift else RED_DIM
        pygame.draw.circle(cv, led, (403, 43), 6)
        if shift:
            pygame.draw.circle(cv, (255, 160, 150), (401, 41), 2)

        # luzes indicadoras (3x2)
        lamps = [
            (GREEN, d.get("connected", False)),
            (AMBER if temp_level(wt) < 2 else RED, temp_level(wt) >= 1),
            (AMBER if temp_level(ot) < 2 else RED, temp_level(ot) >= 1),
            (RED, volt_level(volt) >= 1),
            (AMBER, fuel > 0 and fuel < 15),
            (RED, over),
        ]
        for i, (col, on) in enumerate(lamps):
            cx = 520 + 19 + (i % 3) * 38
            cy = 31 + 7 + (i // 3) * 11
            pygame.draw.circle(cv, col if on else lerp_col(col, (0, 0, 0), 0.85), (cx, cy), 4)

        # mostradores
        self.speedo.draw(cv, speed)
        self.tach.draw(cv, rpm)

        # barras laterais
        draw_segbar(cv, (10, 92, 34, 172), fuel / 100.0, "fuel")
        blit_c(cv, text(f"{int(fuel)}%", 12, TXT), 27, 312)
        draw_segbar(cv, (596, 92, 34, 172), boost / config.BOOST_MAX_BAR, "boost")
        blit_c(cv, text(f"{boost:.1f}", 12, TXT), 613, 312)

        # rosto + marcha
        self.face.draw()
        g = "N" if gear <= 0 else str(gear)
        blit_c(cv, text(g, 50, KHAKI, doom=True), 320, 228)

        # motor temp / bateria
        c = self._col(temp_level(wt), RED, blink)
        blit_c(cv, text(f"{wt:.0f}\u00b0C", 20, c), 100, 293)
        c = self._col(volt_level(volt), RED, blink)
        blit_c(cv, text(f"{volt:.1f}V", 20, c), 202, 293)

        # TPS / Load
        self.tps.draw(cv, thr)
        self.load.draw(cv, load)

        self._draw_berserk(cv, d, blink)

        # temp ar
        blit_c(cv, text(f"{iat:.1f}\u00b0C", 18, GREEN), 334, 392)

        # consumo + trip
        kml = d.get("consumption_kml")
        s = "--.-" if kml is None else f"{min(kml, 99.9):.1f}"
        blit_c(cv, text(f"{s} km/l", 17, GREEN), 554, 371)
        blit_c(cv, text(fmt_hms(d.get("trip_seconds", 0) or 0), 20, GREEN), 523, 424)

        if not self._direct:
            pygame.transform.smoothscale(cv, self.screen.get_size(), self.screen)

    def _draw_berserk(self, cv, d, blink):
        st = d.get("zero100_state", "WAIT_STOP")
        t = d.get("zero100_time", 0) or 0
        last = d.get("zero100_last")
        best = d.get("zero100_best")
        hints = {"WAIT_STOP": ("PARE", AMBER), "READY": ("PRONTO", GREEN),
                 "RUNNING": ("GO!", RED), "DONE": ("OK", GREEN)}
        hint, hc = hints.get(st, ("", TXT))
        shown = last if (st in ("WAIT_STOP", "DONE") and last is not None) else t
        tcol = AMBER if st != "RUNNING" or blink else (255, 230, 140)
        blit_c(cv, text(fmt_time(shown), 36, tcol), 100, 378)
        blit_c(cv, text(hint, 14, hc), 206, 354) if False else None
        cv.blit(text(hint, 14, hc), (238 - text(hint, 14, hc).get_width(), 351))
        lt = "--" if last is None else f"{last:.2f}s"
        cv.blit(text(f"0-100 km/h: {lt}", 13, TXT), (20, 403))
        bt = "--" if best is None else fmt_time(best)
        cv.blit(text(f"BEST: {bt}", 15, RED), (20, 420))

    def draw_chrome(self, data: dict):
        pass  # a luz "link" no painel superior já mostra o estado do OBD

    def draw_alarms(self, alarm):
        try:
            if not alarm.blink_on:
                return
            col = RED if alarm.overall() == 2 else AMBER
            if alarm.overall() >= 1:
                pygame.draw.rect(self.screen, col, self.screen.get_rect(), 4)
        except Exception:
            pass
