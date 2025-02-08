from rest_framework.exceptions import PermissionDenied

from farminsight_dashboard_backend.models import Userprofile, Harvest, GrowingCycle
from farminsight_dashboard_backend.services import is_user_part_of_fpf, get_fpf_by_id
from farminsight_dashboard_backend.serializers import HarvestSerializer


def create_harvest(data, creating_user: Userprofile) -> HarvestSerializer:
    growing_cycle = GrowingCycle.objects.get(id=data['growingCycleId'])
    if not is_user_part_of_fpf(growing_cycle.FPF_id, creating_user):
        raise PermissionDenied()

    serializer = HarvestSerializer(data=data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        return serializer


def update_harvest(harvest_id:str, data, creating_user: Userprofile) -> HarvestSerializer:
    growing_cycle = GrowingCycle.objects.get(id=data['growingCycleId'])
    if not is_user_part_of_fpf(growing_cycle.FPF_id, creating_user):
        raise PermissionDenied()

    harvest = Harvest.objects.get(id=harvest_id)
    serializer = HarvestSerializer(harvest, data=data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        return serializer


def remove_harvest(harvest_id:str, deleting_user: Userprofile):
    harvest = Harvest.objects.get(id=harvest_id)
    if is_user_part_of_fpf(harvest.growingCycle.FPF_id, deleting_user):
        harvest.delete()
    else:
        raise PermissionDenied()


def get_harvests_by_growing_cycle_id(growing_cycle_id: str) -> HarvestSerializer:
    growing_cycle = GrowingCycle.objects.get(id=growing_cycle_id)
    return HarvestSerializer(growing_cycle.harvests, many=True)
