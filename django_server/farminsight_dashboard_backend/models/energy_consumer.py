import uuid
from django.db import models
from .fpf import FPF


class EnergyConsumer(models.Model):
    """
    Represents an energy consuming device within an FPF.
    Priority: 1 = highest priority (critical), 10 = lowest priority (optional)
    shutdownThreshold: Battery percentage at which this consumer should be shut down

    Optional Linkage:
    - sensor: Link to a Sensor to get live power consumption data (e.g., Shelly smart plug readings)
    - controllableAction: Link to a ControllableAction to enable automatic on/off control
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)
    consumptionWatts = models.FloatField(
        help_text="Default/fallback power consumption in watts. If sensor is linked, live data will be used."
    )
    priority = models.IntegerField(
        default=5,
        help_text="Priority level 1-10 (1=critical, 10=optional)"
    )
    shutdownThreshold = models.IntegerField(
        default=0,
        help_text="Battery percentage at which this consumer should be shut down (0 = never auto-shutdown, use global thresholds)"
    )
    dependencies = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='dependents',
        help_text="Other consumers that must be active for this consumer to operate"
    )
    isActive = models.BooleanField(default=True)
    FPF = models.ForeignKey(FPF, related_name='energy_consumers', on_delete=models.CASCADE)

    # Optional linkage to Sensor for live power consumption measurement
    sensor = models.ForeignKey(
        'Sensor',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='energy_consumers',
        help_text="Link to a sensor for live power consumption measurement (e.g., Shelly power reading)"
    )

    # Optional linkage to ControllableAction for automatic control
    controllableAction = models.ForeignKey(
        'ControllableAction',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='energy_consumers',
        help_text="Link to a controllable action for automatic on/off control"
    )

    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', 'name']

    def __str__(self):
        return f"{self.FPF.name}: {self.name} ({self.consumptionWatts}W, priority: {self.priority})"
