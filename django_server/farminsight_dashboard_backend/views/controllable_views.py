from functools import partial

from rest_framework import views
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from farminsight_dashboard_backend.serializers.controllable_action_serializer import ControllableActionSerializer
from farminsight_dashboard_backend.services.action_queue_services import get_active_state_of_action, \
    process_action_queue
from farminsight_dashboard_backend.services.trigger import create_manual_triggered_action_in_queue

from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.services import get_fpf_by_id, \
    get_organization_by_fpf_id, is_admin, create_controllable_action, delete_controllable_action, \
    get_controllable_action_by_id, get_organization_by_controllable_action_id, \
    set_is_automated, create_auto_triggered_actions_in_queue, create_manual_triggered_action_in_queue, is_member, \
    update_controllable_action
    set_is_automated, \
    get_action_trigger, create_auto_triggered_actions_in_queue, create_hardware

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

        if not is_member(request.user, get_organization_by_controllable_action_id(controllable_action_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # Update the camera
        controllable_action = update_controllable_action(controllable_action_id, request.data)
        logger.info("Controllable Action updated successfully", extra={'resource_id': controllable_action_id})

        return Response(request.data, status=status.HTTP_200_OK)


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

    if request.data.get('hardware').get('name'):
        hardware = create_hardware(request.data.get('hardware').get('name'), fpf_id)
        request.data['hardwareId'] = hardware.id

    controllable_action = ControllableActionSerializer(create_controllable_action(fpf_id, request.data), partial=True).data

    logger.info("Controllable action created successfully", extra={'resource_id': fpf_id})

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

    if trigger_id == "auto": # The user set the controllable action to automatic
        set_is_automated(controllable_action_id, True)
        # Check if the trigger for the affected action can trigger and process the queue

        # get trigger type and refresh the creation
        create_auto_triggered_actions_in_queue(controllable_action_id)


    else: # The user activated a manual trigger

        # Check if the action is already on manual mode and the current active action is the same one.
        # In this case, the action goes back to auto mode as the user deactivated the manual trigger.
        # This gives room for all other auto triggers related to the same hardware to execute.

        active_state = get_active_state_of_action(controllable_action_id)

        # Completely new action
        if active_state is None:
            set_is_automated(controllable_action_id, False)
            create_manual_triggered_action_in_queue(controllable_action_id, trigger_id)

        #if active_state is not None and get_controllable_action_by_id(controllable_action_id).isAutomated == False and (active_state.trigger.id is None or active_state.trigger.id == trigger_id):
        elif active_state is not None and (get_controllable_action_by_id(controllable_action_id).isAutomated == False and str(active_state.trigger.id) == trigger_id):
            set_is_automated(controllable_action_id, True)
            process_action_queue()

        # The user selected a new manual trigger, different from the current active state
        else:
            set_is_automated(controllable_action_id, False)
            create_manual_triggered_action_in_queue(controllable_action_id, trigger_id)

    return Response(status=status.HTTP_200_OK)
