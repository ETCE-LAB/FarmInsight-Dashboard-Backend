import uuid
from django.db import models
from django.db.models import Max

from .fpf import FPF


def get_order_index_default():
    if Hardware.objects.all().count() == 0:
        new_order_default = 0
    else:
        new_order_default = Hardware.objects.all().aggregate(Max('orderIndex'))['orderIndex__max'] + 1
    return new_order_default


class Hardware(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)
    FPF = models.ForeignKey(FPF, related_name='hardware', on_delete=models.CASCADE)
    orderIndex = models.IntegerField(default=get_order_index_default)
    pingEndpoint = models.CharField(blank=True, max_length=256, null=True)

    class Meta:
        ordering = ['orderIndex']

    def __str__(self):
        return f"{self.FPF.name}: {self.name}"
