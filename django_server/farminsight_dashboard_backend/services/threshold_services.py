from farminsight_dashboard_backend.models import Threshold
from farminsight_dashboard_backend.serializers import ThresholdSerializer


def create_threshold(data) -> ThresholdSerializer:
    serializer = ThresholdSerializer(data=data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        return serializer


def update_threshold(threshold_id:str, data) -> ThresholdSerializer:
    threshold = Threshold.objects.get(id=threshold_id)
    serializer = ThresholdSerializer(threshold, data=data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        return serializer


def remove_threshold(threshold_id:str):
    threshold = Threshold.objects.get(id=threshold_id)
    print("Wo genau")
    threshold.delete()

