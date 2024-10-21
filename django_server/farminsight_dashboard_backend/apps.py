from django.apps import AppConfig
from django.db.utils import OperationalError
from django.conf import settings
import logging


class FarminsightDashboardBackendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'farminsight_dashboard_backend'

    def ready(self):
        try:
            from .models import FPF
            from influxdb_client import InfluxDBClient

            influxdb_settings = getattr(settings, 'INFLUXDB_CLIENT_SETTINGS', {})

            client = InfluxDBClient(url=influxdb_settings['url'],
                                    token=influxdb_settings['token'],
                                    org=influxdb_settings['org'])

            bucket_api = client.buckets_api()

            if not FPF.objects.exists():
                logging.warning("Unable to find any FPFs in the database.")
                return
            for fpf in FPF.objects.all():
                if not bucket_api.find_bucket_by_name(str(fpf.id)):
                    logging.info(f"Creating new bucket: {fpf.id}")
                    bucket_api.create_bucket(bucket_name=str(fpf.id),
                                             org=influxdb_settings['org'])
            client.close()
        except OperationalError:
            # Handles the case where the database isn't ready yet (e.g., during migrations)
            pass
