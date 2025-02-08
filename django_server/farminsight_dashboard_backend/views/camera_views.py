from urllib.parse import urlparse
from django.http import StreamingHttpResponse
from rest_framework import views
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from farminsight_dashboard_backend.serializers.camera_serializer import CameraSerializer
from farminsight_dashboard_backend.services import get_active_camera_by_id, update_camera, delete_camera, \
    get_fpf_by_id, create_camera, is_member, get_camera_by_id
from farminsight_dashboard_backend.services.fpf_streaming_services import rtsp_stream, http_stream
from oauth2_provider.models import AccessToken

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
        from farminsight_dashboard_backend.services import CameraScheduler
        serializer = CameraSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_interval = get_camera_by_id(camera_id).intervalSeconds

        # Update the camera
        camera = update_camera(camera_id, serializer.data)

        # Update the scheduler
        if camera.intervalSeconds != old_interval:
            CameraScheduler.get_instance().reschedule_camera_job(camera.id, camera.intervalSeconds)

        return Response(CameraSerializer(camera).data, status=status.HTTP_200_OK)

    def delete(self, request, camera_id):
        """
        Delete a camera by given id and the associated job
        :param request:
        :param camera_id:
        :return:
        """
        from farminsight_dashboard_backend.services import CameraScheduler
        CameraScheduler.get_instance().remove_camera_job(camera_id)
        delete_camera(camera_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_camera(request):
    """
    Create a new camera and schedule a new job
    :param request:
    :return:
    """
    from farminsight_dashboard_backend.services import CameraScheduler

    fpf_id = request.data.get('fpfId')

    get_fpf_by_id(fpf_id)

    camera = CameraSerializer(create_camera(fpf_id, request.data)).data
    CameraScheduler.get_instance().add_camera_job(camera.get('id'))

    return Response(camera, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def get_camera_livestream(request, camera_id):
    """
    Authenticated via Query Param Bearer token
    Only member of the FPFs organization are allowed to stream.
    User http or rtsp streaming protocol (depending on the camera livestream url) to stream a video feed.
    :param request:
    :param camera_id:
    :return:
    """
    token = request.GET.get('token')

    if not token:
        return Response({"error": "Token is required"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        access_token = AccessToken.objects.get(token=token)

        if access_token.is_expired():
            return Response({"error": "Token has expired"}, status=status.HTTP_401_UNAUTHORIZED)

    except AccessToken.DoesNotExist:
        return Response({"error": "Token not found"}, status=status.HTTP_401_UNAUTHORIZED)

    camera = get_active_camera_by_id(camera_id)
    livestream_url = camera.livestreamUrl

    if not is_member(access_token.user, get_fpf_by_id(str(camera.FPF_id)).organization.id):
        return Response(status=status.HTTP_403_FORBIDDEN)

    parsed_url = urlparse(livestream_url)
    scheme = parsed_url.scheme.lower()

    if scheme in ['http', 'https']:
        return StreamingHttpResponse(
            http_stream(livestream_url),
            content_type="multipart/x-mixed-replace; boundary=frame"
        )
    elif scheme == 'rtsp':
        return StreamingHttpResponse(
            rtsp_stream(livestream_url),
            content_type="multipart/x-mixed-replace; boundary=frame"
        )
    else:
        return Response(
            {"error": f"Unsupported protocol: {scheme}"},
            status=400
        )
