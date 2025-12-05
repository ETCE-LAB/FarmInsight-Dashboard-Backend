import json
import requests
import logging
import threading
import time
from uuid import UUID
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client import InfluxDBClient, Point, WritePrecision

from farminsight_dashboard_backend.exceptions import InfluxDBQueryException, InfluxDBNoConnectionException, InfluxDBWriteException
from farminsight_dashboard_backend.models import FPF, Organization
from farminsight_dashboard_backend.utils import _validate_forecasts_structure


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
                f'|> range(start: -24h) '  # Arbitrary long range to include all data
                f'|> filter(fn: (r) => r["_measurement"] == "WeatherForecast" and r["locationId"] == "{str(location_id)}") '
                f'|> sort(columns: ["_time"], desc: false) '
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

            forecasts.sort(key=lambda x: x['forecastDate'], reverse=True)

        except requests.exceptions.ConnectionError as e:
            self.client = None
            self.log.error(f"Failed to connect to InfluxDB: {e}")
            raise InfluxDBNoConnectionException("Unable to connect to InfluxDB.")

        except Exception as e:
            raise InfluxDBQueryException(str(e))

        return forecasts

    def fetch_latest_weather_forecast(self, organization_id: str, location_id: str) -> dict:
        """
        Fetch the latest weather forecast for today for a given location.
        Returns a dictionary with weather data including sunshine_duration and wind_speed.
        
        :param organization_id: The organization ID (used as bucket name)
        :param location_id: The location ID
        :return: Dictionary with weather forecast data for today, or None if not available
        """
        try:
            forecasts = self.fetch_last_weather_forcast(organization_id, location_id)
            if not forecasts:
                return None
            
            # Find today's forecast
            today = datetime.now().date()
            for forecast in forecasts:
                forecast_date = forecast.get('forecastDate')
                if forecast_date and forecast_date.date() == today:
                    return {
                        'sunshine_duration': float(forecast.get('sunshineDurationSeconds', 0)),
                        'wind_speed_10m_max': float(forecast.get('windSpeedMax', 0)),
                        'rain_sum': float(forecast.get('rainMM', 0)),
                        'temperature_min': float(forecast.get('temperatureMinC', 0)),
                        'temperature_max': float(forecast.get('temperatureMaxC', 0)),
                        'precipitation_sum': float(forecast.get('precipitationMM', 0)),
                        'precipitation_probability_max': float(forecast.get('precipitationProbability', 0)),
                        'weather_code': forecast.get('weatherCode', ''),
                    }
            
            # If no today forecast, return the first (most recent) forecast
            if forecasts:
                forecast = forecasts[0]
                return {
                    'sunshine_duration': float(forecast.get('sunshineDurationSeconds', 0)),
                    'wind_speed_10m_max': float(forecast.get('windSpeedMax', 0)),
                    'rain_sum': float(forecast.get('rainMM', 0)),
                    'temperature_min': float(forecast.get('temperatureMinC', 0)),
                    'temperature_max': float(forecast.get('temperatureMaxC', 0)),
                    'precipitation_sum': float(forecast.get('precipitationMM', 0)),
                    'precipitation_probability_max': float(forecast.get('precipitationProbability', 0)),
                    'weather_code': forecast.get('weatherCode', ''),
                }
            
            return None
        except Exception as e:
            self.log.debug(f"Error fetching latest weather forecast: {e}")
            return None

    @_retry_connection
    def fetch_all_weather_forecasts(self, orga_id: str, location_id: str, from_date: str, to_date: str):
        try:
            query_api = self.client.query_api()

            # Construct the query
            query = (
                f'from(bucket: "{orga_id}") '
                f'|> range(start: {from_date}, stop: {to_date}) '
                f'|> filter(fn: (r) => r["_measurement"] == "WeatherForecast" and r["locationId"] == "{str(location_id)}") '
                f'|> sort(columns: ["_time"], desc: false) '
            )

            # Execute the query
            result = query_api.query(org=self.influxdb_settings['org'], query=query)

            forecasts = []

            # Loop through the results (tables and records)
            for table in result:
                for record in table.records:
                    values = record.values

                    # One Field to rule them all
                    data = json.loads(values.get('_value'))

                    forecast_date = datetime.strptime(data["ForecastDate"], "%Y-%m-%d")

                    sunrise_date = datetime.strptime(data["sunrise"], "%Y-%m-%dT%H:%M")
                    sunset_date = datetime.strptime(data["sunset"], "%Y-%m-%dT%H:%M")

                    fetch_date = values.get('_time')
                    if not isinstance(fetch_date, datetime):
                        try:
                            fetch_date = datetime.fromisoformat(fetch_date)
                        except Exception as e:
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

            forecasts.sort(key=lambda x: x['forecastDate'], reverse=True)

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
                    "rain_sum": float(forecast['rain_sum'] or 0.0),
                    "sunshine_duration": float(forecast['sunshine_duration'] or 0.0),
                    "weather_code": int(forecast['weather_code'] or 0),
                    "wind_speed_max": float(forecast['wind_speed_10m_max']),
                    "temperature_min": float(forecast['temperature_2m_min']),
                    "temperature_max": float(forecast['temperature_2m_max']),
                    "sunrise": str(forecast['sunrise']),
                    "sunset": str(forecast['sunset']),
                    "precipitation_sum": float(forecast['precipitation_sum'] or 0),
                    "precipitation_probability_max": int(forecast['precipitation_probability_max'] or 0)
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


    @_retry_connection
    def write_model_forecast(self, fpf_id: str, model_id: str, model_name: str, forecasts: dict):
        """
        Writes model forecasts (including actions) for a given FPF into InfluxDB.
        Each forecast is stored as a JSON blob for flexibility.
        :param fpf_id: FPF UUID (bucket name)
        :param model_id: ID of the model that generated the forecasts
        :param model_name: Display name of the model
        :param forecasts: dict with structure:
            {
              "forecasts": [ ... ],
              "actions": [ ... ]
            }
        """
        # Validate before writing
        is_valid, error_msg = _validate_forecasts_structure(forecasts)
        if not is_valid:
            self.log.error(
                f"Forecast validation failed for model '{model_name}' (ID {model_id}): {error_msg}"
            )
            return  # do NOT write invalid data

        try:
            write_api = self.client.write_api(write_options=SYNCHRONOUS)

            # Use the same "ModelForecast" measurement for all models
            timestamp = timezone.now().isoformat()
            forecast_json = json.dumps(forecasts)

            point = (
                Point("ModelForecast")
                .tag("modelId", str(model_id))
                .tag("modelName", str(model_name))
                .field("forecastData", forecast_json)
                .time(timestamp, WritePrecision.NS)
            )

            write_api.write(bucket=str(fpf_id), record=point)
            self.log.info(f"Wrote model forecast for model '{model_name}' into bucket {fpf_id}.")

        except Exception as e:
            self.client = None
            raise InfluxDBWriteException(f"Failed to write model forecast: {e}")


    @_retry_connection
    def fetch_latest_model_forecast(self, fpf_id: str, model_id: str, hours: int = 24) -> list[dict]:
        """
        Fetches the most recent model forecast for the given FPF and model.
        :param fpf_id: The ID of the FPF (bucket name)
        :param model_id: The ID of the model (tag in Influx)
        :param hours: Time range to look back (default: 24h)
        :return: List of parsed forecast dict (each item has 'timestamp', 'modelName', 'forecasts', 'actions')
        """
        from farminsight_dashboard_backend.services import get_model_by_id
        try:
            query_api = self.client.query_api()

            query = (
                f'from(bucket: "{str(UUID(fpf_id))}") '
                f'|> range(start: -{hours}h) '
                f'|> filter(fn: (r) => r["_measurement"] == "ModelForecast" and r["modelId"] == "{str(model_id)}") '
                f'|> sort(columns: ["_time"], desc: true) '
                f'|> limit(n: 1)'
            )

            result = query_api.query(org=self.influxdb_settings['org'], query=query)

            for table in result:
                for record in table.records:
                    try:
                        forecast_data = json.loads(record.get_value())
                    except Exception:
                        forecast_data = {}

                    return {
                        "timestamp": record.get_time().isoformat(),
                        "modelId": record.values.get("modelId"),
                        "modelName": get_model_by_id(model_id).name,
                        "data": forecast_data
                    }

            # No records found
            return None

        except Exception as e:
            self.client = None
            raise InfluxDBQueryException(f"Failed to fetch model forecast: {e}")


    @_retry_connection
    def write_energy_consumption(self, fpf_id: str, consumer_id: str, watts: float, timestamp: str = None):
        """
        Writes energy consumption data for a given consumer to InfluxDB.
        :param fpf_id: The ID of the FPF (used as the bucket name in InfluxDB).
        :param consumer_id: The ID of the energy consumer.
        :param watts: Power consumption in watts.
        :param timestamp: Optional timestamp (ISO format). Defaults to now.
        """
        try:
            write_api = self.client.write_api(write_options=SYNCHRONOUS)

            if timestamp is None:
                timestamp = timezone.now().isoformat()

            point = (
                Point("EnergyConsumption")
                .tag("consumerId", str(consumer_id))
                .field("watts", float(watts))
                .time(timestamp, WritePrecision.NS)
            )
            write_api.write(bucket=str(fpf_id), record=point)

        except Exception as e:
            self.client = None
            raise InfluxDBWriteException(f"Failed to write energy consumption: {e}")

    @_retry_connection
    def write_energy_production(self, fpf_id: str, source_id: str, watts: float, timestamp: str = None):
        """
        Writes energy production data for a given source to InfluxDB.
        :param fpf_id: The ID of the FPF (used as the bucket name in InfluxDB).
        :param source_id: The ID of the energy source.
        :param watts: Power production in watts.
        :param timestamp: Optional timestamp (ISO format). Defaults to now.
        """
        try:
            write_api = self.client.write_api(write_options=SYNCHRONOUS)

            if timestamp is None:
                timestamp = timezone.now().isoformat()

            point = (
                Point("EnergyProduction")
                .tag("sourceId", str(source_id))
                .field("watts", float(watts))
                .time(timestamp, WritePrecision.NS)
            )
            write_api.write(bucket=str(fpf_id), record=point)

        except Exception as e:
            self.client = None
            raise InfluxDBWriteException(f"Failed to write energy production: {e}")

    @_retry_connection
    def write_battery_level(self, fpf_id: str, level_wh: float, percentage: float, timestamp: str = None):
        """
        Writes battery level data to InfluxDB.
        :param fpf_id: The ID of the FPF (used as the bucket name in InfluxDB).
        :param level_wh: Battery level in Wh.
        :param percentage: Battery percentage (0-100).
        :param timestamp: Optional timestamp (ISO format). Defaults to now.
        """
        try:
            write_api = self.client.write_api(write_options=SYNCHRONOUS)

            if timestamp is None:
                timestamp = timezone.now().isoformat()

            point = (
                Point("BatteryLevel")
                .field("level_wh", float(level_wh))
                .field("percentage", float(percentage))
                .time(timestamp, WritePrecision.NS)
            )
            write_api.write(bucket=str(fpf_id), record=point)

        except Exception as e:
            self.client = None
            raise InfluxDBWriteException(f"Failed to write battery level: {e}")

    @_retry_connection
    def fetch_energy_balance(self, fpf_id: str, from_date: str, to_date: str) -> dict:
        """
        Fetches energy balance (consumption vs production) for a given FPF and time range.
        :param fpf_id: The ID of the FPF (bucket name).
        :param from_date: Start date in ISO 8601 format.
        :param to_date: End date in ISO 8601 format.
        :return: Dictionary with consumption and production data.
        """
        try:
            query_api = self.client.query_api()

            # Fetch consumption
            consumption_query = (
                f'from(bucket: "{fpf_id}") '
                f'|> range(start: {from_date}, stop: {to_date}) '
                f'|> filter(fn: (r) => r["_measurement"] == "EnergyConsumption") '
                f'|> group() '
                f'|> aggregateWindow(every: 1h, fn: mean, createEmpty: false)'
            )

            # Fetch production
            production_query = (
                f'from(bucket: "{fpf_id}") '
                f'|> range(start: {from_date}, stop: {to_date}) '
                f'|> filter(fn: (r) => r["_measurement"] == "EnergyProduction") '
                f'|> group() '
                f'|> aggregateWindow(every: 1h, fn: mean, createEmpty: false)'
            )

            consumption_result = query_api.query(org=self.influxdb_settings['org'], query=consumption_query)
            production_result = query_api.query(org=self.influxdb_settings['org'], query=production_query)

            consumption_data = []
            production_data = []

            for table in consumption_result:
                for record in table.records:
                    consumption_data.append({
                        "timestamp": record.get_time().isoformat(),
                        "watts": record.get_value()
                    })

            for table in production_result:
                for record in table.records:
                    production_data.append({
                        "timestamp": record.get_time().isoformat(),
                        "watts": record.get_value()
                    })

            # Calculate totals
            total_consumption_wh = sum(d['watts'] for d in consumption_data) if consumption_data else 0
            total_production_wh = sum(d['watts'] for d in production_data) if production_data else 0

            return {
                "fpf_id": fpf_id,
                "from_date": from_date,
                "to_date": to_date,
                "consumption": {
                    "data": consumption_data,
                    "total_wh": total_consumption_wh
                },
                "production": {
                    "data": production_data,
                    "total_wh": total_production_wh
                },
                "net_wh": total_production_wh - total_consumption_wh
            }

        except Exception as e:
            self.client = None
            raise InfluxDBQueryException(f"Failed to fetch energy balance: {e}")

    @_retry_connection
    def fetch_latest_battery_level(self, fpf_id: str) -> dict:
        """
        Fetches the most recent battery level for a given FPF.
        :param fpf_id: The ID of the FPF (bucket name).
        :return: Dictionary with battery level data or None.
        """
        try:
            query_api = self.client.query_api()

            query = (
                f'from(bucket: "{fpf_id}") '
                f'|> range(start: -24h) '
                f'|> filter(fn: (r) => r["_measurement"] == "BatteryLevel") '
                f'|> sort(columns: ["_time"], desc: true) '
                f'|> limit(n: 1)'
            )

            result = query_api.query(org=self.influxdb_settings['org'], query=query)

            for table in result:
                for record in table.records:
                    return {
                        "timestamp": record.get_time().isoformat(),
                        "level_wh": record.values.get("level_wh"),
                        "percentage": record.values.get("percentage")
                    }

            return None

        except Exception as e:
            self.client = None
            raise InfluxDBQueryException(f"Failed to fetch battery level: {e}")


    def close(self):
        """Close the InfluxDB client if it's open."""
        if self.client:
            self.client.close()