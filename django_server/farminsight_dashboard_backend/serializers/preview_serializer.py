from rest_framework import serializers

from django_server import settings
from farminsight_dashboard_backend.models import FPF, Image
from farminsight_dashboard_backend.serializers.sensor_serializer import PreviewSensorSerializer
from farminsight_dashboard_backend.serializers.organization_serializer import OrganizationSerializer


class FPFPreviewSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer()
    sensors = PreviewSensorSerializer(many=True)
    lastImageUrl = serializers.SerializerMethodField()

    class Meta:
        model = FPF
        fields = ['id', 'name', 'organization', 'lastImageUrl', 'sensors']

    def get_lastImageUrl(self, obj):
        newest_image: Image = None
        for camera in obj.cameras.all():
            try:
                image = camera.images.latest('measuredAt')
                if newest_image is None or newest_image.measuredAt < image.measuredAt:
                    newest_image = image
            except :
                pass
        return f"{settings.SITE_URL}{settings.MEDIA_URL}{newest_image.image.name}" if newest_image is not None else None