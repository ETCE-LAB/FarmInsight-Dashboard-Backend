from rest_framework import serializers
from farminsight_dashboard_backend.models import EnergyConsumer, Sensor, ControllableAction


class EnergyConsumerSerializer(serializers.ModelSerializer):
    dependencyIds = serializers.PrimaryKeyRelatedField(
        source='dependencies',
        many=True,
        queryset=EnergyConsumer.objects.all(),
        required=False
    )
    sensorId = serializers.PrimaryKeyRelatedField(
        source='sensor',
        queryset=Sensor.objects.all(),
        required=False,
        allow_null=True
    )
    controllableActionId = serializers.PrimaryKeyRelatedField(
        source='controllableAction',
        queryset=ControllableAction.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = EnergyConsumer
        fields = [
            'id',
            'name',
            'consumptionWatts',
            'priority',
            'shutdownThreshold',
            'forecastShutdownThreshold',
            'forecastBufferDays',
            'dependencyIds',
            'sensorId',
            'controllableActionId',
            'isActive',
            'createdAt',
            'updatedAt',
        ]
        read_only_fields = ['id', 'createdAt', 'updatedAt']


class EnergyConsumerDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer including full dependency information and linked sensor/action
    """
    dependencyIds = serializers.SerializerMethodField()
    dependencies = serializers.SerializerMethodField()
    sensorId = serializers.SerializerMethodField()
    sensor = serializers.SerializerMethodField()
    controllableActionId = serializers.SerializerMethodField()
    controllableAction = serializers.SerializerMethodField()

    class Meta:
        model = EnergyConsumer
        fields = [
            'id',
            'name',
            'consumptionWatts',
            'priority',
            'shutdownThreshold',
            'forecastShutdownThreshold',
            'forecastBufferDays',
            'dependencyIds',
            'dependencies',
            'sensorId',
            'sensor',
            'controllableActionId',
            'controllableAction',
            'isActive',
            'createdAt',
            'updatedAt',
        ]
        read_only_fields = ['id', 'createdAt', 'updatedAt']

    def get_dependencyIds(self, obj):
        return [str(dep.id) for dep in obj.dependencies.all()]

    def get_dependencies(self, obj):
        return [{
            'id': str(dep.id),
            'name': dep.name,
            'consumptionWatts': dep.consumptionWatts,
            'priority': dep.priority,
            'shutdownThreshold': dep.shutdownThreshold,
            'forecastShutdownThreshold': dep.forecastShutdownThreshold,
            'forecastBufferDays': dep.forecastBufferDays,
            'isActive': dep.isActive
        } for dep in obj.dependencies.all()]

    def get_sensorId(self, obj):
        return str(obj.sensor.id) if obj.sensor else None

    def get_sensor(self, obj):
        if obj.sensor:
            return {
                'id': str(obj.sensor.id),
                'name': obj.sensor.name,
                'unit': obj.sensor.unit,
                'parameter': obj.sensor.parameter,
                'isActive': obj.sensor.isActive
            }
        return None

    def get_controllableActionId(self, obj):
        return str(obj.controllableAction.id) if obj.controllableAction else None

    def get_controllableAction(self, obj):
        if obj.controllableAction:
            return {
                'id': str(obj.controllableAction.id),
                'name': obj.controllableAction.name,
                'isActive': obj.controllableAction.isActive,
                'isAutomated': obj.controllableAction.isAutomated
            }
        return None
