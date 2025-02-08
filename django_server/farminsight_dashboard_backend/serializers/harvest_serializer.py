from rest_framework import serializers
from farminsight_dashboard_backend.models import Harvest, GrowingCycle


class HarvestSerializer(serializers.ModelSerializer):
    growingCycleId = serializers.PrimaryKeyRelatedField(
        source='growingCycle',
        queryset=GrowingCycle.objects.all()
    )

    class Meta:
        model = Harvest
        read_only_fields = ('id',)
        fields = ['id', 'date', 'amountInKg', 'note', 'growingCycleId']
