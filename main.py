import config
import app_log
from obd.store           import DataStore
from obd.reader          import OBDReader
from obd.mock            import MockReader
from obd.logger          import DataLogger
from dashboard.multi_app import MultiPageApp


def main():
    if config.LOG_ENABLED:
        app_log.install_excepthook()
        app_log.info(f"=== sessão iniciada — log de erros: {app_log.path} ===")

    store  = DataStore()
    reader = MockReader(store) if config.MOCK_MODE else OBDReader(store)
    reader.start()

    logger = None
    if config.LOG_ENABLED:
        logger = DataLogger(store)
        logger.start()
        app_log.info(f"Gravando dados em: {logger.path}")

    try:
        app = MultiPageApp(store, start_page=getattr(config, "START_PAGE", 0))
        app.run()
    except Exception:
        if config.LOG_ENABLED:
            app_log.exception("Erro não tratado no loop principal")
        raise
    finally:
        reader.stop()
        reader.join(timeout=2)
        if logger:
            logger.stop()
            logger.join(timeout=2)
        if config.LOG_ENABLED:
            app_log.info("=== sessão encerrada ===")


if __name__ == "__main__":
    main()
