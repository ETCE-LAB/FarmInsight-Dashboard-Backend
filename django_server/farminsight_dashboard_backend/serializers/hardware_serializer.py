from rest_framework import serializers
from farminsight_dashboard_backend.models import Hardware, ControllableAction


class HardwareSerializer(serializers.ModelSerializer):
    canBeDeleted = serializers.SerializerMethodField(method_name='can_be_deleted')

    class Meta:
        model = Hardware
        read_only_fields = ('id',)
        fields = '__all__'

    def can_be_deleted(self, obj):
        return ControllableAction.objects.filter(hardware=obj).count() == 0