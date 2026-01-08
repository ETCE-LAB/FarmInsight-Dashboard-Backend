import uuid
from django.db import models
from .fpf import FPF
from django.db.models import Max

def get_order_index_default():
    if ResourceManagementModel.objects.all().count() == 0:
        new_order_default = 0
    else:
        new_order_default = ResourceManagementModel.objects.all().aggregate(Max('orderIndex'))['orderIndex__max'] + 1
    return new_order_default


class ResourceManagementModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)
    URL = models.CharField(max_length=256)
    model_type = models.CharField(max_length=50, default='water', blank=True)
    required_parameters = models.JSONField(default=list, blank=True)
    isActive = models.BooleanField(default=False)
    intervalSeconds = models.IntegerField()
    activeScenario = models.CharField(max_length=256, blank=True)
    availableScenarios = models.JSONField(default=list, blank=True)
    forecasts = models.JSONField(default=list, blank=True)
    FPF = models.ForeignKey(FPF, related_name='models', on_delete=models.CASCADE)
    orderIndex = models.IntegerField(default=get_order_index_default)

    class Meta:
        ordering = ['orderIndex']

    def __str__(self):
        return f"name: {self.name} URL: {self.URL} isActive: {self.isActive} required_parameters: {self.required_parameters}"
