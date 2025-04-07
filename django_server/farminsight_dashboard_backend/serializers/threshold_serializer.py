from rest_framework import serializers
from farminsight_dashboard_backend.models import Threshold, Sensor


class ThresholdSerializer(serializers.ModelSerializer):
    sensorId = serializers.PrimaryKeyRelatedField(
        source='sensor',
        queryset=Sensor.objects.all()
    )

    class Meta:
        model = Threshold
        read_only_fields = ('id',)
        fields = ['id', 'lowerBound', 'upperBound', 'color', 'description', 'sensorId']

    def validate(self, data):
        lower_bound = data.get('lowerBound')
        upper_bound = data.get('upperBound')

        if lower_bound is None and upper_bound is None:
            raise serializers.ValidationError({"lowerBound": "At least one bound has to be set.",
                                               "upperBound": "At least one bound has to be set."})

        if lower_bound is not None and upper_bound is not None:
            if lower_bound > upper_bound:
                raise serializers.ValidationError({"lowerBound": "Lower bound has to be less than upper bound.",})

        return data