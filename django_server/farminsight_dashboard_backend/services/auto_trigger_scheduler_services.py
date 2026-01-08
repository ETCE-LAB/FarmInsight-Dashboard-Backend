import threading
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import STATE_RUNNING
from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone

from farminsight_dashboard_backend.services import process_action_queue, create_auto_triggered_actions_in_queue
from farminsight_dashboard_backend.utils import get_logger


class AutoTriggerScheduler:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __new__(cls, *args, **kwargs):
        return super(AutoTriggerScheduler, cls).__new__(cls)

    def __init__(self):
        if not getattr(self, "_initialized", False):
            self._scheduler = BackgroundScheduler()
            self.log = get_logger()
            self._initialized = True

    def start(self, interval_seconds: int = 60):
        if self._scheduler.state == STATE_RUNNING:
            self.log.debug("AutoTriggerScheduler already running, skipping start.")
            return
        self._scheduler.add_job(
            create_auto_triggered_actions_in_queue,
            trigger=IntervalTrigger(seconds=interval_seconds),
            id="auto_trigger_processing",
            replace_existing=True,
            next_run_time=timezone.now() + timedelta(seconds=1)
        )
        self._scheduler.start()
        self.log.info(f"AutoTriggerScheduler started with interval: {interval_seconds} seconds.")
