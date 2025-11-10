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

class ResourceManagementModelDataSerializer(serializers.ModelSerializer):
    actions = ActionMappingSerializer(source="action", many=True, read_only=True)
    latest_forecast = serializers.SerializerMethodField()

    class Meta:
        model = ResourceManagementModel
        fields = [
            "id",
            "name",
            "forecasts",
            "actions",
            "latest_forecast",
        ]

    def get_latest_forecast(self, obj):
        """
        Fetch the latest forecast for this model from InfluxDB.
        Only if forecasts exist for the model.
        """
        from farminsight_dashboard_backend.services.influx_services import InfluxDBManager
        if not obj.forecasts:
            return None

        influx = InfluxDBManager.get_instance()
        try:
            # FPF is a ForeignKey on the model
            return influx.fetch_latest_model_forecast(
                fpf_id=str(obj.FPF.id),
                model_id=str(obj.id)
            )
        except Exception as e:
            # Log but don't break serialization
            import logging
            logging.getLogger("farminsight_dashboard_backend").warning(
                f"Could not fetch forecast for model {obj.id}: {e}"
            )
            return None