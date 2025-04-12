from rest_framework import serializers
from farminsight_dashboard_backend.models import Location, Organization


class LocationSerializer(serializers.ModelSerializer):
    organizationId = serializers.PrimaryKeyRelatedField(
        source='organization',
        queryset=Organization.objects.all()
    )

    class Meta:
        model = Location
        read_only_fields = ('id',)
        fields = [
            'id',
            'name',
            'isPublic',
            'organizationId',
            'latitude',
            'longitude',
            'city',
            'street',
            'houseNumber',
            'gatherForecasts'
        ]
