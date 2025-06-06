import uuid
import requests

from django.core.files import File
from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.models import Camera, FPF
from farminsight_dashboard_backend.serializers import CameraSerializer
from farminsight_dashboard_backend.models import Image
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
        camera =  Camera.objects.get(id=camera_id)
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

def create_camera(fpf_id:str, camera_data:dict) -> Camera:
    """
    Create a new camera by FPF ID and camera data.
    :param fpf_id: ID of the camera's FPF
    :param camera_data: Camera data
    :return: Newly created Camera instance
    """
    try:
        fpf = FPF.objects.get(id=fpf_id)
    except FPF.DoesNotExist:
        raise ValueError("FPF with the given ID does not exist")

    serializer = CameraSerializer(data=camera_data, partial=True)
    serializer.is_valid(raise_exception=True)

    return serializer.save(FPF=fpf)


def update_camera(camera_id:str, camera_data:any) -> Camera:
    """
    Update camera by id and camera data
    :param camera_id: camera to update
    :param camera_data: new camera data
    :return: Updated Camera
    """
    camera = get_camera_by_id(camera_id)
    for key, value in camera_data.items():
        setattr(camera, key, value)
    camera.save()
    return camera


def delete_camera(camera: Camera):
    """
    Delete camera
    :param camera: camera to delete
    """
    camera.delete()


def get_active_camera_count():
    return len(Camera.objects.filter(isActive=True).all())


def set_camera_order(ids: list[str]):
    items = Camera.objects.filter(id__in=ids)
    for item in items:
        item.orderIndex = ids.index(str(item.id))

    Camera.objects.bulk_update(items, ['orderIndex'])