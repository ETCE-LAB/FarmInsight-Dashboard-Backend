import logging

from farminsight_dashboard_backend.models import FPF, Sensor, Location
from farminsight_dashboard_backend.utils import get_date_range
from .influx_services import InfluxDBManager
from ..exceptions import NotFoundException

logger = logging.getLogger(__name__)


def get_all_fpf_data(fpf_id):
    """
    Returns all related data (Sensors, Cameras, GrowingCycles) including measurements and images
    for the given FPF from the databases.
    :param to_date: must be in ISO 8601 format (e.g. 2024-10-01T00:00:00Z) or YYYY-MM-DD format.
    :param from_date: must be in ISO 8601 format (e.g. 2024-10-31T23:59:59Z) or YYYY-MM-DD format.
    :param fpf_id: UUID of the FPF
    :return:
    """
    try:
        fpf = FPF.objects.prefetch_related('sensors', 'cameras', 'growingCycles').get(id=fpf_id)
    except FPF.DoesNotExist:
        logger.error(f"Could not fetch FPF Data. FPF not found.")
        raise NotFoundException(f'FPF with id: {fpf_id} was not found.')
    return fpf

def get_all_sensor_data(sensor_id, from_date=None, to_date=None):
    """
    Returns all related data (Sensors, Cameras, GrowingCycles) including measurements and images
    for the given FPF from the databases.
    :param sensor_id: UUID of the sensor
    :param to_date: must be in ISO 8601 format (e.g. 2024-10-01T00:00:00Z) or YYYY-MM-DD format.
    :param from_date: must be in ISO 8601 format (e.g. 2024-10-31T23:59:59Z) or YYYY-MM-DD format.
    :return:
    """
    try:
        sensor = Sensor.objects.get(id=sensor_id)
    except Sensor.DoesNotExist:
        raise NotFoundException(f'Sensor with id: {sensor_id} was not found.')

    # Set dates and convert to iso code
    from_date_iso, to_date_iso = get_date_range(from_date, to_date)

    # Fetch measurements for all sensors in one call
    measurements_by_sensor = InfluxDBManager.get_instance().fetch_sensor_measurements(
        fpf_id=str(sensor.FPF.id),
        sensor_ids=[str(sensor.id)],
        from_date=from_date_iso,
        to_date=to_date_iso)

    return measurements_by_sensor.get(str(sensor.id), [])

def get_last_weather_forecast(locationId):
    """
    Get the last weather forecast for all locations
    :return: list of weather forecasts
    """
    location = Location.objects.get(id=locationId)
    forecasts = InfluxDBManager.get_instance().fetch_last_weather_forcast(location.organization.id, location.id )

    return forecasts

def get_weather_forecasts_by_date(location_id: str, from_date, to_date=None):
    """
    :param location_id: UUID of the location
    :param to_date: must be in ISO 8601 format (e.g. 2024-10-01T00:00:00Z) or YYYY-MM-DD format.
    :param from_date: must be in ISO 8601 format (e.g. 2024-10-31T23:59:59Z) or YYYY-MM-DD format.
    :return:
    """
    from_date_iso, to_date_iso = get_date_range(from_date, to_date)
    location = Location.objects.get(id=location_id)
    forecasts = InfluxDBManager.get_instance().fetch_all_weather_forecasts(location.organization.id, location.id, from_date_iso, to_date_iso)
    if not forecasts:
        logger.warning(f"No weather forecasts found for {location_id} in the specified date range from {from_date_iso} to {to_date_iso}.")
    return forecasts
