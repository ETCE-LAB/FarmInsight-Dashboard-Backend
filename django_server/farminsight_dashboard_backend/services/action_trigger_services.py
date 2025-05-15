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


def get_all_auto_timeOfDay_action_triggers(action_id):
    """
    Returns all active, not-manual timeOfDay triggers.
    :param action_id:
    :return:
    """
    if not action_id:
        return ActionTrigger.objects.filter(
            isActive=True,
            type='timeOfDay'
        )
    else:
        return ActionTrigger.objects.filter(
            isActive=True,
            action_id=action_id,
            type='timeOfDay'
        )

def get_all_auto_interval_triggers(action_id=None):
    if action_id:
        return ActionTrigger.objects.filter(action__id=action_id, type="interval", isActive=True)
    return ActionTrigger.objects.filter(type="interval", isActive=True)

def get_all_active_auto_triggers(action_id=None):
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

def update_action_trigger(actionTrigger_id, data) -> ActionTriggerSerializer:
    """
    Update the given organization with the given data if the user has sufficient permissions.
    :param org_id: organization id to update
    :param data: new organization data
    :return:
    """
    actionTrigger = ActionTrigger.objects.get(id=actionTrigger_id)
    data["actionId"] = actionTrigger.action_id#
    data["id"] = actionTrigger_id
    serializer = ActionTriggerSerializer(actionTrigger, data=data)

    if serializer.is_valid(raise_exception=True):
        serializer.save()
        return serializer