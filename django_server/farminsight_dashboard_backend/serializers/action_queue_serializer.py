from rest_framework import serializers
from farminsight_dashboard_backend.models import ActionQueue, ActionTrigger, ControllableAction


class ActionQueueSerializer(serializers.ModelSerializer):
    actionId = serializers.PrimaryKeyRelatedField(
        source='action',
        queryset=ControllableAction.objects.all()
    )

    actionTriggerId = serializers.PrimaryKeyRelatedField(
        source='actionTrigger',
        queryset=ActionTrigger.objects.all()
    )

    class Meta:
        model = ActionQueue
        read_only_fields = ['id', 'createdAt', 'actionId', 'actionTriggerId']
        fields = ['id', 'createdAt', 'startedAt', 'endedAt', 'actionId', 'actionTriggerId']
