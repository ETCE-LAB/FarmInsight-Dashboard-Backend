import json
from dataclasses import dataclass
from datetime import datetime
from typing import List

from influxdb_client import InfluxDBClient, Point, WritePrecision
from django.conf import settings
from influxdb_client.client.write_api import SYNCHRONOUS
from django.utils import timezone

from farminsight_dashboard_backend.exceptions import InfluxDBQueryException, InfluxDBNoConnectionException
from farminsight_dashboard_backend.exceptions.custom_exception_handler import InfluxDBWriteException
from farminsight_dashboard_backend.models import FPF, Organization
import requests
import logging
import threading
import time

class InfluxDBManager:
    """
    InfluxDBManager to manage all interactions with the influx database, implemented as a Singleton.
    RETRY_TIMEOUT in seconds.
    """
    _instance = None
    _lock = threading.Lock()

    RETRY_TIMEOUT = 10

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __new__(cls, *args, **kwargs):
        return super(InfluxDBManager, cls).__new__(cls)

    def __init__(self):
        """
        Initialize the InfluxDB manager with settings and a logger.
        """
        if not getattr(self, "_initialized", False):
            self.influxdb_settings = getattr(settings, 'INFLUXDB_CLIENT_SETTINGS', {})
            self.client = None
            self.log = logging.getLogger("farminsight_dashboard_backend")
            self._last_connection_attempt = 0
            self._initialized = True

    def _retry_connection(method):
        """Decorator to ensure a valid connection before executing a method."""
        def wrapper(self, *args, **kwargs):
            if not self.client:
                now = time.time()
                if now - self._last_connection_attempt > self.RETRY_TIMEOUT:
                    self._last_connection_attempt = now
                    self.initialize_connection()
                else:
                    self.log.warning("Skipping connection retry due to recent failed attempt.")
            if not self.client:
                raise InfluxDBNoConnectionException("No valid InfluxDB connection available.")
            return method(self, *args, **kwargs)

        return wrapper

    def initialize_connection(self):
        """
        Attempt to connect to InfluxDB and synchronize FPF buckets.
        """
        if not self.influxdb_settings:
            self.log.warning("InfluxDB settings not found. Skipping InfluxDB setup.")
            return

        try:
            self.client = InfluxDBClient(
                url=self.influxdb_settings['url'],
                token=self.influxdb_settings['token'],
                org=self.influxdb_settings['org']
            )

            if not self.client.ping():
                raise ConnectionError("InfluxDB is not reachable.")
            self.sync_buckets()
            self.log.info("Successfully connected to InfluxDB and synchronized buckets.")


        except (requests.exceptions.RequestException, ConnectionError) as e:
            self.log.warning(f"InfluxDB connection failed: {e} Proceeding without InfluxDB.")
            self.client = None

    def sync_fpf_buckets(self):
        """
        Ensure each FPF in SQLite has a corresponding bucket in InfluxDB.
        """
        try:
            if self.client:
                bucket_api = self.client.buckets_api()
                fpf_objects = FPF.objects.all()

                if not fpf_objects.exists():
                    self.log.warning("No FPFs found in the database.")
                    return

                for fpf in fpf_objects:
                    bucket_name = str(fpf.id)
                    if not bucket_api.find_bucket_by_name(bucket_name):
                        self.log.info(f"Creating new bucket: {bucket_name}")
                        bucket_api.create_bucket(bucket_name=bucket_name, org=self.influxdb_settings['org'])

        except Exception as e:
            self.log.error(f"Failed to sync FPF buckets with InfluxDB: {e}")

    def sync_organization_buckets(self):
        """
        Ensure each Organization in SQLite has a corresponding bucket in InfluxDB.
        """
        try:
            if self.client:
                bucket_api = self.client.buckets_api()
                orga_objects = Organization.objects.all()

                if not orga_objects.exists():
                    self.log.warning("No Organizations found in the database.")
                    return

                for orga in orga_objects:
                    bucket_name = str(orga.id)
                    if not bucket_api.find_bucket_by_name(bucket_name):
                        self.log.info(f"Creating new bucket: {bucket_name}")
                        bucket_api.create_bucket(bucket_name=bucket_name, org=self.influxdb_settings['org'])

        except Exception as e:
            self.log.error(f"Failed to sync Organization buckets with InfluxDB: {e}")

    def sync_buckets(self):
        """
        Synchronize all buckets in InfluxDB.
        """
        self.sync_organization_buckets()
        self.sync_fpf_buckets()

    @_retry_connection
    def fetch_sensor_measurements(self, fpf_id: str, sensor_ids: list, from_date: str, to_date: str) -> dict:
        """
        Queries InfluxDB for measurements within the given date range for multiple sensors.
        :param fpf_id: The ID of the FPF (used as the bucket name in InfluxDB).
        :param sensor_ids: List of sensor IDs to query data for.
        :param from_date: Start date in ISO 8601 format.
        :param to_date: End date in ISO 8601 format.
        :return: Dictionary with sensor IDs as keys, each containing a list of measurements.
        """
        try:
            query_api = self.client.query_api()

            # Build the filter part of the query for multiple sensors
            sensor_filter = " or ".join([f'r["sensorId"] == "{sensor_id}"' for sensor_id in sensor_ids])

            query = (
                f'from(bucket: "{fpf_id}") '
                f'|> range(start: {from_date}, stop: {to_date}) '
                f'|> filter(fn: (r) => r["_measurement"] == "SensorData" and ({sensor_filter}))'
            )

            result = query_api.query(org=self.influxdb_settings['org'], query=query)

            # Process and organize results by sensor ID
            measurements = {sensor_id: [] for sensor_id in sensor_ids}
            for table in result:
                for record in table.records:
                    sensor_id = record.values["sensorId"]
                    measurements[sensor_id].append({
                        "measuredAt": record.get_time().isoformat(),
                        "value": record.get_value()
                    })

        except requests.exceptions.ConnectionError as e:
            raise InfluxDBNoConnectionException("Unable to connect to InfluxDB.")

        except Exception as e:
            self.client = None
            raise InfluxDBQueryException(str(e))

        return measurements

    @_retry_connection
    def fetch_latest_sensor_measurements(self, fpf_id: str, sensor_ids: list) -> dict:
        """
        Queries InfluxDB for the latest measurement for each sensor.
        :param fpf_id: The ID of the FPF (used as the bucket name in InfluxDB).
        :param sensor_ids: List of sensor IDs to query data for.
        :return: Dictionary with sensor IDs as keys, each containing the latest measurement.
        """
        try:
            query_api = self.client.query_api()

            # Build the filter part of the query for multiple sensors
            sensor_filter = " or ".join([f'r["sensorId"] == "{sensor_id}"' for sensor_id in sensor_ids])

            query = (
                f'from(bucket: "{fpf_id}") '
                f'|> range(start: -1y) '  # Arbitrary long range to include all data
                f'|> filter(fn: (r) => r["_measurement"] == "SensorData" and ({sensor_filter})) '
                f'|> sort(columns: ["_time"], desc: true) '
                f'|> unique(column: "sensorId") '
            )
            result = query_api.query(org=self.influxdb_settings['org'], query=query)

            # Process and organize results by sensor ID
            latest_measurements = {}
            for table in result:
                for record in table.records:
                    sensor_id = record.values["sensorId"]
                    latest_measurements[sensor_id] = {
                        "measuredAt": record.get_time().isoformat(),
                        "value": record.get_value()
                    }

        except requests.exceptions.ConnectionError as e:
            self.client = None
            self.log.error(f"Failed to connect to InfluxDB: {e}")
            raise InfluxDBNoConnectionException("Unable to connect to InfluxDB.")

        except Exception as e:
            raise InfluxDBQueryException(str(e))

        return latest_measurements


    @_retry_connection
    def write_sensor_measurements(self, fpf_id: str, sensor_id: str, measurements):
        """
        Writes measurements for a given sensor to InfluxDB.
        :param fpf_id: The ID of the FPF (used as the bucket name in InfluxDB).
        """
        try:
            write_api = self.client.write_api(write_options=SYNCHRONOUS)

            points = []
            for measurement in measurements:
                point = (
                    Point("SensorData")
                    .tag("sensorId", str(sensor_id))
                    .field("value", float(measurement['value']))
                    .time(measurement['measuredAt'], WritePrecision.NS)
                )
                points.append(point)
            write_api.write(bucket=fpf_id, record=points)


        except Exception as e:
            self.client = None
            raise InfluxDBQueryException(str(e))

    @_retry_connection
    def fetch_last_weather_forcast(self, orga_id: str, location_id: str):
        """
        :param fpf_id: The ID of the FPF (used as the bucket name in InfluxDB).
        :param sensor_ids: List of sensor IDs to query data for.
        :return: Dictionary with sensor IDs as keys, each containing the latest measurement.
        """

        try:
            query_api = self.client.query_api()

            # Construct the query
            query = (
                f'from(bucket: "{orga_id}") '
                f'|> range(start: -1y) '  # Arbitrary long range to include all data
                f'|> filter(fn: (r) => r["_measurement"] == "WeatherForecast" and r["locationId"] == "{str(location_id)}") '
                f'|> sort(columns: ["_time"], desc: true) '
                f'|> limit(n: 3) '
            )

            # Execute the query
            result = query_api.query(org=self.influxdb_settings['org'], query=query)

            forecasts = []

            # Loop through the results (tables and records)
            for table in result:
                for record in table.records:
                    values = record.values

                    #One Field to rule them all
                    data = json.loads(values.get('_value'))

                    forecast_date = datetime.strptime(data["ForecastDate"], "%Y-%m-%d")

                    sunrise_date = datetime.strptime(data["sunrise"], "%Y-%m-%dT%H:%M")
                    sunset_date = datetime.strptime(data["sunset"], "%Y-%m-%dT%H:%M")


                    fetch_date = values.get('_time')
                    if not isinstance(fetch_date, datetime):
                        try:
                            fetch_date = datetime.fromisoformat(fetch_date)
                        except Exception as e:
                            print(f"Fehler beim Parsen von fetchDate: {e}")
                            fetch_date = datetime.now()

                    wf = dict(
                        fetchDate=fetch_date,
                        forecastDate=forecast_date,
                        rainMM=str(data.get("rain_sum", 0)),
                        sunshineDurationSeconds=str(data.get("sunshine_duration", 0)),
                        weatherCode=str(data.get("weather_code", "")),
                        windSpeedMax=str(data.get("wind_speed_max", 0)),
                        temperatureMinC=str(data.get("temperature_min", 0)),
                        temperatureMaxC=str(data.get("temperature_max", 0)),
                        sunrise=sunrise_date,
                        sunset=sunset_date,
                        precipitationMM=str(data.get("precipitation_sum", 0)),
                        precipitationProbability=str(data.get("precipitation_probability_max", 0)),
                        locationId=values.get('locationId', "")
                    )
                    forecasts.append(wf)

        except requests.exceptions.ConnectionError as e:
            self.client = None
            self.log.error(f"Failed to connect to InfluxDB: {e}")
            raise InfluxDBNoConnectionException("Unable to connect to InfluxDB.")

        except Exception as e:
            raise InfluxDBQueryException(str(e))

        return forecasts

    @_retry_connection
    def write_weather_forecast(self, orga_id: str, location_id: str, weather_forecasts):
        """
        Writes Weather Forecast for a given Location (Orga) to InfluxDB.
        :param orga_id: The ID of the Organization (used as the bucket name in InfluxDB).
        :param location_id: The ID of the location (UUID).
        :param weather_forecasts: List of weather forecast dictionaries.
        """
        try:
            write_api = self.client.write_api(write_options=SYNCHRONOUS)

            points = []
            for forecast in weather_forecasts:
                forecast_dict = {
                    "ForecastDate": str(forecast['time']),
                    "rain_sum": float(forecast['rain_sum']),
                    "sunshine_duration": float(forecast['sunshine_duration']),
                    "weather_code": int(forecast['weather_code']),
                    "wind_speed_max": float(forecast['wind_speed_10m_max']),
                    "temperature_min": float(forecast['temperature_2m_min']),
                    "temperature_max": float(forecast['temperature_2m_max']),
                    "sunrise": str(forecast['sunrise']),
                    "sunset": str(forecast['sunset']),
                    "precipitation_sum": float(forecast['precipitation_sum']),
                    "precipitation_probability_max": int(forecast['precipitation_probability_max'])
                }


                forecast_json = json.dumps(forecast_dict)

                point = (
                    Point("WeatherForecast")
                    .tag("locationId", str(location_id))
                    .field("forecast", forecast_json)
                    .time(timezone.now().isoformat(), WritePrecision.NS)
                )
                #For some reason the write_api.write() method does not accept a list of points
                write_api.write(bucket=str(orga_id), record=point)


        except Exception as e:
            self.client = None
            raise InfluxDBWriteException(str(e))


    def close(self):
        """Close the InfluxDB client if it's open."""
        if self.client:
            self.client.close()