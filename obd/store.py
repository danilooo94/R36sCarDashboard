import threading

class DataStore:
    _defaults = {
        "rpm":        0,
        "speed":      0,
        "oil_temp":   0,
        "water_temp": 0,
        "voltage":    0.0,
        "throttle":   0.0,
        "load":       0.0,
        "intake_temp": 0.0,
        "map_kpa":     0.0,
        "maf":         0.0,
        "fuel":        0.0,
        "connected":   False,
        "obd_port":    "",
    }

    def __init__(self):
        self._lock = threading.Lock()
        self._data = dict(self._defaults)

    def set(self, key, value):
        with self._lock:
            self._data[key] = value

    def snapshot(self):
        with self._lock:
            return dict(self._data)
