import threading

from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from django_server import settings

from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.models import LogMessage


class DataRetentionScheduler:
    _instance = None
    _lock = threading.Lock()


    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance


    def __new__(cls, *args, **kwargs):
        return super(DataRetentionScheduler, cls).__new__(cls)


    def __init__(self):
        """
        Initialize the CameraScheduler
        """
        if not getattr(self, "_initialized", False):
            #
            self._scheduler = BackgroundScheduler()
            self.logger = get_logger()
            self._initialized = True


    def start(self):
        self._scheduler.add_job(cleanup_task, trigger='interval', hours=1, id="cleanup_task", args=[self.logger])
        self._scheduler.start()
        self.logger.debug("DataRetentionScheduler started")


    # how to run this?
    def stop(self):
        self._scheduler.shutdown()
        self.logger.debug("Cleanup task stopped")


def cleanup_task(logger):
    logger.debug("Cleanup task triggered")
    try:
        dt = datetime.now() - timedelta(days=settings.DB_LOG_RETENTION_DAYS)
        LogMessage.objects.filter(createdAt__lt=dt).delete()
        logger.debug("Cleanup task completed")
    except Exception as e:
        logger.error(f"Error during cleanpu task: {e}")
