import uuid
from django.db import models
from django.utils import timezone
from .growing_cycle import GrowingCycle


class Harvest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateTimeField(default=timezone.now)
    amountInKg = models.FloatField(default=0)
    note = models.CharField(max_length=256, blank=True)
    growingCycle = models.ForeignKey(GrowingCycle, related_name='harvests', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.growingCycle.FPF.name}: {self.growingCycle.plants} {self.date} {self.amountInKg}kg"
