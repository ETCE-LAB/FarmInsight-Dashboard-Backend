import uuid
from enum import Enum

from django.db import models
from .controllable_action import ControllableAction


class ActionTrigger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=32)
    actionValueType = models.CharField(max_length=64)
    actionValue = models.CharField(max_length=128)
    triggerLogic = models.TextField()
    isActive = models.BooleanField(default=False)
    action = models.ForeignKey(ControllableAction, related_name='triggers', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.action.name}: {self.type} {self.valueType} {self.value} active: {self.isActive}"


class ActionValueType(Enum):
    BOOLEAN = 'boolean'
    STRING = 'string'
    INT = 'integer'
    FLOAT = 'float'
    RANGE = 'range'


class ActionTriggerType(Enum):
    MANUAL = 'manual'
    SINGLE_SENSOR_VALUE = 'sensorValue'
    TIME_OF_DAY = 'timeOfDay'
