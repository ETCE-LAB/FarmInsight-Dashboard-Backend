import uuid
from django.db import models
from django.db.models import Max

from .hardware import Hardware
from .fpf import FPF


def get_order_index_default():
    if Camera.objects.all().count() == 0:
        new_order_default = 0
    else:
        new_order_default = Camera.objects.all().aggregate(Max('orderIndex'))['orderIndex__max'] + 1
    return new_order_default


class Camera(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)
    location = models.CharField(max_length=256)
    modelNr = models.CharField(max_length=256)
    resolution = models.CharField(max_length=256)
    isActive = models.BooleanField(default=False)
    intervalSeconds = models.IntegerField()
    snapshotUrl = models.CharField(max_length=256)
    livestreamUrl = models.CharField(max_length=256)
    FPF = models.ForeignKey(FPF, related_name='cameras', on_delete=models.CASCADE)
    orderIndex = models.IntegerField(default=get_order_index_default)
    hardware = models.ForeignKey(Hardware, on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        ordering = ['orderIndex']

    def __str__(self):
        return f"{self.FPF.name}: {self.name} {self.modelNr} {self.location}"
