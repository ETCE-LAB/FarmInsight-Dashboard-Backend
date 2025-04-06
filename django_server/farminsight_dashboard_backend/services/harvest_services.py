from farminsight_dashboard_backend.models import Harvest, GrowingCycle
from farminsight_dashboard_backend.serializers import HarvestSerializer


def create_harvest(data) -> HarvestSerializer:
    serializer = HarvestSerializer(data=data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        return serializer


def update_harvest(harvest_id:str, data) -> HarvestSerializer:
    harvest = Harvest.objects.get(id=harvest_id)
    serializer = HarvestSerializer(harvest, data=data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        return serializer


def remove_harvest(harvest_id:str):
    harvest = Harvest.objects.get(id=harvest_id)
    harvest.delete()


def get_harvests_by_growing_cycle_id(growing_cycle_id: str) -> HarvestSerializer:
    growing_cycle = GrowingCycle.objects.get(id=growing_cycle_id)
    return HarvestSerializer(growing_cycle.harvests, many=True)
