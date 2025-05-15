import json


from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.serializers import ActionQueueSerializer
from farminsight_dashboard_backend.services.trigger.base_trigger_handlers import BaseTriggerHandler

logger = get_logger()

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
                logger.debug(f"[MeasurementTriggerHandler] Unknown comparison type: {comparison}")
                return False

        except Exception as e:
            print(f"[MeasurementTriggerHandler] Error parsing trigger logic: {e}")
            return False

    def enqueue_if_needed(self):
        pass

def create_measurement_auto_triggered_actions_in_queue(sensor_id, measurement_value):
    """
    Creates an entry for the measurement auto trigger.
    :param measurement_value:
    :param sensor_id:
    :return:
    """
    from farminsight_dashboard_backend.services.action_queue_services import is_new_action, process_action_queue, is_already_enqueued
    from farminsight_dashboard_backend.services.action_trigger_services import get_action_trigger
    from farminsight_dashboard_backend.services.trigger.trigger_handler_factory import TriggerHandlerFactory
    from farminsight_dashboard_backend.services.trigger.MeasurementTriggerManager import MeasurementTriggerManager

    trigger_ids = MeasurementTriggerManager.get_trigger_ids_for_sensor(sensor_id)

    if len(trigger_ids) >= 0:
        for trigger_id in trigger_ids:
            trigger = get_action_trigger(str(trigger_id))
            # Trigger type logic to check for triggering && currently active trigger for the action must not be this trigger.
            handler = TriggerHandlerFactory.get_handler(trigger)
            if trigger.action.isAutomated and handler.should_trigger(measurement=measurement_value):
                if is_new_action(trigger.action.id, trigger.id) and not is_already_enqueued(trigger_id):
                    serializer = ActionQueueSerializer(data={
                        "actionId": str(trigger.action.id),
                        "actionTriggerId": str(trigger.id),
                        "value": str(measurement_value)
                    }, partial=True)
                    if serializer.is_valid(raise_exception=True):
                        serializer.save()
                        logger.info(f"Queued auto sensor measurement trigger {trigger.id} for action {trigger.action.id}", extra={'resource_id': trigger.action.FPF_id})

        process_action_queue()

