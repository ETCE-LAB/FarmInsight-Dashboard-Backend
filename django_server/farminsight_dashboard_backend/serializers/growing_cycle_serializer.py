from rest_framework import serializers
from farminsight_dashboard_backend.models import GrowingCycle, FPF


class GrowingCycleSerializer(serializers.ModelSerializer):
    fpfId = serializers.PrimaryKeyRelatedField(
        source='FPF',
        queryset=FPF.objects.all()
    )

    class Meta:
        model = GrowingCycle
        read_only_fields = ('id',)
        fields = ['id', 'startDate', 'endDate', 'plants', 'note', 'fpfId']

    def validate(self, data):
        start_date = data.get('startDate')
        end_date = data.get('endDate')
        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError("Start date must be earlier than end date.")
        return data
