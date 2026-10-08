import glob
import sys
import threading
import time
import serial
import serial.tools.list_ports
import config
import app_log
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
    "BLUETOOTH",
    "STANDARD SERIAL",
)


def find_obd_port():
    """Scan serial ports and return the first one that looks like an OBD/ELM327 adapter.

    Matching order:
      1. Exact VID/PID from known adapters list
      2. Description or hardware ID containing OBD/serial keywords
      3. Linux fallback: first ttyUSB*, ttyACM*, or rfcomm* device
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

    # Pass 3 — Linux fallback: ttyUSB*, ttyACM*, rfcomm*
    if sys.platform.startswith("linux"):
        candidates = sorted(
            glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*") + glob.glob("/dev/rfcomm*")
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
    ("rpm",   commands["ENGINE_SPEED"]),
    ("speed", commands["VEHICLE_SPEED"]),
]

_MEDIUM_COMMANDS = [
    ("water_temp", commands["ENGINE_COOLANT_TEMP"]),
    ("oil_temp",   commands["ENGINE_OIL_TEMP"]),
    ("voltage",    commands["VEHICLE_VOLTAGE"]),
]

_SLOW_COMMANDS = [
    ("fuel", commands["FUEL_LEVEL"]),
]

# Pesos de Média Móvel Exponencial (EMA): val = alpha * novo + (1 - alpha) * anterior
# alpha menor = mais filtrado contra ruídos e chacoalho de boia
_EMA_ALPHAS = {
    "fuel":       0.03,  # Filtro anti-slosh forte para o tanque de combustível
    "water_temp": 0.20,  # Estabilidade de temperatura
    "oil_temp":   0.20,
    "voltage":    0.25,  # Filtro de ripple elétrico
    "speed":      0.75,  # Velocidade ágil
    "rpm":        1.00,  # Resposta instantânea de rotação
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
        conn_type = getattr(config, "OBD_CONNECTION", "serial").lower()
        
        if conn_type == "wifi":
            host = getattr(config, "OBD_HOST", "192.168.0.10")
            port = getattr(config, "OBD_WIFI_PORT", 35000)
            return (host, port)
            
        elif conn_type == "bluetooth":
            mac = getattr(config, "OBD_MAC", None)
            if mac:
                return mac
            app_log.warning("[OBD] OBD_MAC não configurado para conexão bluetooth")
            return None
            
        else:
            # Padrão: "serial" (inclui Bluetooth via /dev/rfcomm0)
            if self.port != "auto":
                return self.port
            port = find_obd_port()
            if port is None:
                app_log.warning("[OBD] no serial port found — retrying in 3 s")
            return port

    def run(self):
        while not self._stop.is_set():
            port = self._resolve_port()
            if port is None:
                self.store.set("connected", False)
                self._stop.wait(timeout=3)
                continue

            try:
                app_log.info(f"[OBD] connecting to {port} at {self.baudrate} baud")
                conn = Connection(port, baudrate=self.baudrate, auto_connect=True)
                self._conn = conn
                self.store.set("connected", True)
                self.store.set("obd_port", port)
                self.store.set("esp32_port", port)
                app_log.info(f"[OBD] connected successfully to {port}")

                cycle = 0
                while not self._stop.is_set():
                    # 1. Alta prioridade: RPM e Velocidade consultados em TODOS os ciclos
                    cmds_to_query = list(_FAST_COMMANDS)

                    # 2. Média prioridade: Temperatura e Bateria a cada 8 ciclos (~1s)
                    if cycle % 8 == 0:
                        cmds_to_query.extend(_MEDIUM_COMMANDS)

                    # 3. Baixa prioridade: Nível de combustível a cada 40 ciclos (~5s)
                    if cycle % 40 == 0:
                        cmds_to_query.extend(_SLOW_COMMANDS)

                    cycle = (cycle + 1) % 1000

                    for key, cmd in cmds_to_query:
                        try:
                            resp = conn.query(cmd)
                            raw_val = resp.value if resp is not None and resp.value is not None else 0
                            filtered_val = self._apply_ema(key, raw_val)
                            self.store.set(key, filtered_val)
                        except Exception as q_err:
                            if not conn.is_connected():
                                raise q_err

                    poll_delay = getattr(config, "OBD_POLL_INTERVAL", 0.01)
                    if poll_delay > 0:
                        self._stop.wait(timeout=poll_delay)
            except Exception as e:
                app_log.error(f"[OBD] connection error on {port}: {e}")
                self.store.set("connected", False)
                self._stop.wait(timeout=2)
                self.store.set("obd_port", "")
                self.store.set("esp32_port", "")
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
