from rest_framework import serializers

from farminsight_dashboard_backend.models import ResourceManagementModel, ActionMapping, FPF, ControllableAction


class ActionMappingSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="action_name")
    controllable_action_id = serializers.UUIDField(source="controllable_action.id")

    class Meta:
        model = ActionMapping
        fields = ["name", "controllable_action_id"]


class ResourceManagementModelSerializer(serializers.ModelSerializer):
    actions = ActionMappingSerializer(source="action", many=True, read_only=True)

    class Meta:
        model = ResourceManagementModel
        fields = [
            "id",
            "name",
            "URL",
            "required_parameters",
            "isActive",
            "intervalSeconds",
            "activeScenario",
            "availableScenarios",
            "forecasts",
            "actions",
        ]