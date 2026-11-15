import glob
import sys
import threading
import time
import serial
import serial.tools.list_ports
import config
import app_log
import settings
from obdii import Connection, commands

# Known USB VID/PID combos used on OBD-II / ELM327 / USB-Serial adapters
_OBD_VIDPID = [
    (0x0403, 0x6001),  # FTDI FT232R (OBDLink SX, VAG-COM, etc.)
    (0x1A86, 0x7523),  # CH340 / CH341 (common ELM327 USB)
    (0x1A86, 0x55D4),  # CH9102
    (0x10C4, 0xEA60),  # CP2102 (Silicon Labs)
    (0x067B, 0x2303),  # Prolific PL2303
    (0x303A, 0x1001),  # Espressif native USB
]

_OBD_DESC_KEYWORDS = (
    "OBD",
    "ELM327",
    "ELM",
    "OBDLINK",
    "FTDI",
    "CH340",
    "CP210",
    "PL2303",
    "USB SERIAL",
    "USB-SERIAL",
)


def find_obd_port():
    """Scan USB serial ports and return the first one that looks like an OBD/ELM327 adapter.

    Matching order:
      1. Exact VID/PID from known USB adapters list
      2. Description or hardware ID containing OBD/USB-serial keywords
      3. Linux fallback: first ttyUSB* or ttyACM* device
      4. Single COM port fallback if exactly one port exists
    """
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        return None

    # Pass 1 — VID/PID
    for port in ports:
        if port.vid is not None and port.pid is not None:
            if (port.vid, port.pid) in _OBD_VIDPID:
                app_log.info(f"[OBD] found by VID/PID: {port.device} — {port.description}")
                return port.device

    # Pass 2 — description / hwid keywords
    for port in ports:
        search_target = f"{port.description or ''} {port.hwid or ''}".upper()
        if any(kw.upper() in search_target for kw in _OBD_DESC_KEYWORDS):
            app_log.info(f"[OBD] found by description: {port.device} — {port.description}")
            return port.device

    # Pass 3 — Linux fallback: wired USB serial devices (ttyUSB*, ttyACM*)
    if sys.platform.startswith("linux"):
        candidates = sorted(
            glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
        )
        if candidates:
            app_log.info(f"[OBD] found by device path: {candidates[0]}")
            return candidates[0]

    # Pass 4 — Single port fallback
    if len(ports) == 1:
        app_log.info(f"[OBD] single serial port found: {ports[0].device} — {ports[0].description}")
        return ports[0].device

    return None


# Comandos categorizados por taxa de amostragem necessária
_FAST_COMMANDS = [
    ("rpm",      commands["ENGINE_SPEED"]),
    ("speed",    commands["VEHICLE_SPEED"]),
    ("throttle", commands["THROTTLE_POSITION"]),
    ("map_kpa",  commands["INTAKE_MAP"]),
]

_MEDIUM_COMMANDS = [
    ("water_temp",  commands["ENGINE_COOLANT_TEMP"]),
    ("oil_temp",    commands["ENGINE_OIL_TEMP"]),
    ("voltage",     commands["VEHICLE_VOLTAGE"]),
    ("load",        commands["ENGINE_LOAD"]),
    ("intake_temp", commands["INTAKE_AIR_TEMP"]),
    ("maf",         commands["MAF_RATE"]),
]

_SLOW_COMMANDS = [
    ("fuel", commands["FUEL_LEVEL"]),
]

# Pesos de Média Móvel Exponencial (EMA): val = alpha * novo + (1 - alpha) * anterior
# alpha menor = mais filtrado contra ruídos e chacoalho de boia
_EMA_ALPHAS = {
    "fuel":        0.03,  # Filtro anti-slosh forte para o tanque de combustível
    "water_temp":  0.20,  # Estabilidade de temperatura
    "oil_temp":    0.20,
    "voltage":     0.25,  # Filtro de ripple elétrico
    "speed":       0.75,  # Velocidade ágil
    "rpm":         1.00,  # Resposta instantânea de rotação
    "throttle":    0.60,  # Posição da borboleta ágil
    "load":        0.40,
    "map_kpa":     0.60,  # Pressão no coletor / Boost
    "intake_temp": 0.20,
    "maf":         0.40,
}


class OBDReader(threading.Thread):
    def __init__(self, store, port=None, baudrate=None):
        super().__init__(daemon=True)
        self.store = store
        self.port = port if port is not None else getattr(config, "OBD_PORT", "auto")
        self.baudrate = baudrate if baudrate is not None else getattr(config, "OBD_BAUD", 38400)
        self._stop = threading.Event()
        self._conn = None
        self._ema_values = {}

    def _apply_ema(self, key: str, raw_value) -> float:
        """Aplica Média Móvel Exponencial (EMA) para suavizar leituras e ruído."""
        if raw_value is None:
            return 0.0
        try:
            val = float(raw_value)
        except (ValueError, TypeError):
            return 0.0

        alpha = _EMA_ALPHAS.get(key, 1.0)
        if key not in self._ema_values:
            self._ema_values[key] = val
        else:
            self._ema_values[key] = (alpha * val) + ((1.0 - alpha) * self._ema_values[key])
        return self._ema_values[key]

    def _resolve_port(self):
        if self.port != "auto":
            return self.port
        port = find_obd_port()
        if port is None and not self._stop.is_set():
            app_log.warning("[OBD] no USB serial port found — retrying in 3 s")
        return port

    def run(self):
        while not self._stop.is_set():
            port = self._resolve_port()
            if port is None:
                if not self._stop.is_set():
                    self.store.set("connected", False)
                self._stop.wait(timeout=3)
                continue

            try:
                app_log.info(f"[OBD] connecting to {port} at {self.baudrate} baud")
                conn = Connection(port, baudrate=self.baudrate, auto_connect=True)
                if self._stop.is_set():
                    try:
                        conn.close()
                    except Exception:
                        pass
                    break
                self._conn = conn
                self.store.set("connected", True)
                self.store.set("obd_port", port)
                app_log.info(f"[OBD] connected successfully to {port}")

                cycle = 0
                while not self._stop.is_set():
                    # 1. Alta prioridade: RPM e Velocidade sempre; TPS e MAP se habilitados
                    cmds_to_query = [
                        ("rpm",   commands["ENGINE_SPEED"]),
                        ("speed", commands["VEHICLE_SPEED"]),
                    ]
                    if settings.enabled("tps_load"):
                        cmds_to_query.append(("throttle", commands["THROTTLE_POSITION"]))
                    if settings.enabled("turbo"):
                        cmds_to_query.append(("map_kpa", commands["INTAKE_MAP"]))

                    # 2. Média prioridade: a cada 8 ciclos (~1s), apenas sensores habilitados
                    if cycle % 8 == 0:
                        if settings.enabled("water_temp"):
                            cmds_to_query.append(("water_temp", commands["ENGINE_COOLANT_TEMP"]))
                        if settings.enabled("oil_temp"):
                            cmds_to_query.append(("oil_temp", commands["ENGINE_OIL_TEMP"]))
                        if settings.enabled("battery_voltage"):
                            cmds_to_query.append(("voltage", commands["VEHICLE_VOLTAGE"]))
                        if settings.enabled("tps_load"):
                            cmds_to_query.append(("load", commands["ENGINE_LOAD"]))
                        if settings.enabled("intake_temp"):
                            cmds_to_query.append(("intake_temp", commands["INTAKE_AIR_TEMP"]))
                        if settings.enabled("consumption"):
                            cmds_to_query.append(("maf", commands["MAF_RATE"]))

                    # 3. Baixa prioridade: Nível de combustível a cada 40 ciclos (~5s)
                    if cycle % 40 == 0 and settings.enabled("fuel_level"):
                        cmds_to_query.append(("fuel", commands["FUEL_LEVEL"]))

                    cycle = (cycle + 1) % 1000

                    for key, cmd in cmds_to_query:
                        if self._stop.is_set():
                            break
                        try:
                            resp = conn.query(cmd)
                            if self._stop.is_set():
                                break
                            raw_val = resp.value if resp is not None and resp.value is not None else 0
                            filtered_val = self._apply_ema(key, raw_val)
                            self.store.set(key, filtered_val)
                        except Exception as q_err:
                            if self._stop.is_set():
                                break
                            if not conn.is_connected():
                                raise q_err

                    poll_delay = getattr(config, "OBD_POLL_INTERVAL", 0.01)
                    if poll_delay > 0 and not self._stop.is_set():
                        self._stop.wait(timeout=poll_delay)
            except Exception as e:
                if self._stop.is_set():
                    break
                app_log.error(f"[OBD] connection error on {port}: {e}")
                self.store.set("connected", False)
                self._stop.wait(timeout=2)
                if not self._stop.is_set():
                    self.store.set("obd_port", "")
                if self._conn:
                    try:
                        self._conn.close()
                    except Exception:
                        pass
                    self._conn = None
                self._stop.wait(timeout=3)

    def stop(self):
        self._stop.set()
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
