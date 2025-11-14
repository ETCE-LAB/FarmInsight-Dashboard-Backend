
from farminsight_dashboard_backend.models import ActionTrigger


class ForecastTriggerHandler:
    def __init__(self, trigger: ActionTrigger):
        self.trigger = trigger

    def should_trigger(self, *args, **kwargs):
        """
        Not implemented here as Forecast actions will be directly enqueued into the Forecast scheduler and will be triggered by it.
        :param args:
        :param kwargs:
        :return:
        """
        return False

    def enqueue_if_needed(self, *args, **kwargs):
        pass


