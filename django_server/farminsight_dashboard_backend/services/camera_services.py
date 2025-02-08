from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.models import Camera, FPF
from farminsight_dashboard_backend.serializers import CameraSerializer


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


def delete_camera(camera_id:str):
    """
    Delete camera by id
    :param camera_id: id of the camera t delete
    """
    camera = get_camera_by_id(camera_id)
    camera.delete()
