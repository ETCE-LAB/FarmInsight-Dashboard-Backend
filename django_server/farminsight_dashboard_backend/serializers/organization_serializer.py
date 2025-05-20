from rest_framework import serializers
from farminsight_dashboard_backend.models import Organization, Membership
from .fpf_serializer import FPFTechnicalKeySerializer
from .location_serializer import LocationSerializer
from .membership_serializer import MembershipSerializerIncUserprofile


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        read_only_fields = ('id',)
        fields = ('id', 'name', 'isPublic')


class OrganizationFullSerializer(serializers.ModelSerializer):
    memberships = MembershipSerializerIncUserprofile(many=True, read_only=True, source='membership_set')
    FPFs = FPFTechnicalKeySerializer(many=True, read_only=True, source='fpf_set')
    locations = LocationSerializer(many=True, read_only=True, source='location_set')

    class Meta:
        model = Organization
        fields = ['id', 'name', 'isPublic', 'memberships', 'FPFs', 'locations']