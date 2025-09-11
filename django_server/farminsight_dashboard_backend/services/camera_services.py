import uuid
import requests

from django.core.files import File

from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.models import Camera
from farminsight_dashboard_backend.serializers import CameraSerializer, CameraDBSchemaSerializer
from farminsight_dashboard_backend.models import Image
from .fpf_connection_services import post_sensor, put_update_sensor, delete_sensor
from farminsight_dashboard_backend.utils import get_logger


logger = get_logger()


def fetch_camera_snapshot(camera_id, snapshot_url):
    """
    Fetch a snapshot from the given snapshot URL of the camera and store it as a jpg file.
    :param camera_id:
    :param snapshot_url:
    :return:
    """
    try:
        response = requests.get(snapshot_url, stream=True)
        if response.status_code == 200:
            filename = f"{str(uuid.uuid4())}.jpg"
            Image.objects.create(
                camera_id=camera_id,
                image=File(response.raw, name=filename)
            )

            return filename
        else:
            raise ValueError(f"HTTP error {response.status_code}")
    except Exception as e:
        logger.error(f"Error fetching snapshot for Camera: {e}", extra={'resource_id': camera_id})


def get_active_camera_by_id(camera_id:str) -> Camera:
    """
    Get active camera by id
    :param camera_id:
    :return: Camera
    :throws: NotFoundException
    """
    try:
        camera = Camera.objects.get(id=camera_id)
        if not camera.isActive:
            raise NotFoundException(f'Camera with id: {camera_id} is not active.')
        return camera
    except Camera.DoesNotExist:
        raise NotFoundException(f'Camera with id: {camera_id} was not found.')


def get_camera_by_id(camera_id:str) -> Camera:
    """
    Get camera by id
    :param camera_id:
    :return: Camera
    :throws: NotFoundException
    """
    try:
        return Camera.objects.get(id=camera_id)
    except Camera.DoesNotExist:
        raise NotFoundException(f'Camera with id: {camera_id} was not found.')


def create_camera(fpf_id: str, camera_data: dict) -> CameraDBSchemaSerializer:
    """
    Create a new Camera in the database and on the FPF backend.
    :return:
    """
    camera = camera_data
    camera['id'] = str(uuid.uuid4())
    camera['FPF'] = fpf_id

    serializer = CameraDBSchemaSerializer(data=camera, partial=True)
    serializer.is_valid(raise_exception=True)

    camera_config = {
        "id": camera.get('id'),
        "intervalSeconds": camera.get('intervalSeconds'),
        "sensorClassId": 'cacacaca-caca-caca-caca-cacacacacaca',
        "additionalInformation": {
            'snapshotUrl': camera.get('snapshotUrl'),
            'livestreamUrl': camera.get('livestreamUrl'),
        },
        "isActive": camera.get('isActive'),
        "sensorType": 'camera',
    }

    try:
        post_sensor(fpf_id, camera_config)
    except Exception as e:
        raise Exception(f"Unable to create camera at FPF. {e}")

    new_camera = Camera(**serializer.validated_data)
    new_camera.id = camera.get('id')
    new_camera.save()
    return serializer


def update_camera(camera_id: str, data: dict) -> CameraSerializer:
    """
    Update camera by id and camera data
    :param camera_id: camera to update
    :param data: new camera data
    :return: Updated Camera
    """
    camera = get_camera_by_id(camera_id)

    # Update camera on FPF
    update_fpf_payload = {
        "intervalSeconds": data.get('intervalSeconds'),
        "sensorClassId": 'cacacaca-caca-caca-caca-cacacacacaca',
        "additionalInformation": {
            'snapshotUrl': data.get('snapshotUrl'),
            'livestreamUrl': data.get('livestreamUrl'),
        },
        "isActive": data.get('isActive'),
        'sensorType': 'camera',
    }

    put_update_sensor(str(camera.FPF_id), camera_id, update_fpf_payload)

    # Update sensor locally
    serializer = CameraSerializer(camera, data=data, partial=True)

    if serializer.is_valid(raise_exception=True):
        serializer.save()
    return serializer


def delete_camera(camera: Camera):
    """
    Delete camera
    :param camera: camera to delete
    """
    delete_sensor(str(camera.FPF_id), str(camera.id))
    camera.delete()


def get_active_camera_count():
    return len(Camera.objects.filter(isActive=True).all())


def set_camera_order(ids: list[str]) -> CameraSerializer:
    items = Camera.objects.filter(id__in=ids)
    for item in items:
        item.orderIndex = ids.index(str(item.id))

    Camera.objects.bulk_update(items, ['orderIndex'])

    return CameraSerializer(items, many=True)