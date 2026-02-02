"""
Energy Data Collector Service

Collects energy consumption and production data from sensors and static values,
and writes them to InfluxDB for historical tracking and graph display.
"""

import threading
from datetime import timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone

from farminsight_dashboard_backend.models import FPF, EnergyConsumer, EnergySource
from farminsight_dashboard_backend.services.influx_services import InfluxDBManager
from farminsight_dashboard_backend.utils import get_logger

logger = get_logger()


class EnergyDataCollector:
    """
    Periodically collects energy data (consumption, production, battery level)
    and writes it to InfluxDB for historical tracking.
    """
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __new__(cls, *args, **kwargs):
        return super(EnergyDataCollector, cls).__new__(cls)

    def __init__(self):
        if not getattr(self, "_initialized", False):
            self._scheduler = BackgroundScheduler()
            self.log = get_logger()
            self._initialized = True

    def start(self, interval_seconds: int = 300):
        """
        Start the energy data collector.
        Collects data every 5 minutes by default.

        :param interval_seconds: Collection interval in seconds (default: 300 = 5 min)
        """
        self._scheduler.add_job(
            self._collect_all_energy_data,
            trigger=IntervalTrigger(seconds=interval_seconds),
            id="energy_data_collector",
            replace_existing=True,
            next_run_time=timezone.now() + timedelta(seconds=10)
        )
        self._scheduler.start()
        self.log.info(f"EnergyDataCollector started with interval: {interval_seconds} seconds.")

    def stop(self):
        """Stop the energy data collector."""
        self._scheduler.shutdown(wait=False)
        self.log.info("EnergyDataCollector stopped.")

    def _collect_all_energy_data(self):
        """
        Iterate over all FPFs and collect their energy data.
        """
        fpfs = FPF.objects.all()

        for fpf in fpfs:
            try:
                self._collect_fpf_energy_data(str(fpf.id))
            except Exception as e:
                self.log.error(f"Error collecting energy data for FPF {fpf.name}: {e}")

    def _collect_fpf_energy_data(self, fpf_id: str):
        """
        Collect and store energy data for a specific FPF.

        :param fpf_id: UUID of the FPF
        """
        influx = InfluxDBManager.get_instance()
        timestamp = timezone.now().isoformat()

        # Collect consumption data from active consumers
        total_consumption = self._collect_consumption_data(fpf_id, influx, timestamp)

        # Collect production data from active sources
        total_production = self._collect_production_data(fpf_id, influx, timestamp)

        # Collect battery level if available
        self._collect_battery_data(fpf_id, influx, timestamp)

        self.log.debug(
            f"Energy data collected for FPF {fpf_id}: "
            f"Consumption={total_consumption}W, Production={total_production}W"
        )

    def _collect_consumption_data(self, fpf_id: str, influx: InfluxDBManager, timestamp: str) -> float:
        """
        Collect consumption data from all active consumers.
        Uses sensor data if available, falls back to static values.

        :return: Total consumption in watts
        """
        consumers = EnergyConsumer.objects.filter(FPF_id=fpf_id, isActive=True)
        total_consumption = 0.0

        for consumer in consumers:
            consumption_watts = consumer.consumptionWatts

            # Try to get live data from linked sensor
            if consumer.sensor and consumer.sensor.isActive:
                try:
                    measurements = influx.fetch_latest_sensor_measurements(
                        fpf_id=fpf_id,
                        sensor_ids=[str(consumer.sensor.id)]
                    )
                    sensor_data = measurements.get(str(consumer.sensor.id))
                    if sensor_data and 'value' in sensor_data:
                        consumption_watts = float(sensor_data['value'])
                except Exception as e:
                    self.log.warning(f"Could not fetch sensor data for consumer {consumer.name}: {e}")

            # Write consumption data point
            try:
                influx.write_energy_consumption(
                    fpf_id=fpf_id,
                    consumer_id=str(consumer.id),
                    watts=consumption_watts,
                    timestamp=timestamp
                )
            except Exception as e:
                self.log.warning(f"Failed to write consumption for {consumer.name}: {e}")

            total_consumption += consumption_watts

        return total_consumption

    def _collect_production_data(self, fpf_id: str, influx: InfluxDBManager, timestamp: str) -> float:
        """
        Collect production data from all active sources (excluding battery type).
        Uses sensor data if available, falls back to static values.

        :return: Total production in watts
        """
        # Exclude battery sources from production calculation
        sources = EnergySource.objects.filter(
            FPF_id=fpf_id,
            isActive=True
        ).exclude(sourceType='battery')

        total_production = 0.0

        for source in sources:
            production_watts = source.currentOutputWatts

            # Try to get live data from linked sensor
            if source.sensor and source.sensor.isActive:
                try:
                    measurements = influx.fetch_latest_sensor_measurements(
                        fpf_id=fpf_id,
                        sensor_ids=[str(source.sensor.id)]
                    )
                    sensor_data = measurements.get(str(source.sensor.id))
                    if sensor_data and 'value' in sensor_data:
                        production_watts = float(sensor_data['value'])
                except Exception as e:
                    self.log.warning(f"Could not fetch sensor data for source {source.name}: {e}")

            # Write production data point
            try:
                influx.write_energy_production(
                    fpf_id=fpf_id,
                    source_id=str(source.id),
                    watts=production_watts,
                    timestamp=timestamp
                )
            except Exception as e:
                self.log.warning(f"Failed to write production for {source.name}: {e}")

            total_production += production_watts

        return total_production

    def _collect_battery_data(self, fpf_id: str, influx: InfluxDBManager, timestamp: str):
        """
        Collect battery level data from battery sources.
        """
        from farminsight_dashboard_backend.services.energy_decision_services import get_fpf_energy_config

        battery_sources = EnergySource.objects.filter(
            FPF_id=fpf_id,
            sourceType='battery',
            isActive=True
        )

        config = get_fpf_energy_config(fpf_id)
        battery_max_wh = config['battery_max_wh']

        for battery in battery_sources:
            battery_level_wh = None

            # Try to get live data from linked sensor
            if battery.sensor and battery.sensor.isActive:
                try:
                    measurements = influx.fetch_latest_sensor_measurements(
                        fpf_id=fpf_id,
                        sensor_ids=[str(battery.sensor.id)]
                    )
                    sensor_data = measurements.get(str(battery.sensor.id))
                    if sensor_data and 'value' in sensor_data:
                        battery_level_wh = float(sensor_data['value'])
                except Exception as e:
                    self.log.warning(f"Could not fetch sensor data for battery {battery.name}: {e}")

            # Fallback to static value
            if battery_level_wh is None:
                battery_level_wh = battery.currentOutputWatts

            # Calculate percentage
            percentage = min(100.0, max(0.0, (battery_level_wh / battery_max_wh) * 100)) if battery_max_wh > 0 else 0.0

            # Write battery level data
            try:
                influx.write_battery_level(
                    fpf_id=fpf_id,
                    level_wh=battery_level_wh,
                    percentage=percentage,
                    timestamp=timestamp
                )
            except Exception as e:
                self.log.warning(f"Failed to write battery level for {battery.name}: {e}")


def collect_energy_data_for_fpf(fpf_id: str):
    """
    Manually trigger energy data collection for a specific FPF.
    Useful for testing or on-demand collection.

    :param fpf_id: UUID of the FPF
    """
    collector = EnergyDataCollector.get_instance()
    collector._collect_fpf_energy_data(fpf_id)


def start_energy_data_collector(interval_seconds: int = 300):
    """
    Start the global energy data collector.

    :param interval_seconds: Collection interval (default: 5 minutes)
    """
    collector = EnergyDataCollector.get_instance()
    collector.start(interval_seconds)


def stop_energy_data_collector():
    """Stop the global energy data collector."""
    collector = EnergyDataCollector.get_instance()
    collector.stop()

