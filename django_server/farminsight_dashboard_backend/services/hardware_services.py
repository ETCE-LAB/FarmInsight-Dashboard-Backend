from farminsight_dashboard_backend.models import Hardware

def get_hardware_for_fpf(fpf_id):
    """
    Returns all distinct Hardware objects used by ControllableActions under the given FPF.
    """
    return Hardware.objects.filter(actions__FPF__id=fpf_id).distinct()

def create_hardware(hardware_name, fpf_id):
    """
    Creates a new Hardware object from the given data.
    """

    if not hardware_name:
        raise ValueError("Hardware name must not be empty.")

    existing_hardware = Hardware.objects.filter(
        name=hardware_name,
        FPF_id=fpf_id
    ).first()

    if existing_hardware:
        return existing_hardware

    try:
        hardware = Hardware.objects.create(
            name=hardware_name,
            FPF_id=fpf_id
        )
        return hardware
    except Exception as e:
        raise RuntimeError(f"Error creating the Hardware: {str(e)}")


def set_hardware_order(ids: list[str]):
    items = Hardware.objects.filter(id__in=ids)
    for item in items:
        item.orderIndex = ids.index(str(item.id))

    Hardware.objects.bulk_update(items, ['orderIndex'])