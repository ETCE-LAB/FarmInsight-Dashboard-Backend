import uuid
from django.db import models
from .organization import Organization
from .location import Location
from farminsight_dashboard_backend.utils import generate_random_api_key


class FPF(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)
    isPublic = models.BooleanField(default=False)
    sensorServiceIp = models.CharField(max_length=256)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    apiKey = models.CharField(max_length=64, default=generate_random_api_key)
    apiKeyValidUntil = models.DateTimeField(null=True, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True, null=True)
    location = models.ForeignKey(Location, blank=True, null=True, on_delete=models.SET_NULL)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'name'], name='unique_fpf_name_per_organization')
        ]

    def __str__(self):
        return f"{self.organization.name}: {self.name}"
