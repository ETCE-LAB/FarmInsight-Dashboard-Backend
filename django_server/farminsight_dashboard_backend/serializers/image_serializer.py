from rest_framework import serializers
from django.conf import settings

from farminsight_dashboard_backend.models import Image


class ImageURLSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = [
            'url',
            'measuredAt',
        ]

    def get_url(self, obj):
        return f"{settings.SITE_URL}{settings.MEDIA_URL}{obj.image.name}"