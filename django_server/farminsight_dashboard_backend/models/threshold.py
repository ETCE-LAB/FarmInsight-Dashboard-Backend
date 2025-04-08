import uuid
from django.db import models
from .sensor import Sensor


class Threshold(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lowerBound = models.FloatField(blank=True, null=True)
    upperBound = models.FloatField(blank=True, null=True)
    color = models.CharField(max_length=64, blank=True)
    description = models.CharField(max_length=512, blank=True)
    sensor = models.ForeignKey(Sensor, related_name='Threshold', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.Sensor.name}: {self.lowerBound} {self.UpperBound}  {self.color} {self.description[:10]}"
