
from farminsight_dashboard_backend.models import ActionTrigger


class BaseTriggerHandler:
    def __init__(self, trigger: ActionTrigger):
        self.trigger = trigger

    def should_trigger(self, *args, **kwargs):
        raise NotImplementedError("Must override should_trigger in subclass.")

    def enqueue_if_needed(self, *args, **kwargs):
        raise NotImplementedError("Must override enqueue in subclass.")


