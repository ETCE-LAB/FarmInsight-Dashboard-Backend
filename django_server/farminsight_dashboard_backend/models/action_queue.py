import uuid
from django.db import models
from .controllable_action import ControllableAction
from .action_trigger import ActionTrigger


class ActionQueue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    createdAt = models.DateTimeField(auto_now_add=True, null=True)
    startedAt = models.DateTimeField(null=True)
    endedAt = models.DateTimeField(null=True)
    action = models.ForeignKey(ControllableAction, related_name='queueEntries', on_delete=models.CASCADE)
    trigger = models.ForeignKey(ActionTrigger, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.action.name}: {self.trigger.actionValue} {self.trigger.type} a: {self.createdAt} s: {self.startedAt} e:{self.endedAt}"
