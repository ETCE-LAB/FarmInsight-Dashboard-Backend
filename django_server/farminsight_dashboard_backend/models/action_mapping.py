from django.db import models

from farminsight_dashboard_backend.models import ResourceManagementModel, ControllableAction


class ActionMapping(models.Model):
    controllable_action = models.ForeignKey(ControllableAction, related_name="action_mappings", on_delete=models.CASCADE)
    action_name = models.CharField(max_length=100)
    resource_management_model = models.ForeignKey(ResourceManagementModel, related_name="action", on_delete=models.CASCADE)
