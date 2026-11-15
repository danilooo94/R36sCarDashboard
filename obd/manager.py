"""Runtime manager for hot-swapping between MockReader and real OBDReader."""
import threading

import app_log
import settings
from obd.mock import MockReader
from obd.reader import OBDReader


class ReaderManager:
    """Manages the active telemetry reader thread and switches modes live without blocking UI."""

    def __init__(self, store):
        self.store = store
        self._lock = threading.Lock()
        self._reader = None
        self._is_mock = None

    @property
    def is_mock(self) -> bool:
        with self._lock:
            return bool(self._is_mock)

    def start(self):
        """Start the initial reader according to current settings."""
        self.sync()

    def sync(self) -> bool:
        """Ensure active reader matches `settings.enabled('mock_mode')`.

        Returns True if a live mode switch occurred after initial startup.
        """
        want_mock = settings.enabled("mock_mode")
        with self._lock:
            if self._reader is not None and self._is_mock == want_mock:
                return False

            old_reader = self._reader
            was_initialized = self._is_mock is not None
            self._is_mock = want_mock

            if old_reader is not None:
                # Signal stop immediately so old_reader never writes stale values to store
                old_reader._stop.set()
                threading.Thread(
                    target=self._cleanup_reader,
                    args=(old_reader,),
                    daemon=True,
                ).start()

            self.store.reset()
            new_reader = MockReader(self.store) if want_mock else OBDReader(self.store)
            self._reader = new_reader
            new_reader.start()

        mode_name = "MOCK simulation" if want_mock else "REAL OBD-II"
        app_log.info(f"[MODE] Active reader set to {mode_name}")
        return was_initialized

    @staticmethod
    def _cleanup_reader(reader):
        try:
            reader.stop()
            reader.join(timeout=2.0)
        except Exception:
            pass

    def stop(self, timeout: float = 2.0):
        with self._lock:
            reader = self._reader
            self._reader = None
        if reader is not None:
            reader.stop()
            reader.join(timeout=timeout)
