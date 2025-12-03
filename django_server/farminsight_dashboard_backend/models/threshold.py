import uuid
from django.db import models
from .sensor import Sensor


class Threshold(models.Model):
    THRESHOLD_TYPES = [
        ("sensor", "Sensor"),
        ("model", "Model"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lowerBound = models.FloatField(blank=True, null=True)
    upperBound = models.FloatField(blank=True, null=True)
    color = models.CharField(max_length=64, blank=True)
    description = models.CharField(max_length=512, blank=True)
    sensor = models.ForeignKey(Sensor, related_name='thresholds', on_delete=models.CASCADE, blank=True, null=True, default=None)
    thresholdType = models.CharField(max_length=64, choices=THRESHOLD_TYPES)
    resourceManagementModel = models.ForeignKey('ResourceManagementModel', related_name='thresholds', on_delete=models.CASCADE, blank=True, null=True, default=None)

    def __str__(self):
        name = self.sensor.name if self.thresholdType == "sensor" else self.resourceManagementModel.name
        return f"{name}: {self.lowerBound} {self.upperBound} {self.color} {self.description[:10]}"

