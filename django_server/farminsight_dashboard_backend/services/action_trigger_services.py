from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.models import ControllableAction, FPF
from farminsight_dashboard_backend.serializers import ControllableActionSerializer, ActionTriggerSerializer
from django.shortcuts import get_object_or_404

def create_action_trigger(action_trigger_data:dict) -> ControllableAction:
    """
    Create a new trigger action for a given controllable action.
    :param action_trigger_data: trigger data
    :return: Newly created trigger instance
    """

    serializer = ActionTriggerSerializer(data=action_trigger_data, partial=True)
    serializer.is_valid(raise_exception=True)

    return serializer.save()