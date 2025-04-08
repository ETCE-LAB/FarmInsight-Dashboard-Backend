from rest_framework import serializers
from farminsight_dashboard_backend.models import ControllableAction, Sensor, Hardware


class ControllableActionSerializer(serializers.ModelSerializer):
    sensorId = serializers.PrimaryKeyRelatedField(
        source='sensor',
        queryset=Sensor.objects.all()
    )

    hardwareId = serializers.PrimaryKeyRelatedField(
        source='hardware',
        queryset=Hardware.objects.all()
    )


    class Meta:
        model = ControllableAction
        fields = ['id', 'name', 'actionClassId', 'isActive', 'isAutomated', 'maximumDurationSeconds', 'additionalInformation', 'sensorId', 'hardwareId']
