import uuid

from channels.db import database_sync_to_async

from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.models import Sensor
from farminsight_dashboard_backend.serializers.sensor_serializer import SensorSerializer, SensorDBSchemaSerializer
from .fpf_connection_services import post_sensor, put_update_sensor


@database_sync_to_async
def sensor_exists(sensor_id) -> bool:
    try:
        Sensor.objects.get(id=sensor_id)
        return True
    except Sensor.DoesNotExist:
        return False


def get_sensor(sensor_id) -> Sensor:
    """
    Return the sensor by given id populated with additional technical information by the FPF.
    :param sensor_id:
    :return:
    """
    try:
        sensor = Sensor.objects.get(id=sensor_id)
    except Sensor.DoesNotExist:
        raise NotFoundException(f'Sensor {sensor_id} not found.')

    return sensor


def update_sensor(sensor_id: str, data: dict) -> SensorSerializer:
    """
    Update the sensor by sensor id and a new sensor object
    :param sensor_id:
    :param data:
    :return:
    """
    sensor = get_sensor(sensor_id)

    # Update sensor on FPF
    update_fpf_payload = {
        "intervalSeconds": data.get('intervalSeconds'),
        "sensorClassId": data.get('hardwareConfiguration', {}).get('sensorClassId', ''),
        "additionalInformation": data.get('hardwareConfiguration', {}).get('additionalInformation', {}),
        "isActive": data.get('isActive'),
        'sensorType': 'sensor',
    }

    put_update_sensor(str(sensor.FPF_id), sensor_id, update_fpf_payload)

    # Update sensor locally
    update_sensor_payload = {key: value for key, value in data.items() if key != "connection"}
    serializer = SensorSerializer(sensor, data=update_sensor_payload, partial=True)

    if serializer.is_valid(raise_exception=True):
        serializer.save()

    return serializer


def create_sensor(fpf_id: str, sensor_data:dict) -> SensorDBSchemaSerializer:
    """
    Create a new Sensor in the database and on the FPF backend.
    :return:
    """
    sensor = sensor_data
    sensor["id"] = str(uuid.uuid4())
    sensor['FPF'] = fpf_id

    # Validate the sensor object before sending it to the FPF
    serializer = SensorDBSchemaSerializer(data=sensor, partial=True)
    serializer.is_valid(raise_exception=True)

    sensor_config = {
        "id": sensor.get('id'),
        "intervalSeconds": sensor.get('intervalSeconds'),
        "sensorClassId": sensor.get('hardwareConfiguration', {}).get('sensorClassId', ''),
        "additionalInformation": sensor.get('hardwareConfiguration', {}).get('additionalInformation', {}),
        "isActive": sensor.get('isActive'),
        "sensorType": 'sensor',
    }

    try:
        post_sensor(fpf_id, sensor_config)
    except Exception as e:
        raise Exception(f"Unable to create sensor at FPF. {e}")

    new_sensor = Sensor(**serializer.validated_data)
    new_sensor.id = sensor['id']
    new_sensor.save()
    return serializer


def set_sensor_order(ids: list[str]) -> SensorSerializer:
    sensors = Sensor.objects.filter(id__in=ids)
    for sensor in sensors:
        sensor.orderIndex = ids.index(str(sensor.id))

    Sensor.objects.bulk_update(sensors, ['orderIndex'])

    return SensorSerializer(sensors, many=True)
