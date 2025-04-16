from rest_framework import serializers
from farminsight_dashboard_backend.models import FPF, Organization, Location
from farminsight_dashboard_backend.models import FPF, Organization
from farminsight_dashboard_backend.serializers.controllable_action_serializer import ControllableActionSerializer
from farminsight_dashboard_backend.serializers.camera_serializer import CameraImageSerializer, CameraSerializer
from farminsight_dashboard_backend.serializers.growing_cycle_serializer import GrowingCycleSerializer
from farminsight_dashboard_backend.serializers.sensor_serializer import SensorDataSerializer, SensorLastValueSerializer
from farminsight_dashboard_backend.serializers.location_serializer import LocationSerializer



class FPFSerializer(serializers.ModelSerializer):
    organizationId = serializers.PrimaryKeyRelatedField(
        source='organization',  # Maps this field to the 'organization' foreign key in the model
        queryset=Organization.objects.all()
    )
    locationId = serializers.PrimaryKeyRelatedField(
        source='location',  # Maps this field to the 'location' foreign key in the model
        queryset=Location.objects.all()
    )

    class Meta:
        model = FPF
        read_only_fields = ('id',)
        fields = ('id', 'name', 'isPublic', 'sensorServiceIp', 'organizationId', 'locationId')

    def validate(self, data):
        fpfs = FPF.objects.filter(name=data['name'], organization=data['organization'])
        if len(fpfs) > 0:
            raise serializers.ValidationError({"name":"This name is already taken for this organization"})
        return data

class FPFFunctionalSerializer(serializers.ModelSerializer):
    locationId = serializers.PrimaryKeyRelatedField(
        source='location',  # Maps to the `location` field in the model
        queryset=Location.objects.all()  # Adjust the queryset as needed
    )
    class Meta:
        model = FPF
        read_only_fields = ('id',)
        fields = ('id', 'name', 'isPublic', 'sensorServiceIp', 'locationId')

class FPFTechnicalKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = FPF
        fields = ['id', 'name', 'isPublic']


class FPFFullSerializer(serializers.ModelSerializer):
    Sensors = SensorLastValueSerializer(many=True, source='sensors')
    Cameras = CameraSerializer(many=True, source='cameras')
    GrowingCycles = GrowingCycleSerializer(many=True, source='growingCycles')
    Location = LocationSerializer(many=False, source='location')
    ControllableAction = ControllableActionSerializer(many=True, source='actions')

    class Meta:
        model = FPF
        fields = [
            'id',
            'name',
            'isPublic',
            'sensorServiceIp',
            'Sensors',
            'Cameras',
            'GrowingCycles',
            'Location',
            'ControllableAction'
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
            'Sensors',
            'Cameras',
            'GrowingCycles',
        ]
