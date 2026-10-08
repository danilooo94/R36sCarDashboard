import config
from obd.store  import DataStore
from obd.reader import OBDReader
from obd.mock   import MockReader
from obd.logger import DataLogger
from dashboard.multi_app import MultiPageApp

def main():
    store  = DataStore()
    reader = MockReader(store) if config.MOCK_MODE else OBDReader(store)
    reader.start()

    logger = None
    if config.LOG_ENABLED:
        logger = DataLogger(store)
        logger.start()
        print(f"Gravando em: {logger.path}")

    try:
        app = MultiPageApp(store, start_page=getattr(config, "START_PAGE", 0))
        app.run()
    finally:
        reader.stop()
        reader.join(timeout=2)
        if logger:
            logger.stop()
            logger.join(timeout=2)

if __name__ == "__main__":
    main()
