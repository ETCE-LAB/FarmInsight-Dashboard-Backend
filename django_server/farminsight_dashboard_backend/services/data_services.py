from farminsight_dashboard_backend.models import FPF, Sensor
from farminsight_dashboard_backend.utils import get_date_range
from .influx_services import InfluxDBManager
from ..exceptions import NotFoundException
from ..serializers.fpf_serializer import FPFFullSerializer


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
