import threading

from datetime import datetime, timedelta

import requests
from requests import RequestException

from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone

from django_server import settings
from farminsight_dashboard_backend.services import get_location_by_id
from farminsight_dashboard_backend.services.data_retention_services import cleanup_task

from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.models import LogMessage, Location


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
        Initialize the WeatherForecastScheduler
        """
        if not getattr(self, "_initialized", False):
            #
            self._scheduler = BackgroundScheduler()
            self.logger = get_logger()
            self._initialized = True


    def start(self):
        self._add_all_forecast_jobs()
        self._scheduler.start()
        self.logger.debug("WeatherForecastScheduler started")



    def stop(self):
        self._scheduler.shutdown()
        self.logger.debug("WeatherForecastScheduler stopped")

    def add_forecast_job(self, location_id: str):
        """
        Add a get job for weather forecast.
        :param location_id: ID of the location
        """
        try:
            location = get_location_by_id(location_id)#
            if location.gatherForecasts:
                self._scheduler.add_job(
                    self.fetch_weather_forecast,
                    trigger='cron',
                    hour='6',
                    minute='0',
                    args=[location_id, location.longitude, location.latitude],
                    id=f"weather_forecast_{location_id}",
                    replace_existing=True,
                    next_run_time=timezone.now() + timedelta(seconds=1)
                )
                self.logger.debug(f"Weather forecast job added for location {location_id}")
        except Exception as e:
            self.logger.error(f"Error adding weather forecast job: {e}")

    def remove_forecast_job(self, location_id: str):
        """
        Remove a snapshot task for a specific camera.
        :param location_id:
        :return:
        """
        try:
            location = Location.objects.get(id=location_id, gatherForecasts=True)
            if location.gatherForecasts == False:
                self._scheduler.remove_job(job_id=f"weather_forecast_{location_id}")
                self.logger.debug(f"weather_forecast_{location.id} task deleted.")
        except Exception as e:
            self.logger.warning(f"weather_forecast with ID {location_id} does not exist or is not active.")

    def fetch_weather_forecast(self, locationId, longitude: str, latitude: str):
        """
        Fetch a Weather Forecast .
        :param locationId: Location object
        """
        try:
            request_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&daily=rain_sum,sunshine_duration,weather_code,wind_speed_10m_max,temperature_2m_min,temperature_2m_max,sunrise,sunset,precipitation_sum,precipitation_probability_max&timezone=Europe%2FBerlin&forecast_days=16"
            response = requests.get(request_url, stream=True)

            raw_data = response.json()['daily']
            data = [
                { key: raw_data[key][i] for key in raw_data }
                for i in range(len(raw_data['time']))
            ]
        except Exception as e:
            pass

        if response.status_code == 200:
            location = Location.objects.get(id=locationId)

            from farminsight_dashboard_backend.services import InfluxDBManager
            InfluxDBManager.get_instance().write_weather_forecast(location.organization.id, location.id, data)

        else:
            raise ValueError(f"Failed to fetch Weather Forecast. HTTP {response.status_code}")


    def _add_all_forecast_jobs(self):
        """
        Add all forecast jobs for all locations
        """
        locations = Location.objects.filter(gatherForecasts=True)
        for location in locations:
            if location.gatherForecasts:
                self.add_forecast_job(location.id)