from rest_framework import serializers
from farminsight_dashboard_backend.models import ActionTrigger, ControllableAction


class ActionTriggerSerializer(serializers.ModelSerializer):
    actionId = serializers.PrimaryKeyRelatedField(
        source='action',
        queryset=ControllableAction.objects.all()
    )

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
                  'actionId'
                  ]

class ActionTriggerTechnicalKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionTrigger
        fields = ['description', 'actionValueType', 'actionValue']
