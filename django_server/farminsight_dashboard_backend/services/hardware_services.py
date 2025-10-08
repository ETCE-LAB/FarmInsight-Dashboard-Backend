import uuid

from farminsight_dashboard_backend.models import Hardware
from farminsight_dashboard_backend.serializers import HardwareSerializer
from farminsight_dashboard_backend.exceptions import NotFoundException
from .fpf_connection_services import post_hardware, put_hardware, delete_hardware


def get_hardware_for_fpf(fpf_id):
    """
    Returns all distinct Hardware objects used by ControllableActions under the given FPF.
    """
    return Hardware.objects.filter(FPF__id=fpf_id).distinct()


def create_hardware_at_fpf(fpf_id: str, hardware_id: str, hardware_name: str):
    data = {'name': hardware_name, 'id': hardware_id }
    try:
        post_hardware(fpf_id, data)
    except Exception as e:
        raise Exception(f"Unable to create Hardware at FPF. {e}")


def get_or_create_hardware(hardware_name, fpf_id):
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

    hardware_id = uuid.uuid4()
    create_hardware_at_fpf(fpf_id, str(hardware_id), hardware_name)

    try:
        hardware = Hardware.objects.create(
            id=hardware_id,
            name=hardware_name,
            FPF_id=fpf_id
        )
        return hardware
    except Exception as e:
        raise RuntimeError(f"Error creating the Hardware: {str(e)}")


def create_hardware(data) -> HardwareSerializer:
    serializer = HardwareSerializer(data=data)
    if serializer.is_valid(raise_exception=True):
        hardware_id = uuid.uuid4()
        create_hardware_at_fpf(data['FPF'], str(hardware_id), data['name'])

        hardware = Hardware(**serializer.validated_data)
        hardware.id = hardware_id
        hardware.save()
        return HardwareSerializer(hardware) # when trying to return a serializer that hasn't used save
        # it creates an exception on serializing it back in the response


def set_hardware_order(ids: list[str]) -> HardwareSerializer:
    items = Hardware.objects.filter(id__in=ids)
    for item in items:
        item.orderIndex = ids.index(str(item.id))

    Hardware.objects.bulk_update(items, ['orderIndex'])
    return HardwareSerializer(items, many=True)


def update_hardware(hardware_id: str, data) -> HardwareSerializer:
    hardware = Hardware.objects.get(id=hardware_id)
    serializer = HardwareSerializer(hardware, data=data)
    if serializer.is_valid(raise_exception=True):
        try:
            put_hardware(str(hardware.FPF_id), hardware_id, data)
        except NotFoundException:
            # TODO: TEMPORARY - should only be used for a time when rolling out energy saving
            create_hardware_at_fpf(str(hardware.FPF_id), hardware_id, data.get('name'))

        serializer.save()
    return serializer


def remove_hardware(hardware_id: str):
    hardware = Hardware.objects.get(id=hardware_id)
    delete_hardware(str(hardware.FPF_id), hardware_id)
    hardware.delete()
