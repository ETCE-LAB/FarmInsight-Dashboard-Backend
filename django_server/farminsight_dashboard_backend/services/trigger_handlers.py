import json
from datetime import datetime

from django.utils.timezone import now
from requests.utils import requote_uri

from farminsight_dashboard_backend.models import ActionTrigger, ActionQueue


class BaseTriggerHandler:
    def __init__(self, trigger: ActionTrigger):
        self.trigger = trigger

    def should_trigger(self, *args, **kwargs):
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


class MeasurementTriggerHandler(BaseTriggerHandler):
    def should_trigger(self, measurement=0, **kwargs):
        """
        Triggers if measurement is in given range or above or below set threshold of trigger
        read measurement in influxDB
        :return:
        """
        try:
            logic = json.loads(self.trigger.triggerLogic)

            comparison = logic.get("comparison")

            if comparison == ">":
                value = logic.get("value")
                return measurement > value
            elif comparison == "<":
                value = logic.get("value")
                return measurement < value
            elif comparison == "between":
                min_measurement = logic.get("min")
                max_measurement = logic.get("max")
                return min_measurement <= measurement <= max_measurement
            else:
                print(f"[MeasurementTriggerHandler] Unknown comparison type: {comparison}")
                return False

        except Exception as e:
            print(f"[MeasurementTriggerHandler] Error parsing trigger logic: {e}")
            return False

class TriggerHandlerFactory:
    handlers = {
        "manual": ManualTriggerHandler,
        "timeOfDay": TimeOfDayTriggerHandler,
        "sensorValue": MeasurementTriggerHandler,
    }

    @staticmethod
    def get_handler(trigger: ActionTrigger) -> BaseTriggerHandler:
        handler_class = TriggerHandlerFactory.handlers.get(trigger.type)
        if not handler_class:
            raise NotImplementedError(f"No handler found for trigger type: {trigger.type}")
        return handler_class(trigger)
