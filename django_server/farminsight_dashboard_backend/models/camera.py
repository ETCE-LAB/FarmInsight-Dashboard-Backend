import uuid
from django.db import models
from .fpf import FPF


class Camera(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)
    location = models.CharField(max_length=256)
    modelNr = models.CharField(max_length=256)
    resolution = models.CharField(max_length=256)
    isActive = models.BooleanField(default=False)
    intervalSeconds = models.IntegerField()
    FPF = models.ForeignKey(FPF, related_name='cameras', on_delete=models.CASCADE)
