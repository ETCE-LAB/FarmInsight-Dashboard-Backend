import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import STATE_RUNNING
from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.services.fpf_health_services import check_all_fpf_health


class FPFHealthScheduler:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __new__(cls, *args, **kwargs):
        return super(FPFHealthScheduler, cls).__new__(cls)

    def __init__(self):
        if not getattr(self, "_initialized", False):
            self.scheduler = BackgroundScheduler()
            self.logger = get_logger()
            self._initialized = True

    def start(self):
        if self.scheduler.state == STATE_RUNNING:
            self.logger.debug("FPFHealthScheduler already running, skipping start.")
            return
        self.logger.info("Starting FPF Health Scheduler.")
        # Run every 5 minutes
        self.scheduler.add_job(self.run_check, 'interval', seconds=300)
        self.scheduler.start()

    def run_check(self):
        try:
            check_all_fpf_health()
        except Exception as e:
            self.logger.error(f"Error running FPF health check: {e}")
    # ---

    def stop(self):
        self.logger.info("Stopping FPF Health Scheduler.")
        self.scheduler.shutdown()