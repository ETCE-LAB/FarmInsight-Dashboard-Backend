from rest_framework import views
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from farminsight_dashboard_backend.serializers.controllable_action_serializer import ControllableActionSerializer
from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.services import get_fpf_by_id, \
    get_organization_by_fpf_id, is_admin, create_controllable_action, delete_controllable_action, \
    get_controllable_action_by_id, get_organization_by_controllable_action_id, create_action_in_queue, \
    process_action_queue, set_is_automated

logger = get_logger()

class ControllableActionView(views.APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, controllable_action_id):
        """
        If incoming camera data is valid, update the camera by given id with the incoming data
        If the interval was updated, reschedule the job of the camera
        :param request:
        :param camera_id: id of the camera to update
        :return:
        """
        pass
        """
        if not is_member(request.user, get_organization_by_camera_id(camera_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)

        from farminsight_dashboard_backend.services import CameraScheduler
        serializer = CameraSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_interval = get_camera_by_id(camera_id).intervalSeconds
        old_is_active = get_camera_by_id(camera_id).isActive

        # Update the camera
        camera = update_camera(camera_id, serializer.data)

        logger.info("Camera updated successfully", extra={'resource_id': camera_id})

        # Update the scheduler
        if camera.intervalSeconds != old_interval or camera.isActive != old_is_active:
            CameraScheduler.get_instance().reschedule_camera_job(camera.id, camera.intervalSeconds)

        return Response(CameraSerializer(camera).data, status=status.HTTP_200_OK)
        """

    def delete(self, request, controllable_action_id):
        """
        Delete a controllable action by given id
        User must be an admin.
        :param request:
        :param controllable_action_id:
        :return:
        """
        if not is_admin(request.user, get_organization_by_controllable_action_id(controllable_action_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # TODO remove the trigger from any schedules or queues

        controllable_action = get_controllable_action_by_id(controllable_action_id)
        fpf_id = controllable_action.FPF_id

        delete_controllable_action(controllable_action)

        logger.info("Controllable action deleted successfully", extra={'resource_id': fpf_id})

        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_controllable_action(request):
    """
    An admin creates a new controllable action
    :param request:
    :return:
    """
    fpf_id = request.data.get('fpfId')

    if not is_admin(request.user, get_organization_by_fpf_id(fpf_id)):
        return Response(status=status.HTTP_403_FORBIDDEN)

    get_fpf_by_id(fpf_id)

    controllable_action = ControllableActionSerializer(create_controllable_action(fpf_id, request.data)).data

    logger.info("Controllable action created successfully", extra={'resource_id': fpf_id})

    # TODO add action to scheduler or other trigger queue (?)

    return Response(controllable_action, status=status.HTTP_201_CREATED)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_controllable_action(request, controllable_action_id, trigger_id):
    """
    An admin executes a controllable action trigger
    trigger_id=='auto' will execute the automatic triggers if present
    :param trigger_id:
    :param controllable_action_id:
    :param request:
    :return:
    """

    if not is_admin(request.user, get_organization_by_controllable_action_id(controllable_action_id)):
        return Response(status=status.HTTP_403_FORBIDDEN)

    # The user set the controllable action to automatic
    if trigger_id == "auto":
        set_is_automated(controllable_action_id, True)
        create_action_in_queue({'actionId': controllable_action_id})

    else: # The user activated a manual trigger
    # TODO update the manual trigger e.g. if input is a number (actionValue) it has to be set and saved before the

        set_is_automated(controllable_action_id, False)
        create_action_in_queue({'actionId':controllable_action_id, 'actionTriggerId':trigger_id})

    process_action_queue()
    return Response(status=status.HTTP_200_OK)
