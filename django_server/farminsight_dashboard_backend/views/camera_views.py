from urllib.parse import urlparse
from django.http import StreamingHttpResponse
from rest_framework import views
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from farminsight_dashboard_backend.serializers.camera_serializer import CameraSerializer
from farminsight_dashboard_backend.services import get_active_camera_by_id, update_camera, delete_camera, \
    get_fpf_by_id, create_camera, is_member, get_camera_by_id, get_organization_by_camera_id, \
    get_organization_by_fpf_id, is_admin, set_camera_order
from farminsight_dashboard_backend.utils import get_logger



logger = get_logger()

class CameraView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, camera_id):
        """
        Get a camera by its id
        :param request:
        :param camera_id:
        :return:
        """
        return Response(CameraSerializer(get_camera_by_id(camera_id)).data, status=status.HTTP_200_OK)

    def put(self, request, camera_id):
        """
        If incoming camera data is valid, update the camera by given id with the incoming data
        If the interval was updated, reschedule the job of the camera
        :param request:
        :param camera_id: id of the camera to update
        :return:
        """
        if not is_member(request.user, get_organization_by_camera_id(camera_id)):
            logger.warning(f"Unauthorized attempt to update camera by user '{request.user.name}'")
            return Response(status=status.HTTP_403_FORBIDDEN)

        camera = get_camera_by_id(camera_id)
        old_interval = camera.intervalSeconds
        old_is_active = camera.isActive

        # Update the camera
        serializer = update_camera(camera_id, request.data)

        logger.info(f"Camera '{camera.name}' updated successfully by user '{request.user.name}'", extra={'resource_id': camera_id})

        # Update the scheduler
        camera = get_camera_by_id(camera_id)
        if camera.intervalSeconds != old_interval or camera.isActive != old_is_active:
            from farminsight_dashboard_backend.services import CameraScheduler
            logger.info(f"Rescheduling camera job for camera '{camera.name}'")
            CameraScheduler.get_instance().reschedule_camera_job(camera.id, camera.intervalSeconds)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, camera_id):
        """
        Delete a camera by given id and the associated job
        :param request:
        :param camera_id:
        :return:
        """
        if not is_admin(request.user, get_organization_by_camera_id(camera_id)):
            logger.warning(f"Unauthorized attempt to delete camera by user '{request.user.name}'")
            return Response(status=status.HTTP_403_FORBIDDEN)

        from farminsight_dashboard_backend.services import CameraScheduler
        CameraScheduler.get_instance().remove_camera_job(camera_id)

        camera = get_camera_by_id(camera_id)
        fpf_id = camera.FPF_id

        delete_camera(camera)

        logger.info(f"Camera '{camera.name}' deleted successfully by user '{request.user.name}'", extra={'resource_id': fpf_id})

        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_camera(request):
    """
    Create a new camera and schedule a new job
    :param request:
    :return:
    """
    fpf_id = request.data.get('fpfId')

    if not is_member(request.user, get_organization_by_fpf_id(fpf_id)):
        logger.warning(f"Unauthorized attempt to create camera by user '{request.user.name}'")
        return Response(status=status.HTTP_403_FORBIDDEN)

    get_fpf_by_id(fpf_id)

    camera = CameraSerializer(create_camera(fpf_id, request.data)).data

    logger.info(f"Camera '{camera.get('name')}' created successfully by user '{request.user.name}'", extra={'resource_id': fpf_id})

    from farminsight_dashboard_backend.services import CameraScheduler
    CameraScheduler.get_instance().add_camera_job(camera.get('id'))

    return Response(camera, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_camera_livestream(request, camera_id):
    """
    Authenticated via Query Param Bearer token
    Only member of the FPFs organization are allowed to stream.
    Uses a Websocket to send Frames to each Watcher
    :param request:
    :param camera_id:
    :return:
    """
    if not is_member(request.user, get_organization_by_camera_id(camera_id)):
        logger.warning(f"Unauthorized attempt to access camera livestream by user '{request.user.name}'")
        return Response(status=status.HTTP_403_FORBIDDEN)

    camera = get_active_camera_by_id(camera_id)
    livestream_url = camera.livestreamUrl

    parsed_url = urlparse(livestream_url)
    scheme = parsed_url.scheme.lower()

    logger.info(f"Camera '{camera.name}' livestream started by user '{request.user.name}'", extra={'resource_id': camera_id})
    try:
        return Response(True, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error starting websocket stream for camera '{camera.name}': {e}", extra={'resource_id': camera_id})
        return Response(
            {"error": f"Could not start websocket stream: {e}"},
            status=500
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_camera_order(request, fpf_id):
    if not is_admin(request.user, get_organization_by_fpf_id(fpf_id)):
        logger.warning(f"Unauthorized attempt to reorder cameras by user '{request.user.name}'")
        return Response(status=status.HTTP_403_FORBIDDEN)

    serializer = set_camera_order(request.data)
    logger.info(f"Camera order for FPF {fpf_id} updated by user '{request.user.name}'")

    return Response(data=serializer.data, status=status.HTTP_200_OK)
