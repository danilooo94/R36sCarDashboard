import math
import random
import threading


class MockReader(threading.Thread):
    def __init__(self, store):
        super().__init__(daemon=True)
        self.store = store
        self._stop = threading.Event()

    def run(self):
        self.store.set("connected", True)
        self.store.set("obd_port", "MOCK-USB")
        t = 0.0
        while not self._stop.is_set():
            rpm      = 850 + abs(math.sin(t * 0.28)) * 5150 + random.uniform(-60, 60)
            speed    = max(0.0, (rpm - 750) / 37.0 + random.uniform(-1.5, 1.5))
            throttle = max(3.0, min(100.0, (rpm - 800) / 56.0 + random.uniform(-2, 2)))
            load     = max(10.0, min(100.0, throttle * 0.85 + 8.0))
            map_kpa  = 35.0 + (throttle / 100.0) * 155.0
            maf      = max(1.8, (rpm / 1000.0) * (load / 100.0) * 9.5)
            oil      = 92 + math.sin(t * 0.05) * 6 + random.uniform(-0.5, 0.5)
            water    = 88 + math.sin(t * 0.04) * 4 + random.uniform(-0.3, 0.3)
            iat      = 31 + math.sin(t * 0.03) * 3
            volt     = 13.9 + math.sin(t * 0.1) * 0.3 + random.uniform(-0.05, 0.05)
            fuel     = max(8.0, 78.0 - (t * 0.05) % 70.0)

            self.store.set("rpm",         rpm)
            self.store.set("speed",       speed)
            self.store.set("throttle",    throttle)
            self.store.set("load",        load)
            self.store.set("map_kpa",     map_kpa)
            self.store.set("maf",         maf)
            self.store.set("oil_temp",    oil)
            self.store.set("water_temp",  water)
            self.store.set("intake_temp", iat)
            self.store.set("voltage",     volt)
            self.store.set("fuel",        fuel)

            t += 0.1
            self._stop.wait(timeout=0.1)

    def stop(self):
        self._stop.set()
