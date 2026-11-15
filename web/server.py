"""Embedded HTTP server manager for Web Analytics & Daily Slice Exports."""
import json
import os
import re
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

import config
from i18n import get_lang
from web import analytics
from web.ui_template import render_index_html

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def get_local_ips() -> list:
    """Discover non-loopback IPv4 addresses on local interfaces (Wi-Fi, USB, LAN)."""
    ips = []

    # 1. Offline UDP route probe (does not transmit any packet)
    for probe_target in (("10.255.255.255", 1), ("192.168.1.1", 1)):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.settimeout(0.1)
            s.connect(probe_target)
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
        except Exception:
            pass
        finally:
            s.close()

    # 2. Hostname interface enumeration
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127.") and not ip.startswith("169.254.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass

    # 3. Linux `hostname -I` fallback (helpful on Armbian/ArkOS R36S)
    if not ips and os.name != "nt":
        try:
            with os.popen("hostname -I 2>/dev/null") as proc:
                for token in proc.read().split():
                    if "." in token and not token.startswith("127.") and token not in ips:
                        ips.append(token)
        except Exception:
            pass

    return ips


class _ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def _make_handler(manager):
    class AnalyticsRequestHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            if manager.verbose:
                super().log_message(fmt, *args)

        def _send_bytes(self, status: int, body: bytes, content_type: str, download_name: str = None):
            manager.increment_requests()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if download_name:
                self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, status: int, payload: dict):
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send_bytes(status, raw, "application/json; charset=utf-8")

        def do_GET(self):
            parsed = urlparse(self.path)
            path = unquote(parsed.path)
            query = parse_qs(parsed.query)

            try:
                if path in ("/", "/index.html"):
                    html = render_index_html(initial_lang=get_lang())
                    self._send_bytes(200, html, "text/html; charset=utf-8")
                    return

                if path == "/api/days":
                    self._send_json(200, {
                        "days":     analytics.list_daily_slices(),
                        "overview": analytics.get_storage_overview(),
                    })
                    return

                if path.startswith("/api/daily/"):
                    date_str = path[len("/api/daily/"):].strip("/")
                    if not _DATE_RE.match(date_str):
                        self._send_json(400, {"error": "Invalid date format (expected YYYY-MM-DD)"})
                        return
                    sess = (query.get("session") or [""])[0] or None
                    self._send_json(200, analytics.get_daily_slice(date_str, session_filter=sess))
                    return

                if path.startswith("/api/export/daily/"):
                    tail = path[len("/api/export/daily/"):]
                    for ext, ctype, builder, prefix in (
                        (".csv",  "text/csv; charset=utf-8",         analytics.export_daily_csv,  "daily_"),
                        (".json", "application/json; charset=utf-8", analytics.export_daily_json, "daily_report_"),
                        (".zip",  "application/zip",                 analytics.export_daily_zip,  "daily_package_"),
                    ):
                        if tail.endswith(ext):
                            date_str = tail[:-len(ext)]
                            if not _DATE_RE.match(date_str):
                                self._send_json(400, {"error": "Invalid date"})
                                return
                            data = builder(date_str)
                            self._send_bytes(200, data, ctype, download_name=f"{prefix}{date_str}{ext}")
                            return

                if path == "/api/export/all.zip":
                    data = analytics.export_all_zip()
                    self._send_bytes(200, data, "application/zip", download_name="car_telemetry_all.zip")
                    return

                if path.startswith("/api/download/session/"):
                    fname = path[len("/api/download/session/"):]
                    fpath = analytics.get_raw_session_path(fname)
                    if not fpath:
                        self._send_json(404, {"error": "Session file not found"})
                        return
                    with open(fpath, "rb") as fh:
                        raw = fh.read()
                    self._send_bytes(200, raw, "text/csv; charset=utf-8", download_name=fname)
                    return

                self._send_json(404, {"error": "Not found"})
            except BrokenPipeError:
                pass
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})

    return AnalyticsRequestHandler


class WebAnalyticsServer:
    """Thread-safe controller to start/stop the Web Analytics HTTP server."""

    def __init__(self, host: str = None, port: int = None, verbose: bool = False):
        self.host = host or getattr(config, "WEB_HOST", "0.0.0.0")
        self.port = int(port or getattr(config, "WEB_PORT", 8080))
        self.verbose = verbose

        self._lock = threading.Lock()
        self._httpd = None
        self._thread = None
        self._requests = 0
        self._last_error = ""

    def increment_requests(self):
        with self._lock:
            self._requests += 1

    @property
    def request_count(self) -> int:
        with self._lock:
            return self._requests

    @property
    def last_error(self) -> str:
        with self._lock:
            return self._last_error

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._httpd is not None and self._thread is not None and self._thread.is_alive()

    def urls(self) -> list:
        if self.host in ("127.0.0.1", "localhost"):
            return [f"http://localhost:{self.port}"]
        ips = get_local_ips()
        out = [f"http://{ip}:{self.port}" for ip in ips]
        local_url = f"http://localhost:{self.port}"
        if local_url not in out:
            out.append(local_url)
        return out

    def primary_url(self) -> str:
        return self.urls()[0]

    def start(self) -> bool:
        with self._lock:
            if self._httpd is not None and self._thread is not None and self._thread.is_alive():
                return True
            self._last_error = ""
            try:
                handler_cls = _make_handler(self)
                httpd = _ReusableThreadingHTTPServer((self.host, self.port), handler_cls)
                t = threading.Thread(target=httpd.serve_forever, name="WebAnalyticsHTTP", daemon=True)
                t.start()
                self._httpd = httpd
                self._thread = t
                return True
            except OSError as exc:
                self._last_error = str(exc)
                self._httpd = None
                self._thread = None
                return False

    def stop(self):
        with self._lock:
            httpd = self._httpd
            thread = self._thread
            self._httpd = None
            self._thread = None

        if httpd is not None:
            try:
                httpd.shutdown()
                httpd.server_close()
            except Exception:
                pass
        if thread is not None:
            thread.join(timeout=1.5)

    def toggle(self) -> bool:
        if self.is_running:
            self.stop()
            return False
        return self.start()

    def serve_blocking(self):
        """Run server in the foreground (used by `python main.py --web`)."""
        if not self.start():
            raise RuntimeError(f"Could not bind {self.host}:{self.port} — {self.last_error}")
        try:
            while self.is_running:
                self._thread.join(timeout=0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
