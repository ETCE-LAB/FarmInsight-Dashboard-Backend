import uuid
from django.db import models
from django.db.models import Max

from .hardware import Hardware
from .fpf import FPF


def get_order_index_default():
    if Sensor.objects.all().count() == 0:
        new_order_default = 0
    else:
        new_order_default = Sensor.objects.all().aggregate(Max('orderIndex'))['orderIndex__max'] + 1
    return new_order_default


class Sensor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)
    location = models.CharField(max_length=256)
    unit = models.CharField(max_length=256, blank=True)
    parameter = models.CharField(max_length=256, blank=True)
    modelNr = models.CharField(max_length=256, blank=True)
    isActive = models.BooleanField(default=False)
    intervalSeconds = models.IntegerField()
    FPF = models.ForeignKey(FPF, related_name='sensors', on_delete=models.CASCADE)
    aggregate = models.BooleanField(default=False)
    orderIndex = models.IntegerField(default=get_order_index_default)
    hardware = models.ForeignKey(Hardware, on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        ordering = ['orderIndex']

    def __str__(self):
        return f"{self.FPF.name}: {self.name} {self.modelNr}  {self.parameter} {self.unit}"
