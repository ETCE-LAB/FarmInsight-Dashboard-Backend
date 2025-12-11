import uuid
from django.db import models
from .fpf import FPF


class ResourceManagementModel(models.Model):
    MODEL_TYPES = [
        ('energy', 'Energy'),
        ('water', 'Water'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)
    URL = models.CharField(max_length=256)
    required_parameters = models.JSONField(default=list, blank=True)
    isActive = models.BooleanField(default=False)
    intervalSeconds = models.IntegerField()
    activeScenario = models.CharField(max_length=256, blank=True)
    availableScenarios = models.JSONField(default=list, blank=True)
    forecasts = models.JSONField(default=list, blank=True)
    model_type = models.CharField(max_length=64, choices=MODEL_TYPES, default='energy')
    FPF = models.ForeignKey(FPF, related_name='models', on_delete=models.CASCADE)

    def __str__(self):
        return f"name: {self.name} URL: {self.URL} isActive: {self.isActive} required_parameters: {self.required_parameters}"
