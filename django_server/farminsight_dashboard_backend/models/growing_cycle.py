import uuid
from django.db import models
from django.utils import timezone
from .fpf import FPF


class GrowingCycle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    startDate = models.DateTimeField(default=timezone.now)
    endDate = models.DateTimeField(blank=True, null=True)
    plants = models.CharField(max_length=256)
    note = models.CharField(max_length=256, blank=True)
    FPF = models.ForeignKey(FPF, related_name='growingCycles', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.FPF.name}: {self.plants} {self.startDate}"
