from rest_framework import serializers
from farminsight_dashboard_backend.models import FPF, Organization, Location
from .custom_serializer import CustomSerializer
from .hardware_serializer import HardwareSerializer
from .controllable_action_serializer import ControllableActionSerializer
from .camera_serializer import CameraImageSerializer, CameraSerializer
from .growing_cycle_serializer import GrowingCycleSerializer
from .sensor_serializer import SensorDataSerializer, SensorLastValueSerializer
from .location_serializer import LocationSerializer
from .resource_management_model_serializer import ResourceManagementModelSerializer, ResourceManagementModelDataSerializer


class FPFSerializer(CustomSerializer):
    organizationId = serializers.PrimaryKeyRelatedField(
        source='organization',  # Maps this field to the 'organization' foreign key in the model
        queryset=Organization.objects.all()
    )
    locationId = serializers.PrimaryKeyRelatedField(
        source='location',  # Maps this field to the 'location' foreign key in the model
        queryset=Location.objects.all(),
        allow_null=True,
    )

    class Meta:
        model = FPF
        read_only_fields = ('id',)
        fields = ('id', 'name', 'isPublic', 'sensorServiceIp', 'organizationId', 'locationId', 'isActive')

    def validate_sensorServiceIp(self, value):
        '''
        this does not accept localhost:8001, add http:// or use 127.0.0.1:8001 for development purposes
        '''
        from urllib.parse import urlparse

        parsed = urlparse(value)
        if parsed.netloc:
            return value

        import ipaddress

        try:
            ipaddress.ip_address(value)
            return value
        except ValueError as e:
            if ':' in value:
                try:
                    ip, port = value.split(':')
                    ipaddress.ip_address(ip)
                    int(port)
                    return value
                except:
                    pass

        raise serializers.ValidationError('Not a valid IP address or URL')

    def validate(self, data):
        if 'organization' in data: # this depends on if there were other errors before
            fpfs = FPF.objects.filter(name=data['name'], organization=data['organization'])
        else:
            fpfs = FPF.objects.filter(name=data['name'], organization_id=data['organizationId'])

        if len(fpfs) > 0:
            raise serializers.ValidationError({"name": "This name is already taken for this organization"})
        return data


class FPFFunctionalSerializer(serializers.ModelSerializer):
    locationId = serializers.PrimaryKeyRelatedField(
        source='location',  # Maps to the `location` field in the model
        queryset=Location.objects.all()  # Adjust the queryset as needed
    )
    class Meta:
        model = FPF
        read_only_fields = ('id',)
        fields = ('id', 'name', 'isPublic', 'sensorServiceIp', 'locationId', 'orderIndex', 'isActive')


class FPFTechnicalKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = FPF
        fields = ['id', 'name', 'isPublic']


class FPFFullSerializer(serializers.ModelSerializer):
    Sensors = SensorLastValueSerializer(many=True, source='sensors')
    Models = ResourceManagementModelSerializer(many=True, source='models')
    Cameras = CameraSerializer(many=True, source='cameras')
    GrowingCycles = GrowingCycleSerializer(many=True, source='growingCycles')
    Location = LocationSerializer(many=False, source='location')
    ControllableAction = ControllableActionSerializer(many=True, source='actions')
    Hardware = HardwareSerializer(many=True, source='hardware')

    class Meta:
        model = FPF
        fields = [
            'id',
            'name',
            'isPublic',
            'sensorServiceIp',
            'Sensors',
            'Models',
            'Cameras',
            'GrowingCycles',
            'Location',
            'ControllableAction',
            'orderIndex',
            'Hardware',
            'isActive'
        ]


class FPFFullDataSerializer(serializers.ModelSerializer):
    Sensors = SensorDataSerializer(many=True, source='sensors')
    Models = ResourceManagementModelDataSerializer(many=True, source='models')
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
            'Models',
            'Cameras',
            'GrowingCycles',
        ]
