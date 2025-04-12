import threading

from datetime import datetime, timedelta

import requests
from requests import RequestException

from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone

from django_server import settings
from farminsight_dashboard_backend.services.data_retention_services import cleanup_task

from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.models import LogMessage

class WeatherForecastScheduler:
    _instance = None
    _lock = threading.Lock()


    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance


    def __new__(cls, *args, **kwargs):
        return super(WeatherForecastScheduler, cls).__new__(cls)


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
        self._scheduler.add_job(cleanup_task, trigger='', days=1, id="cleanup_task", args=[self.logger], next_run_time=timezone.now() + timedelta(seconds=1))
        self._scheduler.start()
        self.logger.debug("WeatherForecastScheduler started")


    # how to run this?
    def stop(self):
        self._scheduler.shutdown()
        self.logger.debug("WeatherForecastScheduler stopped")


    def fetch_weather_forecast(self):
        """
        Fetch a Weather Forecast .
        :return:
        """
        try:
            response = requests.get(snapshot_url, stream=True)
            if response.status_code == 200:
                print(response)

            else:
                raise ValueError(f"Failed to fetch snapshot. HTTP {response.status_code}")
        except Exception as e:
            print(f"Error fetching Weather Forecast")