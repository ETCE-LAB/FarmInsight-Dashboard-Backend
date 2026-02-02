import uuid
from django.db import models
from .fpf import FPF


class EnergySource(models.Model):
    """
    Represents an energy source within an FPF (e.g., solar panels, wind turbines, grid connection).

    Optional Linkage:
    - sensor: Link to a Sensor to get live power output data (e.g., solar inverter readings)
    - controllableAction: Link to a ControllableAction for control (e.g., grid connection switch)
    """
    SOURCE_TYPES = [
        ('solar', 'Solar'),
        ('wind', 'Wind'),
        ('grid', 'Grid'),
        ('battery', 'Battery'),
        ('generator', 'Generator'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)
    sourceType = models.CharField(max_length=64, choices=SOURCE_TYPES)
    maxOutputWatts = models.FloatField(help_text="Maximum power output in watts")
    currentOutputWatts = models.FloatField(
        default=0,
        help_text="Default/fallback current power output. If sensor is linked, live data will be used."
    )
    weatherDependent = models.BooleanField(
        default=False,
        help_text="Whether the output depends on weather conditions (e.g., solar, wind)"
    )
    isActive = models.BooleanField(default=True)
    FPF = models.ForeignKey(FPF, related_name='energy_sources', on_delete=models.CASCADE)

    # Optional linkage to Sensor for live power output measurement
    sensor = models.ForeignKey(
        'Sensor',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='energy_sources',
        help_text="Link to a sensor for live power output measurement (e.g., solar inverter)"
    )

    # Optional linkage to ControllableAction for control (e.g., grid connection switch)
    controllableAction = models.ForeignKey(
        'ControllableAction',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='energy_sources',
        help_text="Link to a controllable action for source control (e.g., grid connection switch)"
    )

    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sourceType', 'name']

    def __str__(self):
        return f"{self.FPF.name}: {self.name} ({self.sourceType}, max: {self.maxOutputWatts}W)"
