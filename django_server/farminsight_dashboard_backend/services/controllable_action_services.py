
from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.models import ControllableAction, FPF
from farminsight_dashboard_backend.serializers import ControllableActionSerializer
from django.shortcuts import get_object_or_404

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
            raise NotFoundException(f'Camera with id: {controllable_action_id} is not active.')
        return controllable_action
    except ControllableAction.DoesNotExist:
        raise NotFoundException(f'Camera with id: {controllable_action_id} was not found.')

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

def create_controllable_action(fpf_id:str, controllable_action_data:dict) -> ControllableAction:
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
    serializer.is_valid(raise_exception=True)

    return serializer.save(FPF=fpf)

def update_controllable_action(controllable_action_id:str, controllable_action_data:any) -> ControllableAction:
    """
    Update controllable_action by id and controllable_action data
    :param controllable_action_id: controllable_action to update
    :param controllable_action_data: new controllable_action data
    :return: Updated controllable_action
    """
    controllable_action = ControllableAction.objects.get(id=controllable_action_id)
    serializer = ControllableActionSerializer(controllable_action, data=controllable_action_data, partial=True)

    if serializer.is_valid(raise_exception=True):
        serializer.save()
    return serializer


def delete_controllable_action(controllable_action: ControllableAction):
    """
    Delete controllable_action
    :param controllable_action: controllable_action to delete
    """
    controllable_action.delete()

def set_is_automated(controllable_action_id:str, is_automated:bool) -> ControllableAction:

    controllable_action = get_object_or_404(ControllableAction, id=controllable_action_id)

    controllable_action.isAutomated = is_automated
    controllable_action.save()

    return controllable_action