from rest_framework import serializers
from farminsight_dashboard_backend.models import FPF, Organization
from farminsight_dashboard_backend.serializers.camera_serializer import CameraImageSerializer, CameraSerializer
from farminsight_dashboard_backend.serializers.growing_cycle_serializer import GrowingCycleSerializer
from farminsight_dashboard_backend.serializers.sensor_serializer import SensorDataSerializer, SensorLastValueSerializer


class FPFSerializer(serializers.ModelSerializer):
    organizationId = serializers.PrimaryKeyRelatedField(
        source='organization',  # Maps this field to the 'organization' foreign key in the model
        queryset=Organization.objects.all()
    )

    class Meta:
        model = FPF
        read_only_fields = ('id',)
        fields = ('id', 'name', 'isPublic', 'sensorServiceIp', 'address', 'organizationId')

    def validate(self, data):
        fpfs = FPF.objects.filter(name=data['name'], organization=data['organization'])
        if len(fpfs) > 0:
            raise serializers.ValidationError({"name":"This name is already taken for this organization"})
        return data

class FPFFunctionalSerializer(serializers.ModelSerializer):

    class Meta:
        model = FPF
        read_only_fields = ('id',)
        fields = ('id', 'name', 'isPublic', 'sensorServiceIp', 'address')

class FPFTechnicalKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = FPF
        fields = ['id', 'name', 'isPublic']


class FPFFullSerializer(serializers.ModelSerializer):
    Sensors = SensorLastValueSerializer(many=True, source='sensors')
    Cameras = CameraSerializer(many=True, source='cameras')
    GrowingCycles = GrowingCycleSerializer(many=True, source='growingCycles')

    class Meta:
        model = FPF
        fields = [
            'id',
            'name',
            'isPublic',
            'sensorServiceIp',
            'address',
            'Sensors',
            'Cameras',
            'GrowingCycles',
        ]
        
class FPFFullDataSerializer(serializers.ModelSerializer):
    Sensors = SensorDataSerializer(many=True, source='sensors')
    Cameras = CameraImageSerializer(many=True, source='cameras')
    GrowingCycles = GrowingCycleSerializer(many=True, source='growingCycles')

    class Meta:
        model = FPF
        fields = [
            'id',
            'name',
            'isPublic',
            'sensorServiceIp',
            'address',
            'Sensors',
            'Cameras',
            'GrowingCycles',
        ]
