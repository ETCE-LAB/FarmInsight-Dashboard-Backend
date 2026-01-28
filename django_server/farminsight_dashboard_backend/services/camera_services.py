import uuid
import time
import requests

from django.core.files import File

from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.models import Camera, FPF, ControllableAction, ActionQueue, ActionTrigger
from farminsight_dashboard_backend.serializers import CameraSerializer
from farminsight_dashboard_backend.models import Image
from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.services.action_queue_services import is_already_enqueued, process_action_queue


logger = get_logger()

SHELLY_PLUG_CLASS_ID = 'baa6ef9a-58dc-4e28-b429-d525dfef0941'
TAPO_PLUG_CLASS_ID = 'dc83813b-1541-4aac-8caa-ba448a6bbdda'

# Smart wait configuration for camera plug activation
CAMERA_PLUG_WAIT_SECONDS = 3  # Time to wait for plug to turn on
CAMERA_PLUG_RETRY_ATTEMPTS = 3  # Number of retry attempts for snapshot
CAMERA_PLUG_RETRY_DELAY = 2  # Delay between retries in seconds

def find_camera_smart_plug(camera: Camera) -> ControllableAction:
    """
    Find the smart plug associated with the camera.
    Heuristic: Look for a ControllableAction in the same FPF that:
    1. Is a Smart Plug (Shelly or Tapo)
    2. Has a name containing the camera's name
    """
    actions = ControllableAction.objects.filter(
        FPF=camera.FPF,
        isActive=True,
        actionClassId__in=[SHELLY_PLUG_CLASS_ID, TAPO_PLUG_CLASS_ID]
    )
    
    for action in actions:
        if camera.name.lower() in action.name.lower():
            return action
            
    return None


def trigger_camera_plug_and_wait(camera_id: str, state: str, wait_seconds: float = CAMERA_PLUG_WAIT_SECONDS) -> bool:
    """
    Trigger the camera's smart plug and wait for it to activate.
    
    :param camera_id: UUID of the camera
    :param state: 'On' or 'Off'
    :param wait_seconds: Time to wait after triggering the plug
    :return: True if plug was found and triggered, False otherwise
    """
    try:
        camera = Camera.objects.get(id=camera_id)
        plug = find_camera_smart_plug(camera)
        
        if plug:
            logger.info(f"Triggering Smart Plug '{plug.name}' to {state} for Camera '{camera.name}'")
            
            # Create a transient trigger
            trigger = ActionTrigger.objects.create(
                name=f"Camera Logic: {state}",
                type="auto",
                actionValue=state,
                action=plug,
                isActive=True
            )
            
            if not is_already_enqueued(trigger.id):
                ActionQueue.objects.create(
                    action=plug,
                    trigger=trigger
                )
                # Process the action queue immediately
                try:
                    process_action_queue()
                except Exception as e:
                    logger.warning(f"Error processing action queue: {e}")
            
            # Wait for plug to activate
            if state.lower() == "on" and wait_seconds > 0:
                logger.debug(f"Waiting {wait_seconds}s for plug to activate...")
                time.sleep(wait_seconds)
            
            return True
        else:
            logger.debug(f"No Smart Plug found for Camera '{camera.name}'")
            return False
            
    except Exception as e:
        logger.error(f"Error triggering camera plug: {e}")
        return False


def trigger_camera_plug(camera_id: str, state: str):
    """
    Trigger the camera's smart plug to 'On' or 'Off'.
    Legacy function for backward compatibility - does not wait.
    """
    trigger_camera_plug_and_wait(camera_id, state, wait_seconds=0)


def _attempt_snapshot(snapshot_url: str, timeout: int = 10) -> requests.Response:
    """
    Attempt to fetch a snapshot from the given URL.
    
    :param snapshot_url: URL to fetch snapshot from
    :param timeout: Request timeout in seconds
    :return: Response object
    :raises: requests.RequestException on failure
    """
    return requests.get(snapshot_url, stream=True, timeout=timeout)


def fetch_camera_snapshot(camera_id, snapshot_url):
    """
    Fetch a snapshot from the given snapshot URL of the camera and store it as a jpg file.
    Implements smart wait mechanism to ensure camera plug is on before taking snapshot.
    
    :param camera_id: UUID of the camera
    :param snapshot_url: URL to fetch the snapshot from
    :return: Filename of the saved image
    """
    # Turn on plug before snapshot with smart wait
    plug_triggered = trigger_camera_plug_and_wait(camera_id, "On", CAMERA_PLUG_WAIT_SECONDS)
    
    last_error = None
    
    for attempt in range(CAMERA_PLUG_RETRY_ATTEMPTS):
        try:
            response = _attempt_snapshot(snapshot_url)
            
            if response.status_code == 200:
                filename = f"{str(uuid.uuid4())}.jpg"
                Image.objects.create(
                    camera_id=camera_id,
                    image=File(response.raw, name=filename)
                )
                logger.info(f"Snapshot captured successfully for Camera {camera_id}")
                return filename
            else:
                last_error = ValueError(f"HTTP error {response.status_code}")
                
        except requests.exceptions.ConnectionError as e:
            last_error = e
            logger.warning(f"Snapshot attempt {attempt + 1}/{CAMERA_PLUG_RETRY_ATTEMPTS} failed (connection error). Camera may still be powering on.")
            
        except requests.exceptions.Timeout as e:
            last_error = e
            logger.warning(f"Snapshot attempt {attempt + 1}/{CAMERA_PLUG_RETRY_ATTEMPTS} timed out.")
            
        except Exception as e:
            last_error = e
            logger.warning(f"Snapshot attempt {attempt + 1}/{CAMERA_PLUG_RETRY_ATTEMPTS} failed: {e}")
        
        # Wait before retrying (if not last attempt)
        if attempt < CAMERA_PLUG_RETRY_ATTEMPTS - 1:
            logger.debug(f"Waiting {CAMERA_PLUG_RETRY_DELAY}s before retry...")
            time.sleep(CAMERA_PLUG_RETRY_DELAY)
    
    # All attempts failed
    logger.error(f"Failed to fetch snapshot for Camera {camera_id} after {CAMERA_PLUG_RETRY_ATTEMPTS} attempts: {last_error}", 
                 extra={'resource_id': camera_id})
    raise last_error if last_error else ValueError("Unknown error fetching snapshot")

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


def update_camera(camera_id:str, data:any) -> CameraSerializer:
    """
    Update camera by id and camera data
    :param camera_id: camera to update
    :param camera_data: new camera data
    :return: Updated Camera
    """
    camera = get_camera_by_id(camera_id)
    serializer = CameraSerializer(camera, data=data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        return serializer


def delete_camera(camera: Camera):
    """
    Delete camera
    :param camera: camera to delete
    """
    camera.delete()


def get_active_camera_count():
    return len(Camera.objects.filter(isActive=True).all())


def set_camera_order(ids: list[str]) -> CameraSerializer:
    items = Camera.objects.filter(id__in=ids)
    for item in items:
        item.orderIndex = ids.index(str(item.id))

    Camera.objects.bulk_update(items, ['orderIndex'])

    return CameraSerializer(items, many=True)