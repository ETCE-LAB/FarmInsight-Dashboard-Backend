from influxdb_client import InfluxDBClient, Point, WritePrecision
from django.conf import settings
from influxdb_client.client.write_api import SYNCHRONOUS

from farminsight_dashboard_backend.exceptions import InfluxDBQueryException, InfluxDBNoConnectionException
from farminsight_dashboard_backend.models import FPF
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

            self.sync_fpf_buckets()
            self.log.info("InfluxDB database connection successful.")

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

    def close(self):
        """Close the InfluxDB client if it's open."""
        if self.client:
            self.client.close()
