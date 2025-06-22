import uuid
from django.db import models
from django.db.models import Max

from .fpf import FPF
from .hardware import Hardware


def get_order_index_default():
    if ControllableAction.objects.all().count() == 0:
        new_order_default = 0
    else:
        new_order_default = ControllableAction.objects.all().aggregate(Max('orderIndex'))['orderIndex__max'] + 1
    return new_order_default


class ControllableAction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)
    actionClassId = models.UUIDField()
    isActive = models.BooleanField(default=False)
    isAutomated = models.BooleanField(default=False)
    maximumDurationSeconds = models.IntegerField(default=0)
    additionalInformation = models.TextField(blank=True)
    FPF = models.ForeignKey(FPF, related_name='actions', on_delete=models.CASCADE)
    hardware = models.ForeignKey(Hardware, related_name='actions', on_delete=models.SET_NULL, blank=True, null=True)
    orderIndex = models.IntegerField(default=get_order_index_default)

    class Meta:
        ordering = ['orderIndex']

    def __str__(self):
        return f"{self.FPF.name}: {self.name} active: {self.isActive}  auto: {self.isAutomated}"
