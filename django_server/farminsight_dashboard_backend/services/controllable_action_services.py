import uuid

from django.shortcuts import get_object_or_404

from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.models import ControllableAction, FPF
from farminsight_dashboard_backend.serializers import ControllableActionSerializer
from .fpf_connection_services import post_action, put_action, delete_action


def get_actions(fpf_id: str) -> ControllableActionSerializer:
    actions = ControllableAction.objects.filter(FPF_id=fpf_id)
    return ControllableActionSerializer(actions, many=True)


def get_active_controllable_action_by_id(controllable_action_id:str) -> ControllableAction:
    """
    Get active controllable_action by id
    :param controllable_action_id:
    :return: ControllableAction
    :throws: NotFoundException
    """
    try:
        controllable_action =  ControllableAction.objects.get(id=controllable_action_id)
        if not controllable_action.isActive:
            raise NotFoundException(f'Controllable Action is not active.')
        return controllable_action
    except ControllableAction.DoesNotExist:
        raise NotFoundException(f'Controllable Action with id: {controllable_action_id} was not found.')


def get_controllable_action_by_id(controllable_action_id:str) -> ControllableAction:
    """
    Get controllable_action by id
    :param controllable_action_id:
    :return: ControllableAction
    :throws: NotFoundException
    """
    try:
        return ControllableAction.objects.get(id=controllable_action_id)
    except ControllableAction.DoesNotExist:
        raise NotFoundException(f'Controllable action with id: {controllable_action_id} was not found.')


def create_controllable_action(fpf_id: str, controllable_action_data: dict) -> ControllableActionSerializer:
    """
    Create a new controllable_action by FPF ID and controllable_action data.
    :param fpf_id: ID of the controllable_action's FPF
    :param controllable_action_data: controllable_action data
    :return: Newly created controllable_action instance
    """
    try:
        fpf = FPF.objects.get(id=fpf_id)
    except FPF.DoesNotExist:
        raise ValueError("FPF with the given ID does not exist")

    serializer = ControllableActionSerializer(data=controllable_action_data, partial=True)
    if serializer.is_valid(raise_exception=True):
        action_id = uuid.uuid4()

        controllable_action_data['id'] = str(action_id)
        post_action(fpf_id, controllable_action_data)

        action = ControllableAction(**serializer.validated_data)
        action.id = action_id
        action.FPF = fpf
        action.save()
        return ControllableActionSerializer(action)


def update_controllable_action(controllable_action_id: str, controllable_action_data: any) -> ControllableActionSerializer:
    """
    Update controllable_action by id and controllable_action data
    :param controllable_action_id: controllable_action to update
    :param controllable_action_data: new controllable_action data
    :return: Updated controllable_action
    """
    controllable_action = ControllableAction.objects.get(id=controllable_action_id)
    serializer = ControllableActionSerializer(controllable_action, data=controllable_action_data, partial=True)

    if serializer.is_valid(raise_exception=True):
        try:
            put_action(controllable_action.FPF_id, controllable_action_id, controllable_action_data)
        except NotFoundException:
            # TODO: TEMPORARY - should only be used for a time when rolling out energy saving, to auto post the camera to the fpf
            post_action(controllable_action.FPF_id, controllable_action_data)
        serializer.save()
    return serializer


def delete_controllable_action(controllable_action: ControllableAction):
    """
    Delete controllable_action
    :param controllable_action: controllable_action to delete
    """
    delete_action(str(controllable_action.FPF_id), str(controllable_action.id))
    controllable_action.delete()


def set_is_automated(controllable_action_id:str, is_automated:bool) -> ControllableAction:
    controllable_action = get_object_or_404(ControllableAction, id=controllable_action_id)

    controllable_action.isAutomated = is_automated
    controllable_action.save()

    return controllable_action


def set_controllable_action_order(ids: list[str]):
    items = ControllableAction.objects.filter(id__in=ids)
    for item in items:
        item.orderIndex = ids.index(str(item.id))

    ControllableAction.objects.bulk_update(items, ['orderIndex'])
