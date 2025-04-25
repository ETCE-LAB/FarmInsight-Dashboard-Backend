from farminsight_dashboard_backend.models import ActionTrigger
from farminsight_dashboard_backend.serializers import ActionTriggerSerializer
from django.shortcuts import get_object_or_404

def create_action_trigger(action_trigger_data:dict) -> ActionTriggerSerializer.data:
    """
    Create a new trigger action for a given controllable action.
    :param action_trigger_data: trigger data
    :return: Newly created trigger instance
    """

    serializer = ActionTriggerSerializer(data=action_trigger_data, partial=True)
    serializer.is_valid(raise_exception=True)

    return serializer.save()


def get_action_trigger(action_trigger_id):
    return get_object_or_404(ActionTrigger, pk=action_trigger_id)

def get_all_auto_action_triggers(action_id):
    """
    Returns all active, not-manual triggers.
    If an action_id is provided, return only the triggers of the action.
    :return:
    """
    if not action_id:
        return ActionTrigger.objects.filter(
            isActive=True
        ).exclude(
            type='manual'
        )
    else:
        return ActionTrigger.objects.filter(
            isActive=True,
            action_id=action_id
        ).exclude(
            type='manual'
        )