import uuid
from django.db import models
from .fpf import FPF
from .hardware import Hardware


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
    orderIndex = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.FPF.name}: {self.name} active: {self.isActive}  auto: {self.isAutomated}"
