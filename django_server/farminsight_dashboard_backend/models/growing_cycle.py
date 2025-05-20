import uuid
from django.db import models
from django.db.models import Max
from django.utils import timezone
from .fpf import FPF


def get_order_index_default():
    if GrowingCycle.objects.all().count() == 0:
        new_order_default = 0
    else:
        new_order_default = GrowingCycle.objects.all().aggregate(Max('orderIndex'))['orderIndex__max'] + 1
    return new_order_default


class GrowingCycle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    startDate = models.DateTimeField(default=timezone.now)
    endDate = models.DateTimeField(blank=True, null=True)
    plants = models.CharField(max_length=256)
    note = models.CharField(max_length=256, blank=True)
    FPF = models.ForeignKey(FPF, related_name='growingCycles', on_delete=models.CASCADE)
    orderIndex = models.IntegerField(default=get_order_index_default)

    class Meta:
        ordering = ['orderIndex']

    def __str__(self):
        return f"{self.FPF.name}: {self.plants} {self.startDate}"
