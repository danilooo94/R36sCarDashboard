import argparse
import sys

import config
import settings


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Daily Cockpit OBD-II & Web Analytics")
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start directly in headless Web Analytics Server mode (no Pygame window)",
    )
    parser.add_argument(
        "--host",
        default=getattr(config, "WEB_HOST", "0.0.0.0"),
        help="Bind host for the Web Analytics HTTP server (default: config.WEB_HOST)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(getattr(config, "WEB_PORT", 8080)),
        help="TCP port for the Web Analytics HTTP server (default: config.WEB_PORT)",
    )
    return parser.parse_args(argv)


def _run_headless_web(host: str, port: int):
    from i18n import t
    from web.server import WebAnalyticsServer

    srv = WebAnalyticsServer(host=host, port=port, verbose=True)
    if not srv.start():
        print(f"[ERROR] Failed to start Web Analytics Server on {host}:{port} — {srv.last_error}", file=sys.stderr)
        sys.exit(1)

    print(t("web.cli_banner"))
    for u in srv.urls():
        print(f"  -> {u}")
    print(t("web.cli_stop_hint"))

    try:
        while srv.is_running:
            srv._thread.join(timeout=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        srv.stop()


def main(argv=None):
    args = _parse_args(argv)
    if args.web:
        _run_headless_web(args.host, args.port)
        return

    import app_log
    from i18n                import t
    from obd.store           import DataStore
    from obd.manager         import ReaderManager
    from obd.logger          import DataLogger
    from dashboard.multi_app import MultiPageApp
    from web.server          import WebAnalyticsServer

    if settings.enabled("data_logging"):
        app_log.install_excepthook()
        app_log.info(t("log.session_start", path=app_log.path))

    store          = DataStore()
    reader_manager = ReaderManager(store)
    reader_manager.start()

    # DataLogger dynamically checks settings.enabled("data_logging") at runtime
    logger = DataLogger(store)
    logger.start()
    if settings.enabled("data_logging"):
        app_log.info(t("log.recording_csv", path=config.LOG_DIR))

    web_server = WebAnalyticsServer(host=args.host, port=args.port, verbose=False)

    try:
        app = MultiPageApp(
            store,
            start_page=getattr(config, "START_PAGE", 0),
            web_server=web_server,
            reader_manager=reader_manager,
        )
        app.run()
    except Exception:
        if settings.enabled("data_logging"):
            app_log.exception(t("log.unhandled_loop_error"))
        raise
    finally:
        web_server.stop()
        reader_manager.stop(timeout=2)
        logger.stop()
        logger.join(timeout=2)
        if settings.enabled("data_logging"):
            app_log.info(t("log.session_end"))


if __name__ == "__main__":
    main()
