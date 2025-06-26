from farminsight_dashboard_backend.models import Userprofile, GrowingCycle
from farminsight_dashboard_backend.services import get_fpf_by_id
from farminsight_dashboard_backend.serializers import GrowingCycleSerializer


def create_growing_cycle(data) -> GrowingCycleSerializer:
    serializer = GrowingCycleSerializer(data=data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        return serializer


def update_growing_cycle(growing_cycle_id:str, data) -> GrowingCycleSerializer:
    growing_cycle = GrowingCycle.objects.get(id=growing_cycle_id)
    serializer = GrowingCycleSerializer(growing_cycle, data=data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        return serializer


def remove_growing_cycle(growing_cycle_id:str):
    growing_cycle = GrowingCycle.objects.get(id=growing_cycle_id)
    growing_cycle.delete()


def get_growing_cycles_by_fpf_id(fpf_id: str) -> GrowingCycleSerializer:
    fpf = get_fpf_by_id(fpf_id)
    return GrowingCycleSerializer(fpf.growingCycles, many=True)


def set_growing_cycle_order(ids: list[str]):
    items = GrowingCycle.objects.filter(id__in=ids)
    for item in items:
        item.orderIndex = ids.index(str(item.id))

    GrowingCycle.objects.bulk_update(items, ['orderIndex'])