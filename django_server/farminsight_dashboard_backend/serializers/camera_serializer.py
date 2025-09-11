from rest_framework import serializers

from farminsight_dashboard_backend.models import Camera, Image
from farminsight_dashboard_backend.serializers.image_serializer import ImageURLSerializer


class CameraSerializer(serializers.ModelSerializer):
    lastImageAt = serializers.SerializerMethodField()

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
            'orderIndex',
            'lastImageAt',
        ]

    def get_lastImageAt(self, obj: Camera):
        last_image = Image.objects.filter(camera_id=obj.id).order_by('-measuredAt').first()
        if last_image:
            return last_image.measuredAt

        return None

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
            'images',
            'orderIndex'
        ]


class CameraDBSchemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Camera
        fields = '__all__'