import uuid
from django.db import models
from django.db.models import Max
from .organization import Organization
from .location import Location
from farminsight_dashboard_backend.utils import generate_random_api_key


def get_order_index_default():
    if FPF.objects.all().count() == 0:
        new_order_default = 0
    else:
        new_order_default = FPF.objects.all().aggregate(Max('orderIndex'))['orderIndex__max'] + 1
    return new_order_default


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
    orderIndex = models.IntegerField(default=get_order_index_default)
    isActive = models.BooleanField(default=True)
    
    # Energy Management Configuration
    energyGridConnectThreshold = models.FloatField(
        default=11.0,
        help_text="Battery percentage at which to connect to grid"
    )
    energyShutdownThreshold = models.FloatField(
        default=10.0,
        help_text="Battery percentage at which to shutdown non-critical consumers"
    )
    energyWarningThreshold = models.FloatField(
        default=20.0,
        help_text="Battery percentage for warning status"
    )
    energyBatteryMaxWh = models.FloatField(
        default=1600.0,
        help_text="Maximum battery capacity in Wh (default 1.6kWh = 1600Wh)"
    )
    energyGridDisconnectThreshold = models.FloatField(
        default=50.0,
        help_text="Battery percentage at which to disconnect from grid (when charging complete)"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'name'], name='unique_fpf_name_per_organization')
        ]
        ordering = ['orderIndex']

    def __str__(self):
        return f"{self.organization.name}: {self.name}"
