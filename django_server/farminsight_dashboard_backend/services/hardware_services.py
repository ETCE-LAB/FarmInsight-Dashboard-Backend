from farminsight_dashboard_backend.models import Hardware, ControllableAction

def get_hardware_for_fpf(fpf_id):
    """
    Returns all distinct Hardware objects used by ControllableActions under the given FPF.
    """
    return Hardware.objects.filter(actions__FPF__id=fpf_id).distinct()
