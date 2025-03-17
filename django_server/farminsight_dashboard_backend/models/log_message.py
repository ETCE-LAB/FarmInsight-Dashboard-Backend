import uuid
from django.db import models
from django.utils import timezone


class LogMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    createdAt = models.DateTimeField(default=timezone.now)
    relatedResourceId = models.UUIDField(blank=True, null=True)
    logLevel = models.CharField(max_length=24)
    message = models.TextField()

    def __str__(self):
        return f"{self.createdAt} {self.logLevel}: {self.message}"