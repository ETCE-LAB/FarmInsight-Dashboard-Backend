from rest_framework import serializers
from farminsight_dashboard_backend.models import LogMessage


class LogMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogMessage
        fields = ['id', 'createdAt', 'relatedResourceId', 'logLevel', 'message']