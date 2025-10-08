import uuid

from django.shortcuts import get_object_or_404

from farminsight_dashboard_backend.models import ActionTrigger
from farminsight_dashboard_backend.serializers import ActionTriggerSerializer
from .fpf_connection_services import post_action_trigger, put_action_trigger
from ..exceptions import NotFoundException


def create_action_trigger(action_trigger_data: dict) -> ActionTriggerSerializer:
    """
    Create a new trigger action for a given controllable action.
    :param action_trigger_data: trigger data
    :return: Newly created trigger instance
    """
    serializer = ActionTriggerSerializer(data=action_trigger_data, partial=True)
    if serializer.is_valid(raise_exception=True):
        trigger_id = uuid.uuid4()

        action_trigger_data['id'] = str(trigger_id)
        post_action_trigger(str(action_trigger_data.get('fpfId')), action_trigger_data)

        trigger = ActionTrigger(**serializer.validated_data)
        trigger.id = trigger_id
        trigger.save()
        return ActionTriggerSerializer(trigger)


def update_action_trigger(action_trigger_id, data) -> ActionTriggerSerializer:
    action_trigger = ActionTrigger.objects.get(id=action_trigger_id)
    data["actionId"] = str(action_trigger.action_id)
    data["id"] = str(action_trigger_id)
    serializer = ActionTriggerSerializer(action_trigger, data=data)

    if serializer.is_valid(raise_exception=True):
        try:
            put_action_trigger(str(action_trigger.action.FPF_id), str(action_trigger_id), data)
        except NotFoundException:
            # TODO: TEMPORARY - should only be used for a time when rolling out energy saving
            post_action_trigger(str(action_trigger.action.FPF_id), data)
        serializer.save()
    return serializer


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
