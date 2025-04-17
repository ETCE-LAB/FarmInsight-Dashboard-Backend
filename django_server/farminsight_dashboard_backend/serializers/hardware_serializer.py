from rest_framework import serializers
from farminsight_dashboard_backend.models import Hardware


class HardwareSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hardware
        read_only_fields = ('id',)
        fields = '__all__'
