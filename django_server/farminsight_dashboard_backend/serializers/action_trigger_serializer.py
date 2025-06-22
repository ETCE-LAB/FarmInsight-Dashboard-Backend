from rest_framework import serializers
from farminsight_dashboard_backend.models import ActionTrigger, ControllableAction, ActionQueue


class ActionTriggerSerializer(serializers.ModelSerializer):
    actionId = serializers.PrimaryKeyRelatedField(
        source='action',
        queryset=ControllableAction.objects.all()
    )
    lastTriggered = serializers.SerializerMethodField()

    class Meta:
        model = ActionTrigger
        read_only_fields = ['id',
                            'actionId'
                            ]
        fields = ['id',
                  'type',
                  'actionValueType',
                  'actionValue',
                  'triggerLogic',
                  'isActive',
                  'description',
                  'actionId',
                  'lastTriggered'
                  ]

    def get_lastTriggered(self, obj):
        latest_entry = ActionQueue.objects.filter(
            trigger__id=obj.id
        ).order_by('-createdAt').first()

        if latest_entry:
            return latest_entry.createdAt

        return None


class ActionTriggerTechnicalKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionTrigger
        fields = ['description', 'actionValueType', 'actionValue']
