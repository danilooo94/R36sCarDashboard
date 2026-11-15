"""Métricas derivadas dos dados OBD para a HUD de telemetria.

Calculadas globalmente pelo MultiPageApp (uma vez por frame), para que o timer
0-100 e o tempo de viagem continuem funcionando mesmo com outra página aberta.
Nenhuma dependência de pygame: lógica pura e testável.
"""
from collections import deque
import json
import math
import os
import time

import config
import settings


def fmt_time(seconds: float) -> str:
    """Formata segundos como m:ss.s (ex.: 0:07.8)."""
    tenths = int(round(max(0.0, seconds) * 10))
    minutes, tenths = divmod(tenths, 600)
    return f"{minutes}:{tenths / 10:04.1f}"


def fmt_hms(seconds: float) -> str:
    """Formata segundos como h:mm:ss (ex.: 1:34:20)."""
    total = int(max(0, seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}"


# ── Marcha estimada ──────────────────────────────────────────────────────────

class GearEstimator:
    """Estima a marcha engatada pela relação RPM / km/h (0 = neutro/parado).

    Tem histerese: só troca de marcha depois que o novo candidato fica estável,
    e mantém a marcha anterior durante embreagem pisada / patinação.
    """

    MIN_SPEED_KMH = 5.0
    MIN_RPM       = 500
    TOLERANCE_LN  = 0.18    # |ln(razão medida / razão da marcha)| máxima p/ aceitar
    STABLE_SECS   = 0.35

    def __init__(self, table=None):
        self.table = dict(table or config.GEAR_RPM_PER_KMH)
        self.gear = 0
        self._cand = 0
        self._cand_since = 0.0

    def _candidate(self, rpm: float, speed: float) -> int:
        if speed < self.MIN_SPEED_KMH or rpm < self.MIN_RPM:
            return 0
        ratio = rpm / speed
        best_gear, best_err = self.gear, None
        for gear, rpm_per_kmh in self.table.items():
            err = abs(math.log(ratio / rpm_per_kmh))
            if best_err is None or err < best_err:
                best_gear, best_err = gear, err
        if best_err is None or best_err > self.TOLERANCE_LN:
            return self.gear          # embreagem / troca em andamento: mantém
        return best_gear

    def update(self, rpm: float, speed: float, now: float) -> int:
        cand = self._candidate(rpm, speed)
        if cand == self.gear:
            self._cand = cand
        elif cand == self._cand:
            if now - self._cand_since >= self.STABLE_SECS:
                self.gear = cand
        else:
            self._cand = cand
            self._cand_since = now
        return self.gear


# ── Timer 0-100 km/h ─────────────────────────────────────────────────────────

class ZeroToHundred:
    """Cronômetro de aceleração (estilo "Berserk Timer").

    Ciclo: WAIT_STOP (precisa parar) -> READY (armado) -> RUNNING (cronometrando)
    -> DONE (mostra resultado por alguns segundos) -> WAIT_STOP.
    Interpola o instante em que a velocidade cruza o início e a meta, pois o OBD
    amostra a poucos Hz.
    """

    WAIT_STOP, READY, RUNNING, DONE = "WAIT_STOP", "READY", "RUNNING", "DONE"

    STOP_KMH       = 2.0     # abaixo disso o carro é considerado parado
    START_KMH      = 3.0     # acima disso a corrida começa
    ABORT_DROP_KMH = 10.0    # queda em relação ao pico invalida a corrida
    TIMEOUT_SECS   = 40.0
    DONE_HOLD_SECS = 5.0

    def __init__(self, target=None, best_path=None):
        self.target = float(target if target is not None else config.ZERO_TO_HUNDRED_TARGET)
        self._best_path = best_path if best_path is not None else config.BEST_0_100_FILE
        self.state = self.WAIT_STOP
        self.elapsed = 0.0
        self.last = None
        self.best = self._load_best()
        self._prev = None            # (t, v) da amostra anterior
        self._t0 = 0.0
        self._peak = 0.0
        self._done_at = 0.0

    # persistência do recorde
    def _load_best(self):
        try:
            with open(self._best_path, "r", encoding="utf-8") as fh:
                value = float(json.load(fh)["best"])
                return value if value > 0 else None
        except Exception:
            return None

    def _save_best(self):
        try:
            os.makedirs(os.path.dirname(self._best_path) or ".", exist_ok=True)
            with open(self._best_path, "w", encoding="utf-8") as fh:
                json.dump({"best": self.best}, fh)
        except Exception:
            pass

    @staticmethod
    def _cross_time(prev, now, speed, level):
        """Instante (interpolado) em que a velocidade cruzou `level`."""
        if prev is not None and prev[1] < level <= speed and speed > prev[1]:
            frac = (level - prev[1]) / (speed - prev[1])
            return prev[0] + frac * (now - prev[0])
        return now

    @property
    def display_time(self) -> float:
        if self.state == self.RUNNING:
            return self.elapsed
        if self.state == self.DONE and self.last is not None:
            return self.last
        return 0.0

    def update(self, speed: float, now: float) -> None:
        prev, self._prev = self._prev, (now, speed)

        if self.state == self.WAIT_STOP:
            if speed <= self.STOP_KMH:
                self.state = self.READY
                self.elapsed = 0.0

        if self.state == self.READY and speed > self.START_KMH:
            self._t0 = self._cross_time(prev, now, speed, self.START_KMH)
            self._peak = speed
            self.state = self.RUNNING

        if self.state == self.RUNNING:
            self._peak = max(self._peak, speed)
            if speed >= self.target:
                t_hit = self._cross_time(prev, now, speed, self.target)
                self.last = max(0.0, t_hit - self._t0)
                self.elapsed = self.last
                if self.best is None or self.last < self.best:
                    self.best = self.last
                    if not settings.enabled("mock_mode"):
                        self._save_best()
                self.state = self.DONE
                self._done_at = now
            elif (speed <= self.STOP_KMH
                  or speed < self._peak - self.ABORT_DROP_KMH
                  or now - self._t0 > self.TIMEOUT_SECS):
                self.state = self.WAIT_STOP
                self.elapsed = 0.0
            else:
                self.elapsed = now - self._t0

        elif self.state == self.DONE:
            if now - self._done_at >= self.DONE_HOLD_SECS:
                self.state = self.WAIT_STOP


# ── Agregador ────────────────────────────────────────────────────────────────

class DerivedTelemetry:
    """Calcula marcha, 0-100, trip, distância, vel. média, consumo e boost."""

    def __init__(self):
        self.gear = GearEstimator()
        self.zero100 = ZeroToHundred()
        self._trip_secs = 0.0
        self._trip_km = 0.0
        self._last_now = None
        self._consumption = None     # km/l suavizado

    def reset(self):
        """Reset session-specific counters when switching between Mock and Real modes."""
        self.gear = GearEstimator()
        self.zero100 = ZeroToHundred()
        self._trip_secs = 0.0
        self._trip_km = 0.0
        self._last_now = None
        self._consumption = None

    def update(self, data: dict, now: float = None) -> dict:
        now = time.monotonic() if now is None else now
        dt = 0.0 if self._last_now is None else min(0.5, max(0.0, now - self._last_now))
        self._last_now = now

        rpm   = float(data.get("rpm", 0) or 0)
        speed = float(data.get("speed", 0) or 0)

        # Tempo e distância de viagem: conta com o motor ligado e o OBD conectado
        if data.get("connected", False) and rpm >= config.TRIP_ENGINE_ON_RPM:
            self._trip_secs += dt
            if speed > 0:
                self._trip_km += (speed / 3600.0) * dt

        avg_speed = (self._trip_km / (self._trip_secs / 3600.0)) if self._trip_secs >= 3.0 else speed

        # Consumo instantâneo (km/l) a partir do MAF, suavizado (~2 s)
        if settings.enabled("consumption"):
            maf = float(data.get("maf", 0) or 0)
            if maf <= 0:
                self._consumption = None
            elif speed >= 3.0:
                liters_per_hour = maf * 3600.0 / (config.FUEL_AFR * config.FUEL_DENSITY_G_L)
                instant = speed / liters_per_hour if liters_per_hour > 0 else None
                if instant is not None:
                    if self._consumption is None:
                        self._consumption = instant
                    else:
                        alpha = 1.0 - math.exp(-dt / 2.0) if dt > 0 else 0.0
                        self._consumption += alpha * (instant - self._consumption)
        else:
            self._consumption = None

        # Boost: MAP absoluto (kPa) menos a pressão atmosférica (apenas se turbo habilitado)
        if settings.enabled("turbo"):
            map_kpa = float(data.get("map_kpa", 0) or 0)
            boost_bar = max(0.0, (map_kpa - config.BAROMETRIC_KPA) / 100.0) if map_kpa > 0 else 0.0
        else:
            boost_bar = 0.0

        gear = self.gear.update(rpm, speed, now) if settings.enabled("gear_indicator") else 0
        if settings.enabled("zero_to_hundred"):
            self.zero100.update(speed, now)

        return {
            "gear":             gear,
            "trip_seconds":     self._trip_secs,
            "trip_km":          self._trip_km,
            "avg_speed_kmh":    avg_speed,
            "consumption_kml":  self._consumption,
            "boost_bar":        boost_bar,
            "boost_psi":        boost_bar * 14.5038,
            "zero100_state":    self.zero100.state,
            "zero100_time":     self.zero100.display_time,
            "zero100_last":     self.zero100.last,
            "zero100_best":     self.zero100.best,
        }


# ── Histórico Contínuo para Gráficos ao Vivo ─────────────────────────────────

HISTORY_KEYS = (
    "rpm",
    "speed",
    "water_temp",
    "oil_temp",
    "voltage",
    "throttle",
    "load",
    "intake_temp",
    "consumption_kml",
    "maf",
    "fuel",
    "boost_bar",
    "map_kpa",
)


class TelemetryHistory:
    """Armazena séries temporais `(timestamp, valor)` em segundo plano para todas as abas de gráficos."""

    def __init__(self, sample_interval: float = 0.20, max_seconds: float = 190.0):
        self.sample_interval = float(sample_interval)
        maxlen = max(60, int(math.ceil(max_seconds / self.sample_interval)) + 8)
        self._buffers = {k: deque(maxlen=maxlen) for k in HISTORY_KEYS}
        self._last_sample_at = 0.0

    def clear(self):
        """Limpa todo o histórico acumulado (ex.: ao alternar entre Mock e OBD Real)."""
        for buf in self._buffers.values():
            buf.clear()
        self._last_sample_at = 0.0

    def record(self, data: dict, now: float = None):
        """Amostra todos os parâmetros quando conectado, respeitando `sample_interval`."""
        if not data.get("connected", False):
            return
        now = time.monotonic() if now is None else now
        if self._last_sample_at > 0.0 and (now - self._last_sample_at) < self.sample_interval:
            return
        self._last_sample_at = now

        for k, buf in self._buffers.items():
            raw = data.get(k)
            val = float(raw) if raw is not None else 0.0
            buf.append((now, val))

    def get_window(self, key: str, window_secs: float, now: float = None) -> list:
        """Retorna lista de `(t, valor)` dentro dos últimos `window_secs` segundos."""
        buf = self._buffers.get(key)
        if not buf:
            return []
        now = time.monotonic() if now is None else now
        cutoff = now - window_secs
        return [(t_pt, v_pt) for (t_pt, v_pt) in buf if t_pt >= cutoff]
