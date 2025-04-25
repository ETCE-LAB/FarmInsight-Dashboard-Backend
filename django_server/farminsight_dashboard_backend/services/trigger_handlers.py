import json
from datetime import datetime

from django.utils.timezone import now
from farminsight_dashboard_backend.models import ActionTrigger, ActionQueue


class BaseTriggerHandler:
    def __init__(self, trigger: ActionTrigger):
        self.trigger = trigger

    def should_trigger(self):
        raise NotImplementedError("Must override should_trigger in subclass.")


class ManualTriggerHandler(BaseTriggerHandler):
    def should_trigger(self):
        # Manual triggers are always ready when created
        return True


class TimeOfDayTriggerHandler(BaseTriggerHandler):
    def should_trigger(self):
        """

        :return:
        """
        try:
            logic = json.loads(self.trigger.triggerLogic)
            now = datetime.now().time()

            from_time = datetime.strptime(logic["from"], "%H:%M").time()
            to_time = datetime.strptime(logic["to"], "%H:%M").time()

            # Handle range that crosses midnight
            if from_time <= to_time:
                in_range = from_time <= now <= to_time
            else:
                # e.g., 23:00 to 03:00
                in_range = now >= from_time or now <= to_time

            return in_range

        except Exception as e:
            print(f"[TimeOfDayTriggerHandler] Error parsing trigger logic: {e}")
            return False


class TriggerHandlerFactory:
    handlers = {
        "manual": ManualTriggerHandler,
        "timeOfDay": TimeOfDayTriggerHandler,
        # future: "sensorValue": SensorValueTriggerHandler,
    }

    @staticmethod
    def get_handler(trigger: ActionTrigger) -> BaseTriggerHandler:
        handler_class = TriggerHandlerFactory.handlers.get(trigger.type)
        if not handler_class:
            raise NotImplementedError(f"No handler found for trigger type: {trigger.type}")
        return handler_class(trigger)
