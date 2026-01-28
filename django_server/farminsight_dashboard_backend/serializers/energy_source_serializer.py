from rest_framework import serializers
from farminsight_dashboard_backend.models import EnergySource, Sensor, ControllableAction


class EnergySourceSerializer(serializers.ModelSerializer):
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
        model = EnergySource
        fields = [
            'id',
            'name',
            'sourceType',
            'maxOutputWatts',
            'currentOutputWatts',
            'weatherDependent',
            'sensorId',
            'controllableActionId',
            'isActive',
            'createdAt',
            'updatedAt',
        ]
        read_only_fields = ['id', 'createdAt', 'updatedAt']


class EnergySourceDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer including linked sensor/action information
    """
    sensorId = serializers.SerializerMethodField()
    sensor = serializers.SerializerMethodField()
    controllableActionId = serializers.SerializerMethodField()
    controllableAction = serializers.SerializerMethodField()

    class Meta:
        model = EnergySource
        fields = [
            'id',
            'name',
            'sourceType',
            'maxOutputWatts',
            'currentOutputWatts',
            'weatherDependent',
            'sensorId',
            'sensor',
            'controllableActionId',
            'controllableAction',
            'isActive',
            'createdAt',
            'updatedAt',
        ]
        read_only_fields = ['id', 'createdAt', 'updatedAt']

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


class EnergySourceSummarySerializer(serializers.ModelSerializer):
    """
    Summary serializer for list views
    """
    class Meta:
        model = EnergySource
        fields = [
            'id',
            'name',
            'sourceType',
            'maxOutputWatts',
            'currentOutputWatts',
            'isActive',
        ]
