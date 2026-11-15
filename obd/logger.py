import csv
import os
import threading
from datetime import datetime

import config
import settings

_FIELDS = [
    "timestamp",
    "rpm",
    "speed_kmh",
    "oil_temp_c",
    "water_temp_c",
    "voltage_v",
    "throttle_pct",
    "load_pct",
    "intake_temp_c",
    "map_kpa",
    "maf_gs",
    "fuel_pct",
    "consumption_kml",
]

_STORE_KEYS = {
    "rpm":           "rpm",
    "speed_kmh":     "speed",
    "oil_temp_c":    "oil_temp",
    "water_temp_c":  "water_temp",
    "voltage_v":     "voltage",
    "throttle_pct":  "throttle",
    "load_pct":      "load",
    "intake_temp_c": "intake_temp",
    "map_kpa":       "map_kpa",
    "maf_gs":        "maf",
    "fuel_pct":      "fuel",
}


def _calc_instant_kml(speed_kmh: float, maf_gs: float) -> float:
    if speed_kmh < 3.0 or maf_gs <= 0.0:
        return 0.0
    afr = float(getattr(config, "FUEL_AFR", 14.7))
    density = float(getattr(config, "FUEL_DENSITY_G_L", 745.0))
    liters_per_hour = maf_gs * 3600.0 / (afr * density)
    return round(speed_kmh / liters_per_hour, 2) if liters_per_hour > 0 else 0.0


class DataLogger(threading.Thread):
    """Background CSV logger supporting live on/off toggling and daily file rollover."""

    def __init__(self, store):
        super().__init__(daemon=True)
        self.store = store
        self._stop = threading.Event()
        self._path = None
        self._file = None
        self._writer = None
        self._active_date = None
        self._active_mock = None

    def _open_new_session(self, now: datetime):
        self._close_session()
        os.makedirs(config.LOG_DIR, exist_ok=True)
        filename = now.strftime("session_%Y-%m-%d_%H-%M-%S.csv")
        self._path = os.path.join(config.LOG_DIR, filename)
        self._file = open(self._path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=_FIELDS)
        self._writer.writeheader()
        self._file.flush()
        self._active_date = now.strftime("%Y-%m-%d")

    def _close_session(self):
        if self._file is not None:
            try:
                self._file.flush()
                self._file.close()
            except Exception:
                pass
        self._file = None
        self._writer = None
        self._active_date = None
        self._active_mock = None

    def run(self):
        try:
            while not self._stop.is_set():
                self._stop.wait(timeout=config.LOG_INTERVAL)
                if self._stop.is_set():
                    break

                if not settings.enabled("data_logging"):
                    if self._file is not None:
                        self._close_session()
                    continue

                data = self.store.snapshot()
                if not data.get("connected", False):
                    continue

                now = datetime.now()
                today = now.strftime("%Y-%m-%d")
                is_mock = settings.enabled("mock_mode")
                if self._file is None or self._active_date != today or self._active_mock != is_mock:
                    self._open_new_session(now)
                    self._active_mock = is_mock

                row = {"timestamp": now.isoformat(timespec="seconds")}
                for col, key in _STORE_KEYS.items():
                    val = data.get(key, 0) or 0
                    row[col] = round(val, 2) if isinstance(val, float) else val

                speed = float(data.get("speed", 0) or 0)
                maf = float(data.get("maf", 0) or 0)
                row["consumption_kml"] = _calc_instant_kml(speed, maf)

                self._writer.writerow(row)
                self._file.flush()
        finally:
            self._close_session()

    def stop(self):
        self._stop.set()

    @property
    def path(self):
        return self._path
