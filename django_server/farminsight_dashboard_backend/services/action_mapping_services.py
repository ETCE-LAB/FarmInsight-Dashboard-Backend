from farminsight_dashboard_backend.models import FPF, ControllableAction, ActionMapping, ResourceManagementModel


def create_action_mappings(fpf_id: str, model_id: str, actions_data: list):
    """
    Create ActionMappings for a given ResourceManagementModel.
    """
    try:
        fpf = FPF.objects.get(id=fpf_id)
    except FPF.DoesNotExist:
        raise ValueError("FPF with the given ID does not exist")

    try:
        resource_model = ResourceManagementModel.objects.get(id=model_id)
    except ResourceManagementModel.DoesNotExist:
        raise ValueError("ResourceManagementModel with the given ID does not exist")

    created_mappings = []

    for action in actions_data:
        # Adjust key names based on your frontend payload
        controllable_action_id = action.get("controllable_action_id") or action.get("controllable_action", {}).get("id")
        if not controllable_action_id:
            raise ValueError("Missing controllable_action_id in action data")

        try:
            controllable_action = ControllableAction.objects.get(id=controllable_action_id)
        except ControllableAction.DoesNotExist:
            raise ValueError(f"ControllableAction with ID {controllable_action_id} does not exist")

        mapping = ActionMapping.objects.create(
            controllable_action=controllable_action,
            action_name=action["name"],
            resource_management_model=resource_model,
        )
        created_mappings.append(mapping)

    return created_mappings