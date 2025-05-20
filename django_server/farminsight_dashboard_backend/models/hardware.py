import uuid
from django.db import models
from .fpf import FPF

class Hardware(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)
    FPF = models.ForeignKey(FPF, related_name='hardware', on_delete=models.CASCADE)
    orderIndex = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.FPF.name}: {self.name}"
