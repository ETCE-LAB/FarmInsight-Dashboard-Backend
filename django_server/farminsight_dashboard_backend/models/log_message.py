import uuid
from django.db import models
from django.utils import timezone

from . import Organization, Camera
from .sensor import Sensor
from .fpf import FPF


class LogMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    createdAt = models.DateTimeField(default=timezone.now)
    relatedResourceId = models.UUIDField(blank=True, null=True)
    logLevel = models.CharField(max_length=24)
    message = models.TextField()

    def __str__(self):
        if self.relatedResourceId is not None:
            sensor = Sensor.objects.filter(id=self.relatedResourceId).first()
            if sensor is not None:
                return f"sensor: {sensor} --- {self.createdAt} {self.logLevel}: {self.message}"
            fpf = FPF.objects.filter(id=self.relatedResourceId).first()
            if fpf is not None:
                return f"FPF: {fpf} --- {self.createdAt} {self.logLevel}: {self.message}"
            camera = Camera.objects.filter(id=self.relatedResourceId).first()
            if camera is not None:
                return f"camera: {camera} --- {self.createdAt} {self.logLevel}: {self.message}"
            org = Organization.objects.filter(id=self.relatedResourceId).first()
            if org is not None:
                return f"ORG: {org} --- {self.createdAt} {self.logLevel}: {self.message}"

        return f"{self.createdAt} {self.logLevel}: {self.message}"