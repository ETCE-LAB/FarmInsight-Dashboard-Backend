from rest_framework import serializers

from django_server import settings
from farminsight_dashboard_backend.models import Camera, FPF
from farminsight_dashboard_backend.serializers.image_serializer import ImageURLSerializer


class CameraSerializer(serializers.ModelSerializer):

    class Meta:
        model = Camera
        fields = [
            'id',
            'name',
            'location',
            'modelNr',
            'resolution',
            'isActive',
            'intervalSeconds',
            'livestreamUrl',
            'snapshotUrl'
        ]

    def validate_intervalSeconds(self, value):
        if value <= 0:
            raise serializers.ValidationError("Interval must be a positive number.")
        return value

class CameraImageSerializer(serializers.ModelSerializer):
    images = ImageURLSerializer(many=True)

    class Meta:
        model = Camera
        fields = [
            'id',
            'name',
            'location',
            'modelNr',
            'resolution',
            'isActive',
            'intervalSeconds',
            'livestreamUrl',
            'snapshotUrl',
            'images'
        ]

