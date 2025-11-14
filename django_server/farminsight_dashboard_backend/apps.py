import time
import os
import threading

from django.apps import AppConfig
from django.db.utils import OperationalError
from django.db.migrations.executor import MigrationExecutor
from django.db import connections

from farminsight_dashboard_backend.utils import get_logger


class FarminsightDashboardBackendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'farminsight_dashboard_backend'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = get_logger()

    def initialize_app(self, max_retries=3, retry_interval=3):
        """
        :param max_retries: maximum amount of retries to connect to the database
        :param retry_interval: interval of the retry
        """
        retry_count = 0
        while retry_count < max_retries:
            try:
                if self.has_pending_migrations():
                    self.log.warning(f"Pending migrations detected. Retrying in {retry_interval} seconds...")
                    time.sleep(retry_interval)
                    retry_count += 1
                else:
                    from farminsight_dashboard_backend.services import InfluxDBManager, CameraScheduler, DataRetentionScheduler, WeatherForecastScheduler, AutoTriggerScheduler, ModelScheduler
                    from farminsight_dashboard_backend.services.trigger.MeasurementTriggerManager import \
                        MeasurementTriggerManager

                    InfluxDBManager.get_instance().initialize_connection()
                    CameraScheduler.get_instance().start()
                    DataRetentionScheduler.get_instance().start()
                    WeatherForecastScheduler.get_instance().start()
                    AutoTriggerScheduler.get_instance().start()
                    ModelScheduler.get_instance().start()
                    MeasurementTriggerManager.build_trigger_mapping()
                    self.log.info("Started successfully.")
                    break
            except OperationalError as e:
                self.log.error(f"Database not ready yet: {e}")
                time.sleep(retry_interval)
                retry_count += 1
            except Exception as e:
                self.log.error(f"Error checking migrations: {e}")
                break
        if retry_count == max_retries:
            self.log.error("Max retries reached. App did not start.")

    def has_pending_migrations(self) -> bool:
        """
        Check if there are any pending migrations.
        :return: if there are pending migrations
        """
        try:
            executor = MigrationExecutor(connections['default'])
            targets = executor.loader.graph.leaf_nodes()
            return executor.migration_plan(targets) != []

        except Exception as e:
            self.log.error(f"Error checking migrations: {e}")
            return True  # Assume pending if there's an error

    def ready(self):
        """
        Start a new thread to check for pending migrations and start the app if ready
        """
        if os.environ.get('RUN_MAIN') == 'true':
            threading.Thread(target=self.initialize_app, daemon=True).start()
