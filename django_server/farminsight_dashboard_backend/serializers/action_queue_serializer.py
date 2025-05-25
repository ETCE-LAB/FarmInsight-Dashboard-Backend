from rest_framework import serializers
from farminsight_dashboard_backend.models import ActionQueue, ActionTrigger, ControllableAction
from .action_trigger_serializer import ActionTriggerTechnicalKeySerializer
from .controllable_action_serializer import ControllableActionTechnicalKeySerializer


class ActionQueueSerializer(serializers.ModelSerializer):
    actionId = serializers.PrimaryKeyRelatedField(
        source='action',
        queryset=ControllableAction.objects.all()
    )

    actionTriggerId = serializers.PrimaryKeyRelatedField(
        source='trigger',
        queryset=ActionTrigger.objects.all()
    )

    class Meta:
        model = ActionQueue
        read_only_fields = ['id', 'createdAt', 'actionId', 'actionTriggerId']
        fields = ['id', 'createdAt', 'startedAt', 'endedAt', 'value', 'actionId', 'actionTriggerId']


# This serializer contains more of the data from trigger and action to show in the frontend
class ActionQueueSerializerDescriptive(serializers.ModelSerializer):
    controllableAction = ControllableActionTechnicalKeySerializer(source='action')
    trigger = ActionTriggerTechnicalKeySerializer(source='trigger')

    class Meta:
        model = ActionQueue
        fields = '__all__'