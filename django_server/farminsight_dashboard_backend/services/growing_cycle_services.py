from rest_framework.exceptions import PermissionDenied

from farminsight_dashboard_backend.models import Userprofile, GrowingCycle
from farminsight_dashboard_backend.services import is_user_part_of_fpf, get_fpf_by_id
from farminsight_dashboard_backend.serializers import GrowingCycleSerializer


def create_growing_cycle(data, creating_user: Userprofile) -> GrowingCycleSerializer:
    if not is_user_part_of_fpf(data['fpfId'], creating_user):
        raise PermissionDenied()

    serializer = GrowingCycleSerializer(data=data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        return serializer


def update_growing_cycle(growing_cycle_id:str, data, creating_user: Userprofile) -> GrowingCycleSerializer:
    if not is_user_part_of_fpf(data['fpfId'], creating_user):
        raise PermissionDenied()

    growing_cycle = GrowingCycle.objects.get(id=growing_cycle_id)
    serializer = GrowingCycleSerializer(growing_cycle, data=data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        return serializer


def remove_growing_cycle(growing_cycle_id:str, deleting_user: Userprofile):
    growing_cycle = GrowingCycle.objects.get(id=growing_cycle_id)
    if is_user_part_of_fpf(growing_cycle.FPF_id, deleting_user):
        growing_cycle.delete()
    else:
        raise PermissionDenied()


def get_growing_cycles_by_fpf_id(fpf_id: str) -> GrowingCycleSerializer:
    fpf = get_fpf_by_id(fpf_id)
    return GrowingCycleSerializer(fpf.growingCycles, many=True)
